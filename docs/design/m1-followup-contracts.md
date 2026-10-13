# M1 本轮兼容和按需读取合同

本页说明 A02/A03/A04/A06 候选的边界，供实现审查与统一小验证使用。当前仅完成部分源码和静态检查，尚未通过项目测试或真实保存件联调。固定版本与验收状态由 [versions.json](../../versions.json) 的 `m1_followup_candidate` 维护；研究者入口见[使用说明](../user-manual.md)。此前七年结果和性能回执保持原有身份与测量范围。

## 派生信号的历史身份

旧 `derived_signal_run_v1` 记录全 Engine 实现身份，因此无关实现变动曾阻断继续用它运行账户。原接口没有独立的信号语义版本。本轮保留旧件全部原字节与身份；跨实现版本使用原信号时，Engine 从原 raw prediction、model、fold spec 和成员证据重放信号计划，逐日精确比较分值、有效性、可知时间、成员和来源引用。缺父件或任何差异都拒绝，不重签旧信号。

新 `derived_signal_run_v2` 增加 `signal_semantics_ref`，包含信号行、时间、成员及缺失传播 ABI，以及计划使用的算子语义版本。`implementation_ref` 继续记录生产源码。无关实现变动不改变语义准入，真正算子语义或 ABI 变化必须显式修订并拒绝不匹配的新件。Research 的新请求身份同时包含此语义引用，防止生成缓存绕过版本边界。现有业务数学、执行规则和历史数值不在本轮改变。

原父件成功准入后的 Derived prediction 保存为 `stock_prepared_predictions_v2`，在现有 owner 元数据内保留每个原信号的语义引用。冷加载继续核验保存字节、完整投影和原信号绑定，并比较当前语义。旧 v1 prepared snapshot 若含 Derived 且生产实现不同，必须拒绝，要求从原父件重新准入；不能把无法重放的旧快照自动升级成可信新快照。Raw-only 保存仍沿用旧 v1 形状。

最小验收包括：旧 v1 跨无关实现变动成功且身份不变；篡改分值、时间或来源即使重新计算普通摘要也被原父件重放拒绝；新语义不匹配拒绝；新快照保存与重载业务结果一致；旧跨实现 Derived 快照被拒绝。全 Engine 实现指纹在所有 owner 合并后只冻结一次。

## 已有股票池贯穿账户

现代共享市场路径将非 CSI300 的 `universe_id` 放入 `StockMarketSpec`，贯穿成员 Query、市场 key、support ref、保存重载及账户准入。CSI300 仍采用原有隐式字段与身份，避免无关迁移。市场只能授权同一成员池的账户；不能用一个池的成员事实绑定另一个池的策略。

Data 已存在 csi300、csi500、csi1000、csi1800 producer，但每次执行仍要具备该池、该区间的 snapshot 覆盖。本轮不新增 CSI800，不改 benchmark，不改变旧物化账户合同。验收只需一个非默认已有池的合成短窗口，覆盖 source、save、reload、account 与错池拒绝，并核对 CSI300 形状不变；不采集真实数据或重跑七年。其他模型后端和持久 daily shadow 延后。

## 特征库证券轴扩展

A04 独立 owner 正在实现旧证券与日期 tile 的保留和缺口增量。截面标准化必须遵循声明的完整 reference universe；raw tile 可复用不代表可以复用另一个截面的标准化结果。待固定源码后补入准确接口、旧件兼容与最小覆盖证据，未完成验收前不宣称通用增量能力已交付。

## UI 的按需 owner 读取

Research 提供 `load_stock_signal_evaluation_summary(path, *, research_root) -> dict`。它只读取所选报告和必要 manifest/group 元数据，使用合计 16 MiB 字节预算，核验报告内容摘要、文件字节与 group 身份绑定；不展开模型、OOS、Label 或其他祖先，也不重算统计。返回原 `input_signal_refs`（`signal_run_ref` 列表）、Label 定义与身份、sample mask、statistics ref、summary、聚合 coverage、status 和 limitations。结果明确含 `audit_scope='report_and_bindings'`、`ancestors_audited=False`。这不是完整数值或来源审计。

UI 比较登记的 typed ref 所含 contract、evidence ref 和 content digest，并核对当前所选 signal 在 `input_signal_refs` 内。摘要接口不可用时显示不可用，不退回 full loader。原 `full` 入口保留其完整校验语义。最小验收必须让 UI 调用真实 Research owner，验证真实保存报告身份及无祖先读取，而不只通过 mock。

A06 分页仍全读索引；单账户曲线入口仍调用 Engine 完整保存账户 loader，读取该账户 profile、全部 result parts 和全部结果种类，再做日期筛选。默认曲线覆盖全区间，以最多 600 个等距原始行号点保留首尾；页面明确抽点可能遗漏波动，不重算指标，明细保留最后 50 行。它避免默认打开及其他账户的读取，但不承诺 NAV-only 或 range I/O。验收需覆盖真实 v7/v8 保存件与 UI 呈现；不得以分片读取不存在为前提计算性能收益。

## 收口条件和成本

先固定所有源码，经父任务审查，再集中执行与以上边界直接有关的小验证。没有新训练、供应商采集或大回测。真实七年训练约 160 分钟、已有库首次加载约 25 分钟，仍是已知主要成本；账户准备及登记采用已合并的复用和 basis 快速路径，不恢复旧重复 IO。除非测量表明下一次研究可获得约 50% 收益，不再为小幅性能改造延迟交付。历史分段计时不能写成一次新的连续端到端测量。
