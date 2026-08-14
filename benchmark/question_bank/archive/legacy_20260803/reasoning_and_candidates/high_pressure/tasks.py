import heapq
import itertools
import json
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.models import Component, TaskCase


def _json_shape(fields: Dict[str, Any]) -> str:
    return json.dumps(fields, ensure_ascii=False, separators=(",", ":"))


def _task_t01() -> TaskCase:
    stations = ["A", "B", "C", "D", "E"]
    capacities = {
        ("G101", "一等"): 2,
        ("G101", "二等"): 5,
        ("G202", "二等"): 4,
    }
    operations = [
        ("BUY", "O01", "G101", "二等", "A", "D", 2),
        ("BUY", "O02", "G101", "二等", "B", "E", 2),
        ("BUY", "O03", "G101", "二等", "A", "B", 3),
        ("BUY", "O04", "G101", "二等", "D", "E", 3),
        ("WAIT", "W01", "G101", "二等", "A", "C", 2),
        ("WAIT", "W02", "G101", "二等", "B", "D", 1),
        ("REFUND", "O02", 1),
        ("REFUND", "O03", 2),
        ("REFUND", "O03", 1),
        ("REFUND", "O01", 1),
        ("BUY", "O05", "G101", "一等", "A", "E", 2),
        ("BUY", "O06", "G101", "一等", "B", "D", 1),
        ("WAIT", "W03", "G101", "一等", "B", "D", 1),
        ("REFUND", "O05", 1),
        ("CHANGE", "O04", "G202", "二等", "B", "E"),
        ("BUY", "O07", "G202", "二等", "A", "C", 3),
        ("WAIT", "W04", "G202", "二等", "A", "D", 2),
        ("BUY", "O08", "G202", "二等", "C", "E", 2),
        ("REFUND", "O07", 1),
        ("CHANGE", "O07", "G101", "二等", "A", "C"),
        ("REFUND", "O08", 1),
        ("BUY", "O09", "G202", "二等", "A", "B", 2),
        ("WAIT", "W05", "G202", "二等", "B", "C", 2),
        ("REFUND", "O07", 1),
        ("REFUND", "O04", 1),
        ("BUY", "O10", "G101", "二等", "C", "E", 2),
        ("CHANGE", "O10", "G202", "二等", "A", "D"),
        ("REFUND", "O05", 2),
        ("REFUND", "W03", 1),
        ("BUY", "O11", "G101", "一等", "A", "B", 2),
    ]

    active: Dict[str, Dict[str, Any]] = {}
    waiting: List[Dict[str, Any]] = []
    failed: List[int] = []

    def segments(start: str, end: str) -> List[str]:
        left, right = stations.index(start), stations.index(end)
        return [f"{stations[index]}-{stations[index + 1]}" for index in range(left, right)]

    def occupied(train: str, seat: str, segment: str) -> int:
        return sum(
            order["qty"]
            for order in active.values()
            if order["train"] == train
            and order["seat"] == seat
            and segment in order["segments"]
        )

    def fits(train: str, seat: str, start: str, end: str, qty: int) -> bool:
        capacity = capacities[(train, seat)]
        return all(
            occupied(train, seat, segment) + qty <= capacity
            for segment in segments(start, end)
        )

    def add_order(
        order_id: str, train: str, seat: str, start: str, end: str, qty: int
    ) -> None:
        active[order_id] = {
            "train": train,
            "seat": seat,
            "start": start,
            "end": end,
            "segments": segments(start, end),
            "qty": qty,
        }

    def process_waiting() -> None:
        while waiting:
            first = waiting[0]
            if not fits(
                first["train"],
                first["seat"],
                first["start"],
                first["end"],
                first["qty"],
            ):
                return
            waiting.pop(0)
            add_order(**first)

    for op_index, operation in enumerate(operations, start=1):
        kind = operation[0]
        if kind in {"BUY", "WAIT"}:
            _, order_id, train, seat, start, end, qty = operation
            if kind == "BUY":
                if fits(train, seat, start, end, qty):
                    add_order(order_id, train, seat, start, end, qty)
                else:
                    failed.append(op_index)
            else:
                waiting.append(
                    {
                        "order_id": order_id,
                        "train": train,
                        "seat": seat,
                        "start": start,
                        "end": end,
                        "qty": qty,
                    }
                )
                process_waiting()
        elif kind == "REFUND":
            _, order_id, qty = operation
            if order_id not in active or qty > active[order_id]["qty"]:
                failed.append(op_index)
                continue
            active[order_id]["qty"] -= qty
            if active[order_id]["qty"] == 0:
                del active[order_id]
            process_waiting()
        elif kind == "CHANGE":
            _, order_id, train, seat, start, end = operation
            if order_id not in active:
                failed.append(op_index)
                continue
            old = active[order_id]
            if not fits(train, seat, start, end, old["qty"]):
                failed.append(op_index)
                continue
            del active[order_id]
            add_order(order_id, train, seat, start, end, old["qty"])
            process_waiting()

    availability = {}
    for (train, seat), capacity in capacities.items():
        availability[f"{train}-{seat}"] = {
            segment: capacity - occupied(train, seat, segment)
            for segment in ["A-B", "B-C", "C-D", "D-E"]
        }
    expected = {
        "availability": availability,
        "active_orders": sorted(active),
        "waiting_orders": [item["order_id"] for item in waiting],
        "failed_operations": failed,
    }
    near_miss = dict(expected)
    near_miss["failed_operations"] = failed[:-1]

    op_lines = []
    for index, operation in enumerate(operations, start=1):
        op_lines.append(f"{index:02d}. " + " ".join(map(str, operation)))
    prompt = f"""你负责核对一套火车售票流水。站点顺序固定为 A-B-C-D-E。每张票会占用起点到终点之间的每一段，但不占用终点之后的区间。

容量：G101 一等座每段 2 张，G101 二等座每段 5 张，G202 二等座每段 4 张。初始没有订单。

操作规则：
1. BUY 为立即购票；整个订单所有区间都有余量才成功，否则整单失败且状态不变。
2. WAIT 把订单放入该流水的全局候补队列。每次 WAIT、成功退票或成功改签后，从队首开始处理；队首无法完整满足时停止，不能跳过它处理后面的订单。
3. REFUND 退指定订单的指定人数；数量超过当前有效人数或订单不存在时失败。
4. CHANGE 是整单改签。必须在旧票仍占用容量时检查新行程；新行程可完整满足才释放旧票并建立新票，否则状态不变。
5. 团体人数不可拆分。候补兑现后，候补编号成为有效订单编号。

流水如下：
{chr(10).join(op_lines)}

请输出严格 JSON，字段为：
{_json_shape({"availability":{"车次-席别":{"A-B":0,"B-C":0,"C-D":0,"D-E":0}},"active_orders":["订单号"],"waiting_orders":["候补号"],"failed_operations":[1]})}

availability 必须列出 G101-一等、G101-二等、G202-二等三个对象和四个区间；订单号及失败操作编号按升序排列。"""
    return TaskCase(
        id="T01",
        title="火车售票",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("availability", 4),
            Component("active_orders", 2),
            Component("waiting_orders", 2),
            Component("failed_operations", 2),
        ),
    )


