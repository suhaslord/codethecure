"""Integration checks against real held-out data and the saved checkpoint."""
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from research.core import ROOT
from server import Handler, ResearchLab


@unittest.skipUnless((ROOT / "artifacts" / "model.pt").exists(), "Run python -m research.train first")
class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Handler.lab = ResearchLab()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return json.load(response)

    def post(self, payload):
        request = Request(self.base + "/api/experiment", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return json.load(response)

    def test_report_matches_live_model_and_all_split_images(self):
        report, samples = self.get("/api/report"), self.get("/api/samples")
        self.assertEqual(len(samples), 156)
        self.assertEqual(sum(s["correct"] for s in samples) / 156, report["clean"]["accuracy"])
        self.assertEqual(sum(b["n"] for b in report["clean"]["bins"]), 156)
        self.assertEqual(sum(s["label"] == 0 for s in samples), 42)
        self.assertEqual(self.get("/api/health")["model_sha256"], report["model"]["sha256"])

    def test_zero_stress_preserves_pixels_probabilities_and_prediction(self):
        result = self.post({"sample_id": 1})
        self.assertEqual(result["original_image"], result["transformed_image"])
        self.assertEqual(result["sample"]["prediction"], result["prediction"])
        self.assertAlmostEqual(result["probability_shift"], 0, places=6)
        self.assertEqual(len(result["sweep"]), 9)

    def test_stress_is_repeatable_and_label_free_policy_flags_real_failure(self):
        payload = {"sample_id": 1, "gain": -6, "speckle": 0, "shadow": 0}
        first, second = self.post(payload), self.post(payload)
        self.assertEqual(first, second)
        self.assertTrue(first["sample"]["correct"])
        self.assertFalse(first["correct"])
        self.assertTrue(first["flagged"])
        self.assertIn("Prediction changed", first["reasons"])

    def test_malformed_requests_and_image_bounds(self):
        for payload in ({"sample_id": -1}, {"sample_id": 156}, {"sample_id": True},
                        {"sample_id": 1, "gain": 99}, {"sample_id": 1, "shadow": "bad"},
                        {"sample_id": 1, "speckle": float("nan")}, []):
            with self.assertRaises(HTTPError) as error:
                self.post(payload)
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError) as error:
            self.get("/api/image?id=-1")
        self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError) as error:
            self.get("/api/unknown")
        self.assertEqual(error.exception.code, 404)

    def test_static_app_and_local_font_exist(self):
        for path in ("/", "/app.js", "/styles.css", "/fonts/public-sans.woff2", "/api/image?id=0"):
            with urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)
                self.assertGreater(int(response.headers["Content-Length"]), 0)


if __name__ == "__main__":
    unittest.main()
