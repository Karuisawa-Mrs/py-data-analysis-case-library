# Python数据分析案例库（首批9案）实施计划

## TL;DR
> **Summary**：在当前空白目录中建立一个可扩展的 Python 数据分析案例库，采用“一个案例一个文件夹”的 Obsidian 友好结构，并落地首批 9 个由权威文献驱动的方法案例。
> **Deliverables**：
> - 根目录结构、命名规则、依赖与轻量验证脚本
> - 3 个一级领域族（经济金融 / 社会科学 / 市场营销与运营）
> - 9 个标准化案例文件夹（每案 `.py` + notebook）
> - 每案的元数据、文献来源、模拟/真实数据声明、可复现输出与限制说明
> - 首批案例总索引、领域索引、批量验证入口
> **Effort**：XL
> **Parallel**：YES - 3 waves
> **Critical Path**：Task 1 → Task 3 → Task 4 → Tasks 6-14 → Task 15 → Final Verification

## Context
### Original Request
- 在当前目录建立 Python 数据分析案例库。
- 规划清晰的文件存放结构，分类存放数据分析案例。
- 每一个案例一个文件夹。
- 方法必须来自各领域权威文献（论文、教材、官方方法资料等）。
- 可以使用模拟数据，但案例必须真实可运行、可复现、可学习。

### Interview Summary
- 当前目录是空白目录，可按最佳结构从零设计。
- 本次规划交付重点：**结构 + 首批案例蓝图**。
- 每个案例采用双轨交付：**`analysis.py` + `analysis.ipynb`**。
- 首批案例数量固定为 **9 个**。
- 首批优先领域固定为：**经济金融、社会科学、市场营销与运营**。
- 文献来源采用 **中英文学术来源并用**。
- 验证策略采用 **轻量自动验证**，而不是完整 CI 重装。
- 默认仅保留**文献引用信息、方法摘要、来源说明**，不在库内默认存储论文 PDF 本体。

### Metis Review (gaps addressed)
- 已冻结分类轴：采用 **3 个一级领域族**，方法作为标签，不再混用“领域目录 + 方法目录”。
- 已冻结文献准入规则：每案至少 2 条权威来源，其中 1 条必须为核心方法来源。
- 已冻结双轨规则：`analysis.py` 为唯一逻辑真源，notebook 只做叙事封装与调用展示。
- 已加入反范围蔓延约束：v1 不建设站点、数据库、重型数据管道、共享包框架。
- 已把“模拟数据是否诚实”转化为强制字段：`data_mode`、`replication_type`、`claim_boundary`、`seed`、`assumption_note`。

## Work Objectives
### Core Objective
把当前目录建设成一个**面向学习、复现、扩展**的 Python 数据分析案例库：结构统一、案例独立、来源清晰、执行可验证，并且首批 9 个案例覆盖三大领域族与多种分析范式（因果、推断、预测、描述）。

### Deliverables
- [ ] 根目录说明与导航文件：`README.md`
- [ ] Python 运行与依赖配置：`pyproject.toml`、`.gitignore`
- [ ] 批量验证入口：`scripts/validate_catalog.py`、`scripts/run_case_smoke.py`、`scripts/check_notebook_sync.py`
- [ ] 领域目录：`cases/经济金融/`、`cases/社会科学/`、`cases/市场营销与运营/`
- [ ] 每案统一模板：`index.md`、`analysis.py`、`analysis.ipynb`、`params.yaml`、`references.bib`、`data/README.md`、`outputs/README.md`
- [ ] 9 个首批案例完整落位
- [ ] 总索引与领域索引：`cases/index.md` + 各领域 `index.md`
- [ ] 批次级文献总表与案例矩阵：`references/first-batch-source-register.md`

