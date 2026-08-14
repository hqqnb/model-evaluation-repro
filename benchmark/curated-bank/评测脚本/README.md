# Coding 题评测脚本使用说明

本目录每个 `cXX_*` 文件夹对应一道 Coding 题，包含：

- `test.py`：黑盒评测入口（隐藏测试）；
- `reference.py`（或 `reference_tests.py`）：MA 参考实现/参考测试，**不得随题目下发**；
- 部分目录附带 `slow.py` / `buggy.py` / `loader.py` / `impl.py` 等题目素材。

## 运行方式

候选文件由 MA 收齐后统一运行：

```bash
cd 评测脚本
python3 c01_sliding_window/test.py <候选目录>/solution.py
python3 c02_dsu_kth/test.py        <候选目录>/solution.py
python3 c03_rate_limiter/test.py   <候选目录>/solution.py
python3 c04_log_agg/test.py        <候选目录>/fast.py
python3 c05_binary_search/test.py  <候选目录>/fixed.py
python3 c06_secure_loader/test.py  <候选目录>/secure.py
python3 c07_scheduler/test.py      <候选目录>/scheduler.py
python3 c08_order_validator/test_runner.py <候选目录>/tests.py
python3 c09_log_parser/test.py     <候选目录>/solution.py
python3 c10_ax9_protocol/test.py   <候选目录>/solution.py
```

每个脚本输出 `PASS ... score=N/10` 或 `FAIL ...`。C9 的分数是 `N/7`，折算时乘以 10/7。

## 自检

所有脚本已用 `reference.py` 自检通过（`c08` 用 `reference_tests.py` 验证可发现全部 3 个植入缺陷）。修改任何素材后请重新自检。

## 注意事项

- 候选文件命名不规范时，用 `python3 test.py <实际文件名>` 即可，脚本不校验文件名；
- C1/C2/C4 设有 120 秒超时保护，C5 对单次调用设 10 秒超时，防止死循环挂死评测；
- C8 的评分逻辑：在正确实现上无“误报”得 3 分，每发现一个植入缺陷加 2 分，3 个全发现再奖 3 分（满分 10）；
- 参考实现只是“参考答案”，候选代码只要通过黑盒测试即可，不要求与参考实现一致；
- 测试脚本均只使用 Python 标准库，运行环境 Python 3.11。
