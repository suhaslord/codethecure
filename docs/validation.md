# Validation record

Verified locally on October 14, 2026 (Pacific), using Python 3.13.2, PyTorch 2.7.0, NumPy 2.2.3 and Pillow 11.0.0 on Windows. Model training and inference use CPU.

- All **11 unit and real-checkpoint API integration tests pass**: `python -m unittest discover -s tests -v`.
- JavaScript syntax check passes: `node --check web/app.js`.
- Python compilation passes: `python -m compileall -q research server.py scripts tests`.
- `python -m research.evaluate` reproduces `artifacts/report.json` **byte for byte** from the saved checkpoint. This verifies evaluation reproducibility, not cross-platform training reproducibility.
- Saved model hash agrees with report and live health endpoint. Official dataset checksum verified.
- Exactly **300 whitespace-delimited words** in the abstract section of `docs/submission.md`.
- Narrated video is **2:50.75**, 1600 × 900 H.264 with AAC audio; full FFmpeg decode passes. Its narration is synthesized using Windows SAPI. The optional rebuild helper and a separate actual browser walkthrough are included.

## Browser interactions

Used the shared T3 preview, not a separate browser. Verified real initial inference, Reset restoring the original probabilities/pixels, Load failure example, benchmark data/13 table rows, full 156-image audit, review marks, pair inspection and model-scoped session storage. The audit matches the saved report: **138 flags, 88/90 observed errors captured** at −6 dB gain. Test-created review notes were cleared; the preview is left on BUS-002 with one actual flagged experiment.

At desktop 1280/1440 and mobile 390-pixel widths, no document-level horizontal overflow was measured. Images and the self-hosted font load. The mobile sample library intentionally scrolls horizontally; the benchmark table intentionally scrolls within its container.

The preview screenshot tool repeatedly failed, although navigation, interaction, evaluation and recording worked. Compressed recording frames are in `docs/evidence/`; exact pixel finish could not be fully verified. A separate finish review returned **ship** after operational typography and SVG-icon fixes; no material findings remain. The shipped system is recorded in `DESIGN.md` and `.impeccable/design.json`.

## Limits

One small public image-level benchmark and one model seed. No verified patient-independent split or external validation. Digital perturbations are not validated scanner physics. The policy has substantial review burden and can miss confident errors; it is not a clinical safety mechanism. No Devpost submission, GitHub push or public deployment was performed.
