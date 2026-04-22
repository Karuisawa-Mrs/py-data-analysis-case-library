# 数据说明

## 数据模式

- `data_mode`: `simulated`
- 当前案例不依赖任何真实社会调查原始数据，全部观测由 `analysis.py` 用固定随机种子生成。

## Schema

| table | key | grain | fields |
| --- | --- | --- | --- |
| `indicator_data` | `respondent_id` | `respondent` | `sc1`-`sc3`, `st1`-`st3`, `swb1`-`swb4` |

## 生成规则

- 固定随机种子为 `42`。
- `social_capital` 是外生潜变量，并由 3 个社会资本指标反映。
- `social_trust` 由 `social_capital` 与随机扰动共同生成，并由 3 个信任指标反映。
- `swb`（subjective wellbeing）同时受 `social_capital` 与 `social_trust` 影响，并由 4 个幸福感指标反映。
- 每个观测指标都由“潜变量信号 + 题项测量误差”构成，随后做标准化处理，以便示范连续指标 SEM。

## 获取方式

- `python analysis.py --smoke-test`：生成精简样本并完成最小化 CFA/SEM/中介分析。
- `python analysis.py`：生成完整样本并写出完整案例产物。

## 合规与限制

- 数据为合成示例，不对应任何真实受访者、社区或全国性调查样本。
- 潜变量结构与路径强度由教学目的预先设定，因此只能用于说明建模流程，不能外推为真实社会资本与幸福感的经验关系。
