# 数据说明

## 数据模式

- `data_mode`: `simulated`
- 当前案例不使用真实个体数据，所有记录均由 `analysis.py` 在固定随机种子下生成。

## Schema

| table | key | grain | fields |
| --- | --- | --- | --- |
| `simulated_health_cohort` | `person_id` | `person-baseline` | `age`, `female`, `chronic_burden`, `ses_group`, `followup_years`, `event_observed` |

## 模拟规则

- 事件定义：首次进入“健康受损”状态。
- 时间过程：用指数型基线风险生成潜在事件时间，并让年龄、性别、慢病负担和 SES 影响个体风险。
- 删失机制：
  - 行政删失：研究在固定区间内结束，未发生事件者被右删失。
  - 失访删失：一部分个体在随访期间随机提前退出。
- 前提：删失被视为非信息性删失，用于演示 Kaplan-Meier 与 Cox PH 方法的适用条件。

## 合规与限制

- 不含真实个人信息，不涉及隐私泄露。
- 数据生成过程内生地设定了 SES 梯度，因此只能用于方法演示，不能替代真实健康不平等研究。
