# 增量特征库：今晚实施方案

`draft`，2026-10-11。协调方已审 Engine `9a796740433fb7353745bddeddb5d31555fd94dd` 与 Research `6e4a7b5aff80f1c9e2d161aeffe5c83bb7910c90`，实现分别位于 [Engine PR34](https://github.com/sinnergarden/axiom-engine/pull/34) 与 [Research PR18](https://github.com/sinnergarden/axiom-research/pull/18)。真实小例已通过 Feature 子集复用、增列增日和 Core 对照，并完成 H1 标签、两次不同模型训练及新预测；账户和评价尚未启动，当前阻塞在原生市场输入的新增产物预算。全历史完成时间仍需按实际吞吐测量。

**Owner 与接口。** Data 管事实、成员和 PIT；Core 保留唯一数学；Research 管定义、Release、独立可读配置及实验记录。Engine 新 `feature_library` 外围包管覆盖查询、缺口执行、保存和矩阵投影，Core 仍无 I/O。这是[总纲边界](01_axiom_overview.md#module-boundaries)的待审增量：从现 storage/`VerifiedMatrixStore` 抽取共享 buffer/hash/mmap 与文件生命周期实现；Research 保留 label/fold 准入和公共入口，薄调用 Engine，不整库搬 reader。

Engine 的 `FeatureLibrary` 在构造时接受读取、工作区和列块预算，提供 `plan_coverage(request, source_adapter)`、`ensure_features(request, source_adapter)` 及 `open_feature_view(descriptor).project(keys, columns)`。`FeatureRequest` 独立声明样本证券；参考成员来自已冻结 plan。Research 的 `SavedColumnFeatureSource` 准入原 source，`CatalogFeatureLibrary.ensure` 将登记定义和 raw/CS 请求薄接入 Engine。`build_feature_library_training_view` 生成显式新布局，再由 `load_feature_library_training_view` 准入为既有 `StockFeatureView`；调用方将该 handle 显式传给训练和 batch loader。Engine 不反向 import Research。

**身份与复用。** 单列 `semantic_ref` 绑定 DAG 闭包、算子语义版本、参数、单位/dtype、缺失、历史/时钟与复权口径。覆盖项局部绑定字段/逻辑键/所选 revision、availability/来源资格及每日原 anchor/cutoff；使用 Data 公开 provenance，不能只用物理行序号。CS 闭包再绑定实际每日参考成员/行业，fitted 层再绑定 fit state。完整 catalog、selection、实验总时间、source manifest、commit 不作为唯一缓存键；真实 commit、原 plan/result refs 保留履历。值相同而来源/时钟改变，只复用物理值文件，逻辑产物更新。

用现 `normalized=False` 默认准备 raw/base；raw DAG 含 CS 时仍绑定池。固定参考池下筛训练/交易行只做投影，改池只重算相关 CS 闭包。现88列可用于相同参考池的 normalized 扩展；首次 raw 准备属于另一个 stage，不能从旧 zscore 反推。性能变化须证明等价；语义修复只失效受影响闭包，保留旧件审计。

**保存与迁移。** 延用内容寻址 buffers、原子分区，增加可重建的小型列覆盖索引。分区有局部日期/证券轴和列语义身份，view 显式投影到请求轴/schema。88列一年扩到100列两年时，只算 `旧日期×12新增列 ∪ 新日期×100列` 及所需输入历史，旧 buffer/分区 refs 不变。无覆盖项表示未计算，已发布 validity/reason 表示计算后缺值。分区核验后才原子更新索引，中断后从封存分区恢复。旧 loader/refs 保留；新布局显式启用，旧矩阵仅在原准入通过后作为带原轴/身份的只读叶子接入，不重签旧件。

**结构性提速。** [producer](https://github.com/sinnergarden/axiom-research/blob/c70afc8acfe26b3d8a6b18beaf68432a17ae1a94/src/axiom_research/stock_feature_column_producer.py) 将 packed 数组展开再打包，[准入](https://github.com/sinnergarden/axiom-research/blob/c70afc8acfe26b3d8a6b18beaf68432a17ae1a94/src/axiom_research/stock_matrix_feature_column_metadata.py) 逐 cell 切片 hash。优先让 Core 数组直达有界日期/列块，冻结连续 bytes 后 hash/写入，按同一物理块验证，只在取行时展开。新 proof 按块绑定，整列块拼接不能冒充旧逐行哈希顺序。source 改成有界只读块，物理输入块解码与编译/调度复用；历史需求复用 `required_history`/`_needed`。保留连续日历与每输出日 anchor/cutoff，不以月末 anchor 替代含绝对常量的 KMID2/RSV 输入。

**顺序与验收。** 放行后：① Engine 身份/覆盖及 packed store；② Research 薄接入与配置、raw 默认及 CS/fitted 按需；③ A–D和一次中断恢复；④ 一次真实小例和吞吐报告。代码及公共文档分别走 Draft PR，协调方亲审后合并。

| 用例 | 必交证据 |
|---|---|
| A 首次闭环 | Feature→实际训练→保存信号→现 Engine 策略→评估 refs/计数 |
| B 子集/换模型 | 固定数据/参考池，Feature计算0 |
| C 增列/日期 | 旧区域 refs 不变，仅缺口计算；与一次性小对照核对值/键/validity/原因/时钟 |
| D 改池/修订 | 相关闭包失效；修订按 DAG 历史依赖传播，无关列/日期命中 |

可控 fixture 验证 A–D；真实小例拟用≤24样本证券、6–10输出日、3–6列及完整历史，CS仍用原完整每日参考池。小测一次，记录来源、Core准入/数值与来源传播、写入/准入、RSS、bytes、命中和计算cell，再决定是否优化逐证券Python调度及放大。协调方已有测量为120日×569×88共957秒、RSS0.923GiB，Core约2.4秒/日、保存准入约5.5秒/日，来源另计；本文未重新执行，writer优化不能推出全量12小时。

现 source 仅证明 CSI300/`best_effort_vendor_v1`。CSI1800需实际历史成员输出及profile小例；其他PIT政策需逐cutoff选版验证；未支持的登记特征明确列缺口。126GiB空余扣除Data预留30GiB后，现18bytes/cell的全raw层下限约67.91GiB；raw+normalized约135.82GiB装不下。默认保留特征raw，normalized按实际池/选列缓存；原因/来源按块字典或稀疏结构精确保存，source、索引、元数据及临时峰值实测计预算。既不删除Data Raw，也不承诺今晚全历史预计算完成。


**已执行的小例与边界。** 以下数字来自 2026-10-11 的一次真实 Feature 小例，使用固定 Snapshot、原 CSI300 参考成员、569 只证券和 `best_effort_vendor_v1`，初始选列为 ALP001、ALP002、ALP003、ALP008，日期为 2022-12-23 至 2023-01-03 的七个交易日。读取原 source 和 Data 数据均为只读，新产物保存在独立目录。旧 source 准入另计 32.41 秒，校验约 1.88GiB 实际文件；该成本不能归入数值执行，也不能从热复用数字中省略。

| 真实请求 | raw / CS 实际计算 | 耗时与证据 |
|---|---|---|
| 首次七日四列 | 每层 15,932 单元，各 7 次 Core 调用 | 15.87 秒；训练兼容投影另计 4.63 秒 |
| 同日期选 ALP001、ALP003 | 每层 0 单元，0 次 Core 调用 | 4.15 秒，仍有身份、覆盖和实际文件准入工作 |
| 加 ALP022，并加 2023-01-04 | 每层 6,828 单元，各 8 次缺口 Core 调用 | 19.72 秒；旧 28 个日期×列分区引用保持不变 |
| 原 Core 小矩形对照 | 八日五列一次性定义 | 八日的值、validity、时钟和缺值原因逐项完全一致 |

Feature 进程峰值 RSS 为 0.79GiB。含失败准备回执的全部新增小例产物约 11.87MiB，低于 256MiB 预算。六个有针对性的合成用例还证明了改参考池、修订输入、一次中断恢复和新 raw 字段补历史时的局部复用；这些合成证据不能冒充真实修订或通用新字段适配。

真实纵向曾在既有 `Data.open_column_source` 的旧 Snapshot 准入处触发 4GiB 保护。协调方随后将同一小例的进程上限改为 12GiB、目标常态不超过 8GiB；未改 Data 格式，未重新生产 Feature。接续执行的 Data Snapshot 打开耗时 29.78 秒，saved source 冷准入另计 34.26 秒，进程峰值为 3.40GiB。实际物理输入最高占用约 211MiB，因此 ColumnSource 使用 512MiB 缓存；原 64MiB 缓存不够借用年度物理块。

四列、10 棵树和两列、5 棵树各训练一次，均保存了真实 LightGBM booster、模型和新预测；各用五个成熟日期、1,500 行训练数据，输出 1,138 行完整预测网格，其中两日共 600 行有效。两次的 Feature Core 调用均为 0。四列的 view 准入及标签准备耗时 5.59 秒，随后 fit/predict/保存信号合计 2.31 秒；两列对应为 3.79 和 0.54 秒。既有组合入口未单独保留 backend fit 与 predict 的计时，不能将这些合计数字冒充独立 backend 耗时。

账户输入的原生导出随后在保存 coverage 时拒绝 128MiB 导出配额。固定 Snapshot 的 price-limits coverage 约 117MiB、corporate-actions coverage 约 196MiB，既有接口会完整保存这些全局证据；两份合计 313MiB，尚未计入小例已有的约 24MiB 产物和其他输入，已超过协调方保留的 256MiB 新增总预算。因此账户和评价没有启动，重进程已退出，Feature、标签、模型和预测全部保留。下一步需协调原生输入的保存预算或既有只读复用入口，再接续原 Engine 账户；不重算 Feature 或重新训练。

当前仍未接入旧 88 列 normalized 母矩阵，尚未证明 CSI1800 历史并集，亦未测量全历史索引和预计算吞吐。
