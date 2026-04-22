# Outputs README

运行 `analysis.py` 后，脚本会在本目录下生成以下主要产物：

- `summary.txt`：文字摘要，包含平稳性说明、滞后阶数选择、IRF 与 FEVD 的核心解释。
- `smoke_test.txt`：轻量运行的确认文件，供 smoke 校验脚本检查。
- `lag_order_selection.csv`：AIC/BIC/HQIC/FPE 对不同滞后阶数的评价表。
- `stationarity_checks.csv`：水平值与对数差分值的 ADF 检验结果。
- `irf_m2_shock.png`：以 `M2` 为冲击变量的正交化脉冲响应图。
- `fevd_overview.png`：预测误差方差分解图。

这些文件都由 `analysis.py` 自动生成；请不要手工替换图表，否则 notebook 展示内容会与脚本真源失去同步。
