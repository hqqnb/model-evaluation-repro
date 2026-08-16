import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).parents[1] / "tools" / "generate_agent_review.py"
SPEC = importlib.util.spec_from_file_location("generate_agent_review", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AgentReviewScoringTest(unittest.TestCase):
    def test_final_score_registry_is_the_single_public_total(self):
        registry = MODULE.load_final_score_registry()
        self.assertEqual(registry["scores"]["hy3"]["official_score"], 75.96)
        self.assertEqual(
            set(registry["scores"]),
            {model["key"] for model in MODULE.MODEL_SOURCES if model["ranked"]},
        )
        self.assertTrue(
            all("final_score" not in scorecard for scorecard in MODULE.SCORECARDS.values())
        )

    def test_glm_internal_is_the_only_glm_ranked_result(self):
        glm_models = [
            model for model in MODULE.MODEL_SOURCES if "GLM" in model["label"]
        ]
        self.assertEqual(
            [(model["key"], model["label"]) for model in glm_models],
            [("glm-5.2-internal", "GLM-5.2-内部")],
        )


if __name__ == "__main__":
    unittest.main()
