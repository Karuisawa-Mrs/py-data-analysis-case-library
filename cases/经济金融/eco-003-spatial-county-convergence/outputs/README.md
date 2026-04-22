# 预期产物清单

## 必要产物

- `summary.txt`：Moran's I、LISA 与空间杜宾模型的文本摘要；无论 full run 还是 smoke test 都会生成。
- `smoke_test.txt`：`python analysis.py --smoke-test` 生成的轻量成功标记。

## 辅助产物

- `tables/model_data.csv`：用于 Moran's I / SDM 的特征表。
- `tables/lisa_clusters.csv`：局部 Moran's I 聚类标签与显著性表。

## 验证说明

- 仓库级 smoke test 只要求 `summary.txt` 与 `smoke_test.txt` 存在。
- 辅助表由 `analysis.py` 自动生成，用于人工复核模型输入和局部聚类结果。
- 若替换为完整县域或全国样本，建议额外输出边界图、显著性地图和稳健性比较表。
