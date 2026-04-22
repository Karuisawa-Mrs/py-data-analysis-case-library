---
case_id: "eco-003-spatial-county-convergence"
title: "中国县域经济收敛性：空间杜宾模型分析"
primary_domain: "经济金融"
secondary_tags:
  - "区域经济"
  - "县域发展"
  - "空间计量"
method_tags:
  - "Moran's I"
  - "SDM"
  - "LISA"
research_question: "在一个可轻量复现的中国县域公开样例中，县域经济增长是否呈现空间相关性，以及初始经济规模与财政能力是否与后续增长存在空间溢出型收敛关系？"
analytical_objective: "用忻州市 15 个县级单元的公开摘录数据演示全局 Moran's I、局部 Moran's I（LISA）与空间杜宾模型，说明如何把县域公开统计表整理成一个可运行的空间收敛性教学案例。"
replication_type: "adaptation"
data_mode: "real"
data_sources:
  - name: "忻州市统计局：2019年1-12月各县(市、区)主要经济指标完成情况"
    type: "government statistics excerpt"
    access: "see data/README.md for official URL and extraction notes"
  - name: "忻州市统计局：2025年1-12月全市各县(市、区)主要经济指标完成情况"
    type: "government statistics excerpt"
    access: "see data/README.md for official page and XLS attachment URL"
  - name: "GaryBikini/ChinaAdminDivisonSHP"
    type: "open administrative boundary reference"
    access: "see data/README.md for MIT-licensed boundary reference used to cross-check adjacency"
literature_sources:
  - "lesage2009introduction"
  - "anselin1988spatial"
  - "bi2025county"
seed: 42
assumption_note: "案例只保留忻州市 15 个县级单元的 2019/2025 摘录指标，并以人工整理的邻接表近似县域接壤关系；因此它适合教学演示空间收敛建模流程，不替代全国县域完整面板研究。"
claim_boundary: "结果仅支持对一个轻量真实样例的空间相关与收敛性演示，不可直接外推为全国县域经济收敛的经验结论；空间权重矩阵为仓内精简邻接表，未复刻完整 GIS 边界文件。"
expected_artifacts:
  - "outputs/summary.txt"
  - "outputs/smoke_test.txt"
validation_scope:
  - "结构完整性校验"
  - "PySAL Moran's I / LISA / SDM 脚本 smoke test"
  - "单案例 strict metadata 校验"
status: "draft"
---

# 案例概述

这个案例把“中国县域经济收敛性”收缩成一个可教学复现的公开样例：使用忻州市 15 个县级单元在 2019 与 2025 年的公开经济指标摘录，构造县域 GDP 增长率、财政能力与空间邻接关系，并用 `PySAL` 完成全局空间自相关、局部集聚识别和空间杜宾模型估计。

之所以采用 `adaptation` 而不是“原样复刻”，是因为仓库只保留轻量真实数据切片，而不内嵌完整县域年鉴或大体量矢量边界文件。这样既保留了真实公开来源，也符合案例库“小而可运行”的合同。

## 分析设计

- 样本：山西省忻州市 15 个县级单元（剔除缺少 GDP 的开发区，保留五台山风景区）。
- 因变量：2019-2025 年 GDP 年均增长率。
- 核心解释变量：2019 年初始 GDP 规模与财政收入（取对数）。
- 空间权重：仓内 `county_adjacency.csv` 的人工整理邻接表，行标准化后用于 Moran's I、LISA 与 SDM。
- 估计方法：`spreg.ML_Lag(..., slx_lags=1)`，即 PySAL 官方 notebook 所示的 Spatial Durbin Model（SDM）写法。

## 复现说明

```bash
python analysis.py --smoke-test
python analysis.py
```

## 结果说明

- `outputs/summary.txt`：记录 Moran's I、显著 LISA 单元和 SDM 摘要。
- `outputs/smoke_test.txt`：为仓库级 smoke run 提供轻量成功标记。
- `outputs/tables/`：辅助表格（模型输入、LISA 聚类）。

若你希望把这个案例扩展到全国县域面板，需要替换为完整县域统计年鉴或可再分发的开放县域面板，并重新构造全国尺度的空间权重矩阵。
