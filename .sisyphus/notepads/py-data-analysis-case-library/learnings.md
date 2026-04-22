- 固化了 `templates/case-template/` 作为单案例模板目录，标准文件合同为 `index.md`、`analysis.py`、`analysis.ipynb`、`params.yaml`、`references.bib`、`data/README.md`、`outputs/README.md`。
- `analysis.ipynb` 模板只允许通过 `%run ./analysis.py --smoke-test` 叙事性调用脚本，不承载独立业务逻辑。
- `analysis.py` 模板已内置相对路径解析、`outputs/` 自动创建与 `--smoke-test` 入口，可作为后续案例脚手架基线。
- `scripts/validate_catalog.py` 现已支持分模式校验：`--structure-only`、`--template-only`、`--index-only`、`--strict`、`--artifact-hygiene`，便于分层排查目录、模板、索引、案例合同与仓库卫生问题。
- notebook 同步检查采用启发式约束：允许 `import`、`from`、`%run` 和简单函数调用包装，但若出现 `def`、`class`、循环、`sklearn`/`statsmodels` 导入或训练调用，则视为可能承载独立业务逻辑。
- `soc-005-cox-health-inequality` 采用 `analysis.py` 生成带右删失的模拟队列，最小必要输出包括 `summary.txt`、`smoke_test.txt`、`km_curve_by_ses.png`、`cox_summary.csv` 和 `ph_assumption_test.csv`；smoke test 也要兑现全部 `expected_artifacts`。
- 在当前 Windows 运行环境中，Matplotlib 默认字体可能不支持中文图题；若要保持命令行输出干净，案例图形标签优先使用 ASCII/英文文本，正文解释继续放在 `index.md` 与 `summary.txt`。
- `eco-002-var-monetary-transmission` 证明了 `statsmodels.tsa.api.VAR` 的教学型流程可以稳定复用：先对水平宏观序列做对数差分，再记录 `select_order` 结果，最后统一输出 `IRF` 与 `FEVD` 图表和文字摘要。
- notebook wrapper 约束比模板表面看起来更严格：`check_notebook_sync.py` 允许 `%run`、`import` 和简单函数调用，但像 `filename=`、`encoding=` 这样的关键字参数也可能触发 `non-wrapper code`，后续展示型 notebook 应尽量使用纯位置参数或更简单的读取表达式。
- `eco-001-did-min-wage-policy` 采用模拟企业面板演示 DID：`analysis.py` 统一生成 `data/simulated_panel.csv`、`outputs/parallel_trends.png`、`outputs/did_results.csv`、`outputs/placebo_results.csv` 与文本摘要，smoke 模式也必须产出同名文件以满足 `expected_artifacts` 校验。
- 单案 notebook 校验可通过 `python -c "... scripts.check_notebook_sync ..."` 直接调用 `check_metadata_sync()` 与 `check_independent_logic()` 对目标案例做局部检查，避免被其他未完成案例的 notebook 漂移噪声干扰。
- `soc-004-twfe-left-behind-education` ���á�ѧ��-��ݡ�ģ����壬��ȷ�Ѹ���̶�ЧӦ����Ϊ���ղ���ʱ��仯��ѧ�������ԣ�����ݹ̶�ЧӦ����Ϊ���չ�ͬ�����������������ժҪ�ж����¼ `switcher_share` ��չʾ TWFE ʶ�������ڸ����ڲ�״̬�л���
- GitHub �� `linearmodels` �ٷ�ʾ����ֱ�ӽ�� `PanelOLS(..., entity_effects=True, time_effects=True)` �� `fit(cov_type="clustered", cluster_entity=True, cluster_time=True)` �Ľӿ�ģʽ�������л���ȱ�� `linearmodels`�����˻� `statsmodels` �� `C(student_id) + C(year)` �Ʊ����̶�ЧӦʵ�֣���֤������ִ�С�
- `eco-003-spatial-county-convergence` 证明：即使没有完整可再分发 shapefile，也可以用“真实公开指标摘录 + 轻量人工邻接表”的方式稳定演示 `Moran`、`Moran_Local` 与 `spreg.ML_Lag(slx_lags=1)` 的 Spatial Durbin workflow。
- 在当前环境里，直接安装整套 `pysal` 可能被 `fiona/GDAL` 构建阻塞；更稳的做法是只安装 `esda`、`libpysal`、`spreg` 三个最小包集，足以支撑县域空间计量案例。
- `mkt-009-rfm-customer-segmentation` 证明：教学型 RFM 分群不必依赖真实订单库，也可以用可控的潜在客户原型稳定模拟交易级数据，再聚合出 `Recency/Frequency/Monetary` 并完成 K-means workflow。
- 对 K-means 教学案例，采用 `log1p` 缓解 RFM 偏态、`StandardScaler` 做标准化、再同时输出 inertia 与 silhouette 的 `k_selection.csv`，比只给单一 `K` 更利于解释“为什么这样分群”。
- `mkt-007-uplift-campaign-targeting` 采用随机实验风格模拟客户数据，并显式保留 `p_control`、`p_treat` 与 `true_uplift`，这样既能演示 uplift 排序，也能在 ROI 对比里直接说明“预测响应”与“预测增量响应”的差别。

