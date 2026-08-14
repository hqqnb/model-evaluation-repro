import itertools
from collections import deque
from typing import Dict, Iterable, List, Optional, Tuple


State = str


def _s03_transition(state: State, action: str) -> Optional[State]:
    bits = list(state)
    if action == "A0":
        bits[0] = "0"
    elif action == "BA":
        bits[1] = bits[0]
    elif action == "flipB":
        if bits[0] != "0":
            return None
        bits[1] = "1" if bits[1] == "0" else "0"
    elif action == "CB":
        if bits[1] != "1":
            return None
        bits[2] = bits[1]
    elif action == "flipC":
        if bits[1] != "1":
            return None
        bits[2] = "1" if bits[2] == "0" else "0"
    else:
        raise ValueError(f"unknown action: {action}")
    return "".join(bits)


def _all_states() -> List[State]:
    return ["".join(bits) for bits in itertools.product("01", repeat=3)]


def _robust(sequence: Iterable[str], states: Iterable[State]) -> Dict[State, State]:
    final_by_initial = {}
    for initial in states:
        state = initial
        for action in sequence:
            state = _s03_transition(state, action)
            if state is None:
                break
        if state is not None:
            final_by_initial[initial] = state
    return final_by_initial


def solve_s03() -> Dict[str, object]:
    actions = ["A0", "BA", "flipB", "CB", "flipC"]
    initial_states = _all_states()
    goal = "010"

    queue = deque([()])
    shortest: Optional[Tuple[str, ...]] = None
    while queue:
        sequence = queue.popleft()
        if shortest is not None and len(sequence) >= len(shortest):
            continue
        finals = _robust(sequence, initial_states)
        if len(finals) == len(initial_states) and set(finals.values()) == {goal}:
            shortest = sequence
            continue
        for action in actions:
            queue.append(sequence + (action,))

    if shortest is None:
        raise AssertionError("S03 has no robust plan")
    final_by_initial = _robust(shortest, initial_states)
    return {
        "sequence": list(shortest),
        "steps": len(shortest),
        "final_by_initial": final_by_initial,
        "lower_bound": len(shortest),
        "coverage": initial_states,
    }


def _s04_rhs(bits: Tuple[bool, ...]) -> List[bool]:
    t1, t2, t3, t4, t5, t6 = bits
    count = sum(bits)
    return [
        count == 3,
        t1,
        t2 != t5,
        not t3,
        t4 == t6,
        count != 2,
    ]


def solve_s04() -> Dict[str, object]:
    solutions = []
    for bits in itertools.product([False, True], repeat=6):
        if list(bits) == _s04_rhs(bits):
            solutions.append("".join("T" if bit else "F" for bit in bits))
    return {
        "solutions": solutions,
        "count": len(solutions),
        "always_true": [
            f"S{index + 1}"
            for index in range(6)
            if solutions and all(solution[index] == "T" for solution in solutions)
        ],
        "always_false": [
            f"S{index + 1}"
            for index in range(6)
            if solutions and all(solution[index] == "F" for solution in solutions)
        ],
    }
