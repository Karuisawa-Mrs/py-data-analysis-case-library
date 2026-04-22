# 数据说明

## 数据模式

- `data_mode`: `simulated`
- 当前案例不依赖外部原始数据库，全部观测由 `analysis.py` 在固定随机种子下生成。

## Schema

| table | key | grain | fields |
| --- | --- | --- | --- |
| `student_panel` | `student_id`, `year` | `student-year` | `exam_score`, `left_behind`, `age`, `baseline_age`, `region`, `household_income`, `study_hours`, `caregiver_support`, `school_resources` |

## 生成规则

- 随机种子固定为 `20260422`。
- 每名学生拥有不随时间变化的个体能力与家庭背景成分，这部分通过个体固定效应吸收。
- 每个年份叠加共同教育环境冲击，这部分通过年份固定效应吸收。
- `left_behind` 由地区迁移推力、家庭经济压力、上一期留守状态和年份冲击共同决定，因此既有横截面差异，也有个体内部的时间变化。
- `exam_score` 由留守状态、家庭收入、学习时长、监护支持、学校资源、个体固定特质、年份冲击与随机误差共同生成；并额外设定低龄组和中西部地区的负向影响更强，以便演示异质性分析。

## 获取方式

- `python analysis.py --smoke-test`：生成精简面板并写出最小验证产物。
- `python analysis.py`：生成完整面板、主回归结果与异质性结果。

## 合规与限制

- 该数据不含真实个人信息，不对应任何真实学校或调查对象。
- 变量分布与参数仅用于教学展示，不应被解释为真实中国留守儿童群体的经验事实。
