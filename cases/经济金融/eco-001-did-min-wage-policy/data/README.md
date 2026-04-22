# 模拟数据声明

## 数据模式

- `data_mode`: `simulated`
- 当前案例声明：`simulated`
- 该数据集由 `analysis.py` 按固定 seed 自动生成，不包含真实企业或真实政策观测。

## Schema

| table | key | grain | fields |
| --- | --- | --- | --- |
| `simulated_panel.csv` | `firm_id`, `period` | `firm-period` | `group`, `treated`, `post`, `employment`, `avg_wage`, `productivity`, `demand_index`, `did`, `relative_period` |

主要字段说明：

- `firm_id`：企业唯一标识。
- `period`：离散时期索引，共 6 期。
- `group`：`treated` / `control`。
- `treated`：是否属于处理组。
- `post`：是否处于真实政策实施后时期。
- `employment`：模拟就业人数（连续化处理，便于 OLS 演示）。
- `avg_wage`：模拟平均工资水平。
- `productivity`：模拟企业生产率指标。
- `demand_index`：模拟需求景气度。
- `did`：`treated × post` 交互项。
- `relative_period`：相对政策实施时点的期数。

## 生成规则

- 固定 seed：`20260422`。
- 企业分为处理组与对照组，各自拥有企业固定效应。
- 所有企业共享共同时间趋势，因此政策前期满足近似平行趋势。
- 处理组在政策实施后平均工资额外上升，并通过 `policy_effect` 对就业产生负向处理效应。
- `avg_wage`、`productivity`、`demand_index` 作为可观测控制变量，与就业共同决定回归设定。
- 默认输出位置：`data/simulated_panel.csv`。

## 合规与限制

- 本案例完全使用模拟数据，不涉及隐私、许可或外部访问权限问题。
- 数据只用于教学演示 DID 识别流程，不应用于真实最低工资政策判断或外推。
