# Python 数据分析案例库

这是一个面向 Python 数据分析实践的案例库，用于沉淀可复用、可验证、可维护的案例资产。目录结构按研究问题所属领域组织，方法只作为案例标签或说明信息，不作为顶级分类轴。

## 一级领域族

- `cases/经济金融/`：经济学、金融学、产业政策、宏观与微观实证等主题案例。
- `cases/社会科学/`：教育、人口、公共政策、劳动、治理、行为与社会调查等主题案例。
- `cases/市场营销与运营/`：营销分析、用户增长、渠道经营、定价、供应链与运营优化等主题案例。

## 分类与命名约束

- 顶级案例分类轴固定为 3 个一级领域族：`经济金融`、`社会科学`、`市场营销与运营`。
- 禁止把方法名升格为顶级目录，例如不得创建 `cases/DID/`、`cases/VAR/`、`cases/RDD/` 等并行目录。
- 每个案例目录必须使用英文 `case-id` slug 命名，例如：`eco-001-did-min-wage-policy`。
- 中文标题不得直接作为文件夹名；中文标题只写在案例内 `index.md` 的 frontmatter 与正文中。

## 单案例文件合同

每个案例目录应自包含，并至少遵循以下文件合同：

- `index.md`
- `analysis.py`
- `analysis.ipynb`
- `params.yaml`
- `references.bib`
- `data/README.md`
- `outputs/README.md`

## 逻辑真源约束

- `analysis.py` 是唯一逻辑真源（single source of truth）。
- `analysis.ipynb` 只做叙事封装、展示过程与结果，不承载独有业务逻辑。
- 任何可复现计算逻辑都应先落在 `analysis.py`，再由 notebook 调用或展示。

## Metadata Contract

`index.md` 必须使用标准 YAML frontmatter（以 `---` 包裹），并完整填写以下必填字段：

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

其中，`index.md` 是案例元数据真源；不得再维护第二份独立元数据合同。`params.yaml` 只承载运行时参数默认值，不替代 frontmatter 的元数据语义。

`analysis.py` 是唯一分析逻辑真源。所有可复现计算、数据处理、统计说明与分析结论生成逻辑都应先落在 `analysis.py`，再由 `analysis.ipynb` 通过 `import` 或 `%run` 调用。不得把独立业务逻辑写入 notebook 后再反向同步到脚本。
