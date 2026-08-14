from itertools import combinations
from typing import Dict, List, Optional


def _feedback(state: str, action: str) -> str:
    number = int(state)
    if action == "parity":
        return "even" if number % 2 == 0 else "odd"
    if action == "low":
        return "low" if number in {0, 1} else "high"
    if action == "high":
        return "edge" if number in {0, 3} else "middle"
    raise ValueError(f"unknown question: {action}")


def _partition(states: List[str], action: str) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {}
    for state in states:
        groups.setdefault(_feedback(state, action), []).append(state)
    return groups


def _first_separating_question(
    states: List[str], questions: List[str]
) -> Optional[Dict[str, object]]:
    for question in questions:
        groups = _partition(states, question)
        if all(len(group) == 1 for group in groups.values()):
            return {"question": question, "groups": groups}
    return None


def solve_s05() -> Dict[str, object]:
    states = [str(number) for number in range(4)]
    questions = ["parity", "low", "high"]
    first_action = None
    first_groups: Dict[str, List[str]] = {}
    second_questions: Dict[str, Dict[str, object]] = {}

    for question in questions:
        groups = _partition(states, question)
        candidates = {
            feedback: _first_separating_question(group, questions)
            for feedback, group in groups.items()
        }
        if all(candidate is not None for candidate in candidates.values()):
            first_action = question
            first_groups = groups
            second_questions = {
                feedback: candidate
                for feedback, candidate in candidates.items()
                if candidate is not None
            }
            break

    if first_action is None:
        raise AssertionError("S05 has no guaranteed two-question strategy")

    policy: Dict[str, Dict[str, str]] = {}
    for first_feedback in first_groups:
        candidate = second_questions[first_feedback]
        branch = {"question": str(candidate["question"])}
        for second_feedback, group in candidate["groups"].items():
            branch[second_feedback] = f"guess{group[0]}"
        policy[first_feedback] = branch

    counterexample = next(
        state for state in first_groups["even"] if state != "0"
    )
    return {
        "guaranteed_win": True,
        "first_action": first_action,
        "policy": policy,
        "worst_case_steps": 3,
        "fast_action_counterexample": {
            "action": "parity_even_then_guess0",
            "state": counterexample,
        },
    }


def _evaluate(
    inputs: Dict[str, int], force: Optional[Dict[str, int]] = None
) -> Dict[str, int]:
    values = dict(inputs)
    force = force or {}
    if "D" in force:
        values["D"] = force["D"]
    else:
        values["D"] = values["A"] ^ values["B"]
    if "E" in force:
        values["E"] = force["E"]
    else:
        values["E"] = values["D"] & (1 - values["C"])
    if "F" in force:
        values["F"] = force["F"]
    else:
        values["F"] = values["D"] | (values["A"] & values["B"])
    if "G" in force:
        values["G"] = force["G"]
    else:
        values["G"] = values["A"] & values["C"]
    if "H" in force:
        values["H"] = force["H"]
    else:
        values["H"] = values["F"] ^ values["G"]
    return {key: values[key] for key in "DEFGH"}


def solve_s06() -> Dict[str, object]:
    inputs = {"A": 0, "B": 1, "C": 1}
    baseline = _evaluate(inputs)
    do_d_0 = _evaluate(inputs, {"D": 0})
    do_a_1 = _evaluate({"A": 1, "B": 1, "C": 1})
    invariants = [
        key for key in "DEFGH" if do_d_0[key] == do_a_1[key]
    ]

    candidate_variables = ["D", "E"]
    causes: List[List[str]] = []
    for size in range(1, len(candidate_variables) + 1):
        for subset in combinations(candidate_variables, size):
            force = {}
            for variable in subset:
                force[variable] = 1 - baseline[variable]
            result = _evaluate(inputs, force)
            if result["H"] != baseline["H"]:
                causes.append(list(subset))
        if causes:
            break
    return {
        "baseline": baseline,
        "do_D_0": do_d_0,
        "do_A_1": do_a_1,
        "invariants": invariants,
        "minimum_causes_for_H_flip": causes,
    }
