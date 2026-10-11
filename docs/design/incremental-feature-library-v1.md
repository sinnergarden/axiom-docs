# 增量特征库

增量特征库把已登记特征的计算结果保存为可复用的矩形，供研究按日期、证券和特征列选取。扩列或延长日期时，执行器查询覆盖并只补缺口；例如88列一年扩为100列两年，需要计算旧日期的12个新增列，以及新增日期的100列。训练子集、模型、标签和策略由实验配置分别选择，已有 Feature 可供后续实验继续使用。

## 职责与适用范围

[总纲](01_axiom_overview.md#module-boundaries)规定：Data 提供事实、历史成员及 PIT 口径；Core 是唯一数学执行器；Engine 负责稳定身份、覆盖查询、缺口执行、保存和投影；Research 保留登记定义、配置和实验入口，通过薄适配调用 Engine。特征库复用现有内容寻址 buffers 与 `VerifiedMatrixStore`，不承担模型拟合或策略执行。

样本证券 `sample_universe` 与特征参考池分开。固定参考池时，筛选训练或交易行只需投影；改变截面参考成员或行业时，相关截面层需要重算。默认用 `normalized=False` 保存 raw/base，使用时再按明确参考池缓存 CS 结果。raw DAG 自身含截面算子时同样绑定参考池；fitted 处理还须绑定 fit state。现有 normalized 矩阵保留其原始语义，不能作为池无关 raw 使用。

## 身份与复用规则

每列 `semantic_ref` 绑定其 DAG 闭包、算子语义版本、参数、单位与精度、缺失处理、时钟及复权口径。覆盖记录进一步绑定实际选中的输入 revision、来源资格和每日 anchor/cutoff；CS 依赖还包括实际参考成员。实验的总时间、完整 catalog、选列列表、整份 source manifest 或代码 commit 不单独决定缓存是否有效，commit 用于追溯实现。

改变一个输入会按 DAG 历史依赖影响相应列和输出日，无关结果继续复用。纯性能修改须保持数学和保存语义等价；语义修复只失效受影响闭包。每个输出日使用自己的原 anchor/cutoff，历史输入需求由 DAG 推导；含绝对常量的公式不能换成统一月末 anchor。

## 保存、读取与恢复

每个分区保存局部日期/证券轴、schema、语义及依赖身份、原 Core 回执和来源凭证。连续 packed 数组直接写入内容寻址 buffers，validity 和缺值原因分别保留；没有覆盖记录表示尚未计算，已保存的 invalid 单元表示计算后缺值。

v2 view 每个选中分区只保存一次 descriptor，并记录日期和选列。不可变日期覆盖件保存局部摘要，小根索引仅引用日期件；一次 `ensure` 完成后原子发布一次根索引。读取父件前先检查大小，再核验实际 bytes 和内容引用，随后按请求组装矩阵。新增列或日期保留旧 buffer/partition refs。

中断后核验已封存分区及实际 buffers，再恢复覆盖并补剩余缺口；临时半成品不进入可读覆盖。旧 v1 view 继续由同一公开 reader 读取，旧小索引可转换为日期覆盖件，原产物身份保持不变。

## 公开使用接口

Research 用户通过 `SavedColumnFeatureSource` 打开已保存来源，再由 `CatalogFeatureLibrary.ensure` 提交登记选列、输出日期和样本证券。构造 library 时可设置 `maximum_source_bytes`、`maximum_working_bytes` 和 `column_block`，分别限制来源准入、计算/投影工作区和保存列块。以下变量由调用方从已准备的来源和研究配置提供；示例选择 raw/base。

```python
from axiom_engine.feature_library import FeatureLibrary
from axiom_research import (
    SavedColumnFeatureSource, CatalogFeatureLibrary, load_a01_feature_catalog,
)

library = FeatureLibrary(feature_root)
catalog = load_a01_feature_catalog()
with SavedColumnFeatureSource(source_descriptor) as source:
    descriptor, stats = CatalogFeatureLibrary(library, source, catalog).ensure(
        selection=feature_selection,
        output_sessions=feature_sessions,
        sample_universe=sample_security_ids,
        normalized=False,
    )
    with library.open_feature_view(descriptor) as view:
        packed = view.project(keys=sample_keys, columns=selected_columns)
```

`selection` 使用登记的特征 id 和语义版本；`sample_keys` 是 `(security_id, session)` 键。需要截面标准化时显式设置 `normalized=True`，并使用已声明的参考池。返回的 `stats` 区分命中与实际补算。

| 接口 | 用途 |
|---|---|
| `FeatureLibrary.plan_coverage(request, source_adapter)` | 只查询覆盖及依赖，返回命中和缺口 |
| `FeatureLibrary.ensure_features(request, source_adapter)` | 执行缺口并保存固定 view |
| `FeatureLibrary.open_feature_view(descriptor)` | 打开已保存 view，读取不触发 Core |
| `FeatureView.describe()` | 查看固定日期、物理/样本证券、列及语义能力 |
| `FeatureView.project(keys, columns)` | 返回指定行列的只读 packed 数组 |
| `FeatureView.column_receipts(session, columns)` | 核验并读取原分区的语义、依赖及来源凭证 |

训练使用 `build_feature_library_training_view` 生成一次全期兼容投影，由 `load_feature_library_training_view` 准入为既有 `StockFeatureView`，再显式传入训练或 batch loader。各 sequential fold 共享该全期 owner，按行列选择自己的窗口；换模型或选取已有列不重新计算 Feature。

## 当前能力边界

当前来源适配已验证 CSI300 与 `best_effort_vendor_v1`，支持登记 A01 特征使用的价格、成交额及复权事实。CSI1800 历史成员并集、其他 PIT 政策及新事实字段需要相应 Data 来源与适配验证。旧88列 normalized 母矩阵接入尚未完成。全历史准备应先核实实际证券/日期覆盖及所需输入历史，再按测得吞吐安排执行。

磁盘计划默认保留 raw 库，normalized 按实际参考池和选列需求缓存；容量估算须计入来源证据、分区元数据、索引及临时峰值。全历史预计算耗时与总磁盘用量尚未验收。

已保存的真实小例完成首次 Feature→训练→信号→两个独立 Top5 账户→评价，证明子集/换模型时 Feature 计算为0、增列增日保留旧分区引用。另以合成引用检查2242日×88列元数据，root/view 最大约0.89MB/7.71MB，低于原64MiB父件限制，日期覆盖写量随范围线性增长；这不代表全期真实吞吐或总磁盘。实现与验证记录见 [Engine PR34](https://github.com/sinnergarden/axiom-engine/pull/34)、[Research PR18](https://github.com/sinnergarden/axiom-research/pull/18) 和 [Docs PR68](https://github.com/sinnergarden/axiom-docs/pull/68)，实现状态见 [versions.json](../../versions.json)。
