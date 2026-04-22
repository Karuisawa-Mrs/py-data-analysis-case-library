# 首批 9 案文献总表

> 本表汇总首批 9 个案例的文献来源信息。
> 每案维护 2 条权威来源（1 条核心方法来源 + 1 条应用/教学补充来源）。

## 双语覆盖统计（累计）

- **已填中文来源数**：1 / 18（目标：每案至少 1 条中文）
- **已填英文来源数**：17 / 18（目标：每案至少 1 条英文）

---

## 表头说明

| 字段 | 说明 |
|---|---|
| `case_id` | 案例唯一标识，与计划矩阵一致 |
| `core_method_source` | 核心方法来源（原始论文 / 权威教材 / 顶级期刊方法综述 / 官方方法手册） |
| `supplementary_source` | 应用/教学补充来源（应用论文 / 教材章节 / 官方数据说明 / 课程讲义） |
| `language` | 来源语言（zh / en / mixed） |
| `source_type` | 来源类型（peer-reviewed / textbook / method-doc / data-doc） |
| `locator` | DOI / URL / ISBN 三选一 |
| `data_mode` | 数据模式（simulated / real / hybrid） |
| `replication_type` | 复现关系（illustration / adaptation / replication） |

---

## 首批 9 案文献表

| case_id | domain | core_method_source | supplementary_source | language | source_type | locator | data_mode | replication_type |
|---|---|---|---|---|---|---|---|---|
| `eco-001-did-min-wage-policy` | 经济金融 | callaway2021did: "Difference-in-Differences with Multiple Time Periods" (Journal of Econometrics, 2021) | cunningham2021mixtape: "Causal Inference: The Mixtape" (Yale University Press, 2021) | en | peer-reviewed / textbook | DOI 10.1016/j.jeconom.2020.12.001 / URL mixtape.scunning.com | simulated | illustration |
| `eco-002-var-monetary-transmission` | 经济金融 | lutkepohl2005new: "New Introduction to Multiple Time Series Analysis" (Springer, 2005) | stockwatson2001var: "Vector Autoregressions" (JEP, 2001) | en | textbook / peer-reviewed | ISBN:9783540262398 / DOI 10.1257/jep.15.4.101 | simulated | illustration |
| `eco-003-spatial-county-convergence` | 经济金融 | lesage2009introduction: "Introduction to Spatial Econometrics" (CRC Press, 2009) | anselin1988spatial: "Spatial Econometrics: Methods and Models" (Kluwer, 1988) | en | textbook / book | ISBN:9781420064247 / DOI 10.1007/978-94-015-7799-1 | real | adaptation |
| `soc-004-twfe-left-behind-education` | 社会科学 | wooldridge2010panel: "Econometric Analysis of Cross Section and Panel Data" (MIT Press, 2010) | angristpischke2009: "Mostly Harmless Econometrics" (Princeton, 2009) | en | textbook / textbook | ISBN:9780262232586 / ISBN:9780691120355 | simulated | illustration |
| `soc-005-cox-health-inequality` | 社会科学 | klein2003survival: "Survival Analysis: Techniques for Censored and Truncated Data" (Springer, 2003) | therneau2000modeling: "Modeling Survival Data: Extending the Cox Model" (Springer, 2000) | en | textbook / textbook | ISBN:9780387958774 / ISBN:9781441929853 | simulated | illustration |
| `soc-006-sem-social-capital-wellbeing` | 社会科学 | kline2015principles: "Principles and Practice of Structural Equation Modeling" (Guilford, 2015) | hair2019multivariate: "Multivariate Data Analysis" (Cengage, 2019) | en | textbook / textbook | ISBN:9781462523344 / ISBN:9781473756540 | simulated | illustration |
| `mkt-007-uplift-campaign-targeting` | 市场营销与运营 | atheyimbens2016: "Recursive Partitioning for Heterogeneous Causal Effects" (PNAS, 2016) | radcliffe2007: "Using Control Groups to Target on Predicted Lift" (Direct Marketing Analytics Journal, 2007) | en | peer-reviewed / article | DOI 10.1073/pnas.1510489113 / - | simulated | illustration |
| `mkt-008-churn-prediction-benchmark` | 市场营销与运营 | hastie2021esl: "The Elements of Statistical Learning" (Springer, 2nd ed, 2021) | chen2016xgboost: "XGBoost: A Scalable Tree Boosting System" (KDD, 2016) | en | textbook / conference_paper | ISBN:9780387848570 / DOI 10.1145/2939672.2939785 | simulated | illustration |
| `mkt-009-rfm-customer-segmentation` | 市场营销与运营 | macqueen1967: "Some Methods for Classification and Analysis of Multivariate Observations" (Berkeley Symposium, 1967) | hughes1994: "Strategic Database Marketing" (Probus Publishing, 1994) | en | conference_paper / book | - / - | simulated | illustration |

---

## 来源类型说明

- **peer-reviewed**：经同行评审的学术论文
- **textbook**：大学或专业出版社教材
- **method-doc**：政府/国际组织/学会官方方法文档
- **data-doc**：数据发布方提供的说明文档

---

## 各案文献详情

