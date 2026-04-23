# 第二批 8 案文献总表

> 本表汇总第二批 8 个新增案例的文献来源信息。
> 每案维护 2 条权威来源（1 条核心方法来源 + 1 条应用/教学补充来源）。

## 双语覆盖统计（累计）

- **已填中文来源数**：0 / 16（目标：每案至少 1 条中文）
- **已填英文来源数**：16 / 16（目标：每案至少 1 条英文）

---

## 表头说明

| 字段 | 说明 |
|---|---|
| `case_id` | 案例唯一标识 |
| `core_method_source` | 核心方法来源 |
| `supplementary_source` | 应用/教学补充来源 |
| `language` | 来源语言（zh / en / mixed） |
| `source_type` | 来源类型 |
| `locator` | DOI / URL / ISBN 三选一 |
| `data_mode` | 数据模式 |
| `replication_type` | 复现关系 |
| `fallback_note` | 替代方案说明（由于依赖问题） |

---

## 第二批 8 案文献表

| case_id | domain | core_method_source | supplementary_source | language | source_type | locator | data_mode | replication_type | fallback_note |
|---|---|---|---|---|---|---|---|---|---|
| `eco-010-credit-risk-ml-benchmark` | 经济金融 | lessmann2015benchmarking: "Benchmarking state-of-the-art classification algorithms for credit scoring" (EJOR, 2015) | hastie2009elements: "The Elements of Statistical Learning" (Springer, 2009) | en | peer-reviewed / textbook | DOI 10.1016/j.ejor.2015.05.030 / ISBN:978-0-387-84857-0 | simulated | illustration | sklearn-only; xgboost/lightgbm/shap omitted due to install issues |
| `eco-011-event-study-policy-announcements` | 经济金融 | mackinlay1997event: "Event studies in economics and finance" (JEL, 1997) | campbell1997econometrics: "The Econometrics of Financial Markets" (Princeton, 1997) | en | peer-reviewed / textbook | jstor:2729691 / ISBN:978-0-691-04301-2 | simulated | illustration | pure statsmodels + numpy |
| `eco-012-volatility-forecast-garch-tft` | 经济金融 | engle1982autoregressive: "Autoregressive conditional heteroscedasticity" (Econometrica, 1982) | bollerslev1986generalized: "Generalized autoregressive conditional heteroskedasticity" (JoE, 1986) | en | peer-reviewed / peer-reviewed | jstor:1912773 / DOI 10.1016/0304-4076(86)90063-1 | simulated | illustration | arch + pytorch-forecasting unavailable; fallback: statsmodels ARIMA + sklearn GBRT. See best-practice-roadmap.md |
| `eco-013-double-ml-policy-heterogeneity` | 经济金融 | chernozhukov2018double: "Double/debiased machine learning for treatment and structural parameters" (Econometrics Journal, 2018) | athey2019generalized: "Generalized random forests" (Annals of Statistics, 2019) | en | peer-reviewed / peer-reviewed | DOI 10.1111/ectj.12097 / DOI 10.1214/18-AOS1709 | simulated | illustration | econml unavailable; fallback: manual cross-fitting DML with sklearn. See best-practice-roadmap.md |
| `soc-014-bertopic-policy-discourse` | 社会科学 | grimmer2013text: "Text as data: The promise and pitfalls of automatic content analysis methods for political texts" (Political Analysis, 2013) | grootendorst2022bertopic: "BERTopic: Neural topic modeling with a class-based TF-IDF procedure" (arXiv, 2022) | en | peer-reviewed / preprint | DOI 10.1093/pan/mps028 / arXiv:2203.05794 | simulated | illustration | bertopic + sentence-transformers unavailable; fallback: sklearn LDA + TF-IDF. See best-practice-roadmap.md |
| `soc-015-social-network-community-diffusion` | 社会科学 | newman2004detecting: "Detecting community structure in networks" (EPJ B, 2004) | wasserman1994social: "Social Network Analysis: Methods and Applications" (Cambridge, 1994) | en | peer-reviewed / textbook | DOI 10.1140/epjb/e2004-00124-y / ISBN:978-0-521-38707-1 | simulated | illustration | networkx available; pure numpy fallback implemented |
| `soc-016-multilevel-school-achievement` | 社会科学 | gelman2006data: "Data Analysis Using Regression and Multilevel/Hierarchical Models" (Cambridge, 2006) | raudenbush2002hierarchical: "Hierarchical linear models: Applications and data analysis methods" (Sage, 2002) | en | textbook / textbook | ISBN:978-0-521-68689-1 / ISBN:978-0-7619-2190-1 | simulated | illustration | statsmodels MixedLM used directly |
| `soc-017-public-feedback-sentiment-modeling` | 社会科学 | devlin2019bert: "BERT: Pre-training of deep bidirectional transformers for language understanding" (NAACL, 2019) | jurafsky2023speech: "Speech and Language Processing" (Stanford, 3rd ed, 2023) | en | conference / textbook | arXiv:1810.04805 / URL:https://web.stanford.edu/~jurafsky/slp3/ | simulated | illustration | transformers unavailable; fallback: enhanced TF-IDF (n-grams + char-level) + Logistic Regression. See best-practice-roadmap.md |

