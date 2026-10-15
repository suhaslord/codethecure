"""Audit the exact Git index before publication; never print secret values."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
MAX_FILE = 10 * 1024 * 1024
MAX_MODEL = 1024 * 1024
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?:sk-proj-|sk-ant-api\d*-)[A-Za-z0-9_-]{20,}"),
    re.compile(rb"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{25,}"),
    re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(rb"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(rb"(?i)(?:api[_-]?key|secret|access[_-]?token)\s*[:=]\s*['\"][A-Za-z0-9_+/=-]{24,}['\"]"),
]


def main():
    paths = subprocess.check_output(["git", "ls-files", "--cached", "-z"], cwd=ROOT).split(b"\0")
    findings, largest, models = [], [], []
    for raw in paths:
        if not raw:
            continue
        path = raw.decode("utf-8")
        content = subprocess.check_output(["git", "show", f":{path}"], cwd=ROOT)
        size = len(content)
        largest.append((size, path))
        suffix = Path(path).suffix.lower()
        if size > MAX_FILE:
            findings.append(f"Oversized staged file: {path} ({size} bytes)")
        if suffix in (".pt", ".pth", ".onnx", ".safetensors", ".ckpt"):
            models.append((path, size))
            if size > MAX_MODEL:
                findings.append(f"Model exceeds 1 MiB publication cap: {path}")
        if suffix in (".dcm", ".dicom", ".nii", ".npz", ".pem", ".key") or Path(path).name.startswith(".env"):
            findings.append(f"Sensitive/raw-data file requires review: {path}")
        if b"\0" not in content[:8192]:
            for pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    findings.append(f"Possible credential in {path}; value redacted")
                    break
    print("Audited exact staged files:", len(largest))
    for size, path in sorted(largest, reverse=True)[:8]:
        print(f"{size:>9,} bytes  {path}")
    print("Intentional small checkpoints:", models)
    if findings:
        raise SystemExit("\n".join(findings))
    print("PASS: no credential patterns, raw medical archives or oversized files in the Git index.")
    print("Medical images in evidence are attributed public BreastMNIST derivatives; no patient uploads are supported.")


if __name__ == "__main__":
    main()