### eco-001-did-min-wage-policy
- **文献条目（references.bib）**：
  - callaway2021did: Card & Sant'Anna (2021), "Difference-in-Differences with Multiple Time Periods", Journal of Econometrics, peer-reviewed, DOI 10.1016/j.jeconom.2020.12.001
  - cardkrueger1994minwage: Card & Krueger (1994), "Minimum Wages and Employment: A Case Study...", AER, peer-reviewed, URL
  - cunningham2021mixtape: Cunningham (2021), "Causal Inference: The Mixtape", Yale UP, textbook, URL
- **lit_sources（frontmatter）**：callaway2021did, cardkrueger1994minwage

### eco-002-var-monetary-transmission
- **文献条目（references.bib）**：
  - lutkepohl2005new: Lütkepohl (2005), "New Introduction to Multiple Time Series Analysis", Springer, textbook, ISBN
  - stockwatson2001var: Stock & Watson (2001), "Vector Autoregressions", JEP, peer-reviewed, DOI
  - bernankeblinder1992federalfunds: Bernanke & Blinder (1992), "The Federal Funds Rate...", AER, peer-reviewed, URL
- **lit_sources（frontmatter）**：lutkepohl2005new, stockwatson2001var, bernankeblinder1992federalfunds

### eco-003-spatial-county-convergence
- **文献条目（references.bib）**：
  - lesage2009introduction: LeSage & Pace (2009), "Introduction to Spatial Econometrics", CRC Press, textbook, ISBN
  - anselin1988spatial: Anselin (1988), "Spatial Econometrics: Methods and Models", Kluwer, book, DOI
  - bi2025county: Bi (2025), "The Growth of the County Economy in China", China Economic Journal, peer-reviewed, DOI
- **lit_sources（frontmatter）**：lesage2009introduction, anselin1988spatial, bi2025county

### soc-004-twfe-left-behind-education
- **文献条目（references.bib）**：
  - wooldridge2010panel: Wooldridge (2010), "Econometric Analysis of Cross Section and Panel Data", MIT Press, textbook, ISBN
  - angristpischke2009: Angrist & Pischke (2009), "Mostly Harmless Econometrics", Princeton UP, textbook, ISBN
  - zhangqiu2019leftbehind: Zhang & Qiu (2019), "The Influence of Parents Going Out to Work...", working paper, DOI
- **lit_sources（frontmatter）**：wooldridge2010panel, angristpischke2009, zhangqiu2019leftbehind

### soc-005-cox-health-inequality
- **文献条目（references.bib）**：
  - klein2003survival: Klein & Moeschberger (2003), "Survival Analysis: Techniques for Censored and Truncated Data", Springer, textbook, ISBN
  - therneau2000modeling: Therneau & Grambsch (2000), "Modeling Survival Data: Extending the Cox Model", Springer, textbook, ISBN
  - wang2020healthy: 王广州 (2020), "健康预期寿命测量方法与应用研究", 中国社会科学出版社, book, ISBN **（中文来源）**
- **lit_sources（frontmatter）**：klein2003survival, therneau2000modeling, wang2020healthy

### soc-006-sem-social-capital-wellbeing
- **文献条目（references.bib）**：
  - kline2015principles: Kline (2015), "Principles and Practice of Structural Equation Modeling", Guilford, textbook, ISBN
  - hair2019multivariate: Hair et al. (2019), "Multivariate Data Analysis", Cengage, textbook, ISBN
- **lit_sources（frontmatter）**：kline2015principles, hair2019multivariate

### mkt-007-uplift-campaign-targeting
- **文献条目（references.bib）**：
  - atheyimbens2016: Athey & Imbens (2016), "Recursive Partitioning for Heterogeneous Causal Effects", PNAS, peer-reviewed, DOI
  - radcliffe2007: Radcliffe (2007), "Using Control Groups to Target on Predicted Lift", Direct Marketing Analytics Journal, article
- **lit_sources（frontmatter）**：atheyimbens2016, radcliffe2007

### mkt-008-churn-prediction-benchmark
- **文献条目（references.bib）**：
  - hastie2021esl: Hastie, Tibshirani & Friedman (2021), "The Elements of Statistical Learning", Springer, textbook, ISBN
  - chen2016xgboost: Chen & Guestrin (2016), "XGBoost: A Scalable Tree Boosting System", KDD, conference_paper, DOI
  - molnar2020interpretable: Molnar (2020), "Interpretable Machine Learning", Lulu.com, book, URL
- **lit_sources（frontmatter）**：hastie2021esl, chen2016xgboost, molnar2020interpretable

### mkt-009-rfm-customer-segmentation
- **文献条目（references.bib）**：
  - macqueen1967: MacQueen (1967), "Some Methods for Classification and Analysis of Multivariate Observations", Berkeley Symposium, inproceedings
  - hughes1994: Hughes (1994), "Strategic Database Marketing", Probus Publishing, book
  - punjmoon2015: Punj & Moon (2015), "Customer Segmentation Using Automatic Interaction Detection", JMA, article, DOI
- **lit_sources（frontmatter）**：macqueen1967, hughes1994, punjmoon2015