def _task_t02() -> TaskCase:
    records = [
        ("F01", "雪松", "责任人", "林舟", 1, 1),
        ("F02", "轨道", "金额", "48", 2, 2),
        ("F03", "灯塔", "时间", "09:20", 1, 3),
        ("F04", "港湾", "状态", "已关闭", 2, 4),
        ("F05", "雪松", "金额", "72", 2, 5),
        ("F06", "轨道", "责任人", "周岚", 1, 6),
        ("F07", "灯塔", "责任人", "林舟", 2, 7),
        ("F08", "港湾", "金额", "31", 1, 8),
        ("F09", "雪松", "时间", "14:10", 4, 9),
        ("F10", "轨道", "状态", "待复核", 2, 10),
        ("F11", "灯塔", "金额", "56", 4, 11),
        ("F12", "港湾", "责任人", "陈默", 3, 12),
        ("F13", "雪松", "责任人", "陈默", 3, 13),
        ("F14", "轨道", "金额", "52", 3, 14),
        ("F15", "灯塔", "状态", "已关闭", 1, 15),
        ("F16", "港湾", "时间", "18:40", 2, 16),
        ("F17", "雪松", "金额", "69", 4, 17),
        ("F18", "轨道", "责任人", "周岚", 4, 18),
        ("F19", "灯塔", "时间", "09:35", 3, 19),
        ("F20", "港湾", "状态", "已恢复", 4, 20),
        ("F21", "雪松", "状态", "待复核", 1, 21),
        ("F22", "轨道", "时间", "11:50", 4, 22),
        ("F23", "灯塔", "责任人", "赵宁", 4, 23),
        ("F24", "港湾", "金额", "35", 3, 24),
        ("F25", "雪松", "责任人", "陈默", 4, 25),
        ("F26", "轨道", "状态", "已关闭", 3, 26),
        ("F27", "灯塔", "金额", "54", 3, 27),
        ("F28", "港湾", "时间", "18:55", 4, 28),
        ("F29", "雪松", "状态", "已恢复", 3, 29),
        ("F30", "轨道", "金额", "51", 4, 30),
        ("F31", "灯塔", "状态", "已恢复", 4, 31),
        ("F32", "港湾", "责任人", "赵宁", 1, 32),
        ("F33", "雪松", "时间", "14:05", 3, 33),
        ("F34", "轨道", "责任人", "林舟", 3, 34),
        ("F35", "灯塔", "时间", "09:32", 4, 35),
        ("F36", "港湾", "金额", "34", 4, 36),
        ("F37", "雪松", "状态", "已关闭", 4, 37),
        ("F38", "轨道", "状态", "已恢复", 4, 38),
        ("F39", "灯塔", "责任人", "周岚", 3, 39),
        ("F40", "港湾", "时间", "18:50", 3, 40),
    ]
    source_names = {1: "转述", 2: "同期记录", 3: "正式修订", 4: "校验系统"}
    winners = {}
    for record in records:
        record_id, case, field, value, rank, order = record
        key = (case, field)
        if key not in winners or (rank, order) > (winners[key][4], winners[key][5]):
            winners[key] = record
    facts = {
        case: {
            field: winners[(case, field)][3]
            for field in ["责任人", "金额", "时间", "状态"]
        }
        for case in ["雪松", "轨道", "灯塔", "港湾"]
    }
    overridden = sorted(
        record[0]
        for record in records
        if winners[(record[1], record[2])][0] != record[0]
    )
    expected = {
        "facts": facts,
        "overridden_ids": overridden,
        "system_record_count": sum(record[4] == 4 for record in records),
    }
    near_miss = dict(expected)
    near_miss["facts"] = {**facts, "雪松": {**facts["雪松"], "时间": "14:05"}}
    lines = [
        f"{record_id}｜{case}｜{source_names[rank]}｜{field}={value}"
        for record_id, case, field, value, rank, _ in records
    ]
    prompt = f"""下面是四起事件的交织档案。每条记录只修订同一事件的同一字段，不影响其他字段。需要确定的字段是责任人、金额、时间、状态。

证据优先级从高到低为：校验系统 > 正式修订 > 同期记录 > 转述。同一优先级出现多条记录时，编号较大的记录更新。金额只输出整数文本，不带单位。

档案：
{chr(10).join(lines)}

请输出严格 JSON：
{_json_shape({"facts":{"雪松":{"责任人":"","金额":"","时间":"","状态":""},"轨道":{"责任人":"","金额":"","时间":"","状态":""},"灯塔":{"责任人":"","金额":"","时间":"","状态":""},"港湾":{"责任人":"","金额":"","时间":"","状态":""}},"overridden_ids":["F01"],"system_record_count":0})}

overridden_ids 要列出所有未成为其“事件+字段”最终依据的记录编号，并按编号升序排列。"""
    return TaskCase(
        id="T02",
        title="交织档案解读",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("facts", 6),
            Component("overridden_ids", 3),
            Component("system_record_count", 1),
        ),
    )


