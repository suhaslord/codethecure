# Validation and publication record

Validated October 14, 2026 (Pacific), locally on Windows with Python 3.13.2, PyTorch 2.7.0, NumPy 2.2.3 and Pillow 11.0.0; independently reproduced on a fresh Ubuntu GitHub Actions runner with Python 3.11 and the pinned CPU dependencies.

## Judge access

- Public app: https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site
- Public source: https://github.com/suhaslord/codethecure
- Video: https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site/gainguard-demo.mp4
- Successful fresh-environment verification: https://github.com/suhaslord/codethecure/actions/runs/38689964169

The Site is explicitly public. Anonymous requests with a normal browser user agent return HTTP 200, as does a browser fetch with credentials omitted. No OpenAI or GitHub login is required. Generic automated clients without a browser user agent may receive a platform anti-bot 403.

## Checks

- All **14 Python unit/API integration tests pass**, including strict threshold boundaries, validation review-budget compliance and a test showing that changing test labels cannot change selected cutoffs.
- JavaScript syntax checks and Python compilation pass. The saved-model evaluation repeats byte for byte locally; identical floating-point bytes across operating systems are not promised.
- **12 browser/PyTorch parity cases pass** over four test images and clean, gain-only and combined stresses. Pixels match NumPy exactly; maximum probability difference is about **1.05e-7**, below the **1e-5** tolerance.
- Public inference runs the actual CNN in a Web Worker with asset SHA-256 checks. No running local service or inference API is needed.
- The deployed 156-image audit matches the saved baseline: **138 flags; 88/90 observed errors captured** at -6 dB.
- Threshold curves expose both rules, validation/test views, 13 conditions and cutoff inspection. At mobile width 390 there is no document overflow; wide graphs/tables scroll inside their containers.
- The abstract contains exactly **300 whitespace-delimited words**. The official maximum is 300.
- Updated video duration is **2:55.96**, 1600 x 900 H.264 with AAC audio; full decode passes. It includes the threshold study and recorded application interactions. Narration uses Windows SAPI synthetic speech.

## Publication audit

The exact Git index passed `scripts/audit_publish.py` and **Gitleaks 8.30.1**, with no detected credentials. A separate broad scan flagged example secrets in the downloaded scanner's own README; that ignored tool directory was never staged. No patient uploads, raw NPZ archives, DICOM, environment files, credentials or virtual environments are committed. All published medical images are attributed public BreastMNIST derivatives.

The only committed model is the intentional **360,037-byte** checkpoint; exported browser weights are **356,104 bytes**. The staged audit rejects models over 1 MiB and other files over 10 MiB. The roughly 3.5 MB demo video is intentional. Generated datasets/builds and deployment credentials are ignored. No credential values are recorded.

## Interpretation and submission

The combined policy selects **88% confidence / 15 pp shift / class flips** on validation under a 50% average review budget. Frozen test capture is **88.7%** at **55.9% review** across repeated image-condition pairs. Confidence-only selects **95%**, giving **59.0%** capture at **49.4% review**. These are not independent patients, identical workloads or clinical safety guarantees. The study was added after the original test report and reuses the small validation split; it is exploratory.

Native screenshot capture is unavailable; compressed recordings limit fine-detail visual verification. Actual browser interactions, layout and predictions were checked.

Official deadline verified against Devpost: **October 28, 2026 at 2 PM Pacific / 5 PM EDT / 21:00 UTC**. The public submission package is accessible. The Devpost form itself has not been submitted; entrant/team registration and eligibility are not assumed.
