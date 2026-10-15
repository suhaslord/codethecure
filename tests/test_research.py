import unittest

import numpy as np

from research.core import (perturb, stress, probabilities, entropy, measurements,
                           review_reasons, review_measurements, wilson)


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.image = np.arange(64 * 64, dtype=np.uint8).reshape(64, 64)

    def test_zero_stress_is_pixel_identical(self):
        np.testing.assert_array_equal(self.image, perturb(self.image))
        for name in ("gain_down", "gain_up", "speckle", "shadow"):
            np.testing.assert_array_equal(self.image, stress(self.image, name, 0))

    def test_stress_bounds_and_determinism(self):
        a = perturb(self.image, gain=12, speckle=0.6, shadow=0.9, seed=3)
        np.testing.assert_array_equal(a, perturb(self.image, gain=12, speckle=0.6, shadow=0.9, seed=3))
        self.assertEqual(a.dtype, np.uint8)
        self.assertEqual(a.shape, self.image.shape)
        self.assertTrue(np.all(perturb(self.image, gain=-6) <= self.image))
        self.assertTrue(np.all(perturb(self.image, shadow=0.8) <= self.image))

    def test_temperature_preserves_classes_and_reduces_confidence(self):
        logits = np.array([[3.0, 1.0], [0.0, 4.0]])
        raw, calibrated = probabilities(logits), probabilities(logits, 2)
        np.testing.assert_array_equal(raw.argmax(1), calibrated.argmax(1))
        self.assertTrue(np.all(calibrated.max(1) < raw.max(1)))
        np.testing.assert_allclose(calibrated.sum(1), 1)

    def test_known_metrics_and_auc_ties(self):
        result = measurements(np.array([[0.9, 0.1], [0.2, 0.8], [0.3, 0.7], [0.6, 0.4]]), np.array([0, 1, 0, 1]))
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["auc"], 0.75)
        self.assertEqual(result["confusion"], [[1, 1], [1, 1]])
        self.assertEqual(sum(b["n"] for b in result["bins"]), 4)
        self.assertEqual(measurements(np.full((2, 2), 0.5), np.array([0, 1]))["auc"], 0.5)
        self.assertAlmostEqual(float(entropy(np.array([0.5, 0.5]))), 1)

    def test_review_catches_confident_flip_and_empty_retained(self):
        clean, changed = np.array([0.95, 0.05]), np.array([0.05, 0.95])
        self.assertIn("Prediction changed", review_reasons(clean, changed))
        self.assertEqual(review_reasons(clean, clean), [])
        result = review_measurements(clean[None], changed[None], np.array([0]))
        self.assertEqual(result["errors_caught"], 1)
        self.assertEqual(result["confidence_only_errors_caught"], 0)
        self.assertIsNone(result["retained_accuracy"])

    def test_interval_and_invalid_conditions(self):
        self.assertIsNone(wilson(0, 0))
        lo, hi = wilson(5, 10)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)
        with self.assertRaises(ValueError):
            stress(self.image, "unknown", 1)


if __name__ == "__main__":
    unittest.main()
