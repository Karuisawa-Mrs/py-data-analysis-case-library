# 预期产物清单模板

## 必要产物

- `summary.txt`：主脚本执行后的摘要输出。
- `smoke_test.txt`：`python analysis.py --smoke-test` 生成的轻量校验文件。

## 可选产物

- 图表：如 `figures/*.png`
- 表格：如 `tables/*.csv`
- 中间结果：如 `artifacts/*.parquet`

## 验证说明

- 说明每个产物如何生成。
- 标注哪些产物属于最小复现范围，哪些仅用于展示。
- 若输出依赖真实数据或外部权限，应明确限制条件。