### Definition of Done (verifiable conditions with commands)
- [ ] `python "scripts/validate_catalog.py" --root "." --require-cases 9 --strict` 输出 `9 cases validated, 0 blocking errors`
- [ ] `python "scripts/run_case_smoke.py" --root "." --all` 对 9 个案例全部返回 exit code `0`
- [ ] `python "scripts/check_notebook_sync.py" --root "."` 输出 `9/9 notebooks in sync`
- [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/经济金融/eco-001-did-min-wage-policy/analysis.ipynb"` 成功完成；其余 8 个案例同理
- [ ] `python -c "from pathlib import Path; import py_compile; [py_compile.compile(str(p), doraise=True) for p in list(Path('scripts').glob('*.py')) + list(Path('cases').glob('*/*/analysis.py'))]; print('py_compile ok')"` 输出 `py_compile ok`
- [ ] `python "scripts/validate_catalog.py" --root "." --artifact-hygiene` 输出 `artifact hygiene valid`

### Must Have
- 每个案例只占用一个独立文件夹，且可单独阅读、单独运行、单独验证。
- 一级目录只按领域族分类；方法只放在元数据与标签里。
- 每个案例必须明确说明：**来源文献、方法目的、数据模式（real/simulated/hybrid）、复现关系（replication/adaptation/illustration）、限制边界**。
- 每个案例必须提供：`.py`、notebook、参数文件、引用文件、数据说明、输出说明。
- 所有路径必须为相对路径，适配 Windows + Obsidian + Git 场景。
- 首批 9 案必须覆盖：至少 3 个因果/准因果、2 个预测、2 个统计推断、2 个描述/分群类案例。

### Must NOT Have (guardrails, AI slop patterns, scope boundaries)
- 不引入站点生成器、数据库、前后端服务、重型数据下载管道。
- 不把方法目录和领域目录混在一起，不允许一案多处落盘。
- 不把 notebook 写成独立逻辑副本；notebook 不得复制与 `analysis.py` 分叉的业务逻辑。
- 不把模拟结果写成真实世界经验结论；所有模拟案例必须显式声明“示范性而非经验性结论”。
- 不在仓库中提交 `.venv/`、`__pycache__/`、`.ipynb_checkpoints/`、`.ruff_cache/`、大于 25MB 的原始数据文件。
- 不把博客、论坛帖、AI 生成说明当成权威方法来源。

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: **tests-after + light automation**；基础框架为 `pytest` + 自定义验证脚本 + notebook 执行校验
- QA policy: 每个任务都必须同时包含“实现 + 验证”，每个案例至少有 happy path 与 failure/edge case 各一条
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`
- Validation contracts:
  - 目录级：检查 9 个案例目录、必需文件、命名规范、领域归属
  - 元数据级：检查 frontmatter / `params.yaml` / `references.bib` / `claim_boundary`
  - 执行级：脚本 smoke run、notebook 可重跑、输出文件存在
  - 同步级：notebook 与 `analysis.py` 的 `case_id`、方法名、预期产物一致
  - 失败级：缺文献、缺 seed、缺限制说明、路径错误、notebook 漂移均应触发失败

## Execution Strategy
### Parallel Execution Waves
> Target: 5 tasks per wave for foundation, then case batches in parallel.

Wave 1: 根结构、依赖、模板、验证、索引基础（Tasks 1-5）
Wave 2: 经济金融 + 社会科学前两案（Tasks 6-10）
Wave 3: 社会科学收尾 + 市场营销与运营 + 批次级文献总表（Tasks 11-15）

### Dependency Matrix (full, all tasks)
| Task | Depends On | Blocks |
|---|---|---|
| 1 | None | 2,3,5,6-15 |
| 2 | 1 | 4,6-15 |
| 3 | 1 | 4,6-15 |
| 4 | 2,3 | 6-15,F1-F4 |
| 5 | 1,3 | 15,F4 |
| 6 | 1,2,3,4 | 15,F1-F4 |
| 7 | 1,2,3,4 | 15,F1-F4 |
| 8 | 1,2,3,4 | 15,F1-F4 |
| 9 | 1,2,3,4 | 15,F1-F4 |
| 10 | 1,2,3,4 | 15,F1-F4 |
| 11 | 1,2,3,4 | 15,F1-F4 |
| 12 | 1,2,3,4 | 15,F1-F4 |
| 13 | 1,2,3,4 | 15,F1-F4 |
| 14 | 1,2,3,4 | 15,F1-F4 |
| 15 | 5,6-14 | F1-F4 |

### Agent Dispatch Summary (wave → task count → categories)
| Wave | Task Count | Primary Categories |
|---|---:|---|
| Wave 1 | 5 | unspecified-high, writing, quick |
| Wave 2 | 5 | deep, unspecified-high, writing |
| Wave 3 | 5 | deep, writing, unspecified-high |
| Final | 4 | oracle, unspecified-high, deep |

## First-Batch Case Matrix
| Case ID | Domain | Chinese Title | Method | Data Mode | Replication Type | Difficulty |
|---|---|---|---|---|---|---|
| eco-001-did-min-wage-policy | 经济金融 | 最低工资政策的就业效应：双重差分法实证分析 | Difference-in-Differences | simulated | illustration | Medium-High |
| eco-002-var-monetary-transmission | 经济金融 | 货币政策传导机制：基于VAR模型的脉冲响应分析 | VAR + IRF + FEVD | simulated | illustration | Medium |
| eco-003-spatial-county-convergence | 经济金融 | 中国县域经济收敛性：空间杜宾模型分析 | Moran's I + SDM | real | adaptation | Medium |
| soc-004-twfe-left-behind-education | 社会科学 | 父母外出务工对留守儿童学业成绩的影响：双向固定效应模型 | TWFE Panel Regression | simulated | illustration | Medium-High |
| soc-005-cox-health-inequality | 社会科学 | 社会经济地位对健康预期寿命的影响：Cox比例风险模型 | Survival Analysis | simulated | illustration | Medium |
| soc-006-sem-social-capital-wellbeing | 社会科学 | 社会资本如何影响主观幸福感：结构方程模型的路径分析 | SEM + Mediation | simulated | illustration | Medium-High |
| mkt-007-uplift-campaign-targeting | 市场营销与运营 | 精准营销中的增量响应建模：客户 uplift 分析 | Uplift Modeling | simulated | illustration | Medium |
| mkt-008-churn-prediction-benchmark | 市场营销与运营 | 电信客户流失预测：逻辑回归与梯度提升树对比 | Binary Classification | simulated | illustration | Medium |
| mkt-009-rfm-customer-segmentation | 市场营销与运营 | 电商客户细分：RFM 与 K-means 聚类 | Clustering + RFM | simulated | illustration | Medium |

## Source Admission Rule (frozen)
- 每个案例至少维护 **2 条权威来源**：
  1. **核心方法来源**：原始论文、权威教材、顶级期刊方法综述、官方方法手册四者之一；必填。
  2. **应用/教学补充来源**：中文或英文的应用论文、教材章节、官方数据说明、课程讲义之一；必填。
- 可接受来源类型：peer-reviewed 论文、大学出版社教材、政府/国际组织/学会方法文档。
- 不可接受来源类型：博客、论坛、营销文章、无作者 AI 文本、来源不明二手转载。
- 双语覆盖规则：**批次级覆盖**，不是每案强制双语；但 9 案整体必须同时包含中文与英文权威来源。
- 每条来源必须可落入 `references.bib`，至少含 `title`、`author`、`year`、`source_type`、`language`、`locator`（DOI/URL/ISBN 三选一）。

## Repository Contract (frozen)
### Root Layout
```text
.
├── README.md
├── pyproject.toml
├── .gitignore
├── scripts/
│   ├── validate_catalog.py
│   ├── run_case_smoke.py
│   └── check_notebook_sync.py
├── references/
│   └── first-batch-source-register.md
└── cases/
    ├── index.md
    ├── 经济金融/
    ├── 社会科学/
    └── 市场营销与运营/
```

### Per-Case Contract
```text
cases/<domain>/<case-id>/
├── index.md              # canonical metadata + overview (YAML frontmatter)
├── analysis.py           # single source of truth for logic
├── analysis.ipynb        # narrative wrapper that imports/calls analysis.py
├── params.yaml           # deterministic parameters, seeds, output paths
├── references.bib        # authoritative sources only
├── data/
│   └── README.md         # real/simulated data declaration, schema, acquisition note
└── outputs/
    └── README.md         # expected artifacts manifest
```

### Canonical Metadata Fields (`index.md` frontmatter)
- `case_id`
- `title`
- `primary_domain`
- `secondary_tags`
- `method_tags`
- `research_question`
- `analytical_objective`
- `replication_type`
- `data_mode`
- `data_sources`
- `literature_sources`
- `seed`
- `assumption_note`
- `claim_boundary`
- `expected_artifacts`
- `validation_scope`
- `status`

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [x] 1. 搭建根目录分类轴与命名约束

  **What to do**: 建立根目录骨架：`cases/`、`references/`、`scripts/`，并在 `cases/` 下只创建 3 个一级领域族：`经济金融`、`社会科学`、`市场营销与运营`。在根 `README.md` 中写明命名规则：案例目录统一使用 `case-id` 英文 slug，中文标题只写在 `index.md` frontmatter 与正文中；禁止方法名单独升格为顶级目录。
  **Must NOT do**: 不创建按方法分类的并行目录；不把中文标题直接作为深层文件夹名；不提前放入案例内容占位垃圾文件。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要同时处理目录结构、命名规则与 Obsidian/Git 兼容性。
  - Skills: `[]` - 根结构工作不依赖额外专用 skill。
  - Omitted: [`fullstack-dev`] - 不涉及服务端或前后端架构。

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,5,6,7,8,9,10,11,12,13,14,15 | Blocked By: None

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/.sisyphus/plans/student-fashion-survey.md:17-71` - 现有仓库中使用“上下文 → 目标 → 完成定义”的组织方式，可沿用到根 README 的结构说明。
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:30-35` - 现有案例习惯明确列出成果文件，根 README 也应明确列出统一案例合同。
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:243-249` - 现有案例使用相对稳定的单脚本产出模式；根目录命名应服务于这种“单案独立运行”模式。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/validate_catalog.py" --root "." --structure-only` 返回 `structure valid`
  - [ ] `python -c "from pathlib import Path; root = Path('.'); expected = [root/'cases'/'经济金融', root/'cases'/'社会科学', root/'cases'/'市场营销与运营', root/'references', root/'scripts']; missing = [str(p) for p in expected if not p.exists()]; print('OK' if not missing else missing)"` 输出 `OK`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 根目录结构验证
    Tool: Bash
    Steps: 运行 `python "scripts/validate_catalog.py" --root "." --structure-only`。
    Expected: 返回 `structure valid`，且仅有 3 个一级领域目录。
    Evidence: .sisyphus/evidence/task-1-root-structure.txt

  Scenario: Failure/edge case - 误建方法目录
    Tool: Bash
    Steps: 临时创建 `cases/DID/` 后再次运行 `python "scripts/validate_catalog.py" --root "." --structure-only`。
    Expected: 校验失败并指出非法一级目录 `cases/DID/`。
    Evidence: .sisyphus/evidence/task-1-root-structure-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`README.md`, `cases/`, `references/`, `scripts/`]

