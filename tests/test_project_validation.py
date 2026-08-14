from pathlib import Path
import tempfile
import unittest

from scripts.validate_project import (
    validate_model_config,
    validate_provider_config,
    validate_question_bank_manifest,
    validate_repository_layout,
)


class ProjectValidationTests(unittest.TestCase):
    def test_provider_config_accepts_openai_compatible_provider(self):
        config = {
            "providers": {
                "lingzhi": {
                    "base_url": "https://lingzhi.agibot.com/v1",
                    "api_key_env": "LINGZHI_API_KEY",
                    "protocol": "chat_completions",
                }
            }
        }

        self.assertEqual(validate_provider_config(config), [])

    def test_provider_config_rejects_embedded_api_key(self):
        config = {
            "providers": {
                "bad": {
                    "base_url": "https://example.com/v1",
                    "api_key": "secret-value",
                    "api_key_env": "BAD_KEY",
                    "protocol": "chat_completions",
                }
            }
        }

        errors = validate_provider_config(config)

        self.assertTrue(any("api_key" in error for error in errors))

    def test_model_config_requires_known_provider_and_supported_protocol(self):
        config = {
            "models": {
                "qwen3.8-max": {
                    "provider": "lingzhi",
                    "model": "qwen3.8-max",
                    "protocol": "chat_completions",
                }
            }
        }

        self.assertEqual(validate_model_config(config, {"lingzhi"}), [])
        self.assertEqual(
            validate_model_config(config, set()),
            ["model qwen3.8-max references unknown provider lingzhi"],
        )

    def test_repository_layout_reports_missing_required_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            errors = validate_repository_layout(Path(temp_dir))

        self.assertIn("README.md is missing", errors)
        self.assertIn("configs/providers.example.yaml is missing", errors)

    def test_repository_layout_accepts_required_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for relative in (
                "README.md",
                "configs/providers.example.yaml",
                "configs/models.example.yaml",
                "benchmark",
                "runners",
                "evaluation",
                "scripts",
                "benchmark/question_bank/manifest.json",
                "benchmark/question_bank/validate_manifest.py",
                "benchmark/question_bank/single_turn/dataset/prompts.json",
                "benchmark/question_bank/single_turn/rubrics/rubrics.json",
                "benchmark/question_bank/agent/manifest.json",
                "benchmark/question_bank/agent/tasks.md",
            ):
                target = root / relative
                if "." in target.name:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
                else:
                    target.mkdir(parents=True, exist_ok=True)

            self.assertEqual(validate_repository_layout(root), [])

    def test_question_bank_manifest_is_part_of_repository_validation(self):
        errors = validate_question_bank_manifest(
            Path(__file__).resolve().parents[1]
        )

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
