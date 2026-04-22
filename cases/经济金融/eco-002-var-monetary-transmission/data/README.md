# Data README

## 数据模式

- `data_mode`: `simulated`
- 数据不从外部下载，也不在仓库中存放原始宏观数据库文件。
- 所有时间序列由 `analysis.py` 基于固定随机种子动态生成。

## 变量说明

- `M2`：广义货币存量的示范性水平序列。
- `GDP_deflator`：GDP 平减指数水平序列。
- `investment`：投资水平序列。
- `consumption`：消费水平序列。
- `exchange_rate`：名义汇率指数水平序列（数值上升可理解为本币升值压力增强的示范性指标）。

## 获取与复现

直接运行：

```bash
python analysis.py --smoke-test
python analysis.py
```

脚本会先生成水平序列，再对数差分形成用于 VAR 估计的近似增长率/变动率序列。由于案例目的在于演示传播机制逻辑，因此这些变量仅保留“宏观联动结构”，不声称对应真实国家或真实央行样本。
