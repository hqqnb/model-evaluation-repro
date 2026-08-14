import copy
from typing import List

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.models import Component, TaskCase
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.solvers_advanced import solve_s05, solve_s06
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.solvers_search import solve_s03, solve_s04
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.solvers_world import solve_s01, solve_s02


def _near_miss(answer, field, replacement):
    result = copy.deepcopy(answer)
    result[field] = replacement
    return result


def _s01() -> TaskCase:
    prompt = """有5张卡 A、B、C、D、E，每张只能选或不选。合法世界必须同时满足：
1）恰好选2张；2）若选A，必须选B；3）C、D恰好选1张；
4）若选E，不能选B；5）C或E至少选1张。

请按字符串字典序列出全部合法世界，例如选A、D写作“AD”。再判断三个命题：
“C或D”、“B”、“A”各属于必然、仅可能、不可能中的哪一类。
分类只能使用 `necessary`、`possible_only`、`impossible`。对每个命题都给出
true和false见证；不存在的见证写 null，有多个见证时取字典序最小。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `worlds`、`world_count`、
`query_classes`、`witnesses`。`query_classes` 和 `witnesses` 内均使用
`C_or_D`、`B`、`A` 三个键；每个 witness 含 `true`、`false`。"""
    expected = solve_s01()
    near_miss = _near_miss(
        expected,
        "query_classes",
        {"C_or_D": "possible_only", "B": "possible_only", "A": "impossible"},
    )
    return TaskCase(
        id="S01",
        title="可能世界",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("worlds", 4, "set"),
            Component("world_count", 1),
            Component("query_classes", 3),
            Component("witnesses", 2),
        ),
    )


def _s02() -> TaskCase:
    prompt = """有一张颜色卡 color，只能是 red、blue、green；另有开关 C、D、E。
规则如下，编号不能改：
R1 color=red；R2 color=blue；R3 C=true；R4 color=green；
R5 若C=true则D=true；R6 D=true；R7 E=false。

原规则整体不一致。你可以删除规则；删除后，剩余规则必须存在至少一个满足它们的赋值。
请找出删除数量最少的所有删除集合，并为每个集合给出一个满足剩余规则的赋值。
最后列出所有最小修复中都保留的规则。删除集合和规则编号均按字典序排列；
赋值中的开关使用0/1。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `repair_size`、
`deletion_sets`、`witnesses`、`common_kept`。`witnesses` 以删除集合中
规则编号用加号连接后的字符串为键，每个赋值必须包含 `color`、`C`、`D`、`E`。"""
    expected = solve_s02()
    near_miss = _near_miss(
        expected,
        "deletion_sets",
        [["R1", "R2"], ["R1", "R4"]],
    )
    return TaskCase(
        id="S02",
        title="最小修复",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("repair_size", 1),
            Component("deletion_sets", 4, "set"),
            Component("witnesses", 4),
            Component("common_kept", 1, "set"),
        ),
    )


def _s03() -> TaskCase:
    prompt = """有一个三位状态 ABC，初始状态未知，可能是全部8种000至111。目标是010。
你必须使用同一条动作序列处理所有初始状态，不能观察中间状态。
动作只改变写明的位，前置条件不满足时该动作非法：
A0：把A设为0；BA：把B设为A；flipB：仅当A=0时翻转B；
CB：仅当B=1时把C设为B；flipC：仅当B=1时翻转C。

请找出保证所有初始状态最终都为010的最短序列。输出每个初始状态的最终状态，
并给出最短步数和覆盖证明：`coverage` 列出该序列成功覆盖的全部初始状态，
`lower_bound` 填你确认任何更短序列都不可能成功的步数下界。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `sequence`、`steps`、
`final_by_initial`、`lower_bound`、`coverage`。`final_by_initial` 必须包含
从000到111的全部8个初始状态，`coverage` 按字符串字典序排列。"""
    expected = solve_s03()
    near_miss = _near_miss(expected, "sequence", expected["sequence"][:-1])
    return TaskCase(
        id="S03",
        title="稳健计划",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("sequence", 3),
            Component("steps", 1),
            Component("final_by_initial", 3),
            Component("lower_bound", 2),
            Component("coverage", 1, "set"),
        ),
    )