def _task_t03() -> TaskCase:
    prompt = """下面记录了一种原创双人棋“越星棋”的若干对局片段。棋盘为 5×5，坐标列为 a-e、行为 1-5。红方前进方向是行号增大，蓝方前进方向是行号减小。每次只移动一枚己方棋子。记录中的“合法/非法”和行动后的局面都准确。

你需要从记录中判断四项隐藏规则。每项只有两个候选：

- 普通移动 STEP：O=向任意正交方向移动一格；D=向任意对角方向移动一格。
- 吃子 CAPTURE：J=隔着相邻敌子跳到其后空格并移除敌子；R=直接移动到相邻敌子所在格并替换它。
- 星格效果 STAR：E=落到 c3 后当前玩家立即再行动一次；T=落到 c3 后立刻交换行棋方。
- 获胜条件 WIN：H=红到达第5行或蓝到达第1行立即获胜；C=率先累计吃掉3枚棋子获胜。

对局记录：
1. 红 b2→b3，合法；棋子到 b3，轮到蓝。
2. 红 b2→c3，非法，局面不变。
3. 红 b2，蓝 b3，b4 为空；红 b2→b4，合法，蓝 b3 被移除，轮到蓝。
4. 红 b2，蓝 b3；红 b2→b3，非法。
5. 红 c2→c3，合法；随后仍由红方行动。
6. 红 a2→a3，合法；随后轮到蓝方。
7. 红 d4→d5，合法；记录立即标记红方获胜。
8. 红方此前已吃掉2枚蓝子；红 b2 跳过 b3 的蓝子到 b4，完成第3次吃子，但记录未结束，轮到蓝方。
9. 蓝 d4→d3，合法；随后轮到红方。
10. 蓝 d2→d1，合法；记录立即标记蓝方获胜。

新局面 Q：轮到红方。红子位于 b2、d3、e4；蓝子位于 b3、c2、d4；其余格为空。c3 是星格。请列出红子 b2 的全部合法行动，格式为“起点>终点”，按终点坐标字典序排列。

随后单独考虑局面 R：轮到红方，红子在 d4，蓝子在 c4，其余为空。若红方行动 d4>d5，请判断行动是否合法、行动后是否立即结束以及胜者。

只输出严格 JSON：
{"STEP":"O或D","CAPTURE":"J或R","STAR":"E或T","WIN":"H或C","Q_legal_moves":["b2>a2"],"R":{"legal":true,"ended":true,"winner":"红/蓝/无"}}"""
    expected = {
        "STEP": "O",
        "CAPTURE": "J",
        "STAR": "E",
        "WIN": "H",
        "Q_legal_moves": ["b2>a2", "b2>b1", "b2>b4", "b2>d2"],
        "R": {"legal": True, "ended": True, "winner": "红"},
    }
    near_miss = {**expected, "Q_legal_moves": ["b2>a2", "b2>b1", "b2>b4"]}
    return TaskCase(
        id="T03",
        title="观棋不语",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("STEP", 1),
            Component("CAPTURE", 2),
            Component("STAR", 1),
            Component("WIN", 2),
            Component("Q_legal_moves", 2),
            Component("R", 2),
        ),
    )


