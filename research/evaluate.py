"""Recompute all test measurements from the saved checkpoint without retraining."""
import json
import hashlib

import numpy as np
import torch

from research.core import (ROOT, SEED, STRESSES, UltrasoundCNN, load_data, tensor,
                           probabilities, measurements, review_measurements, stress)
from research.thresholds import build_study


def main() -> None:
    torch.set_num_threads(2)
    checkpoint_path = ROOT / "artifacts" / "model.pt"
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    report_path = ROOT / "artifacts" / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() != report["model"]["sha256"]:
        raise ValueError("Model/report mismatch; retrain to regenerate both artifacts.")
    data = load_data()
    model = UltrasoundCNN()
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()

    def infer(images):
        with torch.inference_mode():
            return np.concatenate([model(chunk).numpy() for chunk in tensor(images).split(64)])

    def cohort(split):
        images, labels = data[f"{split}_images"], data[f"{split}_labels"].reshape(-1)
        clean = probabilities(infer(images), checkpoint["temperature"])
        conditions = [{"condition": "clean", "probabilities": clean}]
        for name in STRESSES:
            for severity in (1, 2, 3):
                changed = np.array([stress(im, name, severity, SEED + i) for i, im in enumerate(images)])
                conditions.append({"condition": f"{name}:{severity}",
                                   "probabilities": probabilities(infer(changed), checkpoint["temperature"])})
        return clean, labels, conditions

    validation_cohort = cohort("val")
    test_cohort = cohort("test")
    report["threshold_study"] = build_study(validation_cohort, test_cohort)

    labels = data["test_labels"].reshape(-1)
    logits = infer(data["test_images"])
    clean = probabilities(logits, checkpoint["temperature"])
    report["clean_raw"] = measurements(probabilities(logits), labels)
    report["clean"] = measurements(clean, labels)
    report["clean_review"] = review_measurements(clean, clean, labels)
    for condition in report["conditions"]:
        images = np.array([stress(im, condition["stress"], condition["severity"], SEED + i)
                           for i, im in enumerate(data["test_images"])])
        p = probabilities(infer(images), checkpoint["temperature"])
        condition["metrics"] = measurements(p, labels)
        condition["review"] = review_measurements(clean, p, labels)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Recomputed clean and all 12 stress conditions from the saved model.")
    print("Selected review thresholds on validation only, then measured the frozen policies on test.")


if __name__ == "__main__":
    main()