def _s04() -> TaskCase:
    prompt = """有6句陈述，真或假由陈述内容决定；“真话总数”统计这6句本身。
S1：真话总数恰好是3。
S2：S1是真的。
S3：S2与S5真假相反。
S4：S3是假的。
S5：S4与S6真假相同。
S6：真话总数不是2。

请找出所有自洽的真假赋值。字符串第1至第6位依次对应S1至S6，
T表示真、F表示假。即使只有一个解，也必须输出完整solutions数组，不得遗漏。还要输出解的数量，
以及所有解中始终为真的句子和始终为假的句子。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `solutions`、`count`、
`always_true`、`always_false`。`solutions` 按字符串字典序排列；两个句子列表
均按编号升序排列。若没有始终为真或始终为假的句子，相应位置输出空数组。"""
    expected = solve_s04()
    near_miss = _near_miss(expected, "solutions", ["FFTFFF"])
    return TaskCase(
        id="S04",
        title="自指陈述",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("solutions", 5, "set"),
            Component("count", 1),
            Component("always_true", 2, "set"),
            Component("always_false", 2, "set"),
        ),
    )


def _s05() -> TaskCase:
    prompt = """暗号数 n 是0、1、2、3中的一个，你的目标是猜中n。提问不会改变n。
提问 parity：只回答 even 或 odd；提问 low：n为0/1回答 low，否则回答 high；
提问 high：n为0/3回答 edge，否则回答 middle。提问后可以根据回答继续提问一次，
然后必须猜数。每次提问和最终猜数都各计1步。

请给出一个保证成功的最短策略：第一步提问什么；每种回答下第二步提问什么；
第二步每种回答下猜哪个数；并给出最坏步数。若有多棵最短策略，问题优先级为
`parity` < `low` < `high`：第一步和每个反馈分支都选优先级最靠前的可行问题。
另在回答为even的状态中，找出“先问parity后直接猜0”的失败状态。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `guaranteed_win`、
`first_action`、`policy`、`worst_case_steps`、`fast_action_counterexample`。
`policy` 以第一问的实际反馈为键，每个分支含 `question`，并以第二问的实际反馈为键
写 `guess0` 至 `guess3`。反例的 `action` 固定写 `parity_even_then_guess0`。"""
    expected = solve_s05()
    near_miss = copy.deepcopy(expected)
    near_miss["policy"]["odd"]["high"] = "guess1"
    return TaskCase(
        id="S05",
        title="隐藏信息博弈",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("guaranteed_win", 2),
            Component("first_action", 1),
            Component("policy", 4),
            Component("worst_case_steps", 2),
            Component("fast_action_counterexample", 1),
        ),
    )


def _s06() -> TaskCase:
    prompt = """输入变量为A=0、B=1、C=1。按以下顺序计算：
D=A XOR B；E=D AND (NOT C)；F=D OR (A AND B)；G=A AND C；H=F XOR G。

分别输出原始结果、强制干预do(D=0)后的结果、把输入A改为1后的结果。
干预会替换指定变量的原始规则，然后其余变量按顺序重算。
再列出两次干预后取值相同的变量，只比较两次干预结果，不与原始结果比较。
最后只在候选变量D、E中寻找变量数最少的干预集合：
把候选变量强制改成与原始结果相反，要求H与原始H不同。

只输出合法 JSON，不得添加解释。顶层键必须且只能为 `baseline`、`do_D_0`、
`do_A_1`、`invariants`、`minimum_causes_for_H_flip`。前三个对象都按D、E、F、G、H
顺序给出0/1；`invariants` 按字母序；最小集合按先长度、后字典序排列。"""
    expected = solve_s06()
    near_miss = _near_miss(
        expected,
        "minimum_causes_for_H_flip",
        [["E"]],
    )
    return TaskCase(
        id="S06",
        title="因果干预",
        prompt=prompt,
        expected=expected,
        near_miss=near_miss,
        components=(
            Component("baseline", 2),
            Component("do_D_0", 2),
            Component("do_A_1", 2),
            Component("invariants", 2, "set"),
            Component("minimum_causes_for_H_flip", 2, "set"),
        ),
    )


def build_tasks() -> List[TaskCase]:
    return [_s01(), _s02(), _s03(), _s04(), _s05(), _s06()]