def _task_t04() -> TaskCase:
    people = {
        "P01": ("研发", 3, True, False),
        "P02": ("研发", 1, True, False),
        "P03": ("研发", 5, False, False),
        "P04": ("研发", 2, True, True),
        "P05": ("销售", 4, True, False),
        "P06": ("销售", 2, True, False),
        "P07": ("销售", 1, True, False),
        "P08": ("销售", 6, True, True),
        "P09": ("产品", 3, True, False),
        "P10": ("产品", 2, False, False),
        "P11": ("产品", 5, True, False),
        "P12": ("产品", 1, True, False),
        "P13": ("运营", 4, True, False),
        "P14": ("运营", 2, True, False),
        "P15": ("运营", 3, True, True),
        "P16": ("运营", 1, False, False),
        "P17": ("财务", 5, True, False),
        "P18": ("财务", 2, True, False),
        "P19": ("财务", 1, True, False),
        "P20": ("财务", 4, True, True),
    }
    draws = {
        "金奖1": ["P04", "P03", "P02", "P01"],
        "金奖2": ["P08", "P05", "P11", "P13"],
        "团队奖": ["P10", "P09", "P14"],
        "创新1": ["P05", "P02", "P17"],
        "创新2": ["P09", "P11", "P14"],
        "创新3": ["P15", "P13", "P18"],
        "幸运1": ["P11", "P06", "P18"],
        "幸运2": ["P09", "P07", "P19"],
        "幸运3": ["P14", "P17", "P01", "P19"],
        "幸运4": ["P13", "P12", "P18"],
    }
    invalid = []
    winners: Dict[str, Any] = {}
    personal_winners = set()
    team_department = ""

    def eligible(person_id: str, award: str) -> bool:
        department, years, present, historical = people[person_id]
        if not present or historical:
            return False
        if award.startswith("金奖"):
            return years >= 2 and person_id not in personal_winners
        if award == "团队奖":
            return True
        if award.startswith("创新"):
            return (
                years >= 2
                and person_id not in personal_winners
                and department != team_department
            )
        return person_id not in personal_winners and department != team_department

    for draw_id, sequence in draws.items():
        selected = None
        for person_id in sequence:
            if eligible(person_id, draw_id):
                selected = person_id
                break
            invalid.append(f"{draw_id}:{person_id}")
        assert selected
        if draw_id == "团队奖":
            team_department = people[selected][0]
            winners[draw_id] = team_department
        else:
            winners[draw_id] = selected
            personal_winners.add(selected)
    department_counts = Counter()
    for draw_id, winner in winners.items():
        if draw_id == "团队奖":
            department_counts[winner] += 1
        else:
            department_counts[people[winner][0]] += 1
    expected = {
        "winners": winners,
        "invalid_draws": invalid,
        "department_counts": dict(sorted(department_counts.items())),
    }
    near_miss = {**expected, "invalid_draws": invalid[:-1]}
    roster = [
        f"{person_id} 部门={data[0]} 入职={data[1]}年 出席={'是' if data[2] else '否'} 历史大奖={'是' if data[3] else '否'}"
        for person_id, data in people.items()
    ]
    draw_lines = [f"{draw_id}: {' > '.join(sequence)}" for draw_id, sequence in draws.items()]
    prompt = f"""请审计一次年会抽奖。每个抽取槽位都给出预先确定的候选顺序，从左到右寻找第一位当时符合资格的人；不重新随机。

参与者：
{chr(10).join(roster)}

规则：
1. 顺序依次为金奖1、金奖2、团队奖、创新1-3、幸运1-4。
2. 所有奖项都要求本人出席且没有“历史大奖”记录。
3. 金奖要求入职至少2年；个人一旦获得任何本次个人奖，后续不能再获个人奖。
4. 团队奖候选人只用于确定其部门，团队奖不算个人中奖。
5. 团队奖产生后，该部门所有人不能获得后续创新奖和幸运奖。
6. 创新奖要求入职至少2年；幸运奖无入职年限要求。
7. 每次跳过不合格候选，都记录为“槽位:人员”，保持实际检查顺序。

候选顺序：
{chr(10).join(draw_lines)}

输出严格 JSON：
{_json_shape({"winners":{"金奖1":"P00","团队奖":"部门"},"invalid_draws":["金奖1:P00"],"department_counts":{"研发":0}})}

winners 必须列出全部10个槽位；department_counts 统计各部门获得的个人奖数量加团队奖数量，只列出现过的部门。"""
    return TaskCase(
        id="T04",
        title="年会抽奖审计",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("winners", 6),
            Component("invalid_draws", 2),
            Component("department_counts", 2),
        ),
    )


def _task_t05() -> TaskCase:
    commands = [
        "POWER_ON",
        "OPEN_HATCH",
        "LOAD",
        "CLOSE_HATCH",
        "HEAT",
        "PRESSURIZE",
        "MIX",
        "COOL",
        "PRESSURIZE",
        "MIX",
        "VENT",
        "OPEN_HATCH",
        "UNLOCK",
        "VENT",
        "OPEN_HATCH",
        "UNLOAD",
        "CLOSE_HATCH",
        "LOAD",
        "HEAT",
        "HEAT",
        "COOL",
        "PRESSURIZE",
        "MIX",
        "VENT",
        "UNLOAD",
        "OPEN_HATCH",
        "UNLOAD",
        "CLOSE_HATCH",
        "POWER_OFF",
        "POWER_ON",
    ]
    state = {
        "power": "OFF",
        "battery": 8,
        "temperature": 2,
        "pressure": 0,
        "hatch": "CLOSED",
        "material": 0,
        "coolant": 3,
        "lock": 0,
        "fault": "NONE",
        "mixed_batches": 0,
    }
    illegal = []
    first_danger = None

    def invalid(index: int, code: str) -> None:
        illegal.append(index)
        state["fault"] = code

    for index, command in enumerate(commands, start=1):
        if command == "POWER_ON":
            if state["power"] != "OFF" or state["battery"] < 1 or state["lock"]:
                invalid(index, "E-POWER")
            else:
                state["power"] = "IDLE"
                state["battery"] -= 1
        elif command == "POWER_OFF":
            if state["pressure"] != 0 or state["hatch"] != "CLOSED":
                invalid(index, "E-OFF")
            else:
                state["power"] = "OFF"
        elif command == "OPEN_HATCH":
            if state["power"] != "IDLE" or state["pressure"] != 0 or state["lock"]:
                invalid(index, "E-HATCH")
            else:
                state["hatch"] = "OPEN"
        elif command == "CLOSE_HATCH":
            if state["hatch"] != "OPEN":
                invalid(index, "E-HATCH")
            else:
                state["hatch"] = "CLOSED"
        elif command == "LOAD":
            if state["hatch"] != "OPEN" or state["material"] != 0:
                invalid(index, "E-LOAD")
            else:
                state["material"] = 1
        elif command == "UNLOAD":
            if (
                state["hatch"] != "OPEN"
                or state["material"] == 0
                or state["temperature"] > 4
            ):
                invalid(index, "E-UNLOAD")
            else:
                state["material"] = 0
        elif command == "HEAT":
            if state["power"] != "IDLE" or state["hatch"] != "CLOSED":
                invalid(index, "E-HEAT")
            else:
                state["temperature"] += 3
                state["battery"] -= 1
        elif command == "COOL":
            if state["coolant"] == 0 or state["hatch"] != "CLOSED":
                invalid(index, "E-COOL")
            else:
                state["temperature"] = max(1, state["temperature"] - 4)
                state["coolant"] -= 1
        elif command == "PRESSURIZE":
            if state["hatch"] != "CLOSED" or state["material"] == 0:
                invalid(index, "E-PRESS")
            else:
                state["pressure"] += 3
                state["battery"] -= 1
        elif command == "VENT":
            if state["hatch"] != "CLOSED":
                invalid(index, "E-VENT")
            else:
                state["pressure"] = max(0, state["pressure"] - 4)
        elif command == "MIX":
            if (
                state["material"] == 0
                or state["temperature"] < 4
                or state["pressure"] < 2
                or state["lock"]
            ):
                invalid(index, "E-MIX")
            else:
                state["temperature"] += 1
                state["pressure"] += 1
                state["mixed_batches"] += 1
        elif command == "UNLOCK":
            if not state["lock"] or state["temperature"] > 5 or state["pressure"] > 2:
                invalid(index, "E-UNLOCK")
            else:
                state["lock"] = 0
                state["fault"] = "NONE"

        if index % 5 == 0:
            state["temperature"] += 1 if state["power"] == "IDLE" else 0
            if state["temperature"] >= 9 or state["pressure"] >= 7:
                state["lock"] = 1
                state["fault"] = "E-DANGER"
                if first_danger is None:
                    first_danger = index

    expected = {
        "final_state": state,
        "illegal_commands": illegal,
        "first_danger_check": first_danger,
        "successful_mix_count": state["mixed_batches"],
    }
    near_miss = {**expected, "illegal_commands": illegal[:-1]}
    prompt = f"""请逐条执行一台批处理机器的指令。初始状态：
power=OFF, battery=8, temperature=2, pressure=0, hatch=CLOSED, material=0, coolant=3, lock=0, fault=NONE, mixed_batches=0。

规则：
1. 非法指令不改变其他状态，但把 fault 写为对应错误码；非法编号需要全部记录。
2. POWER_ON：仅 OFF、battery≥1、lock=0；执行后 power=IDLE、battery-1。
3. POWER_OFF：仅 pressure=0 且 hatch=CLOSED；执行后 power=OFF。
4. OPEN_HATCH：仅 power=IDLE、pressure=0、lock=0。CLOSE_HATCH 仅舱门已开。
5. LOAD：仅舱门开且没有材料；UNLOAD：仅舱门开、有材料且 temperature≤4。
6. HEAT：仅 IDLE 且舱门关；temperature+3、battery-1。
7. COOL：仅 coolant>0 且舱门关；temperature 降4但不低于1，coolant-1。
8. PRESSURIZE：仅舱门关且有材料；pressure+3、battery-1。
9. VENT：仅舱门关；pressure 降4但不低于0。
10. MIX：仅有材料、temperature≥4、pressure≥2、lock=0；temperature+1、pressure+1、mixed_batches+1。
11. UNLOCK：仅 lock=1、temperature≤5、pressure≤2；执行后 lock=0、fault=NONE。
12. 每执行完第5、10、15、20、25、30条指令都进行自动检查：若 power=IDLE，temperature 先+1；随后若 temperature≥9 或 pressure≥7，则 lock=1、fault=E-DANGER。记录首次触发危险锁的检查编号。

连续指令：
{chr(10).join(f"{index:02d}. {command}" for index, command in enumerate(commands, 1))}

输出严格 JSON：
{_json_shape({"final_state":state,"illegal_commands":[1],"first_danger_check":0,"successful_mix_count":0})}"""
    return TaskCase(
        id="T05",
        title="大状态机器操作",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("final_state", 6),
            Component("illegal_commands", 3),
            Component("successful_mix_count", 1),
        ),
    )


