"""Build a public static app with actual browser inference and public test data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from research.core import SEED, perturb
from server import ResearchLab


def export(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "web", output, dirs_exist_ok=True)
    lab = ResearchLab()
    assets = output / "public-data"
    assets.mkdir(exist_ok=True)
    checkpoint = torch.load(ROOT / "artifacts/model.pt", map_location="cpu", weights_only=True)
    parameters, arrays, offset = [], [], 0
    for name, value in checkpoint["state_dict"].items():
        flat = value.numpy().astype("<f4").reshape(-1)
        parameters.append({"name": name, "shape": list(value.shape), "offset": offset, "length": len(flat)})
        offset += len(flat)
        arrays.append(flat)
    (assets / "weights.bin").write_bytes(np.concatenate(arrays).tobytes())
    (assets / "images.bin").write_bytes(lab.images.tobytes())
    noise = np.array([np.random.default_rng(SEED + i).normal(0, 1, (64, 64)) for i in range(len(lab.images))], dtype="<f8")
    (assets / "noise.bin").write_bytes(noise.tobytes())
    samples = [lab.sample(i) for i in range(len(lab.images))]
    (assets / "samples.json").write_text(json.dumps(samples), encoding="utf-8")
    (assets / "report.json").write_text(json.dumps(lab.report), encoding="utf-8")
    for i, image in enumerate(lab.images):
        Image.fromarray(image).save(assets / f"image-{i}.png")
    manifest = {"parameters": parameters, "temperature": lab.temperature,
                "model_sha256": lab.report["model"]["sha256"], "seed": SEED,
                "provenance": lab.report["dataset"], "files": {}}
    for name in ("weights.bin", "images.bin", "noise.bin", "samples.json", "report.json"):
        content = (assets / name).read_bytes()
        manifest["files"][name] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    (assets / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Reference fixtures are generated from Python, including non-zero combined stress.
    fixtures = []
    for index in (0, 1, 42, 155):
        for config in ({"gain": 0, "speckle": 0, "shadow": 0}, {"gain": -6, "speckle": 0, "shadow": 0},
                       {"gain": 3, "speckle": 0.3, "shadow": 0.5}):
            image = perturb(lab.images[index], **config, seed=SEED + index)
            fixtures.append({"id": index, "settings": config, "pixels": image.reshape(-1).tolist(),
                             "probabilities": lab.infer(image[None])[0].tolist()})
    (assets / "parity.json").write_text(json.dumps(fixtures), encoding="utf-8")
    (output / "deployment.js").write_text("window.GAINGUARD_STATIC = true;\n", encoding="utf-8")
    page = (output / "index.html").read_text(encoding="utf-8")
    page = page.replace('href="/', 'href="./').replace('src="/', 'src="./')
    page = page.replace('./api/image?id=1', './public-data/image-1.png')
    (output / "index.html").write_text(page, encoding="utf-8")
    (output / ".nojekyll").touch()
    shutil.copy2(ROOT / "docs/gainguard-demo.mp4", output / "gainguard-demo.mp4")
    print(f"Exported full browser-inference app to {output}; weights {manifest['files']['weights.bin']['bytes']:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    export(parser.parse_args().output.resolve())
