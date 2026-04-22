# 预期产物清单

## 必要产物

- `summary.txt`：完整运行后的摘要说明，包括删失比例、Kaplan-Meier 中位健康存活时间和风险比解释。
- `smoke_test.txt`：`python analysis.py --smoke-test` 生成的轻量校验摘要。
- `km_curve_by_ses.png`：不同 SES 组的 Kaplan-Meier 健康存活曲线。
- `cox_summary.csv`：Cox 比例风险模型估计结果与风险比。
- `ph_assumption_test.csv`：比例风险假设检验结果。

## 验证说明

- smoke test 会生成全部必要产物，但使用更小的模拟样本。
- 完整运行使用默认样本量，输出更稳定的曲线和估计值。
- 图表是生存概率曲线，不应解释为简单频数柱状图或累计人数图。