def _task_t06() -> TaskCase:
    patterns = {
        "P1": "AABBCCDD",
        "P2": "BBAADDCC",
        "P3": "CCDDAABB",
        "P4": "DDCCBBAA",
        "P5": "ABCDABCD",
        "P6": "BCDABCDA",
        "P7": "CDABCDAB",
        "P8": "DABCDABC",
    }
    allowed = [
        ("P1", "P5"),
        ("P2", "P6"),
        ("P3", "P7"),
        ("P4", "P8"),
        ("P1", "P2"),
        ("P5", "P6"),
        ("P3", "P4"),
        ("P7", "P8"),
    ]
    diagonal = "ABACCCBC"
    solutions = []
    for choice in itertools.product(*allowed):
        if len(set(choice)) != 8:
            continue
        rows = [patterns[item] for item in choice]
        if "".join(rows[index][index] for index in range(8)) != diagonal:
            continue
        solutions.append((choice, rows))
    assert len(solutions) == 1
    choice, rows = solutions[0]
    weights = {"A": 1, "B": 2, "C": 3, "D": 4}
    checksum = sum(
        (row_index + 1) * (column_index + 1) * weights[value]
        for row_index, row in enumerate(rows)
        for column_index, value in enumerate(row)
    )
    column_counts = {
        f"C{column + 1}": dict(Counter(row[column] for row in rows))
        for column in range(8)
    }
    expected = {
        "patterns_by_row": list(choice),
        "rows": rows,
        "main_diagonal": diagonal,
        "checksum": checksum,
    }
    near_miss = {**expected, "patterns_by_row": list(choice[:-1]) + ["P7"]}
    prompt = f"""请完成一个 8×8 字符矩阵。每一行必须完整采用下列模式之一，P1-P8 每个恰好使用一次：
{chr(10).join(f"{key}={value}" for key, value in patterns.items())}

各行候选范围：
R1∈{{P1,P5}}；R2∈{{P2,P6}}；R3∈{{P3,P7}}；R4∈{{P4,P8}}；
R5∈{{P1,P2}}；R6∈{{P5,P6}}；R7∈{{P3,P4}}；R8∈{{P7,P8}}。

主对角线 R1C1,R2C2,...,R8C8 依次为 {diagonal}。

为了便于核查，正确矩阵的各列字符计数如下：
{json.dumps(column_counts, ensure_ascii=False, sort_keys=True)}

校验码计算：A=1、B=2、C=3、D=4；对每个单元格 Rij，将“行号×列号×字符值”求和。

请输出严格 JSON：
{_json_shape({"patterns_by_row":["P1"],"rows":["AABBCCDD"],"main_diagonal":"XXXXXXXX","checksum":0})}

patterns_by_row 和 rows 均按 R1 至 R8 顺序。"""
    return TaskCase(
        id="T06",
        title="字符矩阵",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("patterns_by_row", 3),
            Component("rows", 4),
            Component("main_diagonal", 1),
            Component("checksum", 2),
        ),
    )


