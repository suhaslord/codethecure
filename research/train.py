"""Train once, calibrate on validation, evaluate the fixed protocol on test."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import random

import numpy as np
import torch
from torch import nn

from research.core import (ROOT, DATA, MD5, URL, SEED, STRESSES, REVIEW_POLICY,
                           UltrasoundCNN, load_data, tensor, probabilities,
                           measurements, review_measurements, stress)


def main(epochs: int) -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    # CPU makes the experiment reproducible without a CUDA-specific environment.
    model = UltrasoundCNN()
    data = load_data()
    x, y = tensor(data["train_images"]), torch.from_numpy(data["train_labels"].reshape(-1)).long()
    vx, vy = tensor(data["val_images"]), torch.from_numpy(data["val_labels"].reshape(-1)).long()
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001, weight_decay=0.01)
    criterion = nn.CrossEntropyLoss()
    best_loss, best_epoch, best_state, history = float("inf"), 0, None, []
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(x))
        for ids in order.split(32):
            optimizer.zero_grad()
            loss = criterion(model(x[ids]), y[ids])
            loss.backward()
            optimizer.step()
        model.eval()
        with torch.inference_mode():
            val_loss = criterion(model(vx), vy).item()
        history.append({"epoch": epoch, "validation_nll": val_loss})
        if val_loss < best_loss:
            best_loss, best_epoch, best_state = val_loss, epoch, deepcopy(model.state_dict())
        if epoch % 10 == 0:
            print(f"Epoch {epoch}/{epochs}: validation NLL {val_loss:.4f}", flush=True)
    model.load_state_dict(best_state)
    model.eval()

    def infer(images: np.ndarray) -> np.ndarray:
        with torch.inference_mode():
            return np.concatenate([model(chunk).numpy() for chunk in tensor(images).split(64)])

    val_logits = infer(data["val_images"])
    val_labels = data["val_labels"].reshape(-1)
    grid = np.linspace(0.5, 4, 141)
    losses = [-np.log(probabilities(val_logits, t)[np.arange(len(vy)), val_labels]).mean() for t in grid]
    temperature = float(grid[int(np.argmin(losses))])
    output = ROOT / "artifacts"
    output.mkdir(exist_ok=True)
    checkpoint = output / "model.pt"
    torch.save({"state_dict": best_state, "temperature": temperature, "epoch": best_epoch}, checkpoint)
    clean_logits = infer(data["test_images"])
    clean = probabilities(clean_logits, temperature)
    test_labels = data["test_labels"].reshape(-1)
    conditions = []
    for name in STRESSES:
        for severity in (1, 2, 3):
            images = np.array([stress(image, name, severity, SEED + i) for i, image in enumerate(data["test_images"])])
            probability = probabilities(infer(images), temperature)
            conditions.append({"stress": name, "severity": severity,
                               "metrics": measurements(probability, test_labels),
                               "review": review_measurements(clean, probability, test_labels)})
    report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
              "seed": SEED, "dataset": {"name": "BreastMNIST", "resolution": 64,
                  "source": URL, "license": "CC BY 4.0", "md5": MD5,
                  "splits": {s: len(data[f"{s}_images"]) for s in ("train", "val", "test")},
                  "test_class_counts": {"malignant": int((test_labels == 0).sum()), "normal_benign": int((test_labels == 1).sum())}},
              "model": {"architecture": "3-convolution CNN", "parameters": sum(p.numel() for p in model.parameters()),
                        "selected_epoch": best_epoch, "epochs": epochs, "temperature": temperature,
                        "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                        "optimizer": "AdamW", "learning_rate": 0.001, "weight_decay": 0.01,
                        "batch_size": 32, "torch_version": torch.__version__},
              "review_policy": REVIEW_POLICY,
              "clean_raw": measurements(probabilities(clean_logits), test_labels),
              "clean": measurements(clean, test_labels),
              "clean_review": review_measurements(clean, clean, test_labels),
              "conditions": conditions, "training_history": history,
              "limitations": ["Single small benchmark; no external validation or verified patient-level split.",
                  "Synthetic pixel perturbations are not validated acquisition physics; labels may cease to be meaningful under severe corruption.",
                  "Softmax confidence and entropy do not quantify clinical uncertainty.",
                  "Temperature and checkpoint are selected on the same 78-image validation split; calibration may overfit.",
                  "Fixed 80% / 15 pp review thresholds are demonstration policy, not clinically optimized.",
                  "Repeated conditions share the same 156 images; do not pool as independent patients.",
                  "Wilson intervals describe binomial image-level sampling only; they do not account for patient clustering or model-training variability.",
                  "One training seed; no claim of novelty over existing corruption benchmarks or clinical readiness."]}
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    from research.evaluate import main as evaluate
    evaluate()
    print(json.dumps({"best_epoch": best_epoch, "temperature": temperature, "test_accuracy": report["clean"]["accuracy"], "test_auc": report["clean"]["auc"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=60)
    args = parser.parse_args()
    if not 1 <= args.epochs <= 500:
        parser.error("epochs must be between 1 and 500")
    main(args.epochs)
