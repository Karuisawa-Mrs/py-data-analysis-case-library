# 数据说明

## 数据模式

- `data_mode`: `simulated`
- 数据文件不随仓库分发，运行 `analysis.py` 时即时生成。

## 模拟对象

案例模拟的是电信/订阅制业务中的客户横截面快照，每一行代表一个客户在观察窗口结束时的状态。目标变量为 `churned`，表示客户是否在该窗口内流失。

## 变量结构

- 连续变量：`tenure_months`、`monthly_charges`、`avg_monthly_data_gb`、`support_tickets_90d`、`payment_delay_days`、`recent_outage_hours`、`satisfaction_score`、`referrals_12m`
- 二元变量：`autopay`、`paperless_billing`、`fiber_optic`、`multi_line`、`streaming_bundle`、`senior_customer`
- 分类型变量：`contract_type`、`region_tier`
- 目标变量：`churned`

## 生成逻辑

- 低满意度、短合约、账单拖延、近期故障、客服工单较多会提高流失概率。
- 自动扣费、长期合约、更多增值服务与更高推荐数会降低流失概率。
- 脚本会检查并维持一个合理但偏低的流失率区间，用于演示类别不平衡下的预测 benchmark。

## 使用边界

该数据完全为模拟数据，只用于演示机器学习预测流程，不可解释为真实运营规律或实证证据。