def _task_t07() -> TaskCase:
    items = {
        "A": ("红", 3, 7, {"木", "快"}),
        "B": ("红", 5, 9, {"金"}),
        "C": ("蓝", 4, 6, {"木"}),
        "D": ("蓝", 2, 5, {"水", "快"}),
        "E": ("绿", 6, 10, {"金", "稳"}),
        "F": ("绿", 3, 4, {"水"}),
        "G": ("红", 4, 8, {"稳"}),
        "H": ("蓝", 5, 7, {"金", "快"}),
        "I": ("绿", 2, 6, {"木", "快"}),
        "J": ("红", 6, 11, {"水"}),
        "K": ("蓝", 3, 5, {"稳"}),
        "L": ("绿", 4, 8, {"金"}),
        "M": ("红", 2, 3, {"木"}),
        "N": ("蓝", 6, 10, {"水", "稳"}),
        "O": ("绿", 5, 9, {"快"}),
        "P": ("蓝", 2, 4, {"金", "木"}),
    }
    valid = []
    for combo in itertools.combinations(items, 6):
        chosen = set(combo)
        cost = sum(items[item][1] for item in combo)
        score = sum(items[item][2] for item in combo)
        colors = Counter(items[item][0] for item in combo)
        tags = Counter(tag for item in combo for tag in items[item][3])
        if not 20 <= cost <= 24:
            continue
        if colors != Counter({"红": 2, "蓝": 2, "绿": 2}):
            continue
        if tags["快"] != 2 or tags["金"] < 2 or tags["木"] < 2:
            continue
        if "B" in chosen and "E" not in chosen:
            continue
        if {"J", "N"} <= chosen or {"A", "M"} <= chosen:
            continue
        if "P" in chosen:
            score += tags["木"]
        if score % 7 != 3:
            continue
        valid.append(("".join(combo), cost, score))
    assert 2 <= len(valid) <= 30
    valid.sort()
    expected = {
        "combinations": [item[0] for item in valid],
        "count": len(valid),
        "first": valid[0][0],
        "last": valid[-1][0],
    }
    near_miss = {**expected, "count": len(valid) - 1}
    item_lines = [
        f"{key}: 颜色={value[0]}, 成本={value[1]}, 基础分={value[2]}, 标签={','.join(sorted(value[3]))}"
        for key, value in items.items()
    ]
    prompt = f"""从以下16个对象中找出所有满足条件的6对象组合。组合内部按字母排序，输出时用连续字符串表示，例如 ABCDEF。

对象：
{chr(10).join(item_lines)}

条件：
1. 总成本在20至24之间，含边界。
2. 红、蓝、绿各恰好选择2个。
3. “快”标签恰好出现2次；“金”至少2次；“木”至少2次。
4. 如果选B，必须选E。
5. J与N不能同时选择；A与M不能同时选择。
6. 总分先等于基础分之和；如果组合包含P，再额外加上组合内“木”标签的出现次数。
7. 最终总分除以7的余数必须为3。

必须完整列出全部合法组合，不能只找最优组合。输出严格 JSON：
{_json_shape({"combinations":["ABCDEF"],"count":1,"first":"ABCDEF","last":"ABCDEF"})}

combinations 按字符串字典序排列。"""
    return TaskCase(
        id="T07",
        title="目标穷举",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("combinations", 6),
            Component("count", 2),
            Component("first", 1),
            Component("last", 1),
        ),
    )


def _task_t08() -> TaskCase:
    dictionary = {
        "1": "RIVER",
        "2": "STONE",
        "3": "NORTH",
        "4": "ECHO",
        "5": "LIGHT",
    }
    encoded_blocks = [
        "@1",
        "{2|@2}",
        "<@3>",
        "@4{3|X}",
        "#2",
        "{2|<@5>}",
        "{2|@1<@4>}",
        "Q#1Z",
        "<{2|@2}>",
        "@3#4",
    ]

    def split_top(text: str, separator: str) -> List[str]:
        parts, start, depth = [], 0, 0
        for index, char in enumerate(text):
            if char in "{<":
                depth += 1
            elif char in "}>":
                depth -= 1
            elif char == separator and depth == 0:
                parts.append(text[start:index])
                start = index + 1
        parts.append(text[start:])
        return parts

    blocks: List[str] = []

    def decode(text: str) -> str:
        result = ""
        index = 0
        while index < len(text):
            if text[index] == "@":
                result += dictionary[text[index + 1]]
                index += 2
            elif text[index] == "#":
                result += blocks[int(text[index + 1]) - 1]
                index += 2
            elif text[index] == "{":
                close = _matching(text, index, "{", "}")
                count_text, body = split_top(text[index + 1 : close], "|")
                result += decode(body) * int(count_text)
                index = close + 1
            elif text[index] == "<":
                close = _matching(text, index, "<", ">")
                result += decode(text[index + 1 : close])[::-1]
                index = close + 1
            else:
                result += text[index]
                index += 1
        return result

    for encoded in encoded_blocks:
        blocks.append(decode(encoded))
    decoded = "|".join(blocks)
    plain = "".join(blocks)
    expected = {
        "blocks": blocks,
        "decoded": decoded,
        "length_without_separators": len(plain),
        "count_R": plain.count("R"),
        "checksum_mod_997": sum(ord(char) for char in plain) % 997,
    }
    near_miss = {**expected, "count_R": expected["count_R"] + 1}
    prompt = f"""请按下面的原创规则解压信息。所有输出均区分字符顺序，但字母只使用大写。

字典：@1={dictionary['1']}，@2={dictionary['2']}，@3={dictionary['3']}，@4={dictionary['4']}，@5={dictionary['5']}。

规则：
1. @n 替换为对应字典文本。
2. {{k|TEXT}} 表示先递归解码 TEXT，再连续重复 k 次。
3. <TEXT> 表示先递归解码 TEXT，再把得到的完整字符序列倒序。
4. #n 表示复制已经完成解码的第 n 个顶层块，编号从1开始。
5. 顶层块按给定顺序解码；块之间最终使用字符 | 连接。| 不计入长度、字符计数和校验码。
6. 校验码为所有解码字母 ASCII 码之和除以997的余数。

顶层块：
{chr(10).join(f"{index}. {value}" for index, value in enumerate(encoded_blocks, 1))}

输出严格 JSON：
{_json_shape({"blocks":["TEXT"],"decoded":"TEXT|TEXT","length_without_separators":0,"count_R":0,"checksum_mod_997":0})}"""
    return TaskCase(
        id="T08",
        title="信息解压",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("blocks", 4),
            Component("decoded", 3),
            Component("length_without_separators", 1),
            Component("count_R", 1),
            Component("checksum_mod_997", 1),
        ),
    )


