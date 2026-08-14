from benchmark.agent_benchmark.short_logic.solvers_world import solve_s01, solve_s02


def test_s01_returns_all_worlds_and_three_query_classes():
    answer = solve_s01()

    assert answer["worlds"] == ["BC", "CE", "DE"]
    assert answer["query_classes"] == {
        "C_or_D": "necessary",
        "B": "possible_only",
        "A": "impossible",
    }
    assert answer["witnesses"]["B"]["true"] == "BC"
    assert answer["witnesses"]["B"]["false"] == "CE"


def test_s02_returns_all_minimum_repairs_and_common_kept_rules():
    answer = solve_s02()

    assert answer["repair_size"] == 2
    assert answer["deletion_sets"] == [
        ["R1", "R2"],
        ["R1", "R4"],
        ["R2", "R4"],
    ]
    assert answer["common_kept"] == ["R3", "R5", "R6", "R7"]
    assert set(answer["witnesses"]) == {"R1+R2", "R1+R4", "R2+R4"}
