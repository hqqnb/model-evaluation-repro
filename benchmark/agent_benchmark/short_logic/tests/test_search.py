from benchmark.agent_benchmark.short_logic.solvers_search import solve_s03, solve_s04


def test_s03_finds_the_shortest_sequence_for_all_initial_states():
    answer = solve_s03()

    assert answer["sequence"] == ["A0", "BA", "flipB", "CB", "flipC"]
    assert answer["steps"] == 5
    assert set(answer["final_by_initial"].values()) == {"010"}
    assert answer["lower_bound"] == 5
    assert answer["coverage"] == [
        "000",
        "001",
        "010",
        "011",
        "100",
        "101",
        "110",
        "111",
    ]


def test_s04_returns_all_fixed_point_truth_assignments():
    answer = solve_s04()

    assert answer["solutions"] == ["FFTFTF"]
    assert answer["count"] == 1
    assert answer["always_true"] == ["S3", "S5"]
    assert answer["always_false"] == ["S1", "S2", "S4", "S6"]
