# 预期产物清单

## 必要产物

- `summary.txt`：完整运行后的摘要说明，包括样本流失率、模型比较结果与解释边界。
- `smoke_test.txt`：`python analysis.py --smoke-test` 生成的轻量校验摘要。
- `model_metrics.csv`：逻辑回归与梯度提升树的主要评估指标表。
- `precision_recall_curve.png`：两种模型在 holdout 集上的 PR 曲线对比图。
- `confusion_matrices.png`：按各自 F1 最优阈值绘制的混淆矩阵对比图。
- `feature_importance_comparison.csv`：逻辑回归绝对系数与梯度提升树特征重要性对比表。

## 验证说明

- smoke test 会生成全部必要产物，但使用更小的模拟样本量。
- 完整运行使用默认样本量，指标与重要性排序通常更稳定。
- 混淆矩阵使用各模型在测试集上的 F1 最优阈值，仅用于演示阈值选择与误判权衡。
