# Coding 能力测试（10 题）

通用规则：

- 语言：Python 3.11，**仅限标准库**，不得使用第三方包；
- 每题提交一个独立文件（文件名见题内说明），只实现规定的类/函数，不要读取标准输入；
- 黑盒测试由评测脚本自动运行（`python3 test.py <你的文件>`），测试数据对考生不可见；
- 每题建议时限 30 分钟，允许纸笔与本地运行调试，禁止联网。

---

## C1 滑动窗口奇数次异或（算法）

给定长度为 n 的整数数组 a 和窗口大小 k。对每个长度为 k 的连续子窗口，求该窗口内**出现次数为奇数**的所有元素的异或和；若窗口内所有元素出现次数都是偶数，则结果为 0。

实现：

```python
def solve(n: int, k: int, a: list[int]) -> list[int]:
    """返回长度为 n-k+1 的列表，第 i 个元素为窗口 a[i:i+k] 的答案。"""
```

约束：1 ≤ k ≤ n ≤ 10^6，1 ≤ a[i] ≤ 10^9。

示例：

```
n=5, k=3, a=[1,2,2,3,3]
窗口 [1,2,2]：1 出现 1 次 → 答案 1
窗口 [2,2,3]：3 出现 1 次 → 答案 3
窗口 [2,3,3]：2 出现 1 次 → 答案 2
输出 [1,3,2]
```

要求：时间复杂度 O(n)，空间 O(k) 或 O(n) 均可。评测包含 n=10^6 的大数据性能测试。

提交文件：`solution.py`（只包含 `solve` 函数及必要 import）。

---

## C2 连通块第 K 大（数据结构）

有 n 个点，初始各自独立，每个点 i 有一个值 v_i（互不相同）。支持两类操作：

- `1 a b`：把 a、b 所在的两个连通块合并（若已同块则忽略）；
- `2 x k`：查询 x 所在连通块中第 k 大的值（k=1 为最大值）；若 k 大于块内点数，返回 -1。

实现：

```python
class DSUKth:
    def __init__(self, values: list[int]):
        """values[0..n-1] 为每个点的值。"""

    def union(self, a: int, b: int) -> None:
        """a,b 为 1 起始编号。"""

    def kth_largest(self, x: int, k: int) -> int:
        """x 为 1 起始编号。"""
```

约束：n, q ≤ 2×10^5。期望均摊复杂度 O(log² n) 或更优。

提交文件：`solution.py`（只包含 `DSUKth` 类）。

示例：

```
values = [5, 1, 9, 3, 7]
union(1, 3)          # 块 {1,3} 值 {5,9}
union(3, 5)          # 块 {1,3,5} 值 {5,9,7}
kth_largest(1, 1)    # 9
kth_largest(5, 2)    # 7
kth_largest(2, 1)    # 1（点 2 独立）
kth_largest(1, 9)    # -1（块内只有 3 个点）
```

---

## C3 并发令牌桶限流器（并发）

实现一个线程安全的令牌桶限流器：

```python
class RateLimiter:
    def __init__(self, capacity: float, refill_per_second: float):
        """capacity：桶容量（最大积攒令牌数）；refill_per_second：每秒补充速率。"""

    def try_acquire(self, key: str, tokens: float, now_ms: int) -> bool:
        """key 相同视为同一个桶；now_ms 为当前毫秒时间戳（单调不减）。
        若桶内令牌足够则扣除并返回 True，否则返回 False。"""
```

要求：

1. 线程安全：多个线程并发调用同一 key 不得出现重复放行/超发；
2. 时间正确：以毫秒粒度按速率补充令牌，令牌数不得超过 capacity；
3. 支持多个 key 相互独立。

评测：单线程正确性测试（限速总量与突发容量）、8 线程 × 10 万次压力测试（不得抛异常、不得超发）。所有调用共享同一个实例，但允许在方法内部加锁。

提交文件：`solution.py`（只包含 `RateLimiter` 类）。

---

## C4 日志聚合性能优化（性能）

评测目录提供 `data.log`：500,000 行，每行格式：

