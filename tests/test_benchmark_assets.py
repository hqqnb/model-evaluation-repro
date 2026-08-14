import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkAssetTests(unittest.TestCase):
    def test_unified_bank_attachments_are_self_contained(self):
        bank_root = ROOT / "benchmark/question_bank/single_turn"
        prompts_path = bank_root / "dataset/prompts.json"
        prompts = json.loads(prompts_path.read_text(encoding="utf-8"))

        missing = [
            attachment
            for item in prompts["items"]
            for attachment in item.get("attachments", [])
            if not (bank_root / attachment).is_file()
        ]

        self.assertEqual(missing, [])

    def test_unified_bank_entry_points_exist(self):
        bank_root = ROOT / "benchmark/question_bank"
        manifest = json.loads((bank_root / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["task_count"], 28)
        self.assertTrue((bank_root / "agent/tasks.md").is_file())
        for legacy_name in ("collector-bank", "curated-bank", "agent_benchmark"):
            self.assertFalse((ROOT / "benchmark" / legacy_name).exists())


if __name__ == "__main__":
    unittest.main()
