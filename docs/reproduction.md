# 复现指南

## Clean clone

```bash
git clone <private-repository-url>
cd model-evaluation
./scripts/bootstrap.sh
cp .env.example .env.local
./scripts/smoke-test.sh
```

## API smoke test

先在服务商控制台确认模型 ID、免费额度保护和调用协议，再设置对应环境变量：

```bash
export LINGZHI_API_KEY='your-local-key'
ENV_FILE=.env.local \
CONFIG=runners/model-api-collector/config/qwen.yaml \
./scripts/run-evaluation.sh qwen3.8-max
```

第一次只运行一题一次。确认结果文件和费用状态后，再运行正式 manifest。

## Agent evaluation

AutomationBench 依赖 Python 3.13。安装后，按其 README 运行指定任务，并同时记录：

- `--model`；
- `--base-url`；
- `--api-key-var`；
- `--api` 或 `--responses-api`；
- `--toolset`；
- `--max-steps`；
- `--max-concurrent`；
- 题库版本和导出文件路径。

正式测评默认使用 `--max-concurrent 1` 先验证单题，再逐步增加并发，避免错误配置放大费用。
