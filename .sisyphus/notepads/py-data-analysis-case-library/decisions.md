- 选择将 `index.md` frontmatter 定义为唯一元数据真源，并在根 `README.md` 新增 `Metadata Contract` 明确必填字段，避免出现第二份独立元数据合同。
- 保留 `params.yaml` 中的 `seed`、`data_mode`、`replication_type`、`claim_boundary` 作为运行时默认参数模板，但通过注释与 README 明确其从属于脚本执行层，不替代 frontmatter 语义。
- `run_case_smoke.py` 选择直接以子进程执行 `python analysis.py --smoke-test`，并在运行后读取 `index.md` 的 `expected_artifacts` 做二次核验，这样 smoke 验证同时覆盖“脚本可执行”和“产物合同兑现”。
- `check_notebook_sync.py` 以 `index.md` frontmatter 作为 notebook 同步真源：`case_id` 必须出现在 notebook 文本中，一级标题必须等于 `title`，`method_tags` 必须在 markdown 叙事中出现，避免 notebook 漂移成第二套元数据来源。
- 为匹配单案例任务的验收口径，`scripts/validate_catalog.py` 在 `--case ... --strict` 成功时额外输出 `case valid`；不带 `--case` 的全量严格校验仍保留原有计数输出。
- `eco-002-var-monetary-transmission` 采用“模拟水平变量 + 对数差分估计 VAR”的方案，而不是直接模拟平稳增长率后省略解释步骤；这样 `stationarity_checks.csv` 能同时展示“为何不用水平值直接建 VAR”。
- 该案例将 `M2` 放在 Cholesky 排序的首位，并把正交化 `M2` 创新解释为示范性流动性冲击；这是为了教学上清晰展示 IRF/FEVD，而不是宣称完成了真实货币政策结构识别。
- `eco-001-did-min-wage-policy` 的主回归采用 `statsmodels` 的 `employment ~ did + controls + C(firm_id) + C(period)` 设定，而不是将 notebook 或额外脚本作为分析入口；这样既贴合 GitHub 上常见的固定效应 DID 实现模式，也满足“`analysis.py` 是唯一逻辑真源”的仓库合同。
- 平行趋势图的可视化标签改为英文 ASCII，避免当前 Windows + Matplotlib 默认字体在命令行 smoke/full run 中产生中文缺字警告；中文解释保留在 `index.md`、`analysis.ipynb` 与 `summary.txt`。
- `soc-004-twfe-left-behind-education` ����ʵ�����ȱ����� GitHub �� `linearmodels` TWFE �÷�һ�£������� `statsmodels` ����·������Ϊ��ǰ�ֿ�ִ�л���ȱ�� `linearmodels` ���������ȱ��������̶�ЧӦ�Ĺ淶д����Ҳ�����˲ֿ� smoke/strict ��֤�Ŀ�����Ҫ��
- ������ `expected_artifacts` ��ֻ���� `summary.txt` �� `smoke_test.txt`���� `analysis.py` ����������ع�������� CSV���Ա��ڲ������ϸ�У�����ǰ���±�����ѧ͸���ȡ�
- `eco-003-spatial-county-convergence` 选择使用忻州市统计局 2019/2025 年县域公开表作为真实样例来源，并把开发区剔除、五台山风景区保留，以兼顾“真实数据”与“小样本可运行”的案例库约束。
- 为满足单案例任务的验收合同，`analysis.py` 采用 `summary.txt` + `smoke_test.txt` 作为必备产物，辅助的 `tables/*.csv` 不写入 `expected_artifacts`，这样仓库级 smoke 校验与人工复核都能兼顾。
- `mkt-009-rfm-customer-segmentation` 选择将 `analysis.py` 直接生成为“交易级模拟 → RFM 聚合 → K-grid 评估 → 分群画像”的单脚本真源，不额外拆成数据准备脚本，以保持案例目录可单独阅读和单独运行。
- 该案例将 `expected_artifacts` 设为 `summary.txt`、`smoke_test.txt` 与三张关键 CSV（K 选择、客户标签、群组画像），确保 smoke test 不只验证脚本能跑通，也验证分群结果确实落盘。
- `mkt-007-uplift-campaign-targeting` 选择 two-model / T-learner 风格实现：分别拟合处理组与对照组响应模型，并用 `mu1_hat - mu0_hat` 作为 uplift 分数；这样既贴近 GitHub 上 `scikit-uplift` 与 Criteo benchmark 的常见实现模式，也避免为教学案例额外引入专用 uplift 依赖。

- 2026-04-23: mkt-008 ʹ��ģ����Ŷ��ĺ���� + Logistic Regression vs GradientBoostingClassifier �Աȣ�notebook ������ %run ./analysis.py --smoke-test ��װ�㣬����̶�Ϊ metrics/PR ����/��������/������Ҫ������ benchmark �����

- 2026-04-23: soc-006 uses continuous simulated indicators rather than discretized Likert cut points because semopy MLW fitting is more stable in the current environment; the questionnaire interpretation stays in index.md.
- 2026-04-23: soc-006 keeps the notebook as a minimal wrapper with only %run ./analysis.py --smoke-test, preserving analysis.py as the single logic source.

- 2026-04-23: `validate_catalog.py` now normalizes path reporting with a fallback string formatter instead of assuming every validated case path is under `--root`; this keeps `--case` robust for absolute paths.
- 2026-04-23: Bootstrap and clustered-covariance fallbacks were narrowed away from bare `except Exception` blocks; SEM bootstrap failures are now logged, and TWFE covariance fallback only catches expected numerical/statsmodels warning-style failures.
- 2026-04-23: The validator was realigned so strict case checks require `seed` in `params.yaml` but forbid duplicated metadata keys (`case_id`, `data_mode`, `replication_type`, `claim_boundary`); this matches the repository rule that frontmatter is authoritative.
- 2026-04-23: Cases that previously read metadata semantics from `params.yaml` now pin those teaching labels inside `analysis.py` constants, avoiding validator drift while preserving stable summary text.
