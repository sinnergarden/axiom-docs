# 增量特征库

增量特征库把已登记特征的计算结果保存为可复用的矩形，供研究按日期、证券和特征列选取。扩列或延长日期时，执行器查询覆盖并只补缺口；例如88列一年扩为100列两年，需要计算旧日期的12个新增列，以及新增日期的100列。训练子集、模型、标签和策略由实验配置分别选择，已有 Feature 可供后续实验继续使用。

当前状态、已验证范围、成本测量及适用源码统一以 [versions.json](../../versions.json) 的 `incremental_feature_library_candidate` 条目为准。本文说明使用方法和复用条件；完整多年研究及 M1 验收仍有未完成项。

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

从已有列挑子集时，可以直接调用 `FeatureView.project`；换模型、标签或策略不改变这份 Feature。新增列时，把已登记的新列加入 `selection`，在同一库调用 `ensure`。新增日期时，扩大 `output_sessions`；超出已保存来源的日期须先由来源 owner 准备并准入相应事实、每日 cutoff 和 DAG 所需历史，再调用同一库。已有覆盖且语义与依赖相符的旧区域保留引用，缺口返回新的固定 view。88列一年扩为100列两年说明补算规则，目前真实大样本覆盖仍为88列，新增列与日期的正确性另有有界真实用例验证。

筛选训练证券通过 `sample_universe` 或投影行键完成，并保持原 `reference_security_ids` 和历史每日成员规则。若改变参考成员、行业或截面变换，相关层按新的依赖重新计算。仅改证券范围或模型名不能取得另一参考池的标准化结果。

| 接口 | 用途 |
|---|---|
| `FeatureLibrary.plan_coverage(request, source_adapter)` | 只查询覆盖及依赖，返回命中和缺口 |
| `FeatureLibrary.ensure_features(request, source_adapter)` | 执行缺口并保存固定 view |
| `FeatureLibrary.open_feature_view(descriptor)` | 打开已保存 view，读取不触发 Core |
| `FeatureView.describe()` | 查看固定日期、物理/样本证券、列及语义能力 |
| `FeatureView.project(keys, columns)` | 返回指定行列的只读 packed 数组 |
| `FeatureView.column_receipts(session, columns)` | 核验并读取原分区的语义、依赖及来源凭证 |

训练使用 `build_feature_library_training_view` 生成一次全期兼容投影，由 `load_feature_library_training_view` 准入为既有 `StockFeatureView`，再显式传入训练或 batch loader。各 sequential fold 共享该全期 owner，按行列选择自己的窗口；换模型或选取已有列不重新计算 Feature。

## 成本与进程复用

首次准备需要准入来源事实及历史、执行缺口的 raw/base 与所需截面层，并保存 buffers 和覆盖。之后扩列或增日只补仍缺少的结果，但覆盖查询、来源核验和保存仍有成本。本次全期准备经历中断恢复和已审定的性能修复，没有报告连续首次运行总耗时。

训练兼容投影是单独的构建步骤；本次完整样本测得708.5秒，Feature 计算为0。新进程公共冷加载也有独立成本：重新核验实际来源与特征 bytes，再逐日比较投影的数值、有效位、时钟、缺失原因、来源引用和成员。本次测得1201.7秒，约20分钟，Feature 计算为0；此数值只适用于该样本与执行环境。

同一进程内，已准入的全期 owner 由多个窗口和 sequential fold 共享，边界继续检查实际使用的文件。新的独立进程重新准入，不能假定只读 descriptor 就能跳过冷加载。后续 subset 或模型迭代复用已有 Feature，仍需承担取行选列及相应标签、拟合、预测、评价或账户运行的成本。精确测量与范围记录在 [versions.json](../../versions.json)，其他规模按实际吞吐和存储重新预算。

## 当前能力边界

当前真实来源适配已验证历史CSI300参考成员与 `best_effort_vendor_v1`，支持登记 A01 特征使用的价格、成交额及复权事实。已完成范围见 [versions.json](../../versions.json)：88列、2242个输出日的 raw/base 与原每日参考池 normalized 结果已经保存，606证券训练投影通过公共冷加载的完整语义校验。CSI1800历史成员并集、所有登记特征、其他 PIT 政策及新事实字段仍需相应来源与适配验证。已有旧母矩阵保留原身份；使用上述公开接口建立增量库，不把旧 normalized 值改称 raw，也不声称任意旧矩阵已自动导入。

股票池是配置输入。固定CSI300名称的试点限制已随 [Research PR22](https://github.com/sinnergarden/axiom-research/pull/22)移除，来源适配按已准入manifest报告真实池名和policy，并用两个不同池的合成样本验证raw复用及每日参考变化。合并版本与状态见 [versions.json](../../versions.json)；全期真实验证仍限原CSI300数据，其他池目前仅通过有界合成检查。现来源共用同一段物理历史，`verify_feature_column_source`仍要求已证明的vendor选择不变口径；`build_feature_column_source`仍检查可见释放时点与稳定的dated-membership来源profile。其他PIT政策须先实现对应的逐cutoff选择语义，不能仅修改policy名字。

特征库与模型后端分别扩展。当前已验证LightGBM及其支持的参数配置；其他算法须完成现有模型接口的训练、保存和推理适配，不能把特征库可复用写成任意模型已经支持。

磁盘计划默认保留 raw 库，normalized 按实际参考池和选列需求缓存；容量估算须计入来源证据、分区元数据、索引及临时峰值。当前CSI300样本测量见 [versions.json](../../versions.json)，CSI1800及所有登记特征的全历史预计算耗时与总磁盘用量仍未验收。

已保存的真实小例完成首次 Feature→训练→信号→两个独立 Top5 账户→评价，证明子集/换模型时 Feature 计算为0、增列增日保留旧分区引用，并与一次性小对照相同。全期真实库另验证了封存分区恢复和正式训练投影的公共冷加载；全期模型、信号、策略及评价由后续执行 owner 完成。实现与验证记录见 [Engine PR34](https://github.com/sinnergarden/axiom-engine/pull/34)、[Research PR18](https://github.com/sinnergarden/axiom-research/pull/18)，读取边界的性能修复见 [Engine PR35](https://github.com/sinnergarden/axiom-engine/pull/35) 与 [Research PR21](https://github.com/sinnergarden/axiom-research/pull/21)。验证层次、测量和未完成项统一记录在 [versions.json](../../versions.json)。
