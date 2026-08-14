from collections import deque
from functools import lru_cache
import itertools


def _r02():
    valid = []
    for pair in itertools.combinations("ABCDE", 2):
        selected = set(pair)
        if len(selected & set("AB")) != 1 or len(selected & set("CDE")) != 1:
            continue
        statements = [
            ("B" in selected) == ("D" in selected),
            ("A" in selected) == ("E" not in selected),
            (("C" in selected) + ("E" in selected)) == 1,
            (("B" in selected) + ("C" in selected)) == 1,
            ("D" not in selected) and ("A" in selected),
        ]
        if sum(statements) == 2:
            valid.append(list(pair))
    assert len(valid) == 1
    return valid[0]


def _r03():
    pairs = [
        (x, y)
        for x in range(-20, 21)
        for y in range(-20, 21)
        if x - y == 2 and x * y == 15
    ]
    values = sorted({x + y for x, y in pairs})
    assert values == [-8, 8]
    return {"step": 5, "values": values}


def _r04():
    rules = {
        "A": lambda a, b, c: a * b + c,
        "B": lambda a, b, c: a + b * c,
        "C": lambda a, b, c: (a + b) * c,
        "D": lambda a, b, c: a * c - b + c,
    }
    samples = [((2, 5, 1), -2), ((4, 1, 3), 14), ((3, 2, 6), 22)]
    matches = [
        name
        for name, rule in rules.items()
        if all(rule(*inputs) == output for inputs, output in samples)
    ]
    assert matches == ["D"]
    return rules[matches[0]](7, 4, 2)


def _candidate_operations(name):
    def left(bits):
        return bits[1:] + bits[:1]

    def right(bits):
        return bits[-1:] + bits[:-1]

    def flip(bits, indexes):
        values = list(bits)
        for index in indexes:
            values[index] = "1" if values[index] == "0" else "0"
        return "".join(values)

    if name == "A":
        return {"K": left, "M": lambda bits: flip(bits, [0, 2])}
    if name == "B":
        return {"K": right, "M": lambda bits: flip(bits, [1])}
    if name == "C":
        return {
            "K": lambda bits: bits[1] + bits[0] + bits[2],
            "M": lambda bits: flip(left(bits), [2]),
        }
    return {
        "K": lambda bits: flip(bits, [0, 1, 2]),
        "M": lambda bits: bits[2] + bits[1] + bits[0],
    }


def _run_bits(start, actions, operations):
    state = start
    for action in actions:
        state = operations[action](state)
    return state


def _r05():
    matches = []
    for name in "ABCD":
        operations = _candidate_operations(name)
        if (
            _run_bits("101", "K", operations) == "011"
            and _run_bits("110", "M", operations) == "100"
            and _run_bits("011", "KM", operations) == "010"
        ):
            matches.append(name)
    assert matches == ["C"]
    return _run_bits("001", "MKM", _candidate_operations(matches[0]))


def _r06():
    observed = [3, 8, 8, 12, 15, 20, 29, 42]
    rules = {
        "A": lambda older, newer, n: 2 * newer - older + n,
        "B": lambda older, newer, n: older + newer - n,
        "C": lambda older, newer, n: 3 * newer - 2 * older + 1,
        "D": lambda older, newer, n: newer + 2 * n,
    }
    matches = []
    for name, rule in rules.items():
        sequence = [3, 8]
        for n in range(3, 9):
            sequence.append(rule(sequence[-2], sequence[-1], n))
        mismatches = [index for index, pair in enumerate(zip(sequence, observed), 1) if pair[0] != pair[1]]
        if len(mismatches) == 1:
            matches.append((name, sequence, mismatches[0]))
    assert len(matches) == 1
    name, sequence, wrong_index = matches[0]
    a9 = rules[name](sequence[-2], sequence[-1], 9)
    return {
        "rule": name,
        "wrong_index": wrong_index,
        "correct_value": sequence[wrong_index - 1],
        "a9": a9,
    }


def _r07():
    coverage = {
        "A": {1, 5},
        "B": {2, 3, 6},
        "C": {1, 4, 6},
        "D": {3, 4, 7},
        "E": {5, 6, 7},
    }
    universe = set(range(1, 8))
    for size in range(1, 6):
        matches = []
        for candidate in itertools.combinations(coverage, size):
            chosen = set(candidate)
            if {"A", "B"} <= chosen or {"D", "E"} <= chosen:
                continue
            if set().union(*(coverage[item] for item in candidate)) == universe:
                matches.append(list(candidate))
        if matches:
            assert len(matches) == 1
            return matches[0]
    raise AssertionError("no explanation found")


