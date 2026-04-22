# data/README

本案例不内置真实交易明细，而是在 `analysis.py` 中按固定 `seed=42` 生成可复现的模拟电商交易数据。

## 数据生成逻辑

- 以客户为单位抽样潜在行为原型（高价值、高成长、高客单、流失风险）；
- 为每位客户生成订单数、最近购买时间和订单金额分布；
- 形成交易级字段：`customer_id`、`order_id`、`order_date`、`order_amount`。

## 使用说明

运行下列命令即可重建分析输入：

```bash
python analysis.py --smoke-test
python analysis.py
```

由于数据为模拟生成，它仅用于演示 RFM 与聚类流程，不代表任何真实平台用户行为。