---

## 来源类型说明

- **peer-reviewed**：经同行评审的学术论文
- **textbook**：大学或专业出版社教材
- **preprint**：预印本论文
- **conference**：会议论文

---

## 各案文献详情

### eco-010-credit-risk-ml-benchmark
- **文献条目（references.bib）**：
  - lessmann2015benchmarking: Lessmann et al. (2015), EJOR, peer-reviewed, DOI
  - hastie2009elements: Hastie, Tibshirani & Friedman (2009), Springer, textbook, ISBN
- **lit_sources（frontmatter）**：lessmann2015benchmarking, hastie2009elements

### eco-011-event-study-policy-announcements
- **文献条目（references.bib）**：
  - mackinlay1997event: MacKinlay (1997), JEL, peer-reviewed, jstor
  - campbell1997econometrics: Campbell, Lo & MacKinlay (1997), Princeton UP, textbook, ISBN
- **lit_sources（frontmatter）**：mackinlay1997event, campbell1997econometrics

### eco-012-volatility-forecast-garch-tft
- **文献条目（references.bib）**：
  - engle1982autoregressive: Engle (1982), Econometrica, peer-reviewed, jstor
  - bollerslev1986generalized: Bollerslev (1986), JoE, peer-reviewed, DOI
- **lit_sources（frontmatter）**：engle1982autoregressive, bollerslev1986generalized
- **迁移路线图**：`cases/经济金融/eco-012-volatility-forecast-garch-tft/best-practice-roadmap.md`

### eco-013-double-ml-policy-heterogeneity
- **文献条目（references.bib）**：
  - chernozhukov2018double: Chernozhukov et al. (2018), Econometrics Journal, peer-reviewed, DOI
  - athey2019generalized: Athey, Tibshirani & Wager (2019), Annals of Statistics, peer-reviewed, DOI
- **lit_sources（frontmatter）**：chernozhukov2018double, athey2019generalized
- **迁移路线图**：`cases/经济金融/eco-013-double-ml-policy-heterogeneity/best-practice-roadmap.md`

### soc-014-bertopic-policy-discourse
- **文献条目（references.bib）**：
  - grimmer2013text: Grimmer & Stewart (2013), Political Analysis, peer-reviewed, DOI
  - grootendorst2022bertopic: Grootendorst (2022), arXiv, preprint, arXiv ID
- **lit_sources（frontmatter）**：grimmer2013text, grootendorst2022bertopic
- **迁移路线图**：`cases/社会科学/soc-014-bertopic-policy-discourse/best-practice-roadmap.md`

### soc-015-social-network-community-diffusion
- **文献条目（references.bib）**：
  - newman2004detecting: Newman (2004), EPJ B, peer-reviewed, DOI
  - wasserman1994social: Wasserman & Faust (1994), Cambridge UP, textbook, ISBN
- **lit_sources（frontmatter）**：newman2004detecting, wasserman1994social

### soc-016-multilevel-school-achievement
- **文献条目（references.bib）**：
  - gelman2006data: Gelman & Hill (2006), Cambridge UP, textbook, ISBN
  - raudenbush2002hierarchical: Raudenbush & Bryk (2002), Sage, textbook, ISBN
- **lit_sources（frontmatter）**：gelman2006data, raudenbush2002hierarchical

### soc-017-public-feedback-sentiment-modeling
- **文献条目（references.bib）**：
  - devlin2019bert: Devlin et al. (2019), NAACL, conference, arXiv
  - jurafsky2023speech: Jurafsky & Martin (2023), Stanford, textbook, URL
- **lit_sources（frontmatter）**：devlin2019bert, jurafsky2023speech
- **迁移路线图**：`cases/社会科学/soc-017-public-feedback-sentiment-modeling/best-practice-roadmap.md`