```
<时间戳>|<级别>|<节点>|<消息>
```

其中级别 ∈ {INFO, WARN, ERROR}，节点与消息不含 `|`，消息可为空。

格式不完整（段数不足 4）的行视为无效行，解析时跳过，不参与统计。

要求：统计每个 (级别, 节点) 组合的 ERROR 消息条数，按级别字典序、再按节点字典序输出：

```python
def aggregate(path: str) -> list[tuple[str, str, int]]:
    """返回 [(level, node, count), ...]"""
```

评测目录同时提供一份 `slow.py`：它用双重循环逐对统计（O(n²)），500k 行无法在时限内跑完。你的实现必须：

- 输出与参考答案完全一致；
- 在 Python 3.11、普通开发机（Apple Silicon）上 **3 秒内**完成（评测脚本给 4 秒容差）；
- 说明你的实现复杂度（在代码注释中写明）。

提交文件：`fast.py`（只包含 `aggregate` 函数）。

---

## C5 修复二分查找（调试）

评测目录提供 `buggy.py`，其函数意图是：返回数组中**最后一个小于 target 的元素**的下标（0 起始）；不存在时返回 -1。

```python
def last_less_than(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid
        else:
            hi = mid
    return lo if a[lo] < target else -1
```

该实现至少存在一个导致死循环或结果错误的缺陷。

要求提交 `fixed.py`，包含同名函数：

1. 正确实现上述语义；
2. 在 `if __name__ == "__main__"` 中附上至少 3 个你认为能暴露原缺陷的回归测试（直接 assert）；
3. 空数组、target 小于全部元素、target 大于全部元素、含重复元素的情况必须正确。

评测脚本会对死循环设置超时保护。

---

## C6 安全加固（安全）

评测目录提供 `loader.py`，包含两个不安全函数：

```python
def load_report(filename: str, base_dir: str = "reports") -> str:
    path = os.path.join(base_dir, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()

def run_export(user_arg: str) -> str:
    return subprocess.run(
        "export_data " + user_arg, shell=True, capture_output=True, text=True
    ).stdout
```

要求提交 `secure.py`，实现语义兼容但安全的两版函数：

1. `load_report` 只允许读取 `base_dir` 目录内的普通文件：拒绝绝对路径、`..` 路径穿越、符号链接逃逸；被拒绝时抛出 `ValueError`；
2. `run_export` 不再使用 shell 拼接：以参数列表方式执行 `export_data`，并拒绝任何非预期参数；
3. 在文件顶部注释说明：原有代码各存在什么漏洞、攻击者如何利用、你的修复为什么有效。

评测会对穿越（`../../etc/passwd`）、绝对路径、命令注入（`; touch /tmp/pwned`、`$(...)`、管道）等输入进行攻击测试，并验证合法输入仍可正常读取。

提交文件：`secure.py`。合法的 `run_export` 参数仅限 `--json`、`--csv`、`--quiet` 之一，其他一律拒绝。

---

## C7 幂等任务队列（设计 + 实现）

场景：多租户后台任务系统。客户端可能因网络重试而重复提交同一个任务，系统必须保证同一 `task_id` 只被执行一次。

要求两部分：

**A. 设计说明（≤ 600 字）**：给出你的 API 设计、存储方案、幂等去重方案，并说明你如何处理：至少一次 vs 至多一次、任务顺序、失败重试、队列积压（背压）。写清楚你选择的关键权衡。

**B. 实现**：

```python
class TaskScheduler:
    def enqueue(self, task_id: str, priority: int, payload: str) -> bool:
        """返回 True 表示本次真正入队；重复 task_id 返回 False 且不重复入队。"""

    def dequeue(self) -> tuple[str, str] | None:
        """返回 (task_id, payload)；按 priority 升序，同优先级按入队先后。"""

    def ack(self, task_id: str) -> None:
        """确认完成，从队列移除。"""
```

要求：enqueue/dequeue/ack 行为正确；同一 task_id 重复 enqueue 不产生重复任务；ack 不存在的 id 不抛异常。

