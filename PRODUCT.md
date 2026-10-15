# GainGuard

<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
User-approved recommendation: local Python research service, PyTorch, NumPy and Pillow; dependency-free HTML, CSS and JavaScript interface. No existing application architecture was present.

## Users
Student ML researchers and hackathon judges examining model reliability. The user explicitly approved a research-focused ultrasound lab with paired experiments, a benchmark and a review queue.

## Product Purpose
Build a working, tested, reproducible cancer-research prototype for CodeTheCure. Narrow OncoVision to breast-ultrasound acquisition perturbations and classifier stability.

## Positioning
Paired ultrasound stress experiments connect visible image changes to class confidence, empirical calibration, benchmark error and an explicit human-review rule.

## Capabilities and Constraints
Public BreastMNIST only. No clinical uploads or diagnosis. Preserve official split membership and label mapping (0 malignant; 1 normal/benign). Artificial perturbations approximate acquisition effects and are not validated scanner physics. Do not imply patient-level independence, external validation or clinical uncertainty from model confidence.

## Evidence on Hand
Verified MedMNIST source metadata and official Zenodo distribution. A trained 89,026-parameter CNN, its checkpoint hash and the computed clean / 12-condition report live in artifacts/. Every displayed result is computed from the actual model.

## Brand Commitments
User-approved light measurement-workbench interface with large paired scans, precise controls and a readable report.

## Product Principles
Reproduce every result. Make review reasons inspectable. Show failures. Clearly distinguish model outputs from dataset labels. Keep the research limitation visible.
