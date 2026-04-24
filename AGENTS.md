# AGENTS.md — Python 数据分析案例库

> 高信号速查：本库是结构化案例资产库，非应用/服务。所有案例共享一套严格文件合同与验证脚本，改动前务必通读下方约束。

---

## 项目本质

- **类型**：Python 数据分析案例资产库（非 Web 应用、无 CI/CD、无传统测试框架）。
- **语言**：Python ≥3.10，Markdown/Obsidian 文档。
- **组织**：按研究问题领域分 3 个一级目录，禁止按方法名分目录。

---

## 目录与入口

```text
scripts/validate_catalog.py    # 结构/合同/元数据校验
scripts/run_case_smoke.py      # 逐案执行 analysis.py --smoke-test
scripts/check_notebook_sync.py # notebook 与 index.md 同步及逻辑漂移检查
templates/case-template/       # 新增案例的复制模板
cases/                         # 案例按领域存放，固定 3 个子目录
├── 经济金融/
├── 社会科学/
└── 市场营销与运营/
```

**单案例文件合同（7 个）**：
`index.md` `analysis.py` `analysis.ipynb` `params.yaml` `references.bib` `data/README.md` `outputs/README.md`

---

## 核心真源约束（极易违反）

1. **`analysis.py` 是唯一分析逻辑真源**。Notebook 只做叙事封装，不得承载独立业务逻辑。
2. **`index.md` frontmatter 是唯一元数据真源**。`params.yaml` 只承载运行时参数，不得重复元数据语义。
3. **禁止反向同步**：不得先在 notebook 写逻辑再抄回 `analysis.py`。

---

## 验证命令速查

```bash
# 结构校验（目录、模板、索引）
python scripts/validate_catalog.py --structure-only
python scripts/validate_catalog.py --template-only
python scripts/validate_catalog.py --index-only

# 严格案例合同校验（frontmatter 17 字段、params.yaml、references.bib）
python scripts/validate_catalog.py --strict
python scripts/validate_catalog.py --case cases/经济金融/eco-001-did-min-wage-policy --strict

# 仓库卫生（清除 notebook 输出、禁止 __pycache__、 oversized 数据文件）
python scripts/validate_catalog.py --artifact-hygiene

# 单案/全量 smoke test
python scripts/run_case_smoke.py --case cases/<domain>/<case-id>
python scripts/run_case_smoke.py --all

# notebook 同步与逻辑漂移检查
python scripts/check_notebook_sync.py
python scripts/check_notebook_sync.py --template-only
```

**命令顺序**：`--artifact-hygiene` → `--strict` → `run_case_smoke.py --all` → `check_notebook_sync.py`
> 注意：`--artifact-hygiene` 必须在 `run_case_smoke.py --all` 之前运行，因为 Python 脚本执行会生成 `__pycache__/` 目录。`run_case_smoke.py` 已在子进程中设置 `PYTHONDONTWRITEBYTECODE=1`，但手动运行 `python analysis.py` 仍可能生成缓存。

---

## 元数据合同（index.md frontmatter）

必须使用 `---` 包裹的 YAML frontmatter，**17 个必填字段**：
`case_id`, `title`, `primary_domain`, `secondary_tags`, `method_tags`, `research_question`, `analytical_objective`, `replication_type`, `data_mode`, `data_sources`, `literature_sources`, `seed`, `assumption_note`, `claim_boundary`, `expected_artifacts`, `validation_scope`, `status`

**params.yaml 规则**：
- **必须有**：`seed`
- **禁止有**：`case_id`, `data_mode`, `replication_type`, `claim_boundary`（这些属于 frontmatter 语义）

---

## Notebook 包装器约束

- Notebook 应通过 `%run ./analysis.py --smoke-test` 调用脚本。
- `check_notebook_sync.py` 会扫描 code cell：若出现 `def`、`class`、循环、`sklearn`/`statsmodels` 导入、`fit(`、`train_test_split(` 等，视为独立逻辑并报错。
- **Notebook 提交前必须清除输出**：artifact hygiene 会检查所有 `.ipynb` 是否含 `execution_count` 或 outputs。

---

## 命名与分类铁律

- 一级目录固定为 3 个中文领域族：`经济金融`、`社会科学`、`市场营销与运营`。
- 案例目录名必须为英文 slug，格式：`{领域前缀}-{序号}-{英文主题}`，如 `eco-001-did-min-wage-policy`。
- **禁止创建方法级目录**（如 `cases/DID/`、`cases/VAR/`）。
- 中文标题只能出现在 `index.md` frontmatter 和正文中，不得作为文件夹名。

---

## 环境与日积月累的坑