提交文件：`scheduler.py`（只包含 `TaskScheduler` 类）。

评测脚本包含去重、优先级顺序、FIFO 顺序、ack 后不再出队等测试。

---

## C8 订单校验函数测试（测试设计）

被测函数 `validate_order(order: dict) -> list[str]` 返回校验错误信息列表；合法订单返回空列表。规格如下：

- `id`：非空字符串；
- `amount`：数值，且 0 < amount ≤ 10000；
- `currency`：恰好 3 个大写英文字母；
- `email`：匹配常见邮箱格式（本地部分@域名，域名至少含一个点）；
- `items`：列表，长度 1~50；每项为字典，含 `name`（非空，≤100 字符）、`qty`（整数 1~99）、`unit_price`（数值，>0）；
- 订单金额校验：`amount` 与 `sum(qty * unit_price)` 的差不超过 0.01（容忍浮点舍入）。

评测目录提供两份实现：`ref_impl.py`（符合规格）与 `impl.py`（**含 3 个被植入的缺陷**）。

要求提交 `tests.py`，定义若干 `test_*` 函数，每个函数调用目标模块的 `validate_order` 并 `assert` 规格要求的行为（例如：某非法订单应返回非空错误）。测试通过环境变量 `TARGET_IMPL` 指向被测文件。

评测方式：你的测试先在 `ref_impl.py` 上运行（**必须全部通过**，防止误报），再在 `impl.py` 上运行；能导致失败的测试数按植入缺陷分组，发现 ≥2 个缺陷即合格，3 个全发现为满分。

提交文件：`tests.py`。测试函数通过 `os.environ["TARGET_IMPL"]` 指向的文件导入 `validate_order`。

---

## C9 自定义日志解析（数据处理）

日志记录格式（每条记录可跨多行）：

```
[YYYY-MM-DD HH:MM:SS.mmm] LVL=<级别> NODE=<节点> MSG="<消息>"
```

规则：

- 消息以 `"` 开始、以**未转义的** `"` 结束，可包含真实换行；
- 消息内转义：`\"` 表示引号、`\\` 表示反斜杠、`\n` 表示换行符；
- 字段之间以单个空格分隔，顺序固定；
- 级别 ∈ {INFO, WARN, ERROR}；
- 非法记录：缺少字段、级别非法、引号未闭合、时间格式不对，均记为错误。

实现：

```python
def parse_log(data: str) -> tuple[list[tuple[str, str, str, str]], list[tuple[int, str]]]:
    """返回 (records, errors)。
    records: [(timestamp, level, node, message), ...]，按出现顺序；
    errors:  [(1起始行号, 原因), ...]。"""
```

评测包含：转义序列、消息内换行、UTF-8 中文/emoji、空消息、缺字段、非法级别、未闭合引号、多行错误定位等用例，输出与参考实现逐项比对。

提交文件：`solution.py`（只包含 `parse_log` 函数）。

---

## C10 AX-9 帧协议编解码（协议）

实现私有链路协议 AX-9 的编码与解码。

帧格式（编码后）：

```
0x7E <长度字节> <负载字节> <CRC 高字节> <CRC 低字节> 0x7E
```

- 长度字节 = 负载长度（1~255）；
- CRC 为 CRC-16/XMODEM（初始值 0x0000，多项式 0x1021），先高字节后低字节；
- 帧内转义：负载与 CRC 中出现 `0x7E` 时编码为 `0x7D 0x5E`，出现 `0x7D` 时编码为 `0x7D 0x5D`；
- 解码时先反转义，再校验长度与 CRC。

实现：

```python
def encode(payload: bytes) -> bytes:
    """返回完整帧。"""

def decode(frame: bytes) -> bytes:
    """返回负载；格式非法（边界缺失、长度不符、CRC 错误、转义错误）抛 ValueError，并说明原因。"""
```

评测包含：固定向量（与参考实现逐字节比对）、1000 组随机负载往返一致性、恶意帧（CRC 篡改、长度不符、截断、孤立 0x7D）必须报错。

提交文件：`solution.py`（只包含 `encode`、`decode` 两个函数）。
