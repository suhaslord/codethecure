"""Select review thresholds using validation only, then freeze them for test.

The budget and candidate grid are protocol choices, not fitted on test outcomes.
The thirteen conditions repeat images; pooled counts are image-condition pairs.
"""
from __future__ import annotations

import numpy as np

CONFIDENCE_GRID = [round(0.5 + i * 0.01, 2) for i in range(51)]
SHIFT_GRID = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 1.0]
REVIEW_BUDGET = 0.50


def flag_mask(clean, changed, confidence, shift=None):
    flags = changed.max(axis=1) < confidence
    if shift is not None:
        flags |= (changed.argmax(1) != clean.argmax(1)) | (np.abs(changed[:, 0] - clean[:, 0]) > shift)
    return flags


def summarize(clean, changed, labels, confidence, shift=None):
    flags = flag_mask(clean, changed, confidence, shift)
    errors = changed.argmax(1) != labels.reshape(-1)
    caught, total = int((flags & errors).sum()), int(errors.sum())
    retained = ~flags
    return {"n": len(labels), "flagged": int(flags.sum()), "review_rate": float(flags.mean()),
            "errors_caught": caught, "total_errors": total,
            "error_capture": caught / total if total else None,
            "error_precision": caught / int(flags.sum()) if flags.any() else None,
            "retained": int(retained.sum()),
            "retained_accuracy": float((~errors[retained]).mean()) if retained.any() else None}


def select_policy(clean, changed, labels, combined):
    """No test probabilities, labels or measurements are accepted here."""
    candidates = []
    for confidence in CONFIDENCE_GRID:
        for shift in SHIFT_GRID if combined else [None]:
            stats = summarize(clean, changed, labels, confidence, shift)
            if stats["review_rate"] <= REVIEW_BUDGET:
                candidates.append({"confidence_below": confidence, "probability_shift_above": shift,
                                   "validation": stats})
    if not candidates:
        return None
    # Prefer more captured validation errors, then less review, then smaller cutoffs.
    return max(candidates, key=lambda p: (p["validation"]["errors_caught"],
                                         -p["validation"]["flagged"],
                                         -p["confidence_below"],
                                         -(p["probability_shift_above"] or 0)))


def build_study(validation, test):
    def pooled(cohort):
        clean, labels, conditions = cohort
        return (np.concatenate([clean for _ in conditions]),
                np.concatenate([entry["probabilities"] for entry in conditions]),
                np.tile(labels, len(conditions)))

    vc, vp, vy = pooled(validation)
    # Complete selection before even pooling final-test outputs.
    selected = {"confidence_only": select_policy(vc, vp, vy, False),
                "combined": select_policy(vc, vp, vy, True)}
    tc, tp, ty = pooled(test)
    frozen = {}
    for name, policy in selected.items():
        if policy is None:
            frozen[name] = None
            continue
        frozen[name] = {**policy, "test": summarize(tc, tp, ty, policy["confidence_below"],
                                                   policy["probability_shift_above"])}
    shift = selected["combined"]["probability_shift_above"] if selected["combined"] else 0.15
    curves = {}
    for split, cohort in (("validation", validation), ("test", test)):
        clean, labels, conditions = cohort
        curves[split] = []
        for entry in conditions:
            curves[split].append({"condition": entry["condition"], "points": [
                {"confidence_threshold": threshold,
                 "confidence_only": summarize(clean, entry["probabilities"], labels, threshold),
                 "combined": summarize(clean, entry["probabilities"], labels, threshold, shift)}
                for threshold in CONFIDENCE_GRID]})
    return {"selection_split": "validation", "review_budget": REVIEW_BUDGET,
            "budget_scope": "Mean review workload across clean plus twelve equally weighted stress conditions",
            "objective": "Maximize validation errors captured subject to the 50% review budget; then minimize review count; then choose smaller cutoffs.",
            "confidence_grid": CONFIDENCE_GRID, "shift_grid": SHIFT_GRID,
            "condition_count": len(validation[2]), "validation_images": len(validation[1]),
            "test_images": len(test[1]), "selected": frozen, "curves": curves,
            "curve_combined_shift_threshold": shift,
            "caveats": ["The study was added after the original test report was seen; this is exploratory, not a prospective or independently preregistered result.",
                "Threshold selection code accepts validation data only. Test curves are descriptive; do not reselect cutoffs using them.",
                "The workload budget applies to the condition-averaged validation cohort; individual conditions and final-test workloads can exceed it.",
                "Image-condition pairs are repeated measurements, not independent patients; no pooled binomial intervals are reported.",
                "Checkpoint selection, calibration and review tuning reuse the same 78 validation images and can overfit."]}
