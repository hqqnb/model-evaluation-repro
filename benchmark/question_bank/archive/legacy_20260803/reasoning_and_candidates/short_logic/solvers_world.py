import itertools
from typing import Dict, List


def solve_s01() -> Dict[str, object]:
    worlds: List[str] = []
    for bits in itertools.product([False, True], repeat=5):
        values = dict(zip("ABCDE", bits))
        if sum(bits) != 2:
            continue
        if values["A"] and not values["B"]:
            continue
        if values["C"] == values["D"]:
            continue
        if values["E"] and values["B"]:
            continue
        if not (values["C"] or values["E"]):
            continue
        worlds.append("".join(name for name in "ABCDE" if values[name]))

    worlds = sorted(worlds)
    query_values = {
        "C_or_D": [("C" in world) or ("D" in world) for world in worlds],
        "B": ["B" in world for world in worlds],
        "A": ["A" in world for world in worlds],
    }
    query_classes = {}
    witnesses = {}
    for name, values in query_values.items():
        if all(values):
            query_classes[name] = "necessary"
        elif any(values):
            query_classes[name] = "possible_only"
        else:
            query_classes[name] = "impossible"
        if query_classes[name] == "possible_only":
            witnesses[name] = {
                "true": worlds[values.index(True)],
                "false": worlds[values.index(False)],
            }
        elif query_classes[name] == "impossible":
            witnesses[name] = {"true": None, "false": worlds[0]}
        else:
            witnesses[name] = {"true": worlds[0], "false": None}

    return {
        "worlds": worlds,
        "world_count": len(worlds),
        "query_classes": query_classes,
        "witnesses": witnesses,
    }


def _s02_rules(values: Dict[str, object]) -> Dict[str, bool]:
    return {
        "R1": values["color"] == "red",
        "R2": values["color"] == "blue",
        "R3": values["C"],
        "R4": values["color"] == "green",
        "R5": (not values["C"]) or values["D"],
        "R6": values["D"],
        "R7": not values["E"],
    }


def solve_s02() -> Dict[str, object]:
    rule_ids = [f"R{i}" for i in range(1, 8)]
    assignments = []
    for color, bits in itertools.product(
        ["red", "blue", "green"], itertools.product([False, True], repeat=3)
    ):
        assignments.append(
            {
                "color": color,
                "C": bits[0],
                "D": bits[1],
                "E": bits[2],
            }
        )

    repairs = []
    for size in range(len(rule_ids) + 1):
        for deleted_tuple in itertools.combinations(rule_ids, size):
            deleted = set(deleted_tuple)
            satisfying = [
                values
                for values in assignments
                if all(
                    result
                    for rule_id, result in _s02_rules(values).items()
                    if rule_id not in deleted
                )
            ]
            if satisfying:
                repairs.append((list(deleted_tuple), satisfying))
        if repairs:
            break

    deletion_sets = [item[0] for item in repairs]
    witnesses = {
        "+".join(deleted): {
            key: (int(value) if isinstance(value, bool) else value)
            for key, value in sorted(satisfying[0].items())
        }
        for deleted, satisfying in repairs
    }
    kept_sets = [
        [rule_id for rule_id in rule_ids if rule_id not in set(deleted)]
        for deleted in deletion_sets
    ]
    common_kept = [
        rule_id
        for rule_id in rule_ids
        if all(rule_id in kept for kept in kept_sets)
    ]
    return {
        "repair_size": len(deletion_sets[0]),
        "deletion_sets": deletion_sets,
        "witnesses": witnesses,
        "common_kept": common_kept,
    }
