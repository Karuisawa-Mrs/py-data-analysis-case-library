# 预期产物清单

## 必要产物

- `summary.txt`：主脚本运行后的文本摘要，包含处理效应、安慰剂结果与解释边界。
- `smoke_test.txt`：`python analysis.py --smoke-test` 的轻量产物登记。
- `parallel_trends.png`：处理组与对照组的平均就业趋势图。
- `did_results.csv`：主 DID 回归的处理效应结果表。
- `placebo_results.csv`：安慰剂检验结果表。
- `group_means.csv`：平行趋势图对应的组均值表。

## 生成方式

- 所有产物都由 `analysis.py` 生成。
- `analysis.ipynb` 仅调用脚本中的接口并解释这些输出，不复制回归逻辑。
- smoke 模式也会生成同名文件，以便通过单案自动校验。

## 验证说明

- `summary.txt` 与 `smoke_test.txt` 用于脚本级 smoke / full run 校验。
- 图表与表格属于最小复现范围的一部分，因为它们直接支撑 DID 识别展示。
- 若修改参数，请同步检查 `params.yaml`、`index.md` 的边界声明与图表解释是否仍然一致。