def _r08():
    operations = {
        "U": lambda state: (state[0] + state[1], state[1]),
        "V": lambda state: (state[0], state[0] + state[1]),
        "W": lambda state: (2 * state[0], state[1] - 1),
        "X": lambda state: (state[0] - 1, 2 * state[1]),
    }
    matches = []
    for order in itertools.permutations(operations):
        state = (1, 2)
        trace = []
        for action in order:
            state = operations[action](state)
            trace.append(state)
        if (
            trace[0][0] * trace[0][1] == 2
            and sum(trace[1]) == 4
            and trace[2][1] == 4
            and trace[2][0] % 2 == 1
            and trace[3][1] == 8
        ):
            matches.append(list(order))
    assert len(matches) == 1
    return matches[0]


def _r09():
    matches = []
    for order in itertools.permutations("ABCDEF"):
        position = {task: order.index(task) + 1 for task in order}
        if (
            position["B"] == position["D"] + 1
            and position["C"] == position["A"] + 1
            and position["B"] < position["E"] < position["A"]
            and position["D"] < position["F"]
            and abs(position["B"] - position["E"]) == 2
            and position["F"] not in {1, 6}
        ):
            matches.append(list(order))
    assert len(matches) == 1
    return matches[0]


def _r10():
    capacities = [6, 5, 4, 7, 3, 5]
    maximum_avoiding = 0
    for counts in itertools.product(*(range(capacity + 1) for capacity in capacities)):
        if any(count >= 4 for count in counts):
            continue
        round_has_all_colors = counts[0] and counts[2] and counts[4]
        square_has_all_colors = counts[1] and counts[3] and counts[5]
        if round_has_all_colors or square_has_all_colors:
            continue
        maximum_avoiding = max(maximum_avoiding, sum(counts))
    return maximum_avoiding + 1


def _r11():
    projects = {
        "A": (4, 7),
        "B": (5, 10),
        "C": (3, 6),
        "D": (6, 13),
        "E": (2, 4),
        "F": (4, 9),
    }
    candidates = []
    for size in range(7):
        for subset in itertools.combinations(projects, size):
            chosen = set(subset)
            cost = sum(projects[item][0] for item in chosen)
            value = sum(projects[item][1] for item in chosen)
            if cost > 12:
                continue
            if "D" in chosen and "A" not in chosen:
                continue
            if "F" in chosen and "C" not in chosen:
                continue
            if {"B", "E"} <= chosen:
                continue
            if {"A", "C", "E"} <= chosen:
                continue
            if not chosen & {"B", "D", "F"}:
                continue
            candidates.append((value, -cost, sorted(chosen), cost))
    best = max(candidates)
    tied = [candidate for candidate in candidates if candidate[:2] == best[:2]]
    assert len(tied) == 1
    return {"projects": best[2], "cost": best[3], "value": best[0]}


def _r12():
    x = 2 * 2 + 1
    y = 10
    z = 2 * y - x
    w = z + y
    return {"X": x, "Y": y, "Z": z, "W": w}


def _r13():
    observed = {"A": 3, "B": 8, "C": 7, "D": 17}
    ub = observed["B"] - 2 * observed["A"]
    uc = observed["C"] - observed["B"] + observed["A"]
    ud = observed["D"] - observed["C"] - observed["B"]
    a = 1
    b = 2 * a + ub
    c = b - a + uc
    d = c + b + ud
    return {"B": b, "C": c, "D": d}


def _r14():
    failed_weight = 0.1 * 0.8 * 0.25 * 0.6
    healthy_weight = 0.9 * 0.2 * 0.9 * 0.3
    return round(failed_weight / (failed_weight + healthy_weight), 4)


def _r15():
    value_a = 0.72 * 100 + 0.28 * -40 - 18
    value_b = 0.62 * 135 + 0.38 * -25 - 24
    high_success = 0.4 * 0.8 * 0.9 + 0.6 * 0.25 * 0.35
    high_failure = 0.4 * 0.8 * 0.1 + 0.6 * 0.25 * 0.65
    high_branch = high_success * 140 + high_failure * -30 - 0.47 * 20
    low_branch = 0.53 * value_b
    value_c = high_branch + low_branch - 8
    values = {"A": value_a, "B": value_b, "C": value_c}
    best = max(values, key=values.get)
    return {"strategy": best, "expected_value": round(values[best], 2)}