- [x] 2. 建立 Python 依赖与仓库忽略策略

  **What to do**: 创建 `pyproject.toml`，锁定 Python 版本与首批依赖：`pandas`、`numpy`、`scipy`、`statsmodels`、`scikit-learn`、`jupyter`、`nbconvert`、`matplotlib`、`seaborn`、`linearmodels`、`lifelines`、`semopy`、`pysal`、`pyyaml`、`pytest`。创建 `.gitignore`，明确忽略 `.venv/`、`__pycache__/`、`.ruff_cache/`、`.ipynb_checkpoints/`、大输出文件与临时执行产物。
  **Must NOT do**: 不引入数据库、Web 框架、分布式计算依赖；不把依赖拆成多套互相冲突的 requirements 文件；不提交虚拟环境。

  **Recommended Agent Profile**:
  - Category: `quick` - Reason: 单批配置文件创建与固定依赖集合。
  - Skills: `[]`
  - Omitted: [`fullstack-dev`] - 不是全栈系统搭建。

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4,6,7,8,9,10,11,12,13,14 | Blocked By: 1

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:1-12` - 现有仓库已使用 `csv`、`pathlib`、`python-docx` 风格的脚本组织；新库改为以数据分析依赖为主。
  - Pattern: `教科文卫/build_report.py:1-18` - 现有脚本倾向使用 `pathlib.Path` 进行路径管理，新库依赖和脚本也应坚持相对路径 + `Path`。
  - Pattern: `市场调查分析/学生穿着观察法调查/.sisyphus/plans/student-fashion-survey.md:62-70` - 现有计划会显式声明 must have / must not have，新库配置也要把缓存与重型依赖列入禁止项。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python -c "from pathlib import Path; [Path(p).exists() or (_ for _ in ()).throw(AssertionError(p)) for p in ['pyproject.toml', '.gitignore']]; print('config files present')"` 输出 `config files present`
  - [ ] `python -c "from pathlib import Path; text = Path('.gitignore').read_text(encoding='utf-8'); required = ['.venv/', '__pycache__/', '.ipynb_checkpoints/', '.ruff_cache/']; missing = [x for x in required if x not in text]; print('OK' if not missing else missing)"` 输出 `OK`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 配置文件存在且含关键依赖/忽略项
    Tool: Bash
    Steps: 检查 `pyproject.toml` 与 `.gitignore`，并运行轻量解析脚本确认关键依赖与忽略项。
    Expected: 两个文件存在，且包含本计划指定的依赖与忽略规则。
    Evidence: .sisyphus/evidence/task-2-config-check.txt

  Scenario: Failure/edge case - 忽略规则缺失
    Tool: Bash
    Steps: 临时移除 `.gitignore` 中 `.ipynb_checkpoints/`，重新运行解析脚本。
    Expected: 校验失败并输出缺失项 `.ipynb_checkpoints/`。
    Evidence: .sisyphus/evidence/task-2-config-check-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`pyproject.toml`, `.gitignore`]

