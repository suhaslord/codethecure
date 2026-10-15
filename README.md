<img src="web/mark.svg" width="56" height="56" alt="GainGuard">

# GainGuard

**What happens when a breast-ultrasound classifier is confidently wrong after an acquisition change?**

GainGuard narrows OncoVision into a reproducible reliability lab for breast-ultrasound AI. It pairs real public images with deterministic gain, speckle and shadow stress transforms; measures changes in calibrated model outputs; and routes unstable experiments to an inspectable research review queue.

Research prototype only. It does not diagnose, accept patient uploads or make clinical recommendations.

## Public demo and submission

- **Public demo:** https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site
- **Source:** https://github.com/suhaslord/codethecure
- **Narrated video (2:56):** https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site/gainguard-demo.mp4
- **300-word abstract and submission checklist:** [docs/submission.md](docs/submission.md)

The public demo runs the actual exported CNN in a browser worker; no local Python service is required. Its transformed pixels match NumPy exactly in the parity fixtures, and probabilities agree with PyTorch within 1e-5. The small model is about 356 KB. Public test images and deterministic noise are exported from the checksum-verified public dataset; the demo does not accept uploads or collect patient data. Review notes stay in this browser tab. The Python workflow below is the reference for reproduction.

## Run it

Requires Python 3.11+ and a supported PyTorch installation. Tested with Python 3.13.2, PyTorch 2.7.0, NumPy 2.2.3 and Pillow 11.0.0 on Windows. Node is optional, for script shortcuts and the JavaScript syntax check.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

Open **http://localhost:5173**. The trained checkpoint and computed report are included. On first use, the app downloads the official 64 × 64 BreastMNIST archive (about 3 MB) and verifies its MD5 checksum. After that, inference, fonts, images and the interface work locally. There are no API keys or paid inference services.

On macOS/Linux, activate with `source .venv/bin/activate`. If your machine needs a different PyTorch wheel, install the appropriate supported wheel first. The model runs on CPU; a GPU is unnecessary.

## A judge-friendly walkthrough

1. Open **Experiment lab**, select **Reset**, then **Load failure example**. BUS-002 starts correctly classified as normal/benign at 95.5% confidence. At −6 dB simulated gain it flips to malignant at 83.1% confidence. The queue flags the flip and the 78.6 percentage-point probability shift, even though confidence remains above 80%.
2. Change gain, speckle or shadow, then select **Run stress test**. Both the displayed image and model input use the identical transformed pixel array. The nine-point sweep uses actual inference with a fixed noise realization.
3. Open **Benchmark** for clean results, calibration, all 12 stress conditions and the review workload. Download the complete JSON report, including metrics not crowded into the interface.
4. Open **Review queue** and **Audit 156 images**. Inspect a flagged pair, mark it reviewed and export the queue. Marks are researcher notes stored in this browser tab for the current checkpoint, not medical decisions.
5. Open **Methods** for label mapping, transforms, thresholds, provenance and limitations.

## Measured results

Official held-out split: **156 images**, including 42 malignant and 114 normal/benign. The 546 training images and 78 validation images are kept separate. Checkpoint selection and temperature fitting use validation only.

- Clean accuracy: **87.8%**, image-level Wilson 95% interval **81.8–92.1%**.
- Clean balanced accuracy: **81.9%**. Malignant AUROC: **0.890**.
- Clean ECE: **5.6% raw → 3.9% temperature-scaled**, using 10 equal-width bins. This is descriptive on one small test split.
- At **−6 dB simulated gain**, accuracy is **42.3%**, with **66 confidently wrong predictions** (≥80% calibrated confidence).
- The combined rule captures **88/90 errors** and flags **138/156 images**. Confidence-only review at <80% captures **24/90 errors** and flags **51/156 images**. These thresholds have different review workloads; this is **not a matched-budget comparison**.
- Among the 18 unflagged images at −6 dB, two predictions are still wrong. **Unflagged does not mean safe.**

See [artifacts/report.json](artifacts/report.json) for full precision, confusion matrices, class recall, AUROC, Brier score, NLL, ECE bins, review counts, intervals, training history and the model SHA-256. Conditions reuse the same images and must not be pooled as independent patients. Some shadow conditions improve accuracy; the report retains these outcomes.

## Validation-selected review thresholds

The new threshold study uses the 78-image validation split only. It fixes a 50% mean review budget across clean and twelve equally weighted stress conditions, searches confidence cutoffs 0.50–1.00 in 0.01 steps and probability-shift cutoffs 0.05–0.50 plus 1.0, and maximizes captured validation errors subject to that budget. Ties prefer less review, then smaller cutoffs. The combined rule also flags class flips. Selected cutoffs are frozen before the test measurements are summarized.

