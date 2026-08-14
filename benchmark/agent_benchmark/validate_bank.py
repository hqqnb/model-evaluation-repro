from collections import Counter

from benchmark.agent_benchmark.grade import grade_answer, load_answer_key, load_questions


SUPPORTED_TYPES = {"choice", "integer", "number", "sequence", "set", "mapping"}
REQUIRED_CATEGORIES = {
    "deduction",
    "induction",
    "abduction",
    "constraint",
    "causal",
    "probability",
    "planning",
    "spatial",
}


def validate() -> str:
    questions = load_questions()
    answers = load_answer_key()

    assert len(questions) == 20
    ids = [item["id"] for item in questions]
    assert len(set(ids)) == 20
    assert set(ids) == set(answers)
    assert sum(item["scoring"]["points"] for item in questions) == 100
    assert {item["category"] for item in questions} == REQUIRED_CATEGORIES
    assert Counter(item["difficulty"] for item in questions) == Counter(
        {"L1": 4, "L2": 8, "L3": 8}
    )

    for item in questions:
        assert item["answer_type"] in SUPPORTED_TYPES
        assert len(item["reasoning_elements"]) >= 4
        assert len(item["prompt"]) >= 180
        record = answers[item["id"]]
        assert record["verification"]["unique_solution_count"] == 1
        assert grade_answer(item["id"], record["expected"]).correct
        assert not grade_answer(item["id"], record["near_miss"]).correct

    counts = Counter(item["difficulty"] for item in questions)
    return (
        f"20 questions validated; 100 total points; "
        f"difficulty L1={counts['L1']} L2={counts['L2']} L3={counts['L3']}"
    )


if __name__ == "__main__":
    print(validate())