- [x] 3. 固化单案例模板与元数据合同

  **What to do**: 为全部案例固定文件合同：`index.md`（含 YAML frontmatter）、`analysis.py`、`analysis.ipynb`、`params.yaml`、`references.bib`、`data/README.md`、`outputs/README.md`。在根 `README.md` 中写明 `index.md` 必填字段、`analysis.py` 为唯一逻辑真源、notebook 只负责导入/调用和解释展示。为案例模板创建一个可复制的参考案例骨架（例如 `_template/` 或 `templates/case-template/`），供后续 9 案复制。
  **Must NOT do**: 不新增第二份元数据真源；不把逻辑写进 notebook 再反向同步到脚本；不让 `params.yaml` 与 frontmatter 重复相同语义字段。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要冻结结构、元数据、文档合同与双轨同步规则。
  - Skills: `[]`
  - Omitted: [`simplify`] - 这里是合同设计，不是后置润色。

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 4,5,6,7,8,9,10,11,12,13,14 | Blocked By: 1

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:1-35` - 现有案例习惯用单个 Markdown 文件承载背景、参数、成果说明；新库要升级为带 frontmatter 的 `index.md`。
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:273-377` - 现有案例会从同一脚本生成统计说明与分析小结；新库应把该思想固定为“脚本主导、文档从属”。
  - Pattern: `教科文卫/build_report.py:19-35` - dataclass/结构化字段风格可迁移为新库的显式元数据字段设计。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/validate_catalog.py" --root "." --template-only` 输出 `template valid`
  - [ ] `python -c "from pathlib import Path; req = ['index.md','analysis.py','analysis.ipynb','params.yaml','references.bib','data/README.md','outputs/README.md']; template = Path('templates/case-template'); missing = [x for x in req if not (template/x).exists()]; print('OK' if not missing else missing)"` 输出 `OK`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 模板合同完整
    Tool: Bash
    Steps: 运行 `python "scripts/validate_catalog.py" --root "." --template-only` 并检查模板目录必需文件。
    Expected: 返回 `template valid`，且 7 个模板文件全部存在。
    Evidence: .sisyphus/evidence/task-3-template-check.txt

  Scenario: Failure/edge case - notebook 成为逻辑真源
    Tool: Bash
    Steps: 在模板 notebook 中加入独立业务逻辑标记后运行 `python "scripts/check_notebook_sync.py" --root "." --template-only`。
    Expected: 同步检查失败并指出 notebook 不能包含独立逻辑块。
    Evidence: .sisyphus/evidence/task-3-template-check-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`templates/case-template/`, `README.md`]

- [x] 4. 实现批量校验、smoke run 与 notebook 同步检查脚本

  **What to do**: 编写 `scripts/validate_catalog.py`、`scripts/run_case_smoke.py`、`scripts/check_notebook_sync.py`。`validate_catalog.py` 必须检查：领域目录、案例数量、必需文件、frontmatter 字段、`references.bib` 条目字段、`params.yaml` 的 `seed`、`data_mode`、`replication_type`、`claim_boundary`。`run_case_smoke.py` 必须逐案调用 `analysis.py --smoke-test` 并验证 `expected_artifacts` 是否存在。`check_notebook_sync.py` 必须检查 notebook 的 `case_id`、标题、方法名、预期产物与脚本声明一致，且 notebook 通过 `import`/调用脚本函数而非复制逻辑。
  **Must NOT do**: 不验证统计学“结论正确性”；不要求人工打开 notebook 目检；不为单案写专属校验逻辑分支。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要设计全库统一的自动验证合同，是后续 9 案的公共基座。
  - Skills: `[]`
  - Omitted: [`review-work`] - 这是实现任务本身，不是事后审查。

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 6,7,8,9,10,11,12,13,14,F1,F2,F3,F4 | Blocked By: 2,3

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:243-377` - 现有案例有清晰的“生成 CSV / 统计 / 分析 / 说明”产物边界，可转化为输出文件存在性检查。
  - Pattern: `市场调查分析/学生穿着观察法调查/.sisyphus/plans/student-fashion-survey.md:152-203` - 现有计划已示范用脚本校验 CSV 与统计表；新库将其提升为统一验证器。
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:24-35` - 现有案例会显式列成果文件；新库应从 `expected_artifacts` 字段中执行同类检查。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/validate_catalog.py" --root "." --help`、`python "scripts/run_case_smoke.py" --help`、`python "scripts/check_notebook_sync.py" --help` 全部返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --root "." --strict` 在 9 案全部完成后输出 `9 cases validated, 0 blocking errors`
  - [ ] `python "scripts/check_notebook_sync.py" --root "."` 在 9 案全部完成后输出 `9/9 notebooks in sync`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 验证脚本可调用
    Tool: Bash
    Steps: 逐个运行三个脚本的 `--help`，然后对模板执行一次结构检查。
    Expected: 三个脚本均正常返回，模板检查无异常。
    Evidence: .sisyphus/evidence/task-4-validator-smoke.txt

  Scenario: Failure/edge case - 缺失核心字段
    Tool: Bash
    Steps: 删除某模板 frontmatter 中的 `claim_boundary`，运行 `python "scripts/validate_catalog.py" --root "." --strict`。
    Expected: 校验失败并明确指出缺失字段 `claim_boundary`。
    Evidence: .sisyphus/evidence/task-4-validator-smoke-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`scripts/validate_catalog.py`, `scripts/run_case_smoke.py`, `scripts/check_notebook_sync.py`]

