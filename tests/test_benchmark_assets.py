import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkAssetTests(unittest.TestCase):
    def test_curated_bank_attachments_are_self_contained(self):
        prompts_path = ROOT / "benchmark/curated-bank/dataset/prompts.json"
        prompts = json.loads(prompts_path.read_text(encoding="utf-8"))

        missing = [
            attachment
            for item in prompts["items"]
            for attachment in item.get("attachments", [])
            if not (ROOT / "benchmark/curated-bank" / attachment).is_file()
        ]

        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
