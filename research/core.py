"""Shared model, deterministic stress transforms and audit measurements."""
from __future__ import annotations

import hashlib
from pathlib import Path
import urllib.request

import numpy as np
import torch
from torch import nn

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "breastmnist_64.npz"
URL = "https://zenodo.org/records/10519652/files/breastmnist_64.npz?download=1"
MD5 = "742edef2a1fd1524b2efff4bd7ba9364"
SEED = 20261014
LABELS = ["Malignant", "Normal / benign"]
STRESSES = ("gain_down", "gain_up", "speckle", "shadow")
REVIEW_POLICY = {"confidence_below": 0.8, "probability_shift_above": 0.15,
                 "prediction_flip": True}


def load_data() -> dict[str, np.ndarray]:
    DATA.parent.mkdir(exist_ok=True)
    if not DATA.exists():
        temporary = DATA.with_suffix(".download")
        urllib.request.urlretrieve(URL, temporary)
        if hashlib.md5(temporary.read_bytes()).hexdigest() != MD5:
            temporary.unlink()
            raise ValueError("Dataset checksum mismatch; retry the official download.")
        temporary.replace(DATA)
    if hashlib.md5(DATA.read_bytes()).hexdigest() != MD5:
        raise ValueError("Dataset checksum mismatch; remove the local NPZ and download again.")
    with np.load(DATA, allow_pickle=False) as source:
        return {key: source[key] for key in source.files}


class UltrasoundCNN(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)), nn.Flatten(),
        )
        self.classifier = nn.Sequential(nn.Linear(1024, 64), nn.ReLU(),
                                        nn.Dropout(0.3), nn.Linear(64, 2))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


def tensor(images: np.ndarray) -> torch.Tensor:
    return torch.from_numpy(np.asarray(images, dtype=np.float32)[:, None] / 255.0)


def perturb(image: np.ndarray, gain: float = 0, speckle: float = 0,
            shadow: float = 0, seed: int = SEED) -> np.ndarray:
    """Digital intensity proxies, not a physical ultrasound acquisition simulator."""
    x = image.astype(np.float64) / 255
    x *= 10 ** (gain / 20)
    if speckle:
        x *= 1 + np.random.default_rng(seed).normal(0, speckle, x.shape)
    if shadow:
        h, w = x.shape
        yy, xx = np.mgrid[0:h, 0:w]
        column = np.exp(-0.5 * ((xx / w - 0.55) / 0.14) ** 2)
        depth = np.clip((yy / h - 0.25) / 0.75, 0, 1)
        x *= 1 - shadow * column * depth
    return np.rint(np.clip(x, 0, 1) * 255).astype(np.uint8)


def stress(image: np.ndarray, name: str, severity: int, seed: int = SEED) -> np.ndarray:
    if name not in STRESSES or severity not in (0, 1, 2, 3):
        raise ValueError("Unknown stress or severity.")
    values = {"gain_down": {"gain": -3 * severity},
              "gain_up": {"gain": 3 * severity},
              "speckle": {"speckle": 0.15 * severity},
              "shadow": {"shadow": 0.25 * severity}}
    return perturb(image, **values[name], seed=seed)


def probabilities(logits: np.ndarray, temperature: float = 1) -> np.ndarray:
    scaled = logits / temperature
    exp = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    return exp / exp.sum(axis=1, keepdims=True)


def entropy(probability: np.ndarray) -> np.ndarray:
    return -(probability * np.log2(np.clip(probability, 1e-12, 1))).sum(axis=-1)


def review_reasons(clean: np.ndarray, changed: np.ndarray) -> list[str]:
    reasons = []
    if clean.argmax() != changed.argmax():
        reasons.append("Prediction changed")
    if changed.max() < REVIEW_POLICY["confidence_below"]:
        reasons.append("Confidence below 80%")
    if abs(float(changed[0] - clean[0])) > REVIEW_POLICY["probability_shift_above"]:
        reasons.append("Malignant-class probability shifted over 15 pp")
    return reasons


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z, p = 1.95996398454, successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    radius = z * np.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [float(center - radius), float(center + radius)]


def measurements(probability: np.ndarray, labels: np.ndarray) -> dict:
    labels = labels.reshape(-1)
    prediction = probability.argmax(1)
    correct = prediction == labels
    confidence = probability.max(1)
    bins, ece = [], 0.0
    bin_indices = np.minimum((confidence * 10).astype(int), 9)
    for bin_index in range(10):
        lower = bin_index / 10
        mask = bin_indices == bin_index
        count = int(mask.sum())
        accuracy = float(correct[mask].mean()) if count else None
        mean = float(confidence[mask].mean()) if count else None
        if count:
            ece += count / len(labels) * abs(accuracy - mean)
        bins.append({"lower": float(lower), "n": count, "accuracy": accuracy, "confidence": mean})
    positive, negative = probability[labels == 0, 0], probability[labels == 1, 0]
    auc = None
    if len(positive) and len(negative):
        differences = positive[:, None] - negative[None, :]
        auc = float(((differences > 0) + 0.5 * (differences == 0)).mean())
    malignant = labels == 0
    benign = labels == 1
    return {"n": len(labels), "accuracy": float(correct.mean()),
            "accuracy_ci": wilson(int(correct.sum()), len(labels)),
            "balanced_accuracy": float(np.mean([correct[malignant].mean(), correct[benign].mean()])),
            "malignant_recall": float(correct[malignant].mean()),
            "auc": auc, "ece": float(ece),
            "brier": float(np.mean((probability[:, 0] - malignant) ** 2)),
            "nll": float(-np.log(np.clip(probability[np.arange(len(labels)), labels], 1e-12, 1)).mean()),
            "confident_errors": int(((~correct) & (confidence >= 0.8)).sum()),
            "errors": int((~correct).sum()), "bins": bins,
            "confusion": [[int(((labels == a) & (prediction == b)).sum()) for b in range(2)] for a in range(2)]}


def review_measurements(clean: np.ndarray, changed: np.ndarray, labels: np.ndarray) -> dict:
    flags = np.array([bool(review_reasons(a, b)) for a, b in zip(clean, changed)])
    errors = changed.argmax(1) != labels.reshape(-1)
    retained = ~flags
    caught, total_errors = int((flags & errors).sum()), int(errors.sum())
    return {"flagged": int(flags.sum()), "review_rate": float(flags.mean()),
            "errors_caught": caught, "total_errors": total_errors,
            "error_capture": caught / total_errors if total_errors else None,
            "error_capture_ci": wilson(caught, total_errors),
            "retained": int(retained.sum()),
            "retained_accuracy": float((~errors[retained]).mean()) if retained.any() else None,
            "confidence_only_flagged": int((changed.max(1) < 0.8).sum()),
            "confidence_only_errors_caught": int(((changed.max(1) < 0.8) & errors).sum()),
            "flip_rate": float((clean.argmax(1) != changed.argmax(1)).mean())}