def _matching(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    for index in range(start, len(text)):
        if text[index] == opening:
            depth += 1
        elif text[index] == closing:
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unclosed expression")


def _task_t09() -> TaskCase:
    start = (1, 0, 0, 2, 1, 1, 0, 0)
    # inlet, bypass, drained, blockA, blockB, filter, chemical, pump
    action_order = [
        "关闭进水",
        "打开旁路",
        "排空",
        "拆滤网",
        "投化学剂",
        "机械疏通A",
        "准备泵",
        "反冲B",
        "强制冲洗",
        "装滤网",
        "关闭旁路",
        "打开进水",
    ]

    def transitions(state: Tuple[int, ...]) -> Iterable[Tuple[str, int, Tuple[int, ...], int]]:
        inlet, bypass, drained, block_a, block_b, filter_on, chemical, pump = state
        if inlet:
            yield "关闭进水", 1, (0, bypass, drained, block_a, block_b, filter_on, chemical, pump), 0
        if not inlet and not bypass:
            yield "打开旁路", 1, (inlet, 1, drained, block_a, block_b, filter_on, chemical, pump), 0
        if not inlet and bypass and not drained:
            yield "排空", 2, (inlet, bypass, 1, block_a, block_b, filter_on, chemical, pump), 0
        if drained and filter_on:
            yield "拆滤网", 1, (inlet, bypass, drained, block_a, block_b, 0, chemical, pump), 0
        if drained and not filter_on and block_a and not chemical:
            yield "投化学剂", 1, (inlet, bypass, drained, 0, block_b + 1, filter_on, 1, pump), 0
        if drained and not filter_on and block_a:
            yield "机械疏通A", 2, (inlet, bypass, drained, block_a - 1, block_b, filter_on, chemical, pump), 0
        if drained and not filter_on and not pump:
            yield "准备泵", 1, (inlet, bypass, drained, block_a, block_b, filter_on, chemical, 1), 0
        if drained and not filter_on and pump and block_b:
            yield "反冲B", 2, (inlet, bypass, drained, block_a, 0, filter_on, chemical, pump), 0
        if drained and not filter_on and block_b:
            yield "强制冲洗", 1, (inlet, bypass, drained, block_a, 0, filter_on, chemical, pump), 1
        if drained and not filter_on and block_a == 0 and block_b == 0:
            yield "装滤网", 1, (inlet, bypass, drained, block_a, block_b, 1, chemical, pump), 0
        if not inlet and bypass and filter_on and block_a == 0 and block_b == 0:
            yield "关闭旁路", 1, (inlet, 0, drained, block_a, block_b, filter_on, chemical, pump), 0
        if not inlet and not bypass and filter_on and block_a == 0 and block_b == 0:
            yield "打开进水", 1, (1, bypass, 0, block_a, block_b, filter_on, chemical, pump), 0

    action_rank = {action: index for index, action in enumerate(action_order)}
    queue = [(0, 0, 0, tuple(), tuple(), start)]
    best = {}
    solutions = []
    while queue:
        damage, cost, steps, rank_path, name_path, state = heapq.heappop(queue)
        metric = (damage, cost, steps, rank_path)
        if state in best and best[state] <= metric:
            continue
        best[state] = metric
        if state[0] == 1 and state[1] == 0 and state[3] == 0 and state[4] == 0 and state[5] == 1:
            solutions.append((metric, name_path, state))
            continue
        if steps >= 14:
            continue
        for action, action_cost, next_state, action_damage in transitions(state):
            heapq.heappush(
                queue,
                (
                    damage + action_damage,
                    cost + action_cost,
                    steps + 1,
                    rank_path + (action_rank[action],),
                    name_path + (action,),
                    next_state,
                ),
            )
    best_metric, path, final_state = min(solutions)
    damage, cost, steps, _ = best_metric
    expected = {
        "sequence": list(path),
        "damage": damage,
        "cost": cost,
        "steps": steps,
        "final": {
            "inlet_open": final_state[0],
            "bypass_open": final_state[1],
            "drained": final_state[2],
            "block_A": final_state[3],
            "block_B": final_state[4],
            "filter_installed": final_state[5],
            "chemical_used": final_state[6],
            "pump_ready": final_state[7],
        },
    }
    near_miss = {**expected, "damage": 1}
    prompt = f"""请为一段堵塞管道制定操作方案。初始状态：
进水开启、旁路关闭、未排空、A段堵塞等级2、B段堵塞等级1、滤网已安装、化学剂未使用、泵未准备。

操作及成本：
1. 关闭进水(1)：进水开启时可用。
2. 打开旁路(1)：进水关闭且旁路关闭时可用。
3. 排空(2)：进水关闭、旁路打开且尚未排空时可用。
4. 拆滤网(1)：已排空且滤网已安装。
5. 投化学剂(1)：已排空、滤网已拆、A仍堵塞、化学剂未使用；A立即清零，但B堵塞等级+1。
6. 机械疏通A(2)：已排空、滤网已拆、A仍堵塞；A等级-1。
7. 准备泵(1)：已排空、滤网已拆、泵未准备。
8. 反冲B(2)：已排空、滤网已拆、泵已准备且B仍堵塞；B清零。
9. 强制冲洗(1)：已排空、滤网已拆且B仍堵塞；B清零，但造成1次永久损坏。
10. 装滤网(1)：已排空、滤网已拆且A、B均为0。
11. 关闭旁路(1)：进水关闭、旁路打开、滤网已装且A、B均为0。
12. 打开进水(1)：进水关闭、旁路关闭、滤网已装且A、B均为0；执行后不再处于排空状态。

目标：最终进水开启、旁路关闭、A=B=0、滤网已安装。按以下顺序优化：先最小化永久损坏次数，再最小化总成本，再最小化操作数；若仍相同，按上面1至12的操作顺序进行字典序比较。

输出严格 JSON：
{_json_shape({"sequence":["关闭进水"],"damage":0,"cost":0,"steps":0,"final":{"inlet_open":1,"bypass_open":0,"drained":0,"block_A":0,"block_B":0,"filter_installed":1,"chemical_used":0,"pump_ready":0}})}"""
    return TaskCase(
        id="T09",
        title="管道疏通",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("sequence", 5),
            Component("damage", 1),
            Component("cost", 1),
            Component("steps", 1),
            Component("final", 2),
        ),
    )