### Windows + Matplotlib 中文缺字
当前 Windows 环境下 Matplotlib 默认字体可能无法渲染中文图题。案例图形标签优先使用 ASCII/英文文本，中文解释保留在 `index.md`、`analysis.ipynb` markdown 区和 `summary.txt`。

### PySAL 安装陷阱
完整 `pysal` 可能因 `fiona/GDAL` 构建失败。稳定做法是只安装最小子包：
```bash
pip install esda libpysal spreg
```

### Conda 兼容环境与重依赖方法
主仓库依赖仍由 `pyproject.toml` 管理；Conda 只用于补足特定方法库在当前 Python 版本下不可安装或不稳定的兼容环境，不提交 conda 环境目录、lockfile 或本机路径。

- 当 `econml`、`pysal`、`arch`、`bertopic`、深度学习/Transformer 等重依赖在当前解释器下安装失败时，优先创建独立 conda 环境验证对应案例。
- 推荐环境命名格式：`case-<method>` 或 `case-<case-id>`，例如 `case-econml`。
- 推荐创建方式：
```bash
conda create -n case-econml --override-channels -c conda-forge python=3.11 pip -y
conda run -n case-econml python -m pip install econml pandas numpy scikit-learn matplotlib pyyaml
conda run -n case-econml python scripts/run_case_smoke.py --case cases/经济金融/eco-013-double-ml-policy-heterogeneity
```
- 若 conda 默认源要求 ToS 且未接受，优先使用 `--override-channels -c conda-forge`，不要在自动化步骤中替用户接受默认 Anaconda channel 条款。
- 即使用 conda 验证成功，`analysis.py` 仍必须保留可解释的 fallback/degraded path，使普通 `python scripts/run_case_smoke.py --all` 在主环境中可运行。

### CRLF 与 frontmatter 解析
Windows 下文件可能以 `---\r\n` 开头。验证脚本已兼容 CRLF，但若自行解析 frontmatter，需同时处理 `\n---\n` 和 `\n---\r\n` 两种结束标记，否则校验静默失败。

### `__pycache__` 与验证顺序
- 任何 `python analysis.py` 执行都会生成 `__pycache__/`。
- `validate_catalog.py --artifact-hygiene` 会检查并拒绝 `__pycache__` 存在。
- `run_case_smoke.py` 已在子进程中设置 `PYTHONDONTWRITEBYTECODE=1`，但手动运行案例时仍需注意。
- 推荐做法：执行验证前先用 `Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force` 清理。

### outputs/ 与 data/ 的 git 策略
- `**/outputs/*` 被 gitignore，**仅保留** `outputs/README.md`。
- 大于 25MB 的原始数据文件不得提交；`.gitignore` 已屏蔽 `.csv.gz`, `.parquet`, `.feather`, `.h5`, `.hdf5`, `.zip`, `.tar.gz`。
- 小型示例 CSV 可故意保留，但需在 `data/README.md` 中声明。

### Smoke Test 契约
每个 `analysis.py` 必须实现 `--smoke-test` 参数，运行最小规模流程并生成 `expected_artifacts` 列出的所有文件。`run_case_smoke.py` 会在子进程中执行 `python analysis.py --smoke-test` 并校验产物存在性。

---

## 依赖

仅使用 `pyproject.toml` 管理依赖，无 `requirements.txt` 或 lockfile。关键包：
`pandas`, `numpy`, `scipy`, `statsmodels`, `scikit-learn`, `jupyter`, `nbconvert`, `matplotlib`, `seaborn`, `linearmodels`, `lifelines`, `semopy`, `pysal`, `pyyaml`, `pytest`

---

## 新建案例的正确姿势

1. 复制 `templates/case-template/` 到新目录 `cases/<domain>/<case-id>/`。
2. 替换 `index.md` frontmatter 中全部 17 个字段，确保 `case_id` 与目录名一致。
3. 在 `analysis.py` 中实现分析逻辑，保留 `--smoke-test` 入口和相对路径解析。
4. 在 `params.yaml` 中只放运行时参数（至少 `seed`）。
5. 运行 `python scripts/validate_catalog.py --case <path> --strict` 通过后再提交。
6. 运行 `python scripts/check_notebook_sync.py` 确保 notebook 无独立逻辑。
7. **清除 notebook 输出后再提交**。

---

## 相关指令文件

- `README.md` — 项目总体说明、分类约束、文件合同
- `.sisyphus/plans/py-data-analysis-case-library.md` — 首批 9 案实施计划与冻结规则
- `.sisyphus/notepads/py-data-analysis-case-library/decisions.md` — 关键设计决策记录
- `.sisyphus/notepads/py-data-analysis-case-library/learnings.md` — 实现经验与坑
