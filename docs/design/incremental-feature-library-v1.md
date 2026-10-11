# 增量特征库：今晚实施方案

`draft`，2026-10-11，供协调方审定，尚未实现。阅读基线：Engine `0d5a4f8`、Research 候选 `c70afc8`、Data `6298fc5`、Docs `ababb83`。Research 最终 head 与协调方放行后才开始跨模块实现；22:55 上海前只做独立工作树和轻量阅读。目标是次日09:40上海前交可用机制及小规模复用证据，全历史完成时间按实测吞吐另报。

**Owner 与接口。** Data 管事实、成员和 PIT；Core 保留唯一数学；Research 管定义、Release、独立可读配置及实验记录。Engine 新 `feature_library` 外围包管覆盖查询、缺口执行、保存和矩阵投影，Core 仍无 I/O。这是[总纲边界](01_axiom_overview.md#module-boundaries)的待审增量：从现 storage/`VerifiedMatrixStore` 抽取共享 buffer/hash/mmap 与文件生命周期实现；Research 保留 label/fold 准入和公共入口，薄调用 Engine，不整库搬 reader。

接口拟为 `plan_coverage(request) → hits/gaps/dependencies`、`ensure_features(request, source_adapter, budget) → view_ref + stats`、`open_feature_view(ref).project(keys, features)`。请求分开声明 `sample_universe` 与 `feature_reference_universe`、日期/cutoff、特征及 stage；source adapter 交付 Data 公共选择结果和原证据。Engine 不反向 import Research。

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
