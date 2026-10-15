"""Local-only research demo. No uploads, accounts or external inference services."""
from __future__ import annotations

import argparse
import base64
from functools import lru_cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import math
from pathlib import Path
import threading
from urllib.parse import urlparse, parse_qs

import numpy as np
from PIL import Image
import torch

from research.core import (ROOT, SEED, LABELS, UltrasoundCNN, load_data, tensor,
                           probabilities, perturb, entropy, review_reasons)


def png(image: np.ndarray) -> bytes:
    stream = BytesIO()
    Image.fromarray(image).save(stream, format="PNG")
    return stream.getvalue()


class ResearchLab:
    def __init__(self) -> None:
        checkpoint_path = ROOT / "artifacts" / "model.pt"
        if not checkpoint_path.exists():
            raise RuntimeError("Train the model first: python -m research.train")
        torch.set_num_threads(2)
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        self.model = UltrasoundCNN()
        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.eval()
        self.temperature = checkpoint["temperature"]
        data = load_data()
        self.images, self.labels = data["test_images"], data["test_labels"].reshape(-1)
        self.report = json.loads((ROOT / "artifacts" / "report.json").read_text(encoding="utf-8"))
        import hashlib
        if hashlib.sha256(checkpoint_path.read_bytes()).hexdigest() != self.report["model"]["sha256"]:
            raise RuntimeError("Model/report mismatch. Regenerate artifacts together with python -m research.train")
        self.lock = threading.Lock()
        self.clean = self.infer(self.images)

    def infer(self, images: np.ndarray) -> np.ndarray:
        with self.lock, torch.inference_mode():
            logits = np.concatenate([self.model(chunk).numpy() for chunk in tensor(images).split(64)])
        return probabilities(logits, self.temperature)

    def sample(self, index: int) -> dict:
        p = self.clean[index]
        return {"id": index, "name": f"BUS-{index + 1:03d}",
                "label": int(self.labels[index]), "label_name": LABELS[self.labels[index]],
                "prediction": int(p.argmax()), "confidence": float(p.max()),
                "probabilities": p.tolist(), "correct": bool(p.argmax() == self.labels[index])}

    @lru_cache(maxsize=512)
    def experiment(self, index: int, gain: float, speckle: float, shadow: float) -> dict:
        original = self.images[index]
        transformed = perturb(original, gain=gain, speckle=speckle, shadow=shadow, seed=SEED + index)
        # Same noise realization at each strength isolates severity from random draws.
        strengths = np.linspace(0, 1, 9)
        sweep_images = np.array([perturb(original, gain=gain * s, speckle=speckle * s,
                                        shadow=shadow * s, seed=SEED + index) for s in strengths])
        sweep_p = self.infer(sweep_images)
        clean, changed = self.clean[index], sweep_p[-1]
        reasons = review_reasons(clean, changed)
        return {"sample": self.sample(index),
                "settings": {"gain": gain, "speckle": speckle, "shadow": shadow, "seed": SEED + index},
                "original_image": "data:image/png;base64," + base64.b64encode(png(original)).decode(),
                "transformed_image": "data:image/png;base64," + base64.b64encode(png(transformed)).decode(),
                "probabilities": changed.tolist(), "prediction": int(changed.argmax()),
                "confidence": float(changed.max()), "entropy": float(entropy(changed)),
                "probability_shift": float(changed[0] - clean[0]),
                "correct": bool(changed.argmax() == self.labels[index]),
                "flagged": bool(reasons), "reasons": reasons,
                "sweep": [{"strength": float(s), "malignant_probability": float(p[0]),
                           "confidence": float(p.max()), "flagged": bool(review_reasons(clean, p))}
                          for s, p in zip(strengths, sweep_p)]}


class Handler(SimpleHTTPRequestHandler):
    lab: ResearchLab

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def json_response(self, data: dict | list, status: int = 200) -> None:
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.json_response({"status": "ready", "model_sha256": self.lab.report["model"]["sha256"]})
        elif parsed.path == "/api/report":
            self.json_response(self.lab.report)
        elif parsed.path == "/api/samples":
            self.json_response([self.lab.sample(i) for i in range(len(self.lab.images))])
        elif parsed.path == "/api/image":
            try:
                index = int(parse_qs(parsed.query).get("id", [""])[0])
                if not 0 <= index < len(self.lab.images):
                    raise ValueError()
                body = png(self.lab.images[index])
            except (ValueError, TypeError):
                self.json_response({"error": "Select a valid held-out sample."}, 400)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif parsed.path.startswith("/api/"):
            self.json_response({"error": "Unknown API route."}, 404)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/experiment":
            self.json_response({"error": "Unknown API route."}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 4096:
                raise ValueError("Request must contain a JSON object under 4 KB.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Request must be a JSON object.")
            index = payload.get("sample_id")
            if type(index) is not int or not 0 <= index < len(self.lab.images):
                raise ValueError("Select a valid held-out sample.")
            settings = []
            for name, minimum, maximum in (("gain", -12, 12), ("speckle", 0, 0.6), ("shadow", 0, 0.9)):
                value = payload.get(name, 0)
                if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
                    raise ValueError(f"{name} must be between {minimum} and {maximum}.")
                settings.append(float(value))
            result = self.lab.experiment(index, *settings)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.json_response({"error": str(error)}, 400)
            return
        self.json_response(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    Handler.lab = ResearchLab()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"GainGuard ready at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
