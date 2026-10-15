import unittest
import numpy as np

from research.thresholds import build_study, flag_mask, select_policy, REVIEW_BUDGET


class ThresholdTests(unittest.TestCase):
    def test_confidence_boundary_is_strict_and_flip_can_be_confident(self):
        clean = np.array([[0.9, 0.1], [0.9, 0.1]])
        changed = np.array([[0.8, 0.2], [0.05, 0.95]])
        np.testing.assert_array_equal(flag_mask(clean, changed, 0.8), [False, False])
        np.testing.assert_array_equal(flag_mask(clean, changed, 0.8, 0.15), [False, True])

    def test_selection_respects_validation_budget(self):
        p = np.array([[0.51, 0.49], [0.6, 0.4], [0.8, 0.2], [0.95, 0.05]])
        labels = np.array([1, 1, 0, 0])
        policy = select_policy(p, p, labels, False)
        self.assertLessEqual(policy["validation"]["review_rate"], REVIEW_BUDGET)
        self.assertEqual(policy["validation"]["errors_caught"], 2)

    def test_test_labels_cannot_change_selected_thresholds(self):
        p = np.array([[0.51, 0.49], [0.6, 0.4], [0.8, 0.2], [0.95, 0.05]])
        labels = np.array([1, 1, 0, 0])
        validation = (p, labels, [{"condition": "clean", "probabilities": p}])
        first = build_study(validation, validation)
        changed_test = (p, 1 - labels, [{"condition": "clean", "probabilities": p}])
        second = build_study(validation, changed_test)
        for name in first["selected"]:
            for key in ("confidence_below", "probability_shift_above", "validation"):
                self.assertEqual(first["selected"][name][key], second["selected"][name][key])
        self.assertNotEqual(first["selected"]["confidence_only"]["test"], second["selected"]["confidence_only"]["test"])
