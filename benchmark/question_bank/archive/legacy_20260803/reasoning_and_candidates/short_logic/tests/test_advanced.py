from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.solvers_advanced import solve_s05, solve_s06


def test_s05_returns_a_guaranteed_policy_and_counterexample():
    answer = solve_s05()

    assert answer["guaranteed_win"] is True
    assert answer["first_action"] == "parity"
    assert answer["worst_case_steps"] == 3
    assert answer["policy"] == {
        "even": {"question": "low", "low": "guess0", "high": "guess2"},
        "odd": {"question": "low", "low": "guess1", "high": "guess3"},
    }
    assert answer["fast_action_counterexample"] == {
        "action": "parity_even_then_guess0",
        "state": "2",
    }


def test_s06_separates_baseline_from_hard_interventions():
    answer = solve_s06()

    assert answer["baseline"] == {"D": 1, "E": 0, "F": 1, "G": 0, "H": 1}
    assert answer["do_D_0"] == {"D": 0, "E": 0, "F": 0, "G": 0, "H": 0}
    assert answer["do_A_1"] == {"D": 0, "E": 0, "F": 1, "G": 1, "H": 0}
    assert answer["invariants"] == ["D", "E", "H"]
    assert answer["minimum_causes_for_H_flip"] == [["D"]]
