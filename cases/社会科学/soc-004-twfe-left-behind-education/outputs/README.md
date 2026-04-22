# 预期产物清单

## 必要产物

- `summary.txt`：完整运行后的文字摘要，含样本描述、主回归和异质性结果。
- `smoke_test.txt`：最小复现摘要，供 `scripts/run_case_smoke.py` 校验。

## 附加产物

- `main_regression.csv`：主回归结果表，包含普通标准误与双向聚类稳健标准误。
- `heterogeneity_age.csv`：按年龄组拆分的 TWFE 结果。
- `heterogeneity_region.csv`：按地区组拆分的 TWFE 结果。
- `simulated_panel_sample.csv`：模拟数据前若干行，便于快速查看字段结构。

## 验证说明

- smoke 模式和完整模式都会创建 `summary.txt` 与 `smoke_test.txt`，以满足案例合同。
- 附加 CSV 产物仅用于解释与检查，不构成仓库级严格校验的硬性条件。