def _r16():
    start = (0, 0, 0, 0)

    def transition(state, action):
        a, b, c, g = state
        if action == "P" and a == 0:
            return (1, 1 - b, c, g)
        if action == "Q" and b == 1:
            return (a, 0, 1, g)
        if action == "R" and c == 1:
            return (0, b, 0, 1)
        if action == "S" and a == 1 and c == 0:
            return (a, 1, c, g)
        if action == "T" and g == 1 and a == 0:
            return (a, 1 - b, c, g)
        return None

    queue = deque([(start, [])])
    solutions = []
    shortest = None
    while queue:
        state, path = queue.popleft()
        if shortest is not None and len(path) > shortest:
            continue
        if state == (1, 1, 0, 1):
            shortest = len(path)
            solutions.append(path)
            continue
        for action in "PQRST":
            next_state = transition(state, action)
            if next_state is not None and len(path) < 8:
                queue.append((next_state, path + [action]))
    shortest_solutions = [path for path in solutions if len(path) == shortest]
    assert shortest == 4 and shortest_solutions == [["P", "Q", "R", "P"]]
    return shortest_solutions[0]


def _r17():
    @lru_cache(None)
    def value(score, rounds, sabotage_left):
        if rounds == 0:
            return score
        action_values = []
        for action in "AD":
            next_score = score + 3 if action == "A" else score * 2
            outcomes = [value(next_score, rounds - 1, sabotage_left)]
            if sabotage_left:
                outcomes.append(value(next_score - 4, rounds - 1, sabotage_left - 1))
            action_values.append((min(outcomes), action))
        return max(action_values)[0]

    first_actions = {}
    for action in "AD":
        next_score = 5 if action == "A" else 4
        outcomes = [value(next_score, 3, 2), value(next_score - 4, 3, 1)]
        first_actions[action] = min(outcomes)
    best_value = max(first_actions.values())
    best_actions = [action for action, result in first_actions.items() if result == best_value]
    assert len(best_actions) == 1
    return {"guaranteed": best_value, "first_action": best_actions[0]}


def _r18():
    tasks = {
        "A": ("X", 2, 0),
        "B": ("Y", 1, 4),
        "C": ("Y", 2, 0),
        "D": ("X", 1, 0),
    }
    candidates = []
    for order in itertools.permutations(tasks):
        if order.index("A") > order.index("C") or order.index("B") > order.index("D"):
            continue
        mode = "X"
        time = 0
        for task in order:
            task_mode, duration, release = tasks[task]
            if task_mode != mode:
                time += 1
                mode = task_mode
            time = max(time, release)
            time += duration
        candidates.append((time, list(order)))
    minimum = min(time for time, _ in candidates)
    best = [order for time, order in candidates if time == minimum]
    assert len(best) == 1
    return {"sequence": best[0], "time": minimum}


def _r19():
    point = (2, 1, 1)
    rotated = (point[1], -point[0], point[2])
    mirrored = (-rotated[0], rotated[1], rotated[2])
    observer = (1, -2, 0)
    relative = tuple(value - origin for value, origin in zip(mirrored, observer))
    return {"east": relative[0], "north": relative[1], "up": relative[2]}


def _r20():
    inventory = {"k1"}
    opened = set()
    requirements = {
        "B": {"k1"},
        "C": {"k2", "t1"},
        "D": {"k3"},
        "E": {"k2", "t2"},
        "F": {"artifact"},
        "G": {"k4", "t1"},
        "H": {"k5"},
        "I": {"k6"},
    }
    contents = {
        "B": {"k2", "t1"},
        "C": {"k3"},
        "D": {"t2"},
        "E": {"artifact"},
        "F": {"k4"},
        "G": {"gem"},
        "H": {"k6"},
        "I": {"k5"},
    }
    changed = True
    while changed:
        changed = False
        for container, required in requirements.items():
            if container not in opened and required <= inventory:
                opened.add(container)
                inventory.update(contents[container])
                changed = True
    return sorted(opened)


def reference_answers():
    return {
        "R01": "D",
        "R02": _r02(),
        "R03": _r03(),
        "R04": _r04(),
        "R05": _r05(),
        "R06": _r06(),
        "R07": _r07(),
        "R08": _r08(),
        "R09": _r09(),
        "R10": _r10(),
        "R11": _r11(),
        "R12": _r12(),
        "R13": _r13(),
        "R14": _r14(),
        "R15": _r15(),
        "R16": _r16(),
        "R17": _r17(),
        "R18": _r18(),
        "R19": _r19(),
        "R20": _r20(),
    }
