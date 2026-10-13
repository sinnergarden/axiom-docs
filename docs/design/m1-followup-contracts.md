# M1 本轮兼容和按需读取合同

本页说明 A02/A03/A04/A06 的实现和验收边界。本轮集成源码及限定小验证已完成，Engine、Research、UI 已经父任务审查并正常合并。固定版本与验收状态由 [versions.json](../../versions.json) 的 `m1_followup_candidate` 维护；研究者入口见[使用说明](../user-manual.md)。此前七年结果和性能回执保持原有身份与测量范围。

## 派生信号的历史身份

旧 `derived_signal_run_v1` 记录全 Engine 实现身份，因此无关实现变动曾阻断继续用它运行账户。原接口没有独立的信号语义版本。本轮保留旧件全部原字节与身份；跨实现版本使用原信号时，Engine 从原 raw prediction、model、fold spec 和成员证据重放信号计划，逐日精确比较分值、有效性、可知时间、成员和来源引用。缺父件或任何差异都拒绝，不重签旧信号。

新 `derived_signal_run_v2` 增加 `signal_semantics_ref`，包含信号行、时间、成员及缺失传播 ABI，以及计划使用的算子语义版本。`implementation_ref` 继续记录生产源码。无关实现变动不改变语义准入，真正算子语义或 ABI 变化必须显式修订并拒绝不匹配的新件。Research 的新请求身份同时包含此语义引用，防止生成缓存绕过版本边界。现有业务数学、执行规则和历史数值不在本轮改变。

原父件成功准入后的 Derived prediction 保存为 `stock_prepared_predictions_v2`，在现有 owner 元数据内保留每个原信号的语义引用。冷加载继续核验保存字节、完整投影和原信号绑定，并比较当前语义。旧 v1 prepared snapshot 若含 Derived 且生产实现不同，必须拒绝，要求从原父件重新准入；不能把无法重放的旧快照自动升级成可信新快照。Raw-only 保存仍沿用旧 v1 形状。

小验证已确认旧 v1 跨实现变动且身份不变、重签分值篡改被原父件重放拒绝、新语义不匹配拒绝、新快照重载业务结果一致及旧跨实现 Derived 快照拒绝。原逐日重放继续精确比较时间和来源；本轮未穷举所有破坏组合。两折合成公共入口另验证新件创建、保存读取和缓存命中。全 Engine 实现指纹在所有 owner 集成后冻结一次。

## 已有股票池贯穿账户

现代共享市场路径将非 CSI300 的 `universe_id` 放入 `StockMarketSpec`，贯穿成员 Query、市场 key、support ref、保存重载及账户准入。CSI300 仍采用原有隐式字段与身份，避免无关迁移。市场只能授权同一成员池的账户；不能用一个池的成员事实绑定另一个池的策略。

Data 已存在 csi300、csi500、csi1000、csi1800 producer，但每次执行仍要具备该池、该区间的 snapshot 覆盖。本轮不新增 CSI800，不改 benchmark，不改变旧物化账户合同。已通过 csi500 合成短窗口的 source、save、reload、account 一致、错池拒绝与 CSI300 形状检查；这不证明某个真实 snapshot 已覆盖所有池和年份。本轮未采集真实数据或重跑七年。其他模型后端和持久 daily shadow 延后。

## 特征库证券轴扩展

A04 已整合原 owner 提交，使用 Feature view v3 保存同一列、同一日期的多个证券 block，读取继续兼容 v1/v2。`column_receipts` 返回 `blocks`，每块保留原 dependency、证券轴和 partition；仅单块时保留旧顶层 `partition`。Research 逐块核对当前 source 的局部依赖，不假定每列只有一个 partition。

