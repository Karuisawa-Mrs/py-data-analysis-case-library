# 数据声明模板

## 数据模式

- `data_mode`: `simulated` / `real` / `hybrid`
- 当前案例声明：`simulated`

## Schema

用表格或项目符号描述主要数据表、字段、主键、时间粒度与单位。

| table | key | grain | fields |
| --- | --- | --- | --- |
| `example_table` | `entity_id` | `entity-period` | `outcome`, `treatment`, `covariate_*` |

## 获取方式

- `simulated`：说明由 `analysis.py` 生成的规则、随机种子和输出位置。
- `real`：说明原始来源、下载链接、访问权限、抓取或清洗步骤。
- `hybrid`：区分真实数据与模拟补全部分，并说明拼接逻辑。

## 合规与限制

说明许可、隐私、脱敏处理、不可共享部分及复现替代方案。
