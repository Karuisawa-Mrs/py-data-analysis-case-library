# 模拟数据声明

## 数据模式

- `data_mode`: `simulated`
- 当前案例声明：`simulated`
- 数据由 `analysis.py` 基于固定 seed 自动生成，不含真实客户、真实营销活动或任何个人隐私信息。

## Schema

| table | key | grain | fields |
| --- | --- | --- | --- |
| `simulated_customers.csv` | `customer_id` | `customer` | `age`, `income_k`, `prior_orders`, `engagement_score`, `loyalty_index`, `price_sensitivity`, `new_customer`, `region_score`, `treatment`, `response`, `p_control`, `p_treat`, `true_uplift` |

主要字段说明：

- `customer_id`：客户唯一标识。
- `treatment`：是否收到营销触达。
- `response`：是否发生转化。
- `p_control`：未触达时的真实响应概率（模拟潜在结果）。
- `p_treat`：触达时的真实响应概率（模拟潜在结果）。
- `true_uplift`：`p_treat - p_control`，用于评价增量触达价值。

## 生成规则

- 固定 seed：`42`。
- 客户被随机分配到处理组/对照组，近似对应营销实验设计。
- 高忠诚、高活跃客户拥有更高自然购买概率，但不一定具备高 uplift。
- 价格敏感或新客更容易被优惠触达“说服”，因此 uplift 更高。
- 默认输出位置：`data/simulated_customers.csv`。

## 合规与限制

- 本案例完全使用模拟数据，不涉及隐私、许可或外部访问权限问题。
- 数据仅用于演示 uplift / CATE 逻辑，不应用于现实营销投放结论外推。
