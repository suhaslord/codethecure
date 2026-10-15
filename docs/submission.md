# GainGuard — acquisition-aware reliability testing for breast-ultrasound AI

## Devpost abstract

Breast ultrasound classifiers can appear reliable on clean images while becoming confidently wrong after acquisition changes. GainGuard is a focused research lab that makes those failures visible, reproducible, and reviewable.

We use public BreastMNIST images, preserving the official split of 546 training, 78 validation, and 156 test images. A convolutional network is trained from scratch; checkpoint selection and temperature calibration use validation data only. The public demonstration runs the exported model inside a browser worker, with pixel transformations checked against NumPy and inference checked against PyTorch.

Researchers compare original and stressed scans, adjust gain, speckle, and shadow proxies, inspect nine model passes, and export evidence tied to a checkpoint hash. The benchmark measures accuracy, malignant-class AUROC, calibration, and review workload across twelve predefined stress conditions.

Clean test accuracy is 87.8%, with AUROC 0.890. At a simulated negative-six-decibel gain shift, accuracy falls to 42.3%; 66 incorrect predictions remain at least 80% confident. The original combined review rule catches 88 of 90 errors while flagging 138 of 156 images, exposing substantial workload.

An additional threshold study selects cutoffs exclusively on validation data under a fixed 50% average review budget. It selects 88% confidence, prediction flips, and a 15-percentage-point probability shift. Frozen test evaluation captures 88.7% of errors at 55.9% review across repeated image-condition pairs. Interactive curves show error detection and workload over confidence thresholds. These are exploratory results, not independent patient observations or an equal-workload superiority claim.

GainGuard includes an inspectable review queue, public source, reproducible evaluation, and automated tests. It is not a diagnostic tool: synthetic stresses are not validated scanner physics, patient independence is unverified, and model confidence is not clinical uncertainty. Threshold tuning reuses the small validation set and was added after the original test report; prospective external evaluation remains essential before drawing any clinical conclusions or deployment recommendations.

## Demo narration — about 2 minutes 30 seconds

**0:00–0:20 · Problem / lab.** “This is GainGuard, a research lab for breast-ultrasound AI reliability. We ask a specific question: after an acquisition-inspired image change, does an AI model become uncertain—or confidently wrong? We use public benchmark images, not patient uploads.”

**0:20–0:55 · Reset, then Load failure example.** “Here is BUS-002, with a normal/benign dataset label. On the original image, our small classifier predicts normal/benign at 95.5% confidence. A simulated minus-six-decibel intensity shift changes its prediction to malignant at 83.1% confidence. A low-confidence trigger alone misses this failure. Our rule catches the prediction flip and the 78.6-point malignant-class probability shift.”

**0:55–1:15 · Sweep / controls.** “The stressed image shown here is exactly the pixel array passed to the model. Gain, speckle and shadow controls run real inference. The curve shows nine model passes, using a fixed noise realization so severity is the variable. You can export the settings, outputs and model hash.”

**1:15–1:50 · Benchmark / highlighted row.** “We trained on 546 images, selected the checkpoint and temperature on 78 validation images, then evaluated 156 held-out images. Clean accuracy is 87.8%, with AUROC 0.890. At minus six decibels, accuracy falls to 42.3%. Sixty-six wrong predictions still have at least 80% confidence. Our rule catches 88 of 90 errors—but sends 138 images to review. That workload matters. We are not claiming an equal-budget win.”

**1:50–2:10 · Queue / audit.** “Run the same protocol on the full test split. Every flag records its reason. Researchers can inspect pairs, mark cases reviewed and export the queue. These are research annotations, not clinical decisions. Two of the 18 unflagged images are still misclassified.”

**2:10–2:30 · Methods.** “GainGuard is a tested, reproducible failure-analysis tool. It does not diagnose cancer. The transforms are digital proxies, and this small dataset does not establish patient-level or external validity. Our next study would use grouped external data, realistic acquisition changes, repeated training seeds and validation-selected review budgets.”