def _task_t10() -> TaskCase:
    beams = {
        "A": {"T1": "N", "T2": "N"},
        "B": {"T2": "E", "T3": "E"},
        "C": {"T3": "S", "T4": "S"},
        "D": {"T4": "W", "T5": "W"},
        "E": {"T5": "N", "T6": "N"},
        "F": {"T6": "E", "T1": "E"},
        "G": {"T2": "S", "T5": "S"},
        "H": {"T3": "N", "T6": "N"},
        "I": {"T1": "W", "T4": "W"},
        "J": {"T1": "S", "T3": "W", "T5": "E"},
    }
    unsafe = {"J"}
    conflicts = {frozenset(pair) for pair in [("A", "C"), ("B", "E"), ("E", "I")]}
    requirements = {"T1": 2, "T2": 1, "T3": 1, "T4": 2, "T5": 1, "T6": 1}
    valid = []
    mounts = sorted(beams)
    for size in range(1, len(mounts) + 1):
        for combo in itertools.combinations(mounts, size):
            chosen = set(combo)
            if chosen & unsafe:
                continue
            if any(pair <= chosen for pair in conflicts):
                continue
            sources = {
                target: sorted(
                    f"{mount}:{beams[mount][target]}"
                    for mount in combo
                    if target in beams[mount]
                )
                for target in requirements
            }
            if any(
                len({source.split(":")[1] for source in sources[target]}) < required
                for target, required in requirements.items()
            ):
                continue
            valid.append((combo, sources))
        if valid:
            break
    assert valid
    combo, sources = valid[0]
    expected = {
        "lasers": list(combo),
        "count": len(combo),
        "target_sources": sources,
        "unused_safe_mounts": sorted(set(mounts) - set(combo) - unsafe),
    }
    near_miss = {**expected, "lasers": list(combo[:-1])}
    layout = """##########
#A..T1..B#
#..../...#
#T2.C.T3.#
#..G..!J.#
#T4.D.T5.#
#...\\....#
#I..T6..F#
#H.....E.#
##########"""
    beam_lines = [
        f"{mount}: " + ", ".join(f"{target}({direction})" for target, direction in targets.items())
        for mount, targets in beams.items()
    ]
    prompt = f"""某10×10房间中，#为墙，T1-T6为目标，A-J为候选激光器安装位，!为敏感区，/和\\为固定镜面。控制器已经把每个候选位开启后的完整光路计算为下表；括号中的 N/E/S/W 表示光束进入目标的方向。

示意图：
{layout}

光路表：
{chr(10).join(beam_lines)}

规则：
1. 选择J会照射敏感区，因此J禁止使用。
2. A与C、B与E、E与I分别会互相照射，每一对不能同时选择。
3. T1和T4必须至少从2个不同方向被照射；T2、T3、T5、T6至少从1个方向被照射。
4. 首先最小化激光器数量；若有多个最小方案，选择激光器编号数组字典序最小的方案。
5. target_sources 中列出最终方案对每个目标的全部“激光器:方向”，按字符串升序排列。
6. unused_safe_mounts 列出未采用且不是J的安全候选位。

输出严格 JSON：
{_json_shape({"lasers":["A"],"count":1,"target_sources":{"T1":["A:N"]},"unused_safe_mounts":["B"]})}"""
    return TaskCase(
        id="T10",
        title="激光布局",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("lasers", 4),
            Component("count", 1),
            Component("target_sources", 4),
            Component("unused_safe_mounts", 1),
        ),
    )


def build_tasks() -> List[TaskCase]:
    tasks = [
        _task_t01(),
        _task_t02(),
        _task_t03(),
        _task_t04(),
        _task_t05(),
        _task_t06(),
        _task_t07(),
        _task_t08(),
        _task_t09(),
        _task_t10(),
    ]
    assert [task.id for task in tasks] == [f"T{index:02d}" for index in range(1, 11)]
    assert all(sum(component.points for component in task.components) == 10 for task in tasks)
    return tasks
