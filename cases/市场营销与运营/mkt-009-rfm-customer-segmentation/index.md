---
case_id: "mkt-009-rfm-customer-segmentation"
title: "电商客户细分：RFM 与 K-means 聚类"
primary_domain: "市场营销与运营"
secondary_tags:
  - "电商分析"
  - "客户分群"
  - "CRM"
method_tags:
  - "Clustering"
  - "RFM"
  - "K-Means"
research_question: "在一个可复现的模拟电商交易样例中，如何基于客户最近购买时间、购买频次与消费金额构造 RFM 特征，并用 K-means 得到可解释的客户分群？"
analytical_objective: "演示从交易级数据聚合到客户级 RFM 特征、用 elbow/silhouette 选择聚类数、输出分群画像与运营动作建议的完整工作流。"
replication_type: "illustration"
data_mode: "simulated"
data_sources:
  - name: "analysis.py simulated transaction generator"
    type: "synthetic ecommerce transactions"
    access: "run analysis.py to generate a reproducible synthetic transaction sample"
literature_sources:
  - "macqueen1967"
  - "hughes1994"
  - "punjmoon2015"
seed: 42
assumption_note: "交易数据由脚本按潜在客户行为原型模拟生成：不同原型在购买间隔、订单金额与活跃概率上存在系统差异，因此该案例适合演示 RFM 特征工程与聚类解释，不代表真实平台分布。"
claim_boundary: "演示客户分群逻辑，不生成因果结论"
expected_artifacts:
  - "outputs/summary.txt"
  - "outputs/smoke_test.txt"
  - "outputs/tables/k_selection.csv"
  - "outputs/tables/customer_segments.csv"
  - "outputs/tables/segment_profiles.csv"
validation_scope:
  - "结构完整性校验"
  - "RFM 聚合与 K-means smoke test"
  - "单案例 strict metadata 校验"
status: "draft"
---

# 案例概述

这个案例使用可复现的模拟电商交易数据，演示如何把交易明细聚合为客户级 RFM（Recency、Frequency、Monetary）特征，再用 K-means 聚类形成客户分群，并为每个分群生成策略建议。

## 分析设计

- 样本：脚本生成的电商客户与订单交易记录。
- 客户特征：
  - `Recency`：距观察窗口结束时最近一次购买的天数；
  - `Frequency`：观察窗口内订单数；
  - `Monetary`：观察窗口内累计消费金额。
- 建模步骤：
  1. 交易级模拟；
  2. 客户级 RFM 聚合；
  3. `log1p` + `StandardScaler` 处理偏态；
  4. 比较不同 `K` 的 inertia（elbow）与 silhouette；
  5. 运行 K-means 并输出分群画像、标签和运营建议。

## 复现说明

```bash
python analysis.py --smoke-test
python analysis.py
```

## 结果说明

- `outputs/summary.txt`：文字摘要，含最优 K、各群画像与策略建议。
- `outputs/smoke_test.txt`：仓库级 smoke run 的轻量成功标记。
- `outputs/tables/k_selection.csv`：不同聚类数下的 inertia / silhouette 对比。
- `outputs/tables/customer_segments.csv`：客户级分群结果。
- `outputs/tables/segment_profiles.csv`：群组均值、占比与建议。

本案例的结论仅用于教学展示“如何做客户分群”，不应直接外推为真实业务中的投放、预算或组织决策依据。