- 2026-04-23: �� churn benchmark ���������� sklearn ����������ģʽ��predict_proba ������ʡ�precision_recall_curve/oc_auc_score ˫ָ�����������ڲ�ƽ�������·ֱ��� class_weight='balanced' �� compute_sample_weight('balanced', y_train) ��������ģ�ͺ���������

- 2026-04-23: soc-006 shows the stable semopy teaching workflow is Model(desc) -> fit(data) -> inspect(std_est=True) -> calc_stats(model); extracting SEM paths by lval/op/rval is enough and avoids dependence on parameter-label syntax.
- 2026-04-23: For latent mediation cases, the library pattern is CFA first, full SEM second, then bootstrap the indirect effect; smoke mode should still emit cfa_fit_stats.csv, sem_fit_stats.csv, and mediation_effects.csv so artifact validation covers real outputs.

## 2026-04-23 00:53:19 F1 audit findings
- Strict validation passed: 9 cases validated, smoke runs passed, notebook sync passed, py_compile passed.
- Frozen plan rules for taxonomy, dual-track layout, case-id naming, metadata fields, source register, and 9-case matrix were confirmed by direct inspection plus script checks.

## 2026-04-23 Final Verification fixes
- Frontmatter parsing for catalog validation, smoke runs, and notebook sync must accept both `---\n` and `---\r\n`; CRLF-only files otherwise silently break Windows validation flows.
- `validate_catalog.py` now needs to enforce the full 17-field frontmatter contract plus runtime presence of `seed` / `data_mode` / `replication_type` in `params.yaml`; partial metadata checks were not enough for plan compliance.
- Template notebook sync is safer when `--template-only` exists as a dedicated mode and the template notebook itself mirrors template `title`, `case_id`, and `method_tags` expectations.
- 2026-04-23: Final verification established a cleaner contract: `index.md` frontmatter is the only metadata truth, while `params.yaml` should keep runtime-only values (at minimum `seed`, plus execution/model parameters) and must not repeat `case_id` / `data_mode` / `replication_type` / `claim_boundary`.
- 2026-04-23: For deterministic spatial permutation tests under PySAL, `np.random.seed(seed)` still needs to be set immediately before `Moran(..., permutations=...)`; `Moran_Local(..., seed=seed)` alone does not cover the global Moran permutation RNG.
- 2026-04-23: Smoke/summary artifacts should never serialize absolute workspace paths on Windows; manifests should emit relative names like `summary.txt`, `outputs`, or `data/...` to keep artifact hygiene portable.
