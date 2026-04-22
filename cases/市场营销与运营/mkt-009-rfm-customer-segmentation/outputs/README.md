# outputs/README

执行 `analysis.py` 后会生成以下结果：

- `summary.txt`：案例摘要、最优聚类数、群组画像与运营建议；
- `smoke_test.txt`：smoke test 成功标记；
- `tables/k_selection.csv`：不同 `K` 的 inertia / silhouette 对比；
- `tables/customer_segments.csv`：客户级 RFM 特征与聚类标签；
- `tables/segment_profiles.csv`：群组规模、均值画像与建议。

这些产物用于教学复核与仓库自动验证，不构成真实业务 KPI 或因果结论。
