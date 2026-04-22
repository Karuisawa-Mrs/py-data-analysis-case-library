# 预期产物清单

## 必要产物

- `summary.txt`：文字摘要，解释 uplift 建模逻辑、ROI 差异与边界声明。
- `smoke_test.txt`：smoke 模式产物登记。
- `uplift_ranking.csv`：按 uplift 排序后的分位汇总结果。
- `roi_comparison.csv`：不同预算比例与投放策略下的 ROI 对比表。
- `top_customers.csv`：按 uplift 分数排序的顶部客户样本。

## 生成方式

- 所有产物都由 `analysis.py` 生成。
- `analysis.ipynb` 仅调用脚本接口与展示文本输出，不复制任何独立业务逻辑。
- smoke 模式也会生成同名文件，以便通过自动校验。

## 验证说明

- `summary.txt` 与 `smoke_test.txt` 用于脚本级 smoke / full run 校验。
- `uplift_ranking.csv` 与 `roi_comparison.csv` 共同支撑“预测响应 ≠ 预测增量响应”的展示。
- 若修改参数，应同步检查 `params.yaml`、`index.md` 与 `claim_boundary` 是否仍然一致。