The included `gainguard-demo.mp4` is a 2-minute-56-second narrated research demonstration rendered from the actual model, images and report, using synthetic speech. It explains the measured failure and tradeoff with readable visuals and includes recorded application interactions. `evidence/walkthrough.mp4` also provides that 24.5-second silent rough capture separately. The narration above is an alternate script for a personal voiceover and live screen walkthrough.

## Five-minute finalist pitch

- **0:00–0:45:** Show the observed BUS-002 failure immediately. Explain why confidence-only review misses it.
- **0:45–1:30:** Explain the niche: acquisition robustness audits for breast-ultrasound ML researchers. Review existing medical-image corruption and calibration work honestly.
- **1:30–2:30:** Demonstrate the exact transformed pixels, live model sweep, review reasons and full-split audit.
- **2:30–3:30:** Show split discipline, clean AUROC/accuracy, calibration and −6 dB results. Explicitly disclose review workload, two missed errors and class imbalance.
- **3:30–4:20:** Explain reproducibility: source, public data checksum, checkpoint hash, fixed seeds and tests.
- **4:20–5:00:** State limitations and the next experiment: external patient-grouped data with realistic scanner changes and a validation-selected review budget.

## Questions to be ready for

**What is new?** The scoped, inspectable researcher workflow connecting acquisition-inspired pixel changes, real model behavior, explicit review reasons and workload. Corruption testing and temperature scaling already exist. This prototype does not claim algorithmic novelty.

**Why breast ultrasound?** It supplies a tractable public cancer-related image task and acquisition-inspired failure probes. We do not claim the synthetic transforms faithfully represent a particular scanner.

**Is this a better cancer classifier?** No such claim. The baseline is deliberately small and inspectable. The deliverable is an audit of its failure behavior.

**Does the review rule improve safety?** That is not established. It captures more observed errors at these thresholds while flagging many more images. At −6 dB, two unflagged predictions remain wrong. A matched-budget study on external data is required.

**Did test labels determine the flags?** No. The flag uses original/stressed model outputs and fixed 80% / 15-percentage-point thresholds. Labels evaluate errors afterward. The illustrative failure example is explicitly selected using held-out labels after evaluation; it is not evidence for model selection.

**What about leakage and patient independence?** We preserve official image split membership and never train/select on test labels. The release does not give us verified patient identifiers for a patient-grouped audit. We cannot claim patient independence; duplicates and source shortcuts remain possible.

**What do the intervals mean?** Image-level Wilson 95% binomial intervals. They ignore patient clustering, model-training variability and the dependence between stress conditions. They are not clinical confidence intervals.

**Why did shadow sometimes improve accuracy?** A corruption need not hurt every model. We retain those results rather than selecting only favorable failures. The report tests the defined protocol; it does not assume monotonically decreasing performance.

**Why not use an LLM?** The central problem is controlled image-classifier behavior. Local CNN inference makes the experiment inspectable, repeatable and usable without external inference services.

## Submission state

Public demo: https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site

Source repository: https://github.com/suhaslord/codethecure

Demo video: https://gainguard-ultrasound-lab.brightsiderai.chatgpt.site/gainguard-demo.mp4

The source, small checkpoint, complete report, threshold curves, 300-word abstract and video under three minutes are prepared for judges. The Devpost form itself has not been submitted.

Official requirements verified against [Devpost](https://codethecure-hackathon-26.devpost.com/) and the [official schedule](https://codethecure-hackathon-26.devpost.com/details/dates): abstract maximum 300 words, working prototype, GitHub source link and prototype walkthrough video maximum three minutes. Deadline: **October 28, 2026 at 2 PM Pacific (5 PM EDT / 21:00 UTC)**. Optional feedback: October 20. Selected finalists present for five minutes followed by four minutes of questions. The organizer also lists an external signup and Discord; participant eligibility, registration and team details belong to the entrant and are not inferred here.
