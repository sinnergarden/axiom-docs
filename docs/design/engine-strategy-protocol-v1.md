# Engine 最小组合策略接口

2026-10-11 父审候选；尚未编码、未执行真实账户。实施期限为当天 14:55 UTC。本页补充 [Trade §6.1](04_axiom_trade.md)，供 Engine、Research 和独立审阅者共享。原 TopK 接口只有固定排序和等权目标，无法表达保留旧持仓、退出覆盖和重新入场状态，因此本轮需要一个显式、可保存的策略配置和纯函数协议。

## 模块、输入与输出

Core 新增 `stock_strategy` 模块。最小协议为 `StockStrategy.plan(*, inputs, state) -> StrategyTargets`；输入和输出都是可转成 JSON 的不可变值，策略不能读取文件、供应商、当日执行行情或账本。内置实现由 `stock_strategy_spec(*, selection="top_k", top_k=5, rank_buffer=None, exit_overlay=None)` 冻结；首版不建设插件注册、动态加载和第二执行器。以后复杂策略可实现同一纯协议，持久化的 Runtime 首版只接纳本页三种已版本化内置组合，不能把不可重建的 Python callable 写入请求。

`inputs` 包含完整、已准入的上一交易日候选 `{security_id, score, member, valid}`，前收盘参考价及 session、可见时间和来源，现金、当前实持数量和可卖数量，待上市权益数量，逐证券买卖数量约束，以及上一完整 session 的风险观察 `{close, cost_minor, owned_quantity, session, available_at, source_refs}`。账户、约束和风险观察各绑定状态水位；风险观察只来自此前已完成的账本与收盘快照，不能把今日 EX 后的数量与昨日原价相乘。所有 `score`、成员和价格仍通过现有 cutoff、身份和完整范围校验。

输出包含 `target_weights`、保留原数量的 `preserve_quantities`、强制退出证券、下一策略状态和逐条理由；新版本决定同时保存策略配置 ref、实际目标、状态前后 ref 及输入来源。非负权重和不大于 1，证券须属于冻结执行池，最大仓位数必须为正整数，布尔值不能冒充整数。Runtime 仍把目标按现有现金加实持市值预算和原价转成整手数量，再使用原 Core intent、风险、撮合、费用、T+1 与现金账本。输出目标不证明卖出成功。

Research 使用新公共工厂 `stock_portfolio_policy(*, strategy_spec, universe_id, execution_universe, execution_rules)`；支持 `universe_id="csi300"` 或 `"csi800"`，绑定完整冻结 union、规则 ref 和成员查询身份。首版池为当时 CSI800 成员，不能以当前行业身份宣称历史非金融池；没有可验证历史行业输入时，必须披露未排除金融。成员 Native 查询仍要求逐 session 原始 PIT 证据和原 cutoff。

## 三种实例与组合顺序

1. **TopK 等权**：按分数降序、证券 ID 升序选 K 只，各占预算 `1/K`。内置配置 `selection="top_k"`。旧接口不足 K 只时仍返回原 `NO_DECISION`；新接口也保留这一行为。
2. **排名缓冲**：配置 `selection="rank_buffer", top_k=5, rank_buffer={"keep_rank":10}`。当前有效成员持仓位列前十时优先保留，空位按排序补足；不可卖的实持或待上市权益先占槽，不能先假定其消失。可配置上限内不足候选时，合格证券仍各占 `1/5`，空位持现金；原数量保留的证券另存显式理由。
3. **TopK 加退出覆盖**：在 TopK 上组合 `exit_overlay={"take_profit":"0.20", "stop_loss":"0.10", "cost_basis":"fee_inclusive_ledger_cost_per_owned_share_v1", "check":"rebalance_sessions_only", "cooldown_rebalance_sessions":1, "reentry":"after_flat_and_cooldown"}`。阈值为正 Decimal 字符串。风险收益为前完整 session 的 `close * owned_quantity * 100 / cost_minor - 1`，盈利达到 20% 或亏损达到 10% 时目标为零，下一交易日由原执行模型处理。成本包括原账本买入费用；`owned_quantity` 包括已经 EX 确认且仍归该账户的待上市赠股，上市本身不重复增加经济数量。这个口径不把现金分红从账面买入成本扣除，故是明确的含费持仓价格收益阈值，而非总回报阈值；缺少可核权益成本或同单位收盘观察时该证券不触发，保存原因。

每次原有周频决策依次执行：更新退出中和冷却状态，过滤禁止重新入场的证券，执行 TopK 或排名缓冲，按前完整 session 的收盘观察应用退出覆盖，检查权重和占槽约束，输出目标。退出覆盖移除后不在同轮补买该证券，也不重分配其预算。TopK 候选不足时保留原选股部分的 `NO_DECISION` 理由与现持数量，但不能阻止已触发或继续退出的证券生成卖出目标。退出中的证券每次检查继续目标零，直到实持与待上市权益都为零；确认清仓的检查及随后 N 次检查禁止重新入场，最早再下一次检查参与候选。每日预测继续保存，账户继续逐日核算，风险覆盖仅在原周频检查点执行；本轮不新增每日止损调度、跨日挂单或日内高低价触发。

Runtime 每笔新证券买入前按实际正数量持仓及待上市权益再次检查上限，卖出失败或部分成交均继续占槽。被容量阻止的买入保存拒绝原因，不能通过推测目标已卖出绕过。相同纯策略与同一风险/执行路径供回测和逐 session 消费；现有完整日量成交代理仍是历史模拟假设，不新增 live 验收声明。

## 兼容、身份与最小验证

策略 spec 使用 `stock_strategy_spec_v1`，输出使用 `stock_strategy_targets_v1`，新配置进入独立 `axiom.stock_portfolio/4` 决定合同；旧 v1/v2/v3 工厂、请求默认值、账户、保存结果及 loader 按原版本保留。新策略配置和池身份进入请求、决定与账户 run ref，不修改原 Signal 身份。公共源码实现 ref 改变时，旧 Derived 信号仍受原实现身份检查；必要时由 Research 从原保存 raw 重新派生并保存新身份，不能伪装旧 SHA，也无需重采、重建 Feature 或 fit/predict。

Engine 只做少量合成和相关兼容验证：拒绝未来收盘/错误权益单位；赠股后同一经济成本不产生假退出；止盈止损触发后不能同轮回买；受阻卖出与待上市权益占槽且买入不超上限；同一信号下三种配置产生可解释的不同目标；旧默认身份保持。Research 独占真实一年账户验证与少量配置比较。交付源 SHA、合成结果及 draft PR 供父审和独立 review；只有父审后才 merge。