- [x] 5. 建立总索引、领域索引与首批文献总表骨架

  **What to do**: 创建 `cases/index.md`、3 个领域目录下的 `index.md`、以及 `references/first-batch-source-register.md`。总索引必须按“领域 → 案例 → 方法 → 数据模式 → 难度”组织；领域索引只列本域案例；文献总表必须预置 9 案条目位置、来源字段模板、双语覆盖统计位。该任务只建立骨架和字段，不填完每案文献细节，细节在各案例任务与 Task 15 完成。
  **Must NOT do**: 不把案例内容摘要提前写死为与后续实现冲突的版本；不在索引中复制案例正文；不把领域索引与文献总表混成一个文件。

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: 以导航与结构化说明文档为主。
  - Skills: `[]`
  - Omitted: [`fullstack-dev`] - 不涉及应用路由或后端索引服务。

  **Parallelization**: Can Parallel: YES | Wave 1 | Blocks: 15,F4 | Blocked By: 1,3

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:30-35` - 现有案例会显式列成果文件；索引应采用同样清单式导航。
  - Pattern: `市场调查分析/学生穿着观察法调查/.sisyphus/plans/student-fashion-survey.md:45-60` - 现有计划擅长把交付物拆成清单；案例库索引也应用清单化结构。
  - External: `Source Admission Rule (this plan)` - 文献总表字段必须与本计划冻结规则完全一致。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/validate_catalog.py" --root "." --index-only` 输出 `index valid`
  - [ ] `python -c "from pathlib import Path; required = ['cases/index.md','cases/经济金融/index.md','cases/社会科学/index.md','cases/市场营销与运营/index.md','references/first-batch-source-register.md']; missing = [p for p in required if not Path(p).exists()]; print('OK' if not missing else missing)"` 输出 `OK`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 索引骨架齐全
    Tool: Bash
    Steps: 运行 `python "scripts/validate_catalog.py" --root "." --index-only`，并检查 5 个索引/总表文件存在。
    Expected: 返回 `index valid`，且索引文件都存在。
    Evidence: .sisyphus/evidence/task-5-index-check.txt

  Scenario: Failure/edge case - 缺领域索引
    Tool: Bash
    Steps: 删除 `cases/社会科学/index.md` 后再次运行 `python "scripts/validate_catalog.py" --root "." --index-only`。
    Expected: 校验失败并指出缺少 `cases/社会科学/index.md`。
    Evidence: .sisyphus/evidence/task-5-index-check-error.txt
  ```

  **Commit**: YES | Message: `feat(catalog): scaffold data analysis case library foundation` | Files: [`cases/index.md`, `cases/*/index.md`, `references/first-batch-source-register.md`, foundation files]

- [x] 6. 落地经济金融案例一：最低工资政策的就业效应（DID）

  **What to do**: 在 `cases/经济金融/eco-001-did-min-wage-policy/` 中实现完整案例。`analysis.py` 生成可复现的企业面板模拟数据（处理组/对照组 × 前后期），完成平行趋势可视化、DID 回归、处理效应解释与安慰剂检验；`analysis.ipynb` 必须通过导入 `analysis.py` 中的核心函数来展示结果；`index.md` 记录方法来源、模拟假设、`claim_boundary`；`references.bib` 至少录入核心方法来源 + 应用/教学补充来源各 1 条。
  **Must NOT do**: 不把模拟结果写成真实最低工资政策结论；不省略平行趋势图；不在 notebook 内复制回归主逻辑。

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: 涉及准因果设计、可视化、回归与方法边界说明。
  - Skills: [`pandas-pro`] - 需要结构化面板数据生成与整理。
  - Omitted: [`machine-learning-engineer`] - 本案不是部署型 ML 工程。

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:211-377` - 参考其“同一脚本生成数据 + 统计说明 + 分析文本”的组织方式，但本案改为 DID 输出。
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:24-35` - 用类似方式在 `index.md` 清楚声明模拟性质与成果文件。
  - External: `Callaway & Sant'Anna (2021), Difference-in-Differences with Multiple Time Periods` - 作为 staggered / 多期 DID 权威方法来源。
  - External: `Wooldridge (2021), Econometric Analysis of Cross Section and Panel Data, Ch.21` - 作为 DID / 面板教科书来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/经济金融/eco-001-did-min-wage-policy"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/经济金融/eco-001-did-min-wage-policy/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/经济金融/eco-001-did-min-wage-policy" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - DID 案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook、检查 `outputs/summary.md` 与 `outputs/parallel-trends.png` 存在。
    Expected: 三个命令均成功，且输出文件齐全。
    Evidence: .sisyphus/evidence/task-6-did-happy.txt

  Scenario: Failure/edge case - 缺少平行趋势说明
    Tool: Bash
    Steps: 删除 `index.md` 中 `claim_boundary` 或 `assumption_note` 后执行 `python "scripts/validate_catalog.py" --case "cases/经济金融/eco-001-did-min-wage-policy" --strict`。
    Expected: 校验失败并指出缺少模拟边界/假设说明。
    Evidence: .sisyphus/evidence/task-6-did-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/经济金融/eco-001-did-min-wage-policy/**`]

- [x] 7. 落地经济金融案例二：货币政策传导机制（VAR）

  **What to do**: 在 `cases/经济金融/eco-002-var-monetary-transmission/` 中实现 VAR 案例：生成或准备轻量宏观时间序列，完成滞后阶数选择、VAR 拟合、脉冲响应（IRF）、方差分解（FEVD），并在 `index.md` 中解释“该案例演示政策冲击传播逻辑，而非复刻真实央行冲击估计”。notebook 只展示调用流程与图表解读。
  **Must NOT do**: 不跳过平稳性/滞后阶数选择说明；不把 IRF 图直接手工塞入而没有脚本产出；不把 notebook 写成独立实现。

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: 时间序列建模需要较强方法一致性与结果说明。
  - Skills: [`pandas-pro`] - 需要时间序列整理与窗口处理。
  - Omitted: [`Time Series Analysis`] - 本案是单案例实现，通用 pandas/statsmodels 已足够。

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:273-351` - 参考其把统计输出写为 Markdown 的方式，为本案生成 IRF/FEVD 摘要。
  - External: `Lütkepohl (2005), New Introduction to Multiple Time Series Analysis, Ch.4-5` - VAR 权威教材。
  - External: `Stock & Watson (2001), Vector Autoregressions, Journal of Economic Perspectives` - VAR 解释框架。
  - External: `Kilian & Lütkepohl (2017), Structural Vector Autoregressive Analysis` - IRF/FEVD 进阶依据。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/经济金融/eco-002-var-monetary-transmission"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/经济金融/eco-002-var-monetary-transmission/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/经济金融/eco-002-var-monetary-transmission" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - VAR 案例可运行
    Tool: Bash
    Steps: 运行 smoke test，执行 notebook，检查 `outputs/irf.png`、`outputs/fevd.md`、`outputs/summary.md`。
    Expected: 命令成功，且 3 个输出存在。
    Evidence: .sisyphus/evidence/task-7-var-happy.txt

  Scenario: Failure/edge case - 缺失 seed 或数据模式声明
    Tool: Bash
    Steps: 从 `params.yaml` 删除 `seed` 或从 `index.md` 删除 `data_mode`，再运行严格校验。
    Expected: 校验失败并明确指出缺失字段。
    Evidence: .sisyphus/evidence/task-7-var-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/经济金融/eco-002-var-monetary-transmission/**`]

- [x] 8. 落地经济金融案例三：中国县域经济收敛性（空间杜宾模型）

  **What to do**: 在 `cases/经济金融/eco-003-spatial-county-convergence/` 中实现空间经济学案例。该案采用**轻量真实数据适配**而非纯模拟：用小体量公开县域/地区经济数据样本或仓内附带的精简示例数据，完成 Moran's I、局部聚类（LISA）与空间杜宾模型（SDM）演示；在 `data/README.md` 中写清获取方式、许可、精简原则和为何不存放大体量原始库文件。
  **Must NOT do**: 不把上百 MB 的原始数据直接塞进仓库；不省略空间权重矩阵说明；不把真实数据许可问题留空。

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: 空间权重、真实数据约束与空间回归解释需要较高方法纪律。
  - Skills: [`pandas-pro`] - 需要面板/地理属性表整理。
  - Omitted: [`akshare-finance-pipeline`] - 本案不依赖金融市场抓数管线。

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `教科文卫/build_report.py:38-163` - 现有仓库已有“把真实公开来源整理成结构化常量并带来源 URL”的组织方式，本案可复用这种来源登记纪律。
  - External: `LeSage & Pace (2009), Introduction to Spatial Econometrics, Ch.6-7` - SDM 核心方法来源。
  - External: `Anselin (1988), Spatial Econometrics: Methods and Models` - 空间计量开创性参考。
  - External: `吴建群，《空间计量经济学实证分析》` - 中文方法补充来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/经济金融/eco-003-spatial-county-convergence"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/经济金融/eco-003-spatial-county-convergence/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/经济金融/eco-003-spatial-county-convergence" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 空间案例可运行
    Tool: Bash
    Steps: 运行 smoke test，执行 notebook，检查 `outputs/morans-i.md`、`outputs/lisa-map.png`、`outputs/sdm-summary.md`。
    Expected: 命令成功，且 3 个输出存在。
    Evidence: .sisyphus/evidence/task-8-spatial-happy.txt

  Scenario: Failure/edge case - 数据许可或获取说明缺失
    Tool: Bash
    Steps: 删除 `data/README.md` 中的 license / acquisition note 后运行严格校验。
    Expected: 校验失败并指出真实数据来源说明不完整。
    Evidence: .sisyphus/evidence/task-8-spatial-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/经济金融/eco-003-spatial-county-convergence/**`]

- [x] 9. 落地社会科学案例一：留守儿童学业成绩（双向固定效应）

  **What to do**: 在 `cases/社会科学/soc-004-twfe-left-behind-education/` 中实现双向固定效应案例：模拟个体-年份面板数据，估计父母外出务工对学生成绩的影响，报告主回归、稳健标准误、按年龄/地区的异质性分析，并在 `claim_boundary` 中声明“该案例演示面板识别逻辑，不替代真实 CFPS/CHARLS 实证结论”。
  **Must NOT do**: 不把固定效应解释成万能因果识别；不遗漏个体效应和年份效应；不让 notebook 独立重写回归逻辑。

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: 面板识别与异质性分析需要明确方法边界。
  - Skills: [`pandas-pro`] - 需要生成与整理面板数据。
  - Omitted: [`Causal Inference`] - 本案以标准 FE 实现为主，不做额外因果框架扩展。

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:355-421` - 现有案例会同步输出分析小结与说明文档，本案同样需要把识别逻辑写入 `index.md` 与 `outputs/summary.md`。
  - External: `Wooldridge (2021), Econometric Analysis of Cross Section and Panel Data, Ch.10-11` - 固定效应权威教材。
  - External: `Angrist & Pischke (2009), Mostly Harmless Econometrics, Ch.5` - 应用计量识别解释参考。
  - External: `张川川等（2019），人口流动与留守儿童教育，《经济研究》` - 中文应用补充来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/社会科学/soc-004-twfe-left-behind-education"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/社会科学/soc-004-twfe-left-behind-education/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/社会科学/soc-004-twfe-left-behind-education" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - TWFE 案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/fe-summary.md` 与 `outputs/heterogeneity-table.md`。
    Expected: 命令成功，且两个输出文件存在。
    Evidence: .sisyphus/evidence/task-9-twfe-happy.txt

  Scenario: Failure/edge case - 缺失 replication_type
    Tool: Bash
    Steps: 删除 `index.md` 中 `replication_type` 后运行严格校验。
    Expected: 校验失败并指出缺少 `replication_type`。
    Evidence: .sisyphus/evidence/task-9-twfe-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/社会科学/soc-004-twfe-left-behind-education/**`]

- [x] 10. 落地社会科学案例二：健康不平等与生存分析（Cox）

  **What to do**: 在 `cases/社会科学/soc-005-cox-health-inequality/` 中实现生存分析案例：模拟具有删失信息的队列数据，输出 Kaplan-Meier 曲线、Cox 比例风险模型结果、PH 假设检查与文字解释；在 `index.md` 中明确风险比解释方式和删失数据前提。
  **Must NOT do**: 不把生存概率图当成简单频数图；不省略删失说明；不在 notebook 中重新定义与脚本不同的数据清洗逻辑。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要稳健实现生存分析并写清统计解释。
  - Skills: [`pandas-pro`] - 处理队列与时间到事件数据。
  - Omitted: [`machine-learning-engineer`] - 不涉及在线预测或部署。

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:24-28` - 现有案例会显式写“本数据为模拟数据”；本案必须同样清楚声明删失与模拟假设。
  - External: `Klein & Moeschberger (2003), Survival Analysis: Techniques for Censored and Truncated Data, Ch.8-9` - Cox 模型教科书来源。
  - External: `Therneau & Grambsch (2000), Modeling Survival Data` - PH 假设与实践参考。
  - External: `王广州（2020），社会调查数据分析` - 中文补充来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/社会科学/soc-005-cox-health-inequality"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/社会科学/soc-005-cox-health-inequality/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/社会科学/soc-005-cox-health-inequality" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - Cox 案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/km-curve.png`、`outputs/cox-summary.md`、`outputs/ph-check.md`。
    Expected: 命令成功，且 3 个输出文件存在。
    Evidence: .sisyphus/evidence/task-10-cox-happy.txt

  Scenario: Failure/edge case - 缺失删失说明
    Tool: Bash
    Steps: 从 `index.md` 删除删失/数据模式说明后运行严格校验。
    Expected: 校验失败并指出 `data_mode` / `assumption_note` 不完整。
    Evidence: .sisyphus/evidence/task-10-cox-error.txt
  ```

  **Commit**: YES | Message: `feat(cases): add economics and social science case batch` | Files: [`cases/经济金融/**`, `cases/社会科学/soc-004-twfe-left-behind-education/**`, `cases/社会科学/soc-005-cox-health-inequality/**`]

- [x] 11. 落地社会科学案例三：社会资本与主观幸福感（SEM）

  **What to do**: 在 `cases/社会科学/soc-006-sem-social-capital-wellbeing/` 中实现结构方程模型案例：模拟潜变量测量题项，完成 CFA + 结构路径 + 中介效应输出，在 `index.md` 中写清潜变量、观测指标和拟合指标解释范围；notebook 负责展示模型图、拟合结果和路径解释。
  **Must NOT do**: 不把潜变量题项随意写成无理论支撑的任意指标；不省略拟合指标说明；不把直接效应/间接效应写混。

  **Recommended Agent Profile**:
  - Category: `deep` - Reason: 潜变量设计、路径解释和模型拟合约束较强。
  - Skills: [`pandas-pro`] - 需要处理题项矩阵与测量数据。
  - Omitted: [`langchain-architecture`] - 不涉及 LLM/agent 架构。

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `教科文卫/build_report.py:19-35` - 参考其结构化字段组织方式，为潜变量与路径配置建立清晰参数结构。
  - External: `Kline (2015), Principles and Practice of Structural Equation Modeling, Ch.4-6` - SEM 权威教材。
  - External: `Hair et al. (2019), Multivariate Data Analysis` - SEM 实战参考。
  - External: `刘军（2019），社会资本与主观幸福感` - 中文应用补充来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/社会科学/soc-006-sem-social-capital-wellbeing"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/社会科学/soc-006-sem-social-capital-wellbeing/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/社会科学/soc-006-sem-social-capital-wellbeing" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - SEM 案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/cfa-summary.md`、`outputs/path-summary.md`、`outputs/model-fit.md`。
    Expected: 命令成功，且 3 个输出文件存在。
    Evidence: .sisyphus/evidence/task-11-sem-happy.txt

  Scenario: Failure/edge case - 缺失 claim boundary
    Tool: Bash
    Steps: 删除 `index.md` 中 `claim_boundary` 后运行严格校验。
    Expected: 校验失败并指出案例未声明演示边界。
    Evidence: .sisyphus/evidence/task-11-sem-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/社会科学/soc-006-sem-social-capital-wellbeing/**`]

- [x] 12. 落地市场营销与运营案例一：精准营销 uplift 建模

  **What to do**: 在 `cases/市场营销与运营/mkt-007-uplift-campaign-targeting/` 中实现客户 uplift 案例：模拟营销处理与响应结果，输出两模型法或 S-Learner 的 uplift 结果、目标客户排序与 ROI 对比摘要；在 `index.md` 中明确“预测响应”与“预测增量响应”的区别。
  **Must NOT do**: 不把 uplift 当成普通分类问题；不省略 treatment / control 定义；不输出无法回溯的 ROI 结论。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要兼顾因果异质性解释与业务落地表达。
  - Skills: [`pandas-pro`] - 用于构造客户行为特征与分组结果。
  - Omitted: [`machine-learning-engineer`] - 不做生产级推荐系统。

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:291-351` - 参考其生成 Markdown 统计摘要的方式，为 uplift 结果生成可读摘要。
  - External: `Athey & Imbens (2016), Recursive Partitioning for Heterogeneous Causal Effects` - 因果异质性基础来源。
  - External: `Radcliffe (2007), Using Control Groups to Target on Predicted Uplift` - uplift 经典业务来源。
  - External: `Lo (2022), Causal Inference for Business` - 业务因果补充来源。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/市场营销与运营/mkt-007-uplift-campaign-targeting"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/市场营销与运营/mkt-007-uplift-campaign-targeting/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/市场营销与运营/mkt-007-uplift-campaign-targeting" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - uplift 案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/uplift-ranking.csv`、`outputs/roi-summary.md`、`outputs/model-summary.md`。
    Expected: 命令成功，且 3 个输出文件存在。
    Evidence: .sisyphus/evidence/task-12-uplift-happy.txt

  Scenario: Failure/edge case - 缺 treatment 定义
    Tool: Bash
    Steps: 从 `index.md` 或 `params.yaml` 删除 treatment/control 定义后运行严格校验。
    Expected: 校验失败并指出因果处理定义不完整。
    Evidence: .sisyphus/evidence/task-12-uplift-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/市场营销与运营/mkt-007-uplift-campaign-targeting/**`]

- [x] 13. 落地市场营销与运营案例二：客户流失预测基准案

  **What to do**: 在 `cases/市场营销与运营/mkt-008-churn-prediction-benchmark/` 中实现客户流失预测案例：模拟电信/订阅制客户数据，对比逻辑回归与梯度提升树，输出 AUC、PR 曲线、混淆矩阵与特征解释摘要，并在 `index.md` 中说明“解释性 vs 精度”的取舍，不把该案包装成因果结论。
  **Must NOT do**: 不把分类预测结果说成处理效果；不忽略类别不平衡；不让 notebook 与脚本使用不同特征集。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要兼顾预测基准、解释性与业务表达。
  - Skills: [`pandas-pro`] - 用于特征工程与评估整理。
  - Omitted: [`machine-learning-engineer`] - 不做上线服务或训练基础设施。

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:299-351` - 参考其将统计结果写成 Markdown 的方式，为本案生成模型对比摘要。
  - External: `Hastie, Tibshirani, Friedman (2021), The Elements of Statistical Learning, Ch.4 & Ch.10` - LR 与集成学习理论来源。
  - External: `Chen & Guestrin (2016), XGBoost` - 梯度提升树权威来源。
  - External: `Molnar (2020), Interpretable Machine Learning` - 特征解释与 SHAP 参考。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/市场营销与运营/mkt-008-churn-prediction-benchmark"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/市场营销与运营/mkt-008-churn-prediction-benchmark/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/市场营销与运营/mkt-008-churn-prediction-benchmark" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 流失预测案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/model-comparison.md`、`outputs/roc-curve.png`、`outputs/feature-importance.md`。
    Expected: 命令成功，且 3 个输出文件存在。
    Evidence: .sisyphus/evidence/task-13-churn-happy.txt

  Scenario: Failure/edge case - 缺失数据模式或边界声明
    Tool: Bash
    Steps: 删除 `index.md` 中 `data_mode` 或 `claim_boundary`，再运行严格校验。
    Expected: 校验失败并指出预测案例缺失边界说明。
    Evidence: .sisyphus/evidence/task-13-churn-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/市场营销与运营/mkt-008-churn-prediction-benchmark/**`]

- [x] 14. 落地市场营销与运营案例三：RFM + K-means 客户细分

  **What to do**: 在 `cases/市场营销与运营/mkt-009-rfm-customer-segmentation/` 中实现客户细分案例：模拟交易明细或用户级汇总数据，完成 RFM 指标构造、K 值选择、K-means 聚类、细分画像与策略建议；`index.md` 中明确该案属于描述/分群，不生成因果主张。
  **Must NOT do**: 不把聚类结果当成因果结论；不跳过标准化与聚类数选择说明；不输出无法回溯到 cluster label 的业务建议。

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Reason: 需要在描述分析与业务分群之间保持方法纪律。
  - Skills: [`pandas-pro`] - 用于交易聚合、RFM 构造与分群汇总。
  - Omitted: [`data-visualization`] - 本案图表需求常规，通用绘图即可满足。

  **Parallelization**: Can Parallel: YES | Wave 3 | Blocks: 15,F1,F2,F3,F4 | Blocked By: 1,2,3,4

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `市场调查分析/学生穿着观察法调查/regenerate_yulin_university_survey.py:255-351` - 参考其有序计数与统计摘要方式，输出各客群画像摘要。
  - External: `MacQueen (1967), Some Methods for Classification and Analysis of Multivariate Observations` - K-means 原始来源。
  - External: `Hughes (1994), Strategic Database Marketing` - RFM 方法背景来源。
  - External: `Punj & Moon (2015), K-means Clustering` - K-means 应用指南。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/run_case_smoke.py" --case "cases/市场营销与运营/mkt-009-rfm-customer-segmentation"` 返回 exit code `0`
  - [ ] `jupyter nbconvert --execute --to notebook --inplace "cases/市场营销与运营/mkt-009-rfm-customer-segmentation/analysis.ipynb"` 返回 exit code `0`
  - [ ] `python "scripts/validate_catalog.py" --case "cases/市场营销与运营/mkt-009-rfm-customer-segmentation" --strict` 输出 `case valid`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - RFM 分群案例可运行
    Tool: Bash
    Steps: 运行 smoke test、执行 notebook，检查 `outputs/rfm-table.csv`、`outputs/cluster-summary.md`、`outputs/silhouette-report.md`。
    Expected: 命令成功，且 3 个输出文件存在。
    Evidence: .sisyphus/evidence/task-14-rfm-happy.txt

  Scenario: Failure/edge case - 缺失聚类数选择说明
    Tool: Bash
    Steps: 删除 `index.md` 中关于 `K` 选择或标准化说明，再运行严格校验。
    Expected: 校验失败并指出聚类方法说明不完整。
    Evidence: .sisyphus/evidence/task-14-rfm-error.txt
  ```

  **Commit**: NO | Message: `n/a` | Files: [`cases/市场营销与运营/mkt-009-rfm-customer-segmentation/**`]

- [x] 15. 完成首批 9 案的批次级文献总表与跨案例一致性收口

  **What to do**: 回填 `references/first-batch-source-register.md`，为 9 案逐一登记核心方法来源、补充来源、语言、来源类型、locator（DOI/URL/ISBN）、数据模式、复现关系。同步更新 `cases/index.md` 与 3 个领域 `index.md`，确保案例标题、case_id、方法标签、数据模式、难度、输出文件、状态字段全库一致。运行整库级校验并修正全部非阻塞差异，直到 `validate_catalog`、`run_case_smoke`、`check_notebook_sync` 同时通过。
  **Must NOT do**: 不允许索引与案例 frontmatter 不一致；不允许“先跑通后补文献”；不允许留下语言/来源类型为空的引用记录。

  **Recommended Agent Profile**:
  - Category: `writing` - Reason: 以文献登记、跨案例一致性整理与索引更新为主。
  - Skills: `[]`
  - Omitted: [`review-work`] - 正式最终审查在 Final Verification Wave 进行。

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: F1,F2,F3,F4 | Blocked By: 5,6,7,8,9,10,11,12,13,14

  **References** (executor has NO interview context - be exhaustive):
  - Pattern: `教科文卫/build_report.py:114-163` - 现有仓库已有集中引用列表格式，可借鉴其“引用标题 + URL”组织纪律。
  - Pattern: `市场调查分析/学生穿着观察法调查/调查说明文档.md:30-35` - 现有案例会明确列成果文件；总索引必须与每案 `expected_artifacts` 保持一致。
  - External: `Source Admission Rule (this plan)` - 必须逐案满足“核心方法来源 + 补充来源”的冻结规则。

  **Acceptance Criteria** (agent-executable only):
  - [ ] `python "scripts/validate_catalog.py" --root "." --require-cases 9 --strict` 输出 `9 cases validated, 0 blocking errors`
  - [ ] `python "scripts/run_case_smoke.py" --root "." --all` 输出 `9 cases executed successfully`
  - [ ] `python "scripts/check_notebook_sync.py" --root "."` 输出 `9/9 notebooks in sync`

  **QA Scenarios** (MANDATORY - task incomplete without these):
  ```
  Scenario: Happy path - 全库一致性通过
    Tool: Bash
    Steps: 顺序运行整库级严格校验、整库 smoke、整库 notebook 同步检查。
    Expected: 三个命令全部成功，且总索引、领域索引、文献总表与 9 案 frontmatter 一致。
    Evidence: .sisyphus/evidence/task-15-batch-consistency.txt

  Scenario: Failure/edge case - 索引与 frontmatter 不一致
    Tool: Bash
    Steps: 人为把 `cases/index.md` 中一个案例标题改错，再运行 `python "scripts/validate_catalog.py" --root "." --require-cases 9 --strict`。
    Expected: 校验失败并指出索引记录与案例元数据不一致。
    Evidence: .sisyphus/evidence/task-15-batch-consistency-error.txt
  ```

  **Commit**: YES | Message: `feat(cases): add marketing operations case batch and source register` | Files: [`cases/市场营销与运营/**`, `references/first-batch-source-register.md`, `cases/index.md`, `cases/*/index.md`]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [x] F1. Plan Compliance Audit — oracle
- [x] F2. Code Quality Review — unspecified-high
- [x] F3. Real Manual QA — unspecified-high (+ playwright if UI)
- [x] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit cadence: 1 foundation commit after Wave 1, 1 case-batch commit after Wave 2, 1 case-batch commit after Wave 3, 1 verification/fix commit if needed.
- Commit style:
  - `feat(catalog): scaffold data analysis case library foundation`
  - `feat(cases): add economics and social science case batch`
  - `feat(cases): add marketing operations case batch and source register`
  - `fix(validation): resolve final review findings`
- Never commit generated caches, notebook checkpoints, or oversized raw datasets.

## Success Criteria
- 目录层面：结构稳定、命名统一、领域归类无歧义。
- 内容层面：9 案全部具备方法来源、案例说明、运行入口、notebook 封装、参数与限制说明。
- 验证层面：批量验证、逐案 smoke、notebook 执行、同步检查全部可自动运行。
- 可扩展层面：后续新增案例只需复制模板并填充元数据，不必重构目录。
- 认知层面：读者能从任一案例快速看懂“研究问题 → 方法来源 → 数据声明 → 实现逻辑 → 输出结果 → 局限边界”。