- Confidence only selects **95%**: validation captures **59.8%** of errors at **46.6%** review; frozen test captures **59.0%** at **49.4%** review.
- Combined rule selects **88% confidence / 15 pp shift / class flips**: validation captures **91.0%** at **49.7%** review; frozen test captures **88.7%** at **55.9%** review.

These are condition-averaged repeated-image results (1,014 validation and 2,028 test image-condition pairs), not independent patients or a perfectly matched test workload. Individual conditions can exceed the budget. The public Benchmark tab plots detection sensitivity and workload over all confidence cutoffs, with split, condition, rule and inspection controls. Test curves are descriptive and must not be used to reselect the frozen policy. The study is exploratory because it was added after the original test report had been seen; checkpoint, calibration and threshold selection reuse the same small validation split. No pooled binomial intervals are claimed.

## Reproduce and validate

```powershell
python -m research.evaluate
python -m unittest discover -s tests -v
node --check web/app.js
```

To retrain from scratch, run `python -m research.train` before evaluation. Training uses a fixed seed and deterministic CPU operations, selects the lowest-validation-NLL checkpoint from 60 epochs, fits a validation-only temperature and evaluates the saved model. `research.evaluate` recomputes test metrics without retraining and verifies the checkpoint hash. Running training overwrites both model and report; restart the server afterward. Exact floating-point results can vary across library versions and hardware.

To build and verify the public browser version:

```powershell
python scripts/export_site.py
node tests/browser_parity.mjs
python -m http.server 5174 --directory dist
```

Open http://localhost:5174. `dist/` contains the deployable static app; it is generated and ignored by Git. No Node packages are needed. The public deployment uses this exact export via Sites. GitHub Actions runs evaluation, tests, export and browser/PyTorch parity on every push. Pinned runtime versions are in requirements.txt; CPU-only PyTorch wheels can be installed first with `python -m pip install torch==2.7.0 --index-url https://download.pytorch.org/whl/cpu`.

The tests cover deterministic transforms, zero-stress identity, known metric calculations and AUROC ties, calibration-bin coverage, temperature behavior, a confident prediction flip, malformed API input, real-data inference/report agreement and static assets. Browser validation additionally exercised reset, failure loading, all 156 audit requests, queue marks and inspection, and desktop/mobile overflow. Native screenshot capture was unavailable; compressed recording frames provide limited visual evidence.

## Project map

- `research/core.py`: model architecture, data integrity, shared transforms, metrics and review policy.
- `research/train.py`, `research/evaluate.py`, `research/thresholds.py`: reproducible training and evaluation.
- `server.py`: local inference and static HTTP service; no external inference.
- `web/`: responsive interface, self-hosted font, threshold curves and browser CNN worker.
- `scripts/export_site.py`: verified public dataset/model export; `tests/browser_parity.mjs`: Python/browser agreement checks.
- `scripts/audit_publish.py`: staged secret, raw-data and file-size publication audit.
- `artifacts/`: trained model, computed report and provenance hash.
- `tests/`: unit and real-checkpoint integration checks.
- `docs/submission.md`: 300-word abstract, demo narration and judging Q&A.
- `docs/gainguard-demo.mp4`: 2-minute-56-second narrated demonstration with actual images, computed results and a recorded application walkthrough; synthetic narration.
- `docs/evidence/walkthrough.mp4`: short, silent browser walkthrough; a rough capture, not a narrated submission video.

The optional `scripts/build_demo.py` authoring helper rebuilds the narrated video from the saved model and report. It uses Windows SAPI and an FFmpeg executable (`--ffmpeg PATH`); neither is required to run the application. Intermediate video/audio files in `docs/demo/` are ignored.

## Scope and prior work

The contribution is the focused, auditable workflow: image change → model response → observable failure → explicit review reason → review-budget cost. It does not introduce a new corruption benchmark or calibration method. Related work includes [MedMNIST-C](https://arxiv.org/abs/2406.17536) and [temperature scaling](https://proceedings.mlr.press/v70/guo17a.html).

This is one small benchmark and one training seed, without verified patient-grouped splitting or external validation. Synthetic intensity transforms are proxies, not validated ultrasound acquisition physics; severe changes may remove label-relevant information. Softmax confidence and entropy are model-output summaries, not clinical uncertainty. The live lab retains the original fixed baseline flags. The benchmark additionally selects confidence and shift thresholds on validation only; neither policy is clinically validated. Next steps are repeated seeds, patient-grouped external data, realistic acquisition changes and prospective validation-selected review budgets on new data.

Data attribution and font licensing are recorded in [THIRD_PARTY.md](THIRD_PARTY.md). The repository and public demo are prepared for judges. The Devpost form itself has not been submitted.