扩展物理证券轴时应保留旧 raw block，只为缺少的证券计算；字段、历史窗口、有效性、时间或供应商 revision 改变时，相关局部依赖必须失效。截面标准化依赖完整 reference universe；只改变 cohort 时 raw 与复权计算应为零，CS 按需重算。最小测试覆盖 A/B 扩为 A/B/C/D、旧块身份保留、局部事实修改以及 cohort-only 变化。八个相关测试已通过。A/B 扩为 A/B/C/D 的两列、两输出日案例只计算新增 C/D 的 8 个 raw 格点，CS 计算完整 cohort 的 16 个格点；与新建结果的值、有效性和时间逐项一致，旧块字节保持不变。暖命中 raw/CS 调用均为零；仅改变 cohort 时 raw 与复权调用为零，CS 调用为两次。覆盖规划复用的是完整包含在新轴中的旧块，不承诺任意删换证券轴均命中。

新增压缩叶证据、证券轴及子集摘要累计量接入原 Store 的调用方驻留预算。编码预留工作区，解压限定输出长度并预留解码工作区；不足时在 `maximum_working_bytes` 上明确拒绝。此预算接入和拒绝边界经过小测试，长期库的新峰值内存与吞吐未实测；不会在超限时静默忽略预算。

## UI 的按需 owner 读取

Research 提供 `load_stock_signal_evaluation_summary(path, *, research_root) -> dict`。它只读取所选报告和必要 manifest/group 元数据，使用合计 16 MiB 字节预算，核验报告内容摘要、文件字节与 group 身份绑定；不展开模型、OOS、Label 或其他祖先，也不重算统计。返回原 `input_signal_refs`（`signal_run_ref` 列表）、Label 定义与身份、sample mask、statistics ref、summary、聚合 coverage、status 和 limitations。结果明确含 `audit_scope='report_and_bindings'`、`ancestors_audited=False`。这不是完整数值或来源审计。

UI 比较登记的 typed ref 所含 contract、evidence ref 和 content digest，并核对当前所选 signal 在 `input_signal_refs` 内。摘要接口不可用时显示不可用，不退回 full loader。原 `full` 入口保留其完整校验语义。实际联调调用真实 Research owner：原 T01 登记报告实际为 v6，页面显示 H40、IC 0.03407934615989485、RankIC 0.04329736541479455 和 1699 个有效日。仅报告、manifest、group 三文件共 1,717,301 字节进入摘要读取，full 与祖先 loader 被阻断。极小生成的 v8 双信号报告也验证了 group key 和字段映射：评价标签共同为 H5，common 配对均为 65，native 分别为 68/65。接口代码接受 v2–v8，本轮单测及联调覆盖 v3、v6、v8，未逐版本穷举。

A06 分页仍全读索引；单账户曲线入口仍调用 Engine 完整保存账户 loader，读取该账户 profile、全部 result parts 和全部结果种类，再做日期筛选。默认曲线覆盖全区间，以最多 600 个等距原始行号点保留首尾；页面明确抽点可能遗漏波动，不重算指标，明细保留最后 50 行。它避免默认打开及其他账户的读取，但不承诺 NAV-only 或 range I/O。联调已让各 3 行的合成 v7/v8 保存账户经真实 Engine loader 进入 UI，各调用一次 owner，并读取全部结果种类；账户路由使用合成 manifest。1699 行展示的 600 点首尾保留另有小测试。没有重读真实七年账户，不以日期筛选计算 IO 收益，也未执行浏览器像素验收。

## 收口条件和成本

本轮共 18 项不同小测试最终通过。首轮一个 A04 测试漏走生产已有的特征 schema 投影，修正测试后只复测该项；loopback 测试初次受沙箱端口限制，获准后只重试该项。父审追加的缓存预算修复后，只复测受影响的四项及一个新预算边界。没有新增真实训练、供应商采集、大回测或公开研究索引写入。合成两折训练用于公共保存和 Derived 生命周期验证。

旧七年训练/预测公共进程总耗时为 160.25 分钟，已经包含约 25 分钟 Feature 冷准入；其中 fit 合计约 8.31 分钟。不可再把 160 分钟称为纯 fit，或把冷准入重复相加。该旧回执还区分 fold 准备、验证和保存准入，部分子计时重叠。新版长期训练吞吐未测。账户准备及登记采用已合并复用和 basis 快速路径，不恢复旧重复 IO。除非测量表明下一次研究可获得约 50% 收益，不再为小幅性能改造延迟交付；历史分段计时不能写成一次新的连续端到端测量。
