# Python 数据分析案例库 — 案例总索引

> 本索引按"领域 → 案例 → 方法 → 数据模式 → 难度"组织，收录首批 9 个案例。
> 具体实现细节（文献来源、参数、输出说明）由各案例任务填充。

## 索引结构说明

- **领域索引**：`cases/<domain>/index.md`（仅列本域案例）
- **单案入口**：`cases/<domain>/<case-id>/index.md`
- **文献总表**：`references/first-batch-source-register.md`

---

## 经济金融

| case_id | 方法标签 | 数据模式 | 难度 | 状态 |
|---|---|---|---|---|
| `eco-001-did-min-wage-policy` | DID | simulated | Medium-High | draft |
| `eco-002-var-monetary-transmission` | VAR, IRF, FEVD | simulated | Medium | ready |
| `eco-003-spatial-county-convergence` | Moran's I, SDM, LISA | real | Medium | draft |
| `eco-010-credit-risk-ml-benchmark` | Logistic Regression, Gradient Boosting, Calibration | simulated | Medium | draft |
| `eco-011-event-study-policy-announcements` | Event Study, Abnormal Returns, CAR | simulated | Medium | draft |
| `eco-012-volatility-forecast-garch-tft` | GARCH, EGARCH, Temporal Fusion Transformer | simulated | High | draft |
| `eco-013-double-ml-policy-heterogeneity` | Double Machine Learning, Causal Forest, CATE | simulated | High | draft |

---

## 社会科学

| case_id | 方法标签 | 数据模式 | 难度 | 状态 |
|---|---|---|---|---|
| `soc-004-twfe-left-behind-education` | TWFE, Panel Regression | simulated | Medium-High | complete |
| `soc-005-cox-health-inequality` | Survival Analysis, Cox, Kaplan-Meier | simulated | Medium | draft |
| `soc-006-sem-social-capital-wellbeing` | SEM, CFA, Mediation | simulated | Medium-High | complete |
| `soc-014-bertopic-policy-discourse` | BERTopic, Topic Modeling, Text-as-Data | simulated | High | draft |
| `soc-015-social-network-community-diffusion` | Network Analysis, Community Detection, SI Diffusion | simulated | Medium | draft |
| `soc-016-multilevel-school-achievement` | Multilevel Model, Linear Mixed Effects, ICC | simulated | Medium | draft |
| `soc-017-public-feedback-sentiment-modeling` | Sentiment Analysis, Text Classification, TF-IDF | simulated | High | draft |

---

## 市场营销与运营

| case_id | 方法标签 | 数据模式 | 难度 | 状态 |
|---|---|---|---|---|
| `mkt-007-uplift-campaign-targeting` | Uplift Modeling, CATE | simulated | Medium | draft |
| `mkt-008-churn-prediction-benchmark` | Binary Classification, Logistic Regression, Gradient Boosting | simulated | Medium | draft |
| `mkt-009-rfm-customer-segmentation` | Clustering, RFM, K-Means | simulated | Medium | draft |

---

## 统计概览

- **领域数**：3
- **案例总数**：17
- **模拟数据案例**：16
- **真实数据案例**：1
- **已完成案例**：2（soc-004, soc-006）
- **就绪案例**：1（eco-002）
- **第二批新增**：8（eco-010~013, soc-014~017）