# 预期产物清单

## 必要产物

- `summary.txt`：完整运行后的文字摘要，概述 CFA 拟合、结构路径和中介结论。
- `smoke_test.txt`：最小复现摘要，供 `scripts/run_case_smoke.py` 校验。
- `cfa_fit_stats.csv`：测量模型拟合指标。
- `sem_fit_stats.csv`：结构模型拟合指标。
- `parameter_estimates.csv`：CFA 与 SEM 参数估计表（含标准化系数）。
- `mediation_effects.csv`：直接效应、间接效应、总效应及 bootstrap 置信区间。

## 附加产物

- `simulated_indicator_sample.csv`：模拟指标数据的前若干行，便于快速检查字段结构。

## 验证说明

- smoke 模式也会生成上述必要产物，因此仓库级 smoke 校验无需额外依赖 notebook 执行。
- `parameter_estimates.csv` 与 `mediation_effects.csv` 是解释性产物，便于学习路径系数和中介分解，不构成额外仓库脚本逻辑来源。
