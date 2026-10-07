# Engine/Runtime 初版设计：统一回测、运行时与事务账本

> 文档编号：AX-TRADE · 专项初版 v0.1 · 所属设计包 v0.2 · 2026-09-05。\
> 状态：实施参考草案，不授权联网下单、账户迁移或生产切换。\
> 上位边界：[总体设计](01_axiom_overview.md)。关联：[Core](03_axiom_core.md)、[Data](02_axiom_data.md)、[Research](05_axiom_research.md)、[UI](06_axiom_ui.md)。\
> 继承既有 SQLite ledger 的账户主键、流水与投影分离；发送恢复、乱序回报、资金精度等是本版补充约定。准确交易规则、券商能力和费率须专项取证。

本专项描述 axiom-engine 内的逻辑模块，物理仓库按[补丁 A](07_重要补丁_A.md)执行；Data 输入与首版范围已同步 2026-09-27 个人版，不改变本模块的计算或交易职责。

2026-09-28 Data 接口实证：DecisionBatchGate 已用真实输入验证批次 Snapshot 固定及 decision/market_replay 分离；本次没有实现或验收委托、成交、账户与完整 BacktestRun。
见 [真实 Developer 教程](../../notebooks/developer_tutorial.html#section-9) 与 [设计对照](../design-conformance.md)。正文继续定义目标合同。

2026-10-05 实现状态：保存 Signal 与固定 MarketReplay 已由公共 run_backtest 消费；
Core 规划组合，Runtime 唯一核算现金/持仓/费用/NAV，Evaluation 消费保存账户，
Research/UI 不另建账户路径。当前股票公开组合政策只接受 Top5，§6.1 的显式
TopK 是待实现增量。无账户依赖的同一保存 Signal 可供多个独立账户/策略消费，但策略与
账户状态各属自己的账本；要展示真实 Top3/Top5 账户结果须分别保存身份，
不能以变更初始资金冒充策略变化。

## 1. 定位：策略运行与执行系统，不只是实盘下单

Trade 内包含 runtime、唯一正式回测、shadow/real、行情/Broker adapter、统一账户核算、SQLite ledger、恢复/对账与账户评估。Runtime 不再单拆 repo。

```text
Request
→ resolve / validate / freeze ResolvedRunPlan
→ Clock / Feed / SignalSource
→ Core decision
→ persist OrderIntent
→ SimBroker or RealBroker
→ fills / account events
→ accounting + ledger
→ run artifacts / evaluation / UI projections
```

Trade 不重新实现 Feature、推理、选股与换仓；Research 不另写一套账户回测；UI 不直改数据库。第一版一账户对应一个策略部署/虚拟实验，暂不做多策略共享实盘资金的复杂分摊。

## 2. 外部交互与模式

| 模式 | 市场与时钟 | 信号来源 | 成交与账户 |
|---|---|---|---|
| backtest | HistoricalClock + 固定 MarketReplayView | CachedSignalSource 或 ModelSignalSource | SimBroker + 独立临时账本/状态；完成后不可变 BacktestRun |
| shadow | 实际时钟 + 已登记 Feed | 发布包同一推理链 | SimBroker + shadow SQLite ledger |
| real | 实际时钟 + 已登记 Feed | 发布包同一推理链 | RealBroker + real SQLite ledger + 对账 |

mode 只在 Runtime 组装 adapters；Core 的 Context 不接 mode。SimBroker 与 RealBroker 实现相同执行事件协议，但不能承诺成交或净值相同。

Research 用 P09 提交回测请求，Trade 返回 BacktestRun/P10 评估；Data 提供 P02/P03，实际使用 Qlib 时才需要 P04；Core 消费 P07 并输出 P08 Intent；UI 经 P12 查询运行、图层和账户投影。

Data 的逻辑 FactView/MarketReplayView 是固定 Snapshot + QuerySpec，可内嵌本次 Plan；不要求预先发布独立 View artifact 或逐域 commit。Runtime 检查本次实际输入、持仓、lookback 与执行范围；不依赖通用 Data admission 平台。market-public 与 system-observed 是不同时间问题，运行明确选择 policy，不能用后补公开证据伪造系统当时已收到。

Runtime adapter 消费 Data 的 P02 DataBatch，并映射为 Core 的 P05 FactBatch；成员/事件查询同时固定 PIT policy 和 cutoff。执行侧 P03 查询固定事件范围、价格和历史修订解释，可预读文件但只能随执行时钟释放事件。映射不重新解释单位/复权/PIT；决策输入、执行回放与 Research Label 结果保持用途边界。长 run 保存实际 batch/session→data/query/model refs，供 P12 重放；当前默认 Snapshot 不能替代历史输入。

离线回测必须可在不安装/登录券商、无 real 凭证的环境运行。Live/Broker SDK 按需加载，不能 import Trade 就连接券商。

## 3. 一套回测，两种信号输入

### 3.1 日常研究

```text
SignalRun + portfolio/rebalance/risk policy + MarketReplayView
→ unified runtime → Core → SimBroker → Accounting → Evaluation
```

只改换仓/持仓/风控，不重训、不重新预测。Research 的 IC、Recall@K 等信号评估是另一个分析步骤，不是第二个 fast backtest。

### 3.2 发布前与问题复验

```text
StrategyRelease + FactView + frozen model schedule + MarketReplayView
→ 同一 runtime 的 ModelSignalSource
→ 同一 Core/SimBroker/Accounting/Evaluation
```

model source 只执行保存模型，不在回测里重训。滚动历史有明确 fold→ModelRelease→允许预测日期映射，不能用最新模型回推全历史。

两种 source 必须在相同 `signal_stage` 接合，避免 cached 已组合分数被再组合一次。依赖账户/成交路径的信号不能作为无条件跨策略复用的缓存，必须随运行重算或绑定对应状态轨迹。

## 4. Request、ResolvedRunPlan 与运行身份

2026-10-04 本轮公共 `axiom_engine.runtime.BacktestRequest / MarketReplay / run_backtest` 显式接收冻结最终 SignalFrame 与固定回放，不 import Research，不解析 mutable workspace。`backtest_run_v1` 绑定 signal/market/profile refs、全部 Engine Python 实现文件的内容身份、`committed_sequence`、`final_account` 和 `content_digest`。`save_backtest_run / load_backtest_run` 保存/验证已有结果；加载不重新计算。实际源码、结果与审批范围见 [当前交付](../current-delivery.md)。下列通用 ResolvedRunPlan、model source、live 恢复仍是目标。

### 4.1 请求最低字段

```yaml
request_id: request_example
mode: backtest
input_mode: cached_signal
signal_run_ref: sig_example
strategy_release_ref: sr_example
market_view_ref: market_example
fact_view_ref: null
initial_account_ref: seed_example
scope: {start_session: "2021-01-04", end_session: "2026-07-31"}
execution_profile_ref: execution_example
evaluation_spec_ref: evaluation_example
```

null 只用于当前模式不适用项，附原因；必要项缺失应拒绝，不用 `NOT_AVAILABLE` 假装绑定完成。

### 4.2 一次解析

Runtime 解析 release/model/snapshot/view/universe/default，并固定具体 refs；代码、配置、依赖包和 adapter 配置也固定。解析后所有子组件复用同一 `ResolvedRunPlan` 和加载对象，不再次访问指针、mtime 或 mutable checkout。

```text
run_id                    一次逻辑运行
attempt_id                一次实际执行/恢复尝试
decision_id               一次策略决策
order_intent_id           一项持久意图
client_order_id           外部发送稳定身份
broker_order_id           券商返回的订单身份
account_id                现金和持仓的主键
strategy_release_ref      本次决策策略来源
```

一个失败 attempt 不生成第二套相同意图。显式“新研究重跑”产生新 run；同 run 的恢复保持 logical IDs 和账户处理水位。

Plan 记录实际使用的代码来源/发布包、配置、依赖、data roots 定位信息、refs、cutoff、initial state、execution/evaluation profiles。Data 侧允许可恢复 commit + 依赖锁 + 实际配置，不强制代码归档；未保存 dirty 修改不能冒称对应 commit。Runtime 的生产发布包要求不变；不能只记主 repo commit，也不要求所有组件位于同一 checkout。

### 4.3 长服务与实时输入

按 session/决策批次固定计划，下一批次可采用新数据/策略并重新 preflight。已启动的 D1/M1 不会因 current 指向 D2/M2 而变。

尚未到来的 Feed/Broker 输入无法提前 hash。启动时固定连接/来源/事件合同，运行中按序保存实际收到的输入及接收时间。账户变化正常流入下一决策；冻结身份不等于冻结未来市场和账户。

## 5. 时间推进与事件协议

共同事件 envelope：schema/version、event_id、source/source_event_id、account_id、run_id、causation/correlation IDs、event_time、received_at、logical sequence、payload digest。历史同时间事件固定排序；真实回报按接收序持久化，并保留业务发生时间。

| 事件 | 生产者 | 作用 |
|---|---|---|
| MarketEvent / CorporateActionFact | Data/Feed adapter | 市场和权益事实 |
| SignalEvent | SignalSource | 当前允许使用的最终投资分数 |
| TargetEvent / OrderIntent | Core | 目标、交易意图，不直接改持仓 |
| OrderEvent / FillEvent | Broker adapter | 已发送/确认/拒单/撤单/部分或全部成交事实 |
| AccountEvent | Accounting / reconciliation | 费用、股息、送转、入出金、结算/调整 |
| AccountProjection / PositionSnapshot | Trade | 带 committed sequence 的账户视图 |

建议日级顺序：结转可用状态/权益事件→取得到 cutoff 的事实和账户→生成决策→登记/发送意图→按市场时钟处理回报→记账→估值/快照→报告。实际事件阶段由 ExecutionProfile 明确，不把所有公司行动统一塞到同一个日终。

Decision Reader 与 Simulator Reader 隔离。Simulator 可以处理之后发生的价格区间，但不能把全天 high/low/close/volume 提前交给开盘 Core。日线不足以证明精确开盘可成交量；使用日成交量约束的 profile 必须标明估计成交窗口、可用信息和日级近似，不能据此宣称精确开盘撮合，也不能用尚未确认的日终成交余额进行更早的日内再决策。

## 6. ExecutionProfile：最低回测真实性

当前 `daily_open_profile()` 默认 `unknown_status_policy="block"`，严格 UNKNOWN 状态阻断保留。用户批准本轮显式 ETF 日线实验设置 `unknown_status_policy="etf_daily_observed"`：仅已识别的 canonical ETF 状态缺源原因可在有效 observed open、正日成交量与合法限价下准入；事实 UNKNOWN 和 order/fill 的 `ETF_OBSERVED_DAILY_ASSUMPTION` 保留。已知/日内停牌、其他未知原因、现金/限价/容量/可卖数量仍阻断。全天 volume 仅在执行侧作容量代理，不进入开盘 Core；它不能证明开盘流动性。T+1/100 基金份额是保守实验参数，未验证为真实 ETF 规则。详见 [ETF 合同](../etf-rotation-data.md#消费者交接) 与 [当前交付](../current-delivery.md#同一输入与两种执行政策)，此 profile 不可当成实盘规则。

| 项目 | 初版要求 | 不允许 |
|---|---|---|
| 信息/价格时序 | 决策 cutoff、最早委托/成交、参考价和成交窗口明确 | 未发生收盘信息却按同一收盘价买入 |
| 停牌/缺价 | 不成交；估值价格和陈旧状态单列 | 填价后当真实可成交 |
| 可用现金/可卖数量 | 接受账户冻结、结算与规则约束 | 目标仓位当实际仓位，超可卖数量 |
| 涨跌停 | 按规则/方向、日级可观测性做保守模拟 | 只要碰价就认为能成交 |
| 成交量 | 事前规划用已知流动性，模拟按明确窗口执行 cap/partial fill | 先用未来成交量选股或无限容量 |
| 费用/滑点 | 佣金/税费/最低费用/价格滑点各自明确 | price 已含滑点又从现金重复扣 |
| 公司行动 | 股息、送转等进入权益/现金/数量与成本基准 | 复权收益与分红现金重复计入 |
| 未成交 | 保留、到期、撤销及再次规划规则 | 每天丢掉挂单并重发 |
| 不支持事件 | profile 的 capability check 阻断受影响正式范围 | 默默忽略配股、退市/代码变化 |

细致冲击模型与订单簿不是首版前提；报告必须保留可执行性限制，并做成本和容量敏感性。不要先假定 1000 万规模一定没有影响，也不写一个通用资金阈值替代标的/换手分析。

初版规则字段随市场、证券类别和日期版本化；实际费率、涨跌幅、最小交易单位和结算细节在上线前用当前权威规则与 Broker 样本确认，不在总纲硬编码。

<a id="stock-daily-observed-minimal"></a>
### 6.1 有界股票日线 Top5

状态：`frozen_for_bounded_implementation`（2026-10-04，主协调亲读并批准）；只补现有 Core/Runtime 与同一账户账本，
不迁移 Qlib 回测器。本轮账户窗口固定 2024-01-02—01-31，交易日历含 2023-12-29 边界。
复用 [Research 保存预测](05_axiom_research.md#stock-qlib-lightgbm-minimal) 的原始完整历史 union、
模型/Feature/信号身份和截面时钟，不重训、不改变已经保存的成员、分数、有效性或 IC。
当前真实模型输入是独立验证 Snapshot；不能默默改用 production，也不能声称二者等价。

实现状态：股票源码 `cb94d7a` 已经主协调亲审后经 [PR #6](https://github.com/sinnergarden/axiom-engine/pull/6)
合并为 `9d0b52c`，源码树保持一致。114 项 owner source tests、独立复审和两份真实短月保存
账户/评价通过有界工程验收；Research 只读登记与原模型/阶段报告关联。该短期窗口 CAGR
保持 null/INSUFFICIENT_SPAN；UI 最终股票消费源码已亲审合并，owner 浏览器 QA 通过，
root 亲看最终像素和用户验收仍分别未完成，实际交付回执见当前交付。

**公开合同与版本。** Core 入口为
`from axiom_engine.core import StockPredictionFrame, plan_stock_portfolio`，接收原 owner
`stock_prediction_run_v1`、stage=prediction_raw、
score_semantics=forward_5_session_cs_zscore_prediction、score_unit=dimensionless；完整 universe、
rows、feature_ref/model_ref 与 limitations 原样保留。owner 的 `sha256:<64hex>` 与
bare 64hex source ref 按原 namespace 保存，不静默补前缀或重新认定来源身份。
时间使用 aware instant 比较，保留原序列化字符串；+08:00 与 Z 可混用，不能用字符串大小
比较可见性。context 复用 trade_session/feature_session/decision_time/knowledge_cutoff、
reference_prices、lot_size、commission_rate、minimum_commission_minor、slippage_bps、
account_state_version，增加 supported_security_ids/supported_universe_ref。
结果 contract_version=axiom.stock_portfolio/1，保存 feature_session、trade_session、
signal_ref、supported_universe_ref、expected_account_version、status
（DECISION_COMPLETE/NO_DECISION）、selected_security_ids、targets、intents、trace；
意图身份绑定账户版本、frame identity、context 与合同。

Runtime 为 backtest_request_v3 / backtest_run_v3 / axiom.backtest/3，现有
run_backtest、SimBroker、AccountLedger 按显式股票 planner/profile/adapter 分派；
公开 load_backtest_run 继续只读取保存件。新输入闭包绑定原预测身份和 payload、组合政策/
supported_universe_ref、股票 profile/ref、固定市场 Snapshot/QuerySpec/Reader 证据、
admission_ref、stock_action_policy 与股票现金事件证据/ref。模型 Snapshot 与执行市场 Snapshot 分别保存；
admission_ref 须绑定整个有界日期/证券范围的历史 member 与前日 native price basis
配对证据，三个日期的 probe 不能替代整段证明。saved v2 evaluator 仅补 run-v3 的明确
输入准入，沿用 input_run_ref={run_id,content_digest,committed_sequence} 和已有指标；
Research/UI 不计算账户或评价。旧 ETF 工厂、request/run_v1/v2、版本元组及保存件不变。

**资格与策略。** 固定 `eligibility_id=sz_main_a_000_002_003_v1`：Data canonical 股票身份中
交易所为深圳、六位证券代码以前缀 000/002/003 开始，再交集 feature session 历史可见
CSI300 member。它是本轮执行资格子集，不代表所有深市股票、全 CSI300 或全市场。
过滤结果另存 strategy/plan；原预测的 314 security union 和所有行不裁剪、不改写。
新账户 plan 分别冻结 prediction_universe 与 execution_universe：前者是原预测全 union，
后者是满足证券身份资格的固定 union，并覆盖所有实际候选和持仓。market replay 完整覆盖
后者和实际日历（含前边界），每 session 都有独立状态/价格/限价来源；不能沿用旧 ETF
“Signal universe 等于 Market universe”假设，也不能只查最终有成交的证券再声称全范围准入。
每周首个真实交易 session 仅使用严格前一 session、当时 cutoff 可见的预测；完整 union
行键和时钟须验证。资格内 valid+finite 分数按降序、security_id 升序解同分，负分同样
参与，Top5 各 20% 目标预算；不足五只或任一资格内 member 行显式 invalid 为 NO_DECISION，
保留仓位且保存原因。结构缺行/重复、未来时钟或账户版本冲突在变更前拒绝。
仓位出池或退出 Top5 的减仓仍由同一策略生成，不能删除持仓或借资格过滤跳过估值。
规划只用前一 session 可见 native close 与显式账户状态；预算固定
budget_basis=available_cash_plus_previous_close_positions_excluding_receivables，即决策输入
账户的可用现金加其持仓按前日 native close 标记价值，每只分配 1/5，以 100 股整数倍
向下取整。这是可部署预算而非完整 NAV；应收计入 NAV、不得加入预算或可用现金。
保存账户版本与 decision stage，不在 Core 推断分红到账，也不把当日 EX 应收与前日
含息价格重复加入预算。先卖后买，
卖单和买单分别按 security_id 升序执行，现金不足不依同日价格或收益改换次序。
实际现金、费用、容量及 T+1 可能使成交权重偏离目标，不用当日 open 反算前日目标。

#### 同一冻结预测的显式 TopK 策略参数（父审合同，待实现）

`BacktestRequest_v3` 已有精确 `portfolio_policy.top_k` 字段，但当前校验只接受 5，
`plan_stock_portfolio` 也把资格门槛、选取数和等权预算写死为 5；仅更改原信号或初始资金
不能构成另一组合策略。增量接受**显式正整数** k，`type(k) is int`，拒绝 bool，
且 `1≤k≤len(冻结 execution_universe)`；不能把 Notebook 本次的 3/5 演示值
写成产品上限，也不能超出固定证券资格范围。历史 feature session 有效合格成员少于
k 时，沿原政策保存 NO_DECISION/INSUFFICIENT_ELIGIBLE_MEMBERS 和要求的 k，
不退而选择较少证券；资格内任一显式 invalid 仍 NO_DECISION。按原分数降序、
security_id 升序解同分取前 k，目标预算各为 1/k，仍按前收、100 股整手与同一
现金、费用、容量、T+1 执行规则计算；v2 trace 保存 RAW_TOP_K 与实际 k，
不把目标权重冒充已成交权重。

公共纯工厂固定导出于 `axiom_engine.runtime`，签名为
`stock_portfolio_policy(*, top_k: int, execution_universe: list[str]) -> dict`，
只返回现有 `{eligibility_id,top_k,rebalance,budget_basis}` 精确形状；冻结 universe
只用于边界校验，不重取成员或预测。Core planner 使用
`plan_stock_portfolio(frame, *, account, context, top_k: int | None = None)`：
省略 top_k 仅为旧 `axiom.stock_portfolio/1` 的原 Top5 兼容解释；所有**显式新配置**
（包括 k=5）统一生成 `axiom.stock_portfolio/2`，并把 k 放入 Core 决策和意图
身份输入，v2 decision 顶层保存 `top_k`。Runtime 将计划的 k 显式传给同一 planner，所有新股票运行的
`core_version=axiom.stock_portfolio/2`；原 request_v3/run_v3、执行器、profile 与
账户账本路径不分叉。新 run_id 仍由完整请求、Core/Runtime/实现版本决定；
旧 v1 Top5 保存账户只按其原版本元组验证和加载，不倒改成 v2，也不声称重新运行
会保留旧 run_id。Notebook 从同一保存 StockPredictionFrame 与原固定市场输入
展示 Top3/Top5：feature/fit/predict 均零调用；若展示成交收益，两种配置应绑定
各自保存账户身份，已有完全同配置、同实现版本的 Top5 可复用，不以改初始资金
或用另一账户缓存冒充新策略。

**两个时钟。** 决策为交易日 08:55 Asia/Shanghai，知识 cutoff 保持前一 session 的
20:30。`stock_daily_observed` 仅是离线日级成交近似：execution Reader 在当日 20:30
读取同日 native unadjusted CNY/share 的 open/close、volume_shares（股）、上下限和状态；
同日 open 是成交价格代理，全天 volume 是容量代理。保存原始字段 available_at 和独立
execution_evidence_cutoff；09:30 时不可见的事实不能进入前日决策，也不能据 open
价格标签把事后回放写成 09:30 已知。当前限价源 usable_from=同日 10:00，不能重标为
09:30；日行情/因子源 20:00 和 best-effort 供源限制同样保留。这是事后有界模拟，
不能证明开盘可成交量、真实开盘成交或严格历史状态可见。

**状态准入。** 股票专用 profile 固定 `stock_daily_open_profile_v1`，支持对照
unknown_status_policy=block 与显式实验 stock_daily_observed；不改 ETF profile 的适用范围。
strict 对照遇 UNKNOWN 不成交；实验只在上述执行资格内、state_reason 精确属于
{status_source_missing, status_not_visible_at_cutoff, status_unknown}、
有效 observed open、正日成交量与合法双侧限价下允许近似。事实和订单/成交保留
UNKNOWN、原 state_reason 及 STOCK_OBSERVED_DAILY_ASSUMPTION；不改写为 normal_trading。
已知停牌（含日内已知停牌）、非预期 source_gap、缺理由/identity/calendar/listing 类未知、
缺价/缺量/缺限价、越界价、上限买入/
下限卖出、可卖不足与现金不足继续阻断。使用日线不能证明未发生停牌或限价队列可成交。

**冻结参数。** 初始现金 10,000,000 CNY 分（100,000 元），无初始持仓或外部现金流；
execution='open'、approximation='retrospective_daily_volume_proxy'、
decision_time_utc='00:55:00Z'、unknown_status_policy='stock_daily_observed'（严格对照为 block）、
stock_action_policy='observed_implemented_only'（严格状态对照沿用相同行动政策）、
lot_size=100、settlement_sessions=1（新买股份到下一实际 session 才可卖）、
commission_rate='0.0003'、minimum_commission_minor=500（按单最低 5 元）、
sell_stamp_tax_rate='0.0005'、transfer_fee_rate='0.00001'（买卖双边研究假设）、
slippage_bps='0'、participation_rate='0.1'、maximum_order_quantity=1000000、price_tick='0.01'。
佣金、最低费、过户费、零滑点和容量比例是明确
模型假设，不冒称完整券商费表或经核实的深圳历史全部收费；不依据本轮结果优化。
按 CNY 分、Decimal 和既有 HALF_UP 入账；印花税仅卖方，过户费另列双边，滑点只进入
成交价，不再现金扣一次；单笔订单最低佣金不因 partial fill 重复收。gross 与佣金/
印花税/过户费分别 HALF_UP 到整数分，fee_minor 是三项之和，保存各 fee component。
成交价须满足 0.01 元刻度，不能静默改价；买上限/卖下限仍保守不成交。单笔超 100 万股
保守截断并保存剩余未成交。卖出完整已结算仓位若含不足 100 股余额，仅当容量足以一次
完整退出才允许；本轮空仓/无数量行动首个路径不产生碎股。

**事件与输入边界。** 执行市场使用同一固定 Snapshot、明确 exchange calendar/
QuerySpec/源元数据，检查完整 execution_universe（本轮身份资格 union 为 83 只）与
实际持仓，不只检查最终 Top5 union。公司行动分别以 ex_date 和 record_date 查询
2023-12-29—2024-01-31，固定 end cutoff=2024-01-31T20:30:00+08:00；保留 query、
全部来源上下文及不可用标记。EX 在窗口内的事件与 record 在窗口内而 EX 在结束后、
当时已可见的 pending 分别覆盖，不把已知 pending 填成 0。前边界无初始持仓不产生
更早 record 的权益，但窗口内 EX 的来源准入仍要检查。未来公告不能补进当时已知范围。
因子 transition、已实施事件与证券生命周期按全部 83 只资格 union、完整窗口和同一
calendar 检查，不只检查最终 Top5；无 transition 不能单独证明无行动。
固定 stock_action_policy=observed_implemented_only，模型事实、来源诊断与执行门槛分开。
source_issue=ambiguous_action_identity_or_revision、原始 NULL 和候选状态/日期/来源证据
全部保留，不消除冲突或挑选金额。全部源候选均明确非实施、且实施状态本身无歧义的
记录（本轮六组预案/股东大会通过记录）只作为来源诊断，不生成现金或数量事件；
不单凭这些记录阻断 000651 或其他证券，也不替换 Top5、改用第六名。
这不推定它们在窗口外，不证明无遗漏已实施行动，完整性仍为 observed-only。
只有已实施状态冲突、可能实施且状态本身不确定、已知相关经济日期的行动缺必要执行
事实或涉及不支持数量行动，以及当期无法解释的因子变化，进入相关证券执行/账户阻断。
送转、配股、合并、退市等相关未支持行动仍阻断，不把 ETF 份额转换支持套到股票。
若已持仓发生无法确定股份数量的变化，终止该账户的有效评价，保留已保存事实、相关
水位、停止原因及来源证据，不继续报告可信 NAV/收益。空响应或仅非实施诊断只能说明
固定源查询观察范围，没有 source-completeness 保证；未来公告不倒灌进当时已知范围。

现金分红规范 stock_cash_action_v1，字段为 event_id、security_id、record_session、
ex_session、pay_session、cash_before_tax_per_share、tax_convention、available_at、
source_refs。仅准入无歧义 native 实施事件、明确为零的 bonus_shares_per_share 与
capital_transfer_shares_per_share、正 cash_dividend_before_tax_per_share、有效 record/EX
日期和 revision-bound 来源；数量率 null 不当作零。股票 source 当前无 pay_date，
pay_session 仅为已核实 native 日期或 null，不沿用 ETF 单位/日期、不把 EX 猜成 PAY。
record EOD 锁实际持仓权益，EX 按 gross_before_tax_no_personal_tax_model 确认税前
应收，PAY 仅在核实日期从应收转现金；null PAY 持续保存 payment unknown/pending/
receivable，不能花费未到账金额。现金事件不改变股份数量或成本基准；事件阶段 payload
幂等，冲突修订拒绝。沿用 P10 observed scope、eligible/open/excluded episode 口径，
不声称已模拟个人持有期红利税或未知未来公告。保存 bounded dividend scope 和完整性
限制；不以事后公司行动或成交条件回头替换 Top5。候选、拒单、未成交、应收与估值限制
都作为保存结果，不让状态近似反向污染信号。

**保存证据体积。** v3 可选 coverage_bundle 只对 bundle 内重复的大 native coverage
去重/压缩；不投影或重新命名 source_refs。每条保存
{reference,encoding,uncompressed_bytes,compressed_digest,payload}，encoding 固定
gzip_base64_json_v1；source_evidence.batch.context 仅以 coverage_ref 替换 coverage，
原 snapshot/query/PIT/purpose/字段来源其余值保留。公共 loader 只从保存 bundle 解码，验证
压缩 digest、声明长度、coverage ref 及重建后完整原 native DataBatch digest；拒绝缺失、
重复、未使用表项。不跟随外部 registry/path，也兼容旧 inline v3。该存储表示不增强原
数据完整性或历史 PIT 证据，不改账户/评价身份语义。解码仍有时间与内存成本，见当前交付。

**验收与来源。** 同一模型/预测、初始账户、资格/费用参数和固定 market replay 保存
strict 与 stock_daily_observed 两份运行；状态政策必须显式不同，不混成同一收益结果。
先小合成核 Top5 同分/负分/不足五/invalid、混合时区、前日决策隔离、100 股/T+1、
单佣金/卖税/双边过户费、停牌和 UNKNOWN、日成交量 partial fill、现金 record/EX/
verified PAY 或 null PAY、全非实施诊断不阻断、实施状态不确定/相关未支持行动阻断、
已持仓未知数量变化终止有效评价及 ledger/NAV 共享水位；合同与有界 Data
input-pair 准入冻结后再跑一次真实短窗口，保留严格状态对照。
保存 loader 不计算；真实账户完成前仍不把模型/IC 通过当作账户通过。
SZSE [2023 主板交易问答](https://www.szse.cn/www/investor/institute/rules/t20230706_601604.html)
核到买入 100 股或整数倍、不足 100 股余额一笔卖出及 0.01 元价格刻度；本轮无初始碎股/
送转，首次路径不产生碎股。SZSE [2021 代码安排](https://www.szse.cn/www/marketServices/technicalservice/notice/t20210205_584702.html)
核到主板 A 股 000001—004999、001001—001199 留作存托凭证；本轮更窄的三前缀是显式
资格选择。财政部/税务总局 [2023 年第 39 号](https://szs.mof.gov.cn/zhengcefabu/202308/t20230827_3904226.htm)
核到自 2023-08-28 减半征收；[财政部 2008 年税制回顾](https://szs.mof.gov.cn/gongzuodongtai/200903/t20090304_118900.htm)
核到原 1‰ 和改为单边征收，结合减半可推导 0.0005；此次未独立取得卖方方向的原始
公告，卖方参数按本轮明确规则冻结。
SZSE [2023 交易规则](https://www.szse.cn/lawrules/rule/repeal/rules/t20230217_598773.html)
§3.1.4/§3.1.5 核到清算交收前不得卖出及当日回转例外列表中不含普通 A 股；它不单独
证明清算周期恰为 T+1。settlement_sessions=1 作为本轮声明模型参数保留此核验边界。
过户费双边 0.00001 的完整深圳原文未取得，始终标研究费用假设。

### 6.4 已保存股票输入的一次准入与顺序账户复用

状态：父已裁决技术边界；Engine 实现候选为
[`9f86ac5`](https://github.com/sinnergarden/axiom-engine/commit/9f86ac5) 与
[`26c49df`](https://github.com/sinnergarden/axiom-engine/commit/26c49df)，创建 PID 修复为
[`b5dc2f4`](https://github.com/sinnergarden/axiom-engine/commit/b5dc2f4)，
`b5dc2f4` 已完成独立 review 与一次有界真实复用验收；后继
[`da10733`](https://github.com/sinnergarden/axiom-engine/commit/da10733) 将默认 scalar cache
恢复为 0，保留 opt-in，12 项定向合成检查通过，待父审 merge。此增量仅作用于有界股票 v7 输入消费，
不重跑旧账户、不改变原 Core/SimBroker/ledger 业务，也不增加 Qlib 执行器或新 daily 路径。

公共入口为 `admit_stock_inputs(manifest: BacktestRequest, *, source: StockInputSource,
block_sessions: int, limits: dict, max_owned_bytes: int) -> AdmittedStockInputs`。
返回对象作为既有 `run_stock_backtest(manifest, *, source, sink, block_sessions, limits)` 的
`source` 参数使用；首版仅限创建对象的进程顺序运行账户，`block_sessions` 与导入时保持一致。
对象记录创建 PID；包括 statistics、inventory、audit、迭代、context 进入/退出和 close 的
公开入口在触锁、存储或内部状态前拒绝异 PID，fork 继承对象也不能复用。对象支持
`with`/`close()`，并发执行或执行期间 close 拒绝。原 `StockInputSource` 路径仍完整准入，
作为 exact oracle 保留；每个账户继续独立创建 ledger、sink 和 run 身份。

输入能力比较使用既有 manifest 的逻辑 ArtifactRef 解释，移除 `request_ref`、
`account_id`、`initial_account` 与 `portfolio_policy.top_k` 后保留其余全部字段。
这只是进程内比较，不新增可发布 input ref、receipt/hash 包装或持久 validated 标记。
delivery URI 仍不改变逻辑输入身份，复用时读取已捕获的原字节，不转读替换路径。

| 变更 | 首版处理 |
|---|---|
| account_id、正整数初始现金、合法 TopK | 可复用；初始持仓仍须为空；资金、k 绑定各自请求/run 身份 |
| 其他 portfolio_policy 字段或新增风险参数 | 不模糊复用；现合同未定义的参数拒绝 |
| profile、费用、滑点、UNKNOWN 解释、规则与规则 ref | 重新准入 |
| universe、calendar、anchor、区间、warmup、scope | 重新准入 |
| Snapshot、native/query/projection refs、fold/model/feature/prediction refs | 重新准入 |
| clock/action policy、合同/实现版本及其他 manifest 字段 | 重新准入或按原合同拒绝 |

导入先按原合同核对全部源字节真实性、canonical JSON、字段/单位、时钟、PIT 配对与
全范围行约束，再捕获执行所需块。Engine 自有临时存储没有公开路径，导入后没有写入口；
`max_owned_bytes` 在每次写入前限制总量。原历史 span 索引导入后释放，账户仅解码当前块，
globals/块/索引/decoder 临时输入仍按累计 decoded 预算限制，不将多年 Python 行对象常驻。
这里 decoded 是 canonical byte-volume 核算，包含声明的临时/索引预留，不是进程 RSS；
实际 Python 对象、解释器与 allocator 峰值仍须在有用验收中独立采样，不能把该计数当 RSS 上限。
任何账户持有的可变解码副本不影响后续账户。所有账户的原 input/fold/row/result 限额继续生效。

`StockInputSource()` 现在默认 `scalar_cache_bytes=0`；真实冷加速没有通过，默认关闭是
保守性能选择。显式 opt-in `StockInputSource(scalar_cache_bytes=262144)` 在一次导入内
复用已通过原 decode/canonical 检查的、不超过 256 字节的相同标量字节。缓存计入累计预算，
在必需输入增长前驱逐；原 scanner oracle 保留。
所有物理字节仍完整扫描/hash，结构、键顺序/重复键及每个 reserved Unknown 对象仍逐项验证。

两个可审增量分别为来源所有权/顺序复用与冷 scanner 标量复用。`source.statistics` 提供
每文件 scan/read/hash、标量 decode/canonical 次数与耗时、选中行消费计数；
`inputs.statistics` 分开记录首次 source audit/capture 与后续 owned 块消费。
合成 probe `PYTHONPATH=src:tests python tools/bench_stock_owned_inputs.py` 不调用 Data、
Feature、fit/predict。一次 2,147,694 字节合成验收中，cold import 为关闭缓存 0.849 秒、
开启 0.540 秒，decode/canonical 为 105,725 次降至 291 次；五个 TopK 的独立账户复用消费
合计 0.146 秒，完整保存 run/账本与原路径 exact 一致。原始扫描为一次，后续原始扫描为零。
这些是合成检查，不能作为真实冷导入加速的结论。

真实验收固定源码为 `b5dc2f4`，implementation 为 `sha256:3f35b804fac3a78939dd26ad244f77b4151d8d717d10d001fc40c0b0feb8b545`：
26 个物理文件共 594,205,431 字节只冷准入一次，capture 后原索引释放。Top5 的 NAV、现金、
持仓、decision、orders、fills、fees 与 ledgers 对旧账户逐字段 exact，只有新 run 绑定的
订单/成交关联 ID 规范化；Top3 复用同一保存预测与相同初始资金，产生不同组合和独立账户。
两账户执行为 0.323/0.293 秒，owned 读取各 15,102,120 字节/11 records，原输入重开和
原 source 扫描/选中行重读均为零。总窗口 477.96 秒，峰值进程树 RSS 83.22 MiB，
owned 临时存储 14.40 MiB；没有 Data、Feature、fit/predict 或供应商调用，原输入/旧报告不变。

必须分开裁决：owned 复用通过；scalar cache 的真实冷加速不通过。真实 audit 为 472.64 秒，
比此前固定 `21cc1d5` 的 349.007 秒参考更慢；这不是同一源码/同机状态的严格 A/B。
48,112,179 次标量中仅 2,462,313 次命中（5.12%），45,648,342 次驱逐，不能据合成样本
提速声称真实收益，也不调整 cache 尺寸反复跑。`da10733` 的 implementation 为
`sha256:0399ff578c5d60f1137aaa2a35ab4f992934a91d62b287cc6adaf1fb16c24732`，
仅做定向合成验证；旧真实回执不改绑到该后继源码。

#### 6.4.1 文件级 C JSON 快路径最小候选（待父审；未编码、未真实运行）

目标是保留完整来源身份与准入语义，移除每个字节和每个标量必经 Python scanner 的税。
现统计中，两份约 205 MB 的 actions 与约 130 MB 的 limits 合计占原字节约 91%，
占 scan 耗时约 95%；先针对原 native Data JSON，其他 profile/fold/model/prediction 保留
现 stream。首版不新增解析依赖或账户执行器。CPython 3.12 的 `_json` 支持 C scanner
及 C encoder；`object_pairs_hook` 仍有逐对象 Python 回调，不能声称纯 C 全部准入。
依据为 [Python json 合同](https://docs.python.org/3.12/library/json.html) 与
[本机同版本 CPython 3.12.12 源码](https://github.com/python/cpython/blob/v3.12.12/Modules/_json.c)。

建议候选配置为 `StockInputSource(..., file_parse_mode="stream",
max_file_parse_bytes=None, max_file_parse_rss_bytes=None)`，均为待审参数，
当前公共入口没有这些参数。首版只在显式 `file_parse_mode="cjson"` 且调用者提供两个
正整数预算时尝试快路径，不默认 8 GiB。文件解析预算独立于现有 64 MiB canonical decoded 的账户块预算；
机器为 24 GiB，不能把该旧块限额当作整文件解析的架构上限。opt-in 按物理文件顺序处理，
去重同文件/相同 ref，一次只有一份整文件 graph；stream 可强制保留旧路径。

1. 对原文件做 stat/fd 锁定和尺寸/总 input gate，读取全部原 bytes；完整 file SHA 保留
   terminal LF，content SHA 仅排除允许的最后一个 LF。严格 UTF-8 转为 text 后释放 raw。
   由 `json.loads` C scanner 解码，pairs hook 保留重复键及严格键顺序拒绝，parse_constant
   拒绝 NaN/Infinity。完整 graph 仍检查 finite（含 `1e999`）、所有 reserved Unknown、
   depth<=128、顶层 object 和原合同，不跳过大型 coverage 的验证。
2. 释放输入 text 后用标准 C encoder 按现 canonical 参数完整重编码（紧凑分隔、
   ensure_ascii=False、allow_nan=False、无 indent）；canonical 输出分块编码，并与仍保留的
   原文件只读 fd 按对应字节范围逐块 exact 比较，累计长度等于原 body 长度，尾部只允许
   最初记录的单个 LF 或 EOF；前后 stat/fd 身份不变。完整 file/content SHA 同时保留。
   这会增加一次原字节顺序读，单独计数，但不再调用旧 Python scanner、逐标量 decode
   或整图重解码，不能仅 loads 成功或仅比较规范化后的对象。随后复用 `_install_native_limits`/`_native_header` 的
   domain、Snapshot/Reader、原 query/单位/字段、warmup/calendar/universe、所有原 records
   与 metadata 行数/范围/嵌套行拒绝等 gate，再建紧凑索引；重复/缺 key 与 PIT、factor、
   lifecycle、action、clock、费用及预测配对仍走同一 `_audit` 业务，成功前不创建账户。
3. 标准 C parser 不给原字节 offsets。完整 canonical 身份已证明后，可把必要 header 与
   原顺序选中 records/metadata 行写入 Engine 私有有界 spool，索引为原 parent_ref、array_path、
   session、原顺序行串联 segment SHA 与 file SHA；均为内部 views，不发布新 DataBatch/ref。
   生成 views 只借用当前 graph 的行，逐行/有界块编码，不 deepcopy 全图、不另建完整
   selected graph，也不通过 Pipe/pickle 传整图。header 的 coverage 已全量验证/hash 后释放，沿用现 header() 省略 coverage 的消费语义。
   每文件完成后释放整 graph，父进程只保留小 header/offsets；选中行供现审核与 owned capture。

最大文件的规划估算取 S=205,471,694 bytes（195.95 MiB）；不是实测峰值或严格内存证明：

| 同时存活内容 | 规划预算 |
|---|---|
| 原 bytes 与 UTF-8→Unicode text | S + 最坏 4S，解码前 bytes 释放 |
| graph、dict/list/数值/字符串、key memo 与 pairs 暂存 | 按 24S 估算，约 4.59 GiB；此乘数不是普适上界 |
| C encoder Unicode writer 的扩容/旧新缓冲 | 按 10S 预留，约 1.91 GiB；不与输入 raw/text 同时保留 |
| canonical 比较/hash 的 Unicode/UTF-8 与原 fd 小块 | 合计 64 MiB；不再生成完整 canonical bytes 副本 |
| 保留 header/索引/父进程及 allocator 余量 | 512 + 256 MiB；spool 另按磁盘 quota |

encoder 阶段规划峰值为 `(24+10)S + (64+512+256)MiB` = 7.31875 GiB（约 7.32 GiB），
解析阶段为 graph+text，不与原 bytes 同时保留，预算更低。8 GiB/256 MiB 只是显式 opt-in
预算的评估例，不是默认值或实测峰值。预检估算、文件尺寸或监控能力不满足调用者预算，
在启动该文件快解析前明确记录择 stream；不能全载 594 MB 所有文件。
64 MiB 账户块、128 MiB owned quota 等不因快解析自动增大。

主要风险是 stdlib loads 不能在 list/graph 的每次 C 分配前执行 caller 预算，24S 也不能
证明恶意/不同形状 JSON 的最坏膨胀。建议只把解析放入一次一文件的临时 helper 进程，由
owner 监控其 RSS，留出 allocator/采样余量；helper 不持有 owned handle、不调用 Core 策略
或运行账户。运行中 MemoryError、RSS 停线、worker 退出或其他资源失控均明确失败，
owner 停止 helper、关闭 fd、丢弃全部未提交 spool/索引，本次准入不返回 handle、不创建账户；
不捕获 OOM 后悄悄重新跑 stream。语法、身份或业务 gate 失败同样直接拒绝。
父 owner 仍建立成功的最终 handle，PID 合同不变。RSS 采样会有短时超调风险，不能宣传
为逐分配硬上界。stream 只在预检时选择或由调用者显式选择；重试需要另起明确调用。
旧 scanner 保留作定向合成反例/exact oracle，不作为 CJSON 每次准入的第二遍完整审核。
真实快路径的原字节读、canonical 额外比较读和消费计数分别报告。

这种整文件标准库路径保留 C tokenization，但仍有逐对象语义 walk 与 canonical re-encode。
标准 `json.load` 内部仍先 read 全文，不能当作 C 流式方案；`iterencode` 常规调用也走
Python encoder，不能拿来证明 C 加速。SAX/事件式 C 库可减少 graph 常驻，却增加依赖与
精确数值/canonical/Unknown/source-binding 适配面，首版不引入。后续需先按这些 gate
做定向合成 exact/拒绝/预检 stream 选择与运行中停线对比，再由父另裁决真实窗口；本轮不编码或再跑。

## 7. 账户与 Ledger 数据模型

账户权威分两层：Trade ledger 是系统内部流水与状态；RealBroker 是外部订单/成交/账户的对账依据。差异产生显式记录和调整事件，不用券商快照直接覆盖旧账。

账户查询以 account_id 为主键；strategy 仅用于归因，不能拿 strategy_id 找钱。backtest、shadow、real 使用不同环境/账户空间，real 数据库与模拟数据库物理隔离。

### 7.1 建议表

| 表 | 主键 / 关键约束 | 内容 |
|---|---|---|
| accounts | account_id | environment、币种、Broker/account 映射、状态 |
| runs / attempts | run_id / attempt_id | frozen plan、执行状态与 checkpoint |
| order_intents | intent_id；account+logical intent key 唯一 | Core 意图、expected account version、原因 |
| orders | order_id；account+client_order_id 唯一 | Broker 身份、请求、状态、累计成交/撤量 |
| outbox | command_id / 幂等键 | 待发送、已尝试、待确认命令及关联意图 |
| inbound_events | account+source+source_event_key 唯一 | 标准化回报、原始回报引用、应用状态 |
| fills | account+broker+trade_key 唯一 | 每笔增量成交，而非累计成交量重复入账 |
| cash_ledger | cash_event_id | 现金、冻结/应收/费用变化及关联事实 |
| position_ledger | position_event_id | 总量、可用/冻结、成本/公司行动变化 |
| cash_state / positions | account；account+security | 由事务维护的当前投影及 committed sequence |
| portfolio_snapshots | account+valuation point+version | 净值、估值来源、现金流、stale 标记 |
| corporate_action_applications | account+event+entitlement version 唯一 | 权益基准、应收/到账/股份变化的应用记录 |
| reconciliation_runs / differences | reconciliation_id / diff_id | 委托、成交、现金、持仓核对与处理 |
| checkpoints / migrations | account+sequence / schema version | 恢复点和可重复迁移 |

Broker 的 trade_key/source_event_key 必须按真实唯一范围构造：若原 ID 只在交易日或 venue 内唯一，则把 account、source、session/venue 一并纳入。不能假定券商 ID 永不复用。

可以按实际需求合并相近表，但不能删除意图、外部发送、回报去重、资金与股份流水之间的逻辑区别。首版不强制复杂双重记账或基金会计，必须让每个状态变化都有可追溯原因。

### 7.2 金额、数量和费用

现金流水采用明确币种最小单位的整数（CNY 可按分），运算使用 Decimal/定点而非二进制浮点累加。价格与中间费用保留足够精度，最终按 Fee/RoundingContract 入账；数量为对应证券规则允许的精度。序列化保留 scale。

滑点若已反映在 fill price，仅作为诊断成本拆分，不再现金扣一次。佣金若有按单最低额，不能对每笔 partial fill 重复收最低额；费用晚到或更正生成费用调整事件，不能修改既有 fill 的经济历史。gross/net cash、税费、应收/实收分别表达。

## 8. 事务与幂等：外部发送不是数据库事务

### 8.1 写入原则

本地短事务使用单写者协调、外键与唯一键。SQLite 的 WAL 允许读写并发但仍非多写者数据库；初版应避免跨网络文件系统放活跃账本。相关行为以 SQLite 官方文档为依据。[E1]

Real/shadow 账本采用 WAL、`foreign_keys=ON`、`synchronous=FULL` 和显式 busy/重试策略作为本版保守默认。WAL+NORMAL 的已提交事务在系统崩溃/掉电后可能丢失，不能只因旧规格采用 NORMAL 就不区分 durability；FULL 也不替代可靠存储与备份。[E2]

### 8.2 准备发送：事务 A

在一个数据库事务中：验证 account_state_version→记录 decision/intent→校验 logical key→创建 order/outbox→按预算冻结现金/数量→提交。

Broker 网络调用发生在事务外，不能长时间持有写锁。并发两次相同逻辑请求只产生一个 outbox 任务。Core 版本检查冲突则重新决策或拒绝，不盲目复用旧计划。

### 8.3 发送与回包

```text
PREPARED → SEND_ATTEMPTED → ACKNOWLEDGED / REJECTED / UNKNOWN
```

提交给 Broker 后进程可能在记录 ACK 前崩溃。恢复时查询稳定 client_order_id、Broker 委托/成交列表；无法判断是否已经发送成功则保留 UNKNOWN 并阻断相关重发。**不能声称可以跨 SQLite 与 Broker 实现一个原子 exactly-once 事务。**

稳定客户端 ID 是否由具体 Broker 原样支持是能力项；不支持时制定匹配/人工处理策略，并在实盘门禁前验证。不能只凭请求超时就重下同一订单。

### 8.4 接受回报与记账：事务 B

原始回报可先保存 inbox；小型原始 payload 可随 inbox 事务保存，较大 payload 则先原子发布不可变对象再登记引用，禁止账本指向尚未落盘的回报文件。账户应用事务必须包含：去重检查→标准事件应用→新增 fill/费用/资金与持仓流水→更新订单累计状态→更新冻结和当前投影→更新 strategy state/checkpoint 与已处理水位→提交。

任何中途异常整体回滚，不出现成交已记但持仓未记。保存到 inbox 但未应用的事件可恢复重试。同 key 同 payload 是幂等重复；同 key 不同 payload 是冲突/更正，不能简单丢弃或覆盖。

### 8.5 乱序与部分成交

成交可能先于委托确认、撤单请求后仍有有效成交、费用稍后才到。事件应用以累计事实和合法状态约束处理，不能只凭枚举状态“已经 canceled”就丢成交。

Broker 同时提供累计数量和增量回报时，adapter 明确归一化，避免把 100→150 当两笔 100+150。撤单只有确认的剩余量可释放冻结；成交更正以反向/调整事件表达，保留旧流水。

### 8.6 完成状态

一个运行结束不代表所有订单已成交。区分 `DECISION_COMPLETE`、`EXECUTION_PENDING`、`RECONCILIATION_REQUIRED`、`COMPLETE`、`FAILED`；完成时必须有一致账户快照/事件水位与产物状态。

## 9. 公司行动、估值与权益

本轮离线子集用 Decimal 计算、CNY 整数分持久化，保存 cash/position/cost/fees/NAV 与水位；现金分红按 record/ex/pay 处理应收和到账。合成三笔成交手算与真实短样本账本核对已通过。送转、拆分、退市范围没有能力证据，应由公共 adapter/preflight 拒绝；不得从因子审计推出全部公司行动已支持。下文送转等要求仍属目标。

Data 提供事件事实及日期；Trade 按账户实际权益登记处理。至少区分登记基准、除权、到账、股份上市/可卖日期，不把所有权益在公告日立即加到账户。

现金股息可先记 receivable，到账再转现金，避免除息日净值虚降又在到账日重复获利；送转增股同时处理成本基准和可用数量。税费或后续追缴按实际/模拟 profile 写明确事件。

账户净值基本关系为：现金 + 持仓市值 + 应收 − 应付；冻结现金仍在现金总额内，不能加两次。可用现金与总现金不是同一个字段。

停牌可按固定估值政策使用上次有效价，但必须标 stale 与持续时长；退市/停牌不等于自动清零或永远按最后价计算良好绩效。缺失的退出/清算事实在支持范围内明确限制或阻断。

### 9.1 初版核算 golden 样例

以下仅为合成核算测试参数，数量粒度设为 1 股，不是实际费率或市场委托合法性样例。初始现金 10,000 元，无持仓；成交价每股 10 元买入 100 股、费用 5 元，期望现金 8,995、持仓 100，10 元估值净资产 9,995。重复应用同 fill 不变化；下个可卖 session 以 11 元卖出 40 股、费用 5 元，现金 9,430、剩余 60 股，11 元估值净资产 10,090。

另设持有 100 股、每股 1 元现金股息：确认权益时应收 100，到账时现金加 100/应收减 100，不得净资产再增加一次。送股/转增夹具核对数量、成本基准、可卖日期；未知税费或精度不能用这些简化示例替代真实 profile。

<a id="etf-unit-split-application-proposal"></a>
### 9.2 ETF 份额拆分的有界账户合同

状态：2026-10-04 语义边界与下列最小保存合同已裁决，供 Engine 实施；
未实现、未解锁全段回放。事实见 [Data §6.2](02_axiom_data.md#etf-unit-split-proposal)。
首轮只验收该节两笔事件；实现匹配明确比例、阶段与取整规则的 ETF 份额拆分合同，
未来同语义事实可追加，不写证券/日期特判。其他未支持行动继续阻断。

#### 首版权益与时钟边界

Engine 从同一固定 Snapshot、声明 cutoff 的 `fund_share_conversions` 公共事件输入，
在登记基准冻结实际权益。首版仅支持折算权益全部已结算、单账户对应单登记持有人、
无冻结权益/挂单、登记与应用数量一致。混合未结算批次、跨账户持有人合并及登记至生效
发生买卖等数量变化均 unsupported，应用前阻断，不覆盖当前持仓、不实现逐批次 ceil。

已结算单位替换不再次 T+1；首个新单位允许执行 session 关联 Data 的 `new_price_basis_session`，仍受
原执行准入、容量、行情、价格限制与事件禁止条件约束。这是 Engine 明示回测约定，
不作为官方可卖规则认证。本轮 513100 的该 session 为 01-14，510500 为 08-29。
原始 Data 状态 UNKNOWN 保留；可见官方全天停牌事件额外禁止成交并保存其具体依据，
不能由 observed 日线 profile 绕过，也不能修改 Data 状态。

计划/结果分开：本轮两份计划已披露各自精确比例，按各自 best-effort next-open 时钟，
在登记/生效时可见。Engine 可以使用 `process_status='planned'` 的完整已公告安排；不以
未来结果 `implemented` 作为准入前提。513100 于 01-13 应用、01-14 复牌时仍只能使用
计划修订；510500 于 08-26 应用、08-29 新单位开盘时同样只用计划。结果分别至 01-17、
08-30 09:30 才可见，用作独立核对，保存来源与核对状态，不改过去决策或重复应用。
未来同语义计划缺少必要比例等字段时仍阻断，不借后来结果补齐。

#### 数量、估值与 Core 前收参考价

数量按登记持有人合计乘官方精确分数。`quantity_rounding=not_stated` 只在精确结果已为
整数、不需要尾差处理时接受；不得自行选择分数取整。510500 按已声明规则 ceil 一次，合计
100 份变为 115，不能两批各 50 分别 ceil 得到 116。新数量与可卖数量一致，受影响未结算
批次必须为空。总成本（整数分）不变，平均成本随新数量派生。事件不是 fill、手续费或
现金股息，不生成买卖盈亏、外部现金流或应收；零权益保存已处理状态，不新建持仓。

Engine 按 `effective_date` 与明示的模型应用阶段处理：513100 官方
`effective_phase=not_stated`，本模型约定于 01-13 日终，数量乘 5，
将最后有效旧尺度参考价除以 5，再提交 NAV；停牌日原行情缺行保留。510500 于 08-26
读取旧尺度真实 close 后，数量合计 ceil，并将该 close 除以 `1.14539`，再提交 NAV。
这些是本轮时钟验收用例；程序按合同阶段及比例执行，不按代码/日期分支。

桥接同时用于账户估值与随后 Core 决策的前收参考价单位归一化，包含零持仓候选；否则
08-29 sizing 会混用旧单位。保留原价格、原 session、stale 原因、固定事件/修订来源及
桥接后的尺度。Core 所用桥接价同时绑定原报价与事件修订的可见时钟，按当前决策 cutoff
校验；不能只继承较早原价的时间戳而提前使用后来比例。新尺度真实报价到达后替换参考价，
不重复折算。不填停牌行情，桥接不成为成交价格或 Research 输入。所需旧尺度参考价缺少可追溯来源或尺度不明时阻断，不猜价。
向上取整的数量尾差及其估值影响留证，不强求 NAV 恰好不变、不伪造现金抵消。

订单复用现有规则：买入仍按 100 份；容量与可卖数量足够时，清仓可卖出全部整数份额，
包括零股。容量不足的部分成交按整手并保留尾仓；不可卖或部分成交不足一手不成交，
不丢弃余量、不新增费用或放宽执行 profile，当日到期订单不变为跨日挂单。

#### 保存与评价消费

保存固定事件与计划修订来源、登记权益、应用阶段、水位、前后总数量/可卖数量/总成本，
精确比例、取整尾差、原参考价/session 与桥接价/事件 ref、停牌禁止证据、结果核对记录。
账户与固定事件应用身份幂等，重复不变、冲突修订拒绝，不得部分更新后继续。确切字段
shape、合同/实现版本与 loader 兼容规则冻结如下，纳入既有运行身份；
旧账户、评价与保存合同保持原件，不能按当前实现补写旧文件。

- Request 为 `backtest_request_v2`，新增 `unit_split_policy='etf_settled_holder_eod_v1'`；
  MarketReplay 为 `market_replay_v2`，BacktestRun 为 `backtest_run_v2`，Runtime 为
  `axiom.backtest/2`。原 `daily_open_profile_v1`/profile_ref、`signal_frame_v1`、
  `axiom.rotation/1` 与 evaluation spec/report v1/v2 不变。
- MarketReplay 新增 `unit_splits:[{event,available_at,source_refs}]`：`event` 原样保存
  Data §6.2 的 27 个原生字段，包含计划状态、修订序号、not_stated/null 与真实收据时钟；
  `available_at` 为所需经济事实的原生 UTC usable_from，source_refs 为固定公共 batch digest。
  每事件在 record session 20:30 Asia/Shanghai，以同 Snapshot 的公共 EventQuery、
  `time_field='effective_date'`、`purpose='market_replay'` 选择当时可见修订后再日期过滤，
  不加 implemented-only 条件。完整 query/field_meta/batch 复用 market.source_evidence。
  本样本选中计划 revision_sequence=1 是历史输入事实；程序按可见修订选择，不能硬编码 1。
- Run 新增 `unit_split_applications`。每项字段为 `event_id,security_id,session,phase,
  sequence,status,record_sequence,record_quantity,before_quantity,after_quantity,
  before_sellable_quantity,after_sellable_quantity,cost_minor,rounding_extra_fraction,
  original_quote,normalized_quote,before_market_value_minor,after_market_value_minor,
  rounding_value_minor,source_refs`。phase 固定 `EOD_AFTER_CLOSE_BEFORE_NAV`，status 为
  `APPLIED|NO_ENTITLEMENT`；sequence 与同次 position ledger 行一致且先于 NAV 提交。
  `rounding_extra_fraction={numerator:new_qty*d-old_qty*n,denominator:d}`，比例为 n/d；
  rounding_value_minor=after_market_value_minor−before_market_value_minor，不补现金。
  两个 quote 均复用 `{price,session,available_at,source_refs}`；normalized price 为
  original×d/n，Decimal 精度 40、HALF_UP，availability 取原价、事件 usable_from、模型
  EOD cutoff 的最大值。零权益也保存应用与零增量，但不创建持仓。
- Position ledger 复用原行 shape：`reason='UNIT_SPLIT'`，source_event_id 为原生 event_id，
  quantity_delta/sellable_delta 为各自 after−before，`cost_delta_minor=0`。
  positions 新增 `mark_basis_event_id`（桥接为 event_id，原生 close 为 null），保留
  mark_session/stale。decisions 新增 `reference_prices`，保存实际传给 Core 的既有 quote map，
  包括零持仓候选。orders 新增 `announced_suspension_event_ids`（无则空列表）；可见
  full_session 事实先以 `ANNOUNCED_SUSPENSION` 阻断，原 market_state/state_reason 保留。
- 复用 request/market/run/content digest，不新增 policy_ref、basis_ref、event_revision_ref
  或 application_id。run 内原生 event_id+UNIT_SPLIT phase 幂等；同 payload 重复无变化，
  冲突先拒绝后不修改。content_digest 闭合上述保存输出。公共 save/load 路径按保存 v1/v2
  分派，仅验证与载入，不执行、读 Data 或要求当前实现相同；旧文件字节不变。

首轮 admission 只接受两笔已核实披露对各自 first-new-price-session 因子转换的解释；
原生因子证据与官方比例分别保留，不推导/替换因子。此数据范围门禁不成为证券日期特判，
其他未解释转换继续阻断。纯单位替换不产生 cash/fill 行，真实新尺度 close 替换桥接。

份额拆分不结束 `0→非0→0` 持仓段；P10/P10 v2 消费同一保存事件流水更新段内数量，
不伪造买入/卖出或重复确认收入，不改变成本分母与现金分红规则。UI 只读 owner 产物，
Research 不应用账户事件或另写撮合器。

验收先做有界合成手算：1:5 数量与参考价同步，总成本/现金不变、停牌无成交；持有人
合计 ceil；零持仓候选 Core 参考价归一化；全已结算/登记一致边界与混合权益拒绝；
幂等/冲突、计划可见性与后来结果不前移、零股清仓/容量尾仓、桥接仅应用一次、NAV 与
持仓段连续性均独立核对。再只读新固定 Snapshot 两事件窗口验证字段与证据映射；通过
审阅后再授权一次全段运行。已完成起点预检保留，不重复同输入构建；新 Snapshot 核对
复用分区/source 闭包并取得新增事件证据，不回写旧输入或冒用旧身份。

## 10. 恢复、对账、备份与部署

### 10.1 恢复次序

```text
阻断新发单
→ 读取冻结 Plan / checkpoint / 未应用 inbox / 未确认 outbox
→ 重放可确定的内部事件
→ 查询 Broker 委托、成交、资金和持仓
→ 去重并应用差异/确认 UNKNOWN
→ 一致性检查
→ 明确允许继续发送
```

系统 restart 不重新选择最新 StrategyRelease，也不自动新建同账户同日意图。Broker 对账前不能把本地“没 ACK”认定为外部“没订单”。人工调整通过 owner service 产生记录，禁止 SQL 直接改余额。

### 10.2 备份

活动账本采用 SQLite backup API 或已验证的安全备份流程，不只复制一个正在写的 `.db` 文件而忽略 WAL。Online Backup API 提供一致的数据库副本；实现应校验复制结果和恢复流程。[E3]

备份覆盖 ledger、必要策略状态/Plan、原始回报、发布包引用和恢复凭证定位（不泄露 secrets）。Catalog 可重建不等于 ledger 可删除。迁移前隔离备份，迁移执行走正式 service/schema migration，异常回滚或恢复。

### 10.3 部署

保留多个 systemd timer/service：Data sync、Research retrain、Trade preopen/postclose 等，各调用本 owner 公共 API。统一的是合同和冻结步骤，不是巨型脚本。

Trade 实际发布包、代码、配置、account/environment、run profile 与依赖在 DeploymentManifest 中固定。生产从冻结发布包运行，不能混读主工作区配置；文件位置可不同但身份必须可证明。

执行安全闸包括账户不符、real 未批准、数据/信号失效、对账差异、Broker 连通性、未知订单、重复任务、人工停机。它可以拒绝发送，不得悄悄改变投资策略；下一步由显式新决策处理。

## 11. 统一账户评估（P10）

Research 和 UI 消费本仓标准结果，不另实现 CAGR/DD。EvaluationSpec 固定 benchmark、price/total-return 口径、净值/入出金调整、频率、年化、费用、窗口、risk-free 及缺失处理。

| 指标 | 最小定义与边界 |
|---|---|
| CAGR | 以现金流调整后的财富/净值指数计算；样本不足、终值无效不编造年化 |
| MaxDD | 同一净值路径对历史前高的最坏回撤 |
| Calmar | 同区间 CAGR / abs(MaxDD)；0 分母返回明确状态 |
| Sharpe | 明确 r−rf、标准差、年化因子；不设跨策略通用优秀阈值 |
| Recovery time | 谷底→恢复前高；并列出前高→恢复的 underwater duration；期末未恢复标 censored |
| Rolling 1Y/2Y excess | 固定基准、1Y/2Y 实际窗口定义；默认几何相对收益 `(1+Rs)/(1+Rb)-1`，差值另命名 |
| Worst-year / worst rolling 1Y | 区分完整日历年和滚动窗口，首尾不完整年单列 |
| 执行与风险 | 换手、费用、滑点、成交率、未成交原因、容量/行业/单票集中度 |
| Episode | 实际入场至退出、持有时长、MFE/MAE、capture/giveback 与贡献；公式版本化 |

这些是本系统拟采用的口径约定，具体 annualization/window profile 在首次正式比较前冻结。重叠滚动窗口的胜率是样本描述，不写成独立入场的获胜概率。

报告同时列 Data/PIT、样本/OOS、执行 profile、未支持事件和未检查范围。收益高不能覆盖正确性 blocker；费用或 benchmark 口径不同的回测不可直接混在排行榜上。

<a id="daily-evaluation"></a>
### 11.1 本轮日级 P10 冻结合同

状态：`accepted`（2026-10-04）；这是已确认的首版合同，实现与测试结果在[当前交付](../current-delivery.md)单独记录。上述指标目录是长期目标；本 profile 只提供日净值/回撤、月收益、完整持仓段及独立沪深300价格基准，不计算年化、Sharpe 或 IRR。

`daily_evaluation_spec()` 的唯一首版 EvaluationSpec 为：

```json
{"contract_version":"evaluation_spec_v1","frequency":"daily","benchmark_security_id":"000300.SH","benchmark_series_kind":"price_index_excluding_dividends","anchor":"previous_session","drawdown_peak":"initial_nav_included","monthly_partial_policy":"separate_observed_return","episode_definition":"position_0_nonzero_0","dividend_recognition":"ex_income_record_entitlement_pay_transfer","return_denominator":"cumulative_buy_cost_including_fees","weighting":"equal_closed_episode","external_cash_flows":"reject","annualization":"none","missing_policy":"null_no_fill","pnl_distribution":{"metric":"net_pnl_minor","unit":"CNY fen","edges_minor":[-100000,-50000,-10000,0,10000,50000,100000],"interval":"left_closed_right_open","minimum_episodes":10}}
```

EvaluationReport 独立保存，不改旧 BacktestRun。其 `contract_version=evaluation_report_v1`；`input_run_ref={run_id,content_digest,committed_sequence}` 精确绑定账户结果，`signal_ref/market_ref/profile_ref` 沿用账户值。`evaluation_ref` 绑定 input_run_ref、spec_ref、benchmark_ref、dividend_scope_ref（包括 null）、evaluation_version、implementation_ref；`content_digest` 校验除自身之外的全部输出。报告还保存 `status=COMPLETE/PARTIAL`、`spec_ref/spec`、`benchmark_ref/benchmark_input`、`dividend_scope_ref/dividend_scope`、实现版本、`series`、`monthly_returns`、`episodes`、`episode_metrics`、`benchmark` 和 `limitations`。输出身份与逻辑运行身份分别保留；不能把 Document.identity 当 run_id。

日账户 `series` 每项保存 session、nav_minor、nav_index、peak_nav_minor、drawdown、committed_sequence；回撤前高包含 initial NAV。金额原值为整数分，比例为 decimal 字符串；UI 只格式化成元与百分比。

`monthly_returns` 每项保存 month、status（COMPLETE/PARTIAL/MISSING）、first_session、last_session、boundary_session、start_nav_minor、end_nav_minor、return、observed_return、reason、committed_sequence。完整月必须由冻结交易日历证明自然月左右边界，并有当月首末交易日的账户观测：左边至少到上月 session 或当月自然首日，右边至少到月最后自然日或下月 session。月收益以此前月末 session NAV 为边界；首月只有 run 的前一 session 恰为该边界时才可使用 initial NAV。不能用工作日猜周末或休市。不能证明完整的首尾月标 PARTIAL，正式 return 为 null，局部 observed_return 另列；缺边界或价格不填 0。

基准默认 `000300.SH`，独立于 ETF 策略池，采用 `price_index_excluding_dividends`，单位 index points。benchmark 保存严格前一 session 的 anchor_session/anchor_close、状态及逐日 close、nav_index、daily_return、drawdown、valid、missing_reason、source_refs，另列 total_return/max_drawdown。缺价或峰值历史不完整时相关值为 null。benchmark_input 保存固定 Data Snapshot、QuerySpec、批次和查询证据。价格指数不含分红，与含分红账户收益的差异必须展示，不能称全收益对照。

持仓段为单证券 0→非0→0，段内加减仓合并。每段保存 episode_id/security_id、CLOSED/OPEN、entry/exit session 与 sequence、left_censored、income_status、statistics_eligible/exclusion_reasons、初末数量、累计买入成本、卖出收入、费用、分红收入、pending/receivable、净盈亏或期末标记盈亏、收益分母、net_return、fill_refs 及分红归属链。初始持仓无入场记录为 left_censored；开放、左截断及已知收入未确定的段不进完整统计。登记日收盘权益归所属段，EX 确认收入一次，PAY 只转现金；读取保存账本金额，不能另行舍入重算。完整可统计段净收益率为净盈亏除以累计买入成本（含费用）；按段等权平均，与 IRR 无关。

episode_metrics 保存 closed_count、eligible_closed_count、open_count、left_censored_count、income_pending_count、win_count/loss_count/tie_count、win_rate、mean_net_pnl_minor、mean_episode_return、return_denominator、weighting、dividend_scope_status。胜率分母为 eligible_closed_count，平局保留；平均净盈亏为 decimal 分均值（可有小数），段内金额仍为整数分。无合格段返回 null。

报告另保存 `pnl_distribution={status,metric,unit,included_episode_count,minimum_episodes,bins}`。仅纳入可统计闭合段净盈亏；不少于 10 段时 status=AVAILABLE，按上述 CNY 分固定边界保存八桶 `{lower_minor,upper_minor,count}`，左右无穷尾端为 null，普通区间左闭右开，0 属于 [0,10000)。桶计数之和等于纳入段数，平局计数仍单列。不足 10 段时 status=INSUFFICIENT_SAMPLE、bins=[]，UI 先显示 episodes 原净盈亏，不称完整分布。门槛是显示规则，不是统计置信度或策略资格判断；不新增框架、依赖或币种泛化。

**分红观察范围。** 旧账户事件按 ex_date 窗口读取，不能证明所有登记日已发生、EX 尚未发生的已知分红均已覆盖。可选 `DividendScope` 经同固定 Snapshot 的公共 Reader，以 `time_field=record_date`、start_session/end_session 和期末 knowledge_cutoff（UTC）查询，保存 `contract_version=dividend_scope_v1`、universe、`coverage=observed_records_only`、actions、source_refs/source_evidence/limitations。actions 保存 event_id、security_id、record_session、ex_session、pay_session、cash_per_unit、available_at、source_refs；Record digest 必须与旧账户事件身份匹配，固定 QuerySpec、purpose 和 cutoff 一并留存。

EX 不晚于期末的经济事件必须与原账户一致；补充只允许当时已知且 record≤end、EX>end 的 pending 检查，不倒改旧净值或重复确认收入。缺 scope 时 `dividend_scope_status=COVERAGE_UNKNOWN`，不能确定的 pending_dividend_minor 为 null；已知 pending 保留，income_pending_count 只表示已知 pending 段数，不能把未知总量当成已排除的 0。缺 scope 不阻止正常已观测闭合段的净盈亏及统计，但须显式限制范围。有 scope 时标 OBSERVED_RECORDS_ONLY，仍不保证供应源完整；结束后披露的公告不成为当时已知。

<a id="long-history-evaluation"></a>
### 11.2 多年保存账户的有界年化评价

状态：`accepted`（2026-10-04，主协调确认最小方案）；已由 [Engine PR #4](https://github.com/sinnergarden/axiom-engine/pull/4) 亲审合并，固定源码 `8876946` / main `f0fd977`，合并后源码树相同。只对完整冻结 BacktestRun 的保存观测增加账户与沪深300 CAGR，以及账户同区间既有最大回撤；不运行账户、不重算行情/成交/费用/分红，不扩为通用指标平台。旧 65 日 P10 保存结果、`daily_evaluation_spec()` 和 v1 schema 保持不变。

新工厂 `long_history_evaluation_spec()` 返回 `evaluation_spec_v2`，完整复制 §11.1 spec，只改变 contract_version 及下列 annualization；其余依赖、月边界、持仓段、分红观察与缺失规则不变：

```json
{"contract_version":"evaluation_spec_v2","annualization":{"method":"geometric_cagr","day_count":"actual_actual_calendar_year_split","interval":"start_inclusive_end_exclusive","start_anchor":"previous_session_initial_nav","end_anchor":"last_saved_nav_session","minimum_year_fraction":"1"}}
```

**时钟与公式。** anchor 为冻结交易日历中第一条账户 NAV session 的严格前一 session，使用账户原 `initial_nav_minor`；这是本 profile 对初始财富的归属时钟，不伪造该 session 曾有一条 NAV 观测。end 为最后保存 NAV 的 session；账户和基准使用相同 anchor/end。按日期区间 `[anchor,end)` 将实际自然日逐日历年拆分，保存 elapsed_calendar_days 及 year_segments。每段的 year_days 为该日历年的 365 或 366，`Y=sum(days/year_days)`，`CAGR=(end_value/start_value)^(1/Y)-1`。包含周末与休市，不以交易 session 数或 252 代替年跨度。区间及源日历必须来自该保存结果的冻结闭包，不能用 current 或工作日猜测。

`evaluation_report_v2` 保留 v1 的所有 sections、引用及完整来源，唯一新增顶层 `period_metrics={window,account,benchmark}`。准确字段为：

```text
window = {anchor_session, end_session, elapsed_calendar_days, day_count,
          year_segments:[{year,days,year_days}], year_fraction}
account = {cagr_status, cagr, cagr_reason, initial_nav_minor, final_nav_minor,
           total_return, max_drawdown}
benchmark = {cagr_status, cagr, cagr_reason, anchor_close, end_close,
             total_return, max_drawdown}
```

session 使用原市场日期；elapsed_calendar_days 和 year_segments 的三个值为整数，day_count 固定为 actual_actual_calendar_year_split，year_fraction 为 decimal 字符串。金额仍为 CNY 分整数，基准原生 close 与收益/回撤比例为 decimal 字符串；缺值为 null。计算采用独立 Decimal context（precision=40、ROUND_HALF_UP），包括年分数和分数次幂；调用方全局精度不得改变保存值。UI 只格式化 owner 保存值，不计算年化或区间指标。

v2 限制文案需反映已提供 CAGR，不能继续携带旧“无年化”描述；原数据、执行与分红等实质限制仍全部保留。

两条腿各自保存 `cagr_status`，只允许 AVAILABLE / INSUFFICIENT_SPAN / MISSING_BOUNDARY；AVAILABLE 的 cagr 为有限 decimal 字符串、cagr_reason=null，其他状态 cagr=null、cagr_reason 为明确原因。先对负 NAV、外部现金流或非法财富拒绝评价；其余输入中，缺起点或终点优先于短跨度标 MISSING_BOUNDARY；合法端点齐全但 Y<1 标 INSUFFICIENT_SPAN，累计收益与既有回撤仍按其自身缺失规则保存。账户初始 NAV 必须大于 0、终值不得小于 0；外部入出金、负财富或非法值明确拒绝，不回退 IRR。年跨度满足门槛时，终值为 0 的账户 CAGR=-1（显示 -100%）。基准沿用原生正 close 的资格；缺 anchor/end close 时 CAGR 与相关 total_return 为 null，不以前/后值填边界。

账户 max_drawdown 取既有 series.drawdown 的最小值（前高已包括 initial NAV），与同一 anchor/end 对齐，不能年化回撤。基准 max_drawdown 复用原 benchmark 的保存计算规则；中间缺价即使两个端点齐全、端点 CAGR 可用，峰值历史不完整时最大回撤仍为 null，原 PARTIAL 与限制保留。CAGR 可用性独立于 monthly_returns 是否 COMPLETE、持仓段是否 eligible 和报告顶层 status：只检查完整保存账户/NAV、合法端点和年跨度，不能因首尾局部月禁用 CAGR。CAGR 字段状态不替换报告顶层既有状态。账户含费用与 EX 已确认收入/应收，沪深300仍是价格指数、不含分红；源/PIT、执行近似、陈旧估值及有界分红观察的全部原限制保留。未确认未来 EX 不补入旧 NAV 或 CAGR；模拟年化结果不解释为预测收益。

新报告的 evaluation_version 固定为 `axiom.evaluation/2`；evaluation_ref 仍绑定 input_run_ref、spec_ref、benchmark_ref、dividend_scope_ref（含 null）、evaluation_version、implementation_ref，content_digest 覆盖除自身之外的全部输出。新 spec/版本/实现产生独立身份和新保存路径，不能改写原 v1 文件。`load_backtest_evaluation` 同入口兼容 v1/v2，只校验合同、身份与内容并加载保存值，不查询 Data、不执行评价。loader 依据保存件配对验证 spec/report/evaluation 版本（v1/v1/axiom.evaluation/1 或 v2/v2/axiom.evaluation/2）及 hash/ref，不因当前实现版本变化拒绝旧 v1，也不补写 period_metrics。Research 仍关联原账户三元引用；换评价只新增登记历史，不增加回测次数。

**定向验收。** 合成 2020-01-01→2022-01-01 的区间必须保存 731 天、两段 `{year:2020,days:366,year_days:366}` 与 `{year:2021,days:365,year_days:365}`，Y=2；财富 100→121、100→64、100→100、100→0 分别得到 0.1、-0.2、0、-1。严格按 Y<1 判断短跨度，不能改为 365 天或自然周年：2020-07-01→2021-07-01 虽跨自然周年，Y=184/366+181/365<1，仍为 INSUFFICIENT_SPAN，终 NAV 为 0 时也保持 cagr=null。另验首尾月不完整但 Y≥1 的 CAGR 可用、端点缺失/中间缺价、外部现金流拒绝、全局 Decimal context 不变、保存复用与只读 loader。只读消费原 65 日账户验证新 profile 的年化不可用，并核对旧 v1 文件 hash/mtime 不变；无需重跑账户或等待新的长历史采集。

来源核对（2026-10-04）：[GIPS Handbook for Firms](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/) §2.A.12 与 §8.C.1 discussion 支持几何复利年化及不足一年不年化。Actual/Actual 按日历年拆分与初始财富归属是本 profile 的明确约定，不称 GIPS 合规。本轮不增加波动率或 Sharpe。

<a id="saved-account-analysis"></a>
### 11.3 已保存账户的有界分析评价（设计已批准，待实现）

本节只为一个已有、完整的 BacktestRun 与同一 run 绑定的已保存 v2 评价增加新
`evaluation_spec_v3 / evaluation_report_v3 / axiom.evaluation/3`。旧账户、旧 v1/v2
spec/report、金额分桶、来源与实验登记不覆写；新报告复制已核验的 v2 指标和限制，
再保存下述新增事实。新公共入口固定为
`analysis_evaluation_spec(*, risk_free)`、
`evaluate_saved_analysis(run: BacktestRun, base_report: EvaluationReport, *,
benchmarks: dict[str, BenchmarkSeries | None], spec: EvaluationSpec) -> EvaluationReport`，
只消费已保存的账户/
评价及独立的真实基准输入；`save_backtest_evaluation` 与
`load_backtest_evaluation` 继续负责独立新路径保存和按版本只读验证。这里描述合同，
不宣称接口已经实现。

`benchmarks` 精确包含 `CSI300/SSE_COMPOSITE/NASDAQ100` 三键；CSI300 必须与
base_report 的原 `benchmark_ref/benchmark_input` 完全一致，不能静默替换原评价基准。
尚无已核来源的另外两腿显式传 None，输出 SOURCE_UNAVAILABLE。新原生指数输入
继续由 Data owner 固定来源合同后交接，不让 UI/Research 查询供应商。
`risk_free` 必须是精确三字段 dict（currency/annual_effective_rate/source），currency 必须为 CNY，金额率
为有限 decimal 字符串，source 为非空字符串。`analysis_evaluation_spec` 返回固定
`EvaluationSpec`，其身份含显式 rf；评价入口拒绝不同 run 三元组的 base_report。
报告同时嵌入 `base_evaluation` 原 v2 保存内容，loader 校验其 digest/ref 及复制指标
原值，读取 v3 不调用评价或账户执行。

**输入、身份与来源。** spec 显式保存
`risk_free={currency:"CNY",annual_effective_rate:"0",source:"EXPLICIT_ZERO_ASSUMPTION"}`：
零利率是本次实验假设，不是查询所得无风险收益，也不得成为隐式默认值；可配置的
其他年有效利率须一并固定数值和来源。`annual_effective_rate>-1`，逐期按下述
Actual/Actual 复利转换。spec 还冻结 20-session 滚动窗、2 个百分点分桶、三个
benchmark key、对齐与缺值政策。报告保留旧 `input_run_ref` 三键和
`signal_ref/market_ref/profile_ref`，另存 `base_evaluation_ref`、
`base_evaluation_content_digest/base_evaluation`、按 key 排序的
`benchmark_refs/benchmark_inputs`（三键均保存完整原输入或 null，loader 逐腿校验
input.identity==ref）、`spec_ref/spec`、
`dividend_scope_ref`（含 null）、`implementation_ref`。新 `evaluation_ref` 的身份输入
精确包含以上 run/base/spec/benchmark/dividend/版本/实现闭包，`content_digest`
覆盖除自身之外的整个新报告；不得把新的评价身份误作新的账户 run_id。
`risk_metrics`、`drawdown_interval`、`return_distribution`、
`benchmark_comparisons`、`analysis_series`、`execution_summary`、
`concentration_series`、`episode_points`、`execution_trace` 为新增顶层输出，
旧 v2 的 `series/monthly_returns/episodes/episode_metrics/pnl_distribution/
benchmark/period_metrics` 原值保留。原 v2 limitations 完整留于 base_evaluation；
v3 顶层标明“原 v2 无 Sharpe”描述原报告范围，本轮可用风险值仅遵循新 v3 状态。

基准 key 固定 `CSI300`（默认）、`SSE_COMPOSITE`、`NASDAQ100`。CSI300 复用旧 v2
评价已固定的价格指数证据；另外两个需 Data owner 提供真实证券身份、币种、价格或
全收益口径、原生交易日历、时区、Snapshot/Query/Reader、每条 close 的
available_at 和来源引用。不能猜指数代码、价格、汇率、日期或缺值。账户 session 的显示投影只按日期标签精确匹配原生 `native_session`，同日无保存点
显式缺失/null，不选择前日、不前填。保留原生交易日历、当地 session 与实际
`available_at`、close、source_refs；NASDAQ100 本币曲线为事后回看，不宣称与
A 股账户同一瞬间可知。跨市场真正 as-of/FX 比较须后续另定，不在本轮加入 stale
政策。每点保存 `account_session/native_session/close/available_at/source_refs` 和
缺失原因，非匹配日期的 native_session/close 均为 null。
每个指数保存原币种归一化走势；人民币账户与同币种价格指数的相对财富
`(NAV_t/initial_NAV)/(B_t/anchor_close)-1` 仅标为**价格指数代理比较**，因为
账户含分红而指数不含。NASDAQ100 如为美元且无同窗口实际汇率来源，仍可展示其
美元本币走势，但人民币账户相对收益存 null/`FX_REQUIRED`，不称超额收益。
缺原生边界或同日点分别保存 MISSING_BOUNDARY/MISSING_OBSERVATION，
不把缺口变为 0；来源无法核实则该腿 unavailable，不冒充已完成多基准验收。
`benchmark_comparisons` 按上述三个 key 各存 input_ref、currency、return_basis、
status 与逐点 native_session/close/normalized_index/account_relative_wealth/
relative_status；CSI300 和上证的价格指数代理 relative_status 为 PRICE_INDEX_PROXY。
无法取得某条真实输入时该 key 的 benchmark_ref 为 null、status 为
SOURCE_UNAVAILABLE，报告顶层 PARTIAL 并保留具体原因；不能用示例数替代。

**回撤区间。** `drawdown_interval={status,peak_session,trough_session,
peak_nav_minor,trough_nav_minor,drawdown,elapsed_calendar_days,
peak_is_initial_anchor,recovery_session,recovery_status}` 取既有逐日 series 的全局
最小回撤，与 `period_metrics.account.max_drawdown` 精确相同；并列最深谷底取首次。
该谷底前同值最高点取最近一次，包含 initial NAV 归属的严格前一 session；
若 peak 为该初始财富时钟，显式标记并不伪造观测。`elapsed_calendar_days` 为
trough 与 peak 日期差。`recovery_session` 为谷底后首次 NAV≥该 peak 值的
session，未恢复则 null/OPEN；无负回撤则端点为 null/NO_DRAWDOWN。

**段收益率分布。** 保留 v2 金额 `pnl_distribution` 原值；新
`return_distribution={status,metric:"net_return",unit:"fraction",
included_episode_count,minimum_episodes:10,edges,bins}` 只读取已有
`statistics_eligible` 闭合段 `net_return`，沿用含费累计买入成本分母。`edges`
为 decimal 字符串 `-0.20,-0.18,…,0,…,0.18,0.20`（21 条边界）；
22 个桶含两侧开放尾桶，中间左闭右开，0 属 `[0,0.02)`，不裁切极值；
桶 count 之和等于样本数。少于 10 段时 `INSUFFICIENT_SAMPLE/bins=[]`；
UI 将尾桶写中文，只格式化原保存 decimal 值，不自行分箱。

**Sharpe 与 Calmar。** 年跨度 `Y` 复用 §11.2 的 Actual/Actual、同一
`[anchor,end)`。逐期 `r_i=NAV_i/NAV_(i-1)-1`，首期之前的财富为原
initial_nav_minor；逐期年分数 `Y_i` 按两个 session 日期拆分，
`rf_i=(1+rf_annual)^(Y_i)-1`，`e_i=r_i-rf_i`。样本标准差
`s_e=sqrt(sum((e_i-mean(e))²)/(n-1))`，
`Sharpe=mean(e)/s_e*sqrt(n/Y)`；保存 `observations/n/Y/annualization_factor`
和有效率假设。状态按缺失或非正前值、`Y<1`、`n<30`、`s_e=0` 顺序给
MISSING_RETURN/INSUFFICIENT_SPAN/INSUFFICIENT_OBSERVATIONS/
ZERO_VOLATILITY，对应 value=null。Calmar 用现有同区间账户
`CAGR/abs(max_drawdown)`；CAGR 不可用沿用原状态，零回撤给
ZERO_DRAWDOWN/value=null，负 CAGR 可产生负 Calmar。所有结果以既有独立
Decimal precision=40、ROUND_HALF_UP 保存 decimal 字符串；不因首尾部分月或
持仓段不合格自动禁用。年化 Sharpe 的 `sqrt(n/Y)` 是显式的观察频率假设，
自相关可影响其解释，不能据此给策略排名或预测标签。
此限制依据 [Sharpe 的原始说明](https://web.stanford.edu/~wfsharpe/art/sr/sr.htm)；
一年门槛是本系统的保守展示约定，不冒称 GIPS 对 Sharpe 的规定。
输出为 `risk_metrics={sharpe:{status,value,observations,year_fraction,
annualization_factor,risk_free},calmar:{status,value}}`；annualization_factor
是 `sqrt(n/Y)` 的 decimal 字符串，缺失时为 null。

**最小辅助分析与追踪。** `analysis_series` 每点保存 `session/committed_sequence/
account_cumulative_return/rolling_return_20/rolling_volatility_20/rolling_status`；
累计收益为 `NAV_t/initial_NAV-1`。20 个账户交易 session 的
`NAV_t/NAV_(t-20)-1` 与窗口中 20 个逐期收益的样本标准差，后者是**逐期**
波动，不年化；首个完整窗允许 initial NAV 虚拟 anchor，不足窗给 null/
INSUFFICIENT_WINDOW，任一期前值非正给 MISSING_RETURN，不前填。`execution_summary` 保存双边换手
`sum(fill.gross_minor)/mean(saved NAV_minor)`、费用占初始资本
`sum(fill.fee_minor)/initial_nav_minor`；平均 NAV=0 时换手为 null/ZERO_MEAN_NAV；`concentration_series` 逐 session
取最大单票 `position.market_value_minor/nav.nav_minor`，同日引用必须有相同
committed_sequence，零 NAV 优先给 null/ZERO_NAV，有正 NAV 的空仓比重为 0。`episode_points` 仅含
可统计闭合段的 `(episode_id, net_return, entry_session, exit_session,
holding_calendar_days)`，天数为两日期差；开放、左截断、已知收入 pending 段不填。
UI 仅读取保存值。

`execution_trace` 按原 decision 数组序号保存 trade/feature session、原 status、
selected_security_ids/targets/trace 与精确链接 `intent_id→order_id→fill_id[]`；
订单未成交时 fill_ids=[]，`requested_quantity` 精确来自 order.quantity，
保留原 decision 的单数或复数 selected 字段。没有保存的 sequence/field 均为 null，
不推定订单 committed_sequence；保留原 order.status/reason、requested/filled/
unfilled_quantity、execution_admission 与成交价/费/sequence。资格内历史分数
可从同一保存 `plan.signal_frame` 精确取出并标
`DERIVED_FROM_SAVED_SIGNAL`；如生成名次，须复核原 Core 同分规则且标为派生，
不能从最终成交倒推目标理由或冒充模型特征贡献。保存件没有逐特征贡献、真实
开盘簿与经纪商回报，不创建这些解释。

**有界验收。** 手工峰值平台/并列谷底与恢复样例、闰年 Y、rf=0 与显式非零值、
零波动/零 DD/终 NAV=0、2% 桶的两端和 0、20-session 窗、现金费与水位、
跨币种/跨日历缺证以及 intent/order/fill 零或一条关联做定向测试。
只读消费已保存 January observed 验证 22 NAV session 与 17 合格闭合段：
其 Y≈0.09，Sharpe/Calmar 必为 INSUFFICIENT_SPAN/null；不据此宣称
多年策略风险指标。旧保存件全字节和 hash/mtime 不变，评价只产生新路径。

## 12. 公共入口与只读接口

日级 P10 的有界公共入口如下；评估是显式离线写入步骤，UI/Research 只调用保存结果的 loader：

```python
from axiom_engine.runtime import (
    BenchmarkSeries, EvaluationSpec, EvaluationReport, DividendScope,
    daily_evaluation_spec, read_csi300_benchmark, read_dividend_scope,
    evaluate_backtest, save_backtest_evaluation, load_backtest_evaluation,
    load_backtest_run,
)
run = load_backtest_run(run_path)
benchmark = read_csi300_benchmark(data, snapshot=snapshot,
    sessions=calendar_anchor_through_end)
scope = read_dividend_scope(data, snapshot=snapshot, universe=universe,
    start_session=start_session, end_session=end_session)
report = evaluate_backtest(run, benchmark=benchmark,
    spec=daily_evaluation_spec(), dividend_scope=scope)  # scope 可为 None
save_backtest_evaluation(report, report_path)

# 只读消费者：校验保存内容，不 run_backtest/evaluate_backtest。
saved = load_backtest_evaluation(report_path)
payload = saved.to_dict()
```

<a id="saved-reader-cost"></a>
**保存 Reader 性能约束。** 状态 `frozen_for_bounded_saved_reader_optimization`（2026-10-05）。
允许同一次加载复用已校验的 coverage canonical bytes，并按原 canonical JSON 的键序、
数组顺序、数值编码与 UTF-8 字节流式核对完整原 DataBatch SHA，减少重复遍历和巨大临时
字符串。有限值、Unknown、来源与引用闭包、投影及损坏输入的全部验证仍须执行；不能
直接信任未验证的原字节或绕过投影语义。旧保存件身份、refs、输出值及公共 API 不变，
校验复用只在本次加载内有效，不建立跨次持久信任缓存，不查询 Data 或重算账户/统计。

Owner 对保存股票样本的完整 Reader 诊断为约 27.34 秒 / 3.99 GB，其中 canonical 校验
与序列化约 23.01 秒；磁盘读取约 0.11 秒、解压约 0.33 秒。此前约 29.10 秒另含两次
Reader/to_dict 与 208 个受保护文件哈希，不能当作页面打开耗时；已导出 HTML 的打开与切页
不调用 Reader。优化验收须核对原/新加载的身份与值、错误输入拒绝和峰值内存，并分别
记录加载、校验、投影的成本；本单样本诊断不作为多年性能保证。

Engine [PR #7](https://github.com/sinnergarden/axiom-engine/pull/7) 已合并有界 Reader
优化：同一保存账户+评价单组的 owner 测量为 27.34→14.90 秒，来源/hash/ref 与
旧文件保持；这是 Reader 范围，不推断整页导出或浏览器开页提速。校验字节只在
同一次加载中复用，不建立跨次信任缓存。

§11.2 的已确认增量入口已由 Engine PR #4 实现；复用上述评价、保存和只读加载函数，仅增加固定工厂，不另建账户路径。以下示例本轮未执行：

```python
# 已实现合同入口，示例未执行；保留旧报告，写入独立的新路径。
from axiom_engine.runtime import long_history_evaluation_spec
report = evaluate_backtest(run, benchmark=benchmark,
    spec=long_history_evaluation_spec(), dividend_scope=scope)
save_backtest_evaluation(report, new_report_path)
# UI/Research 继续仅 load_backtest_evaluation(new_report_path)。
```

§11.3 固定增量为 `analysis_evaluation_spec(*, risk_free)` 与
`evaluate_saved_analysis(run, base_report, *, benchmarks, spec)`，沿用
`save_backtest_evaluation/load_backtest_evaluation`，不增加账户或 Data 隐式调用。
显式 TopK 仍走原 `plan_stock_portfolio` 和 `run_backtest`；Notebook 如仅展示
目标可调用 Core 两次，如比较已成交结果则不同 k 须各有独立账户 run。
这两个增量入口在 Engine 源码/定向验收完成前均为设计状态。

Data 显示投影消费另走 `build_fill_display(run, *, display)` 与独立保存/加载入口，
消费需求为：固定 `display_ref`、完整显示跨度与末日锚点 A、共同 cutoff C、每个
security/session 的 Decimal multiplier、原单位/目标单位与来源 refs；只接受实际
fill.session 同时钟且原单位一致的映射。缺因子/单位不符或未证实 new_price_basis_session
时坐标 null 并保留原因。该报告身份绑定 run 三元组与 Data display_ref/实现版本，
不修改 run、原 fill.price/fee/cash/positions/NAV 或其身份。Data 的精确 wire shape
交接前不猜字段名或新单位生效 session，暂不宣称显示接口可用。

以下为其余通用目标接口，不因上面的有界 profile 而宣称全部实现：

```python
run_backtest(request: BacktestRequest) -> BacktestRunRef
run_session(request: SessionRequest) -> RunRef
resume_run(run_id, approved_recovery_policy) -> RecoveryReport
reconcile(account_id, scope) -> ReconciliationReport
query_account(account_id, as_of, committed_sequence=None) -> AccountProjection
query_run(run_ref) -> RunSummary
query_chart_layers(run_ref, security_id, interval) -> RuntimeChartLayers
```

CLI 只做解析与调用，Notebook/Agent/systemd 使用相同 service。只读 inspect 不发送委托、不调用会写生产目录的初始化。UI 查询返回 committed watermark，避免同一屏拼接不同事务阶段的 cash/positions。

运行调度按 Research 声明的模型依赖检查 [Data 就绪合同](02_axiom_data.md#source-readiness)，在冻结时点 C 固定输入后调用 Core，并保留意图有效截止 E 与实测预算。到 C 必需输入缺失则跳过/阻断，optional 只按既定合同处理；不因某域次晨才就绪而回填可知时间，不在 Runtime 复制供应商接口钟点表。本轮没有新增通用调度框架或实盘路径。

```text
src/axiom_trade/
  runtime/ backtest/ adapters/{feed,signal,broker,state}/
  accounting/ ledger/ reconciliation/ reporting/
  services/ query/ cli/ deploy/ tests/
```

## 13. 分阶段验收

当前完成 T-M1 的有界 cached ETF 离线路径与保存报告；没有声称通用 model source/SimBroker 全部能力。T-M2 的 SQLite outbox/inbox、Broker crash recovery，以及 T-M3/T-M4 的 shadow/real 未实现或未验收。实际范围以 [owner 证据入口](../current-delivery.md)为准。

| 阶段 | 最小交付 | 不能提前宣称 |
|---|---|---|
| T-M1 | 离线单回测、cached signal、Core 接入、SimBroker、核算/标准报告 | 真实 Broker 可用 |
| T-M2 | SQLite ledger、intent/outbox/inbox、部分成交、恢复夹具、只读查询 | 已经获得真钱授权 |
| T-M3 | shadow 持续运行、model source 一致性、对账与部署冻结 | 不同实盘成交环境收益等同回测 |
| T-M4 | 明确 Broker adapter/权限/规则/账户验证后受控 real | 通用支持所有券商和证券事件 |

## 14. 最小验收标准

本轮已有固定输入复现、缺信号/时间边界拒绝、严格状态阻断、显式 ETF 近似准入、T+1/现金/限价/容量、现金分红、保存 digest 和 UI 只读一致性证据。以下 T01–T22 是目标验收目录，53 tests 与合成 handcalc 不等于全部目录通过；特别不能据此宣称数据库事务恢复、实盘对账或全部标准绩效指标已完成。

| ID | 操作/失败点 | 必须结果 |
|---|---|---|
| T01 | Research 同 SignalRun 多策略回测 | 不训练/推理，使用同一 engine，独立账户/结果 |
| T02 | 同信号的 cached/model source | Target/Intent/模拟账户轨迹一致，无重复标准化 |
| T03 | 运行中改 model/data/default/配置 | 已启动 Plan 不变，下批次才采用新版本 |
| T04 | 开盘决策尝试读未来 close/volume | 不可见/拒绝；执行侧信息不泄入 Core |
| T05 | 停牌、缺价、一字限价、低成交量 | 保守成交/不成交/部分成交，明确原因和估值 |
| T06 | 分红、送转、应收到账及重复事件 | 权益正确、不双算收益、不重复入账 |
| T07 | 两个并发相同下单请求 | 一份逻辑意图/outbox，状态版本检查生效 |
| T08 | 事务 A 后、发送前 crash | 可以安全继续发送同一已持久意图 |
| T09 | Broker 已接收但 ACK 丢失 / 进程 crash | 查委托/成交后确认；未知则阻断，不盲目重发 |
| T10 | apply fill 中途故障 | fills/cash/positions/order/checkpoint 一起回滚 |
| T11 | 同 fill 重放 / 同 key 不同 payload | 前者幂等，后者冲突/更正可追踪 |
| T12 | 成交先于 ACK、撤单后迟到成交、累计回报 | 不漏记/双记，冻结与剩余量正确 |
| T13 | partial fills + 按单最低费用 + 费用晚到 | 费用正确累积/调整，滑点不双扣 |
| T14 | 买入未可卖、已冻结数量再次卖出 | 拒绝超可卖/超现金，规则按 profile |
| T15 | 多账户/环境同 strategy 名 | 查询以 account_id 隔离，backtest 不写 real |
| T16 | Broker 与本地现金/持仓不一致 | 暂停相关发送、显式 reconciliation，不覆盖流水 |
| T17 | 备份恢复、checkpoint 重放、换发布目录 | 可恢复账户与原计划；事件与投影一致 |
| T18 | 已发委托但报告/UI 生成失败 | 成交不回滚；报告可重建，运行状态不伪成功 |
| T19 | 已知净值/现金流 fixture 计算指标 | CAGR/DD/Calmar/Sharpe/恢复/滚动超额/Worst-year 口径正确 |
| T20 | UI 同屏现金/持仓/图层查询 | 同一 committed watermark；意图/委托/成交有区别 |
| T21 | 不安装 Broker SDK，禁网跑历史回测 | 正常完成，无环境写入/凭证依赖 |
| T22 | state contract 或 execution rule 不兼容 | preflight 拒绝；不得忽略后继续真钱运行 |

交易所/券商特定实盘能力必须追加真实 sandbox/只读对账证据；隔离 fake Broker 通过不等于真钱已验收。

## 15. 来源、补充决策与待确认

源材料：`qsys_sqlite_ledger_prd.md` §3–4、§9–16；Axiom 总纲 v0.1 §7、§10–13；本对话关于停牌/公司行动/容量、评估指标、scheduler 和 pointer 的输入。保留账户 ID 主键、流水/投影分离和事务性；现金精度、outbox/inbox、迟到回报、FULL 默认与只读一致查询为本版明确补充，不声称原文已完整规定。

外部技术核对（2026-09-05；只用于对应 SQLite 行为）：

- [E1] SQLite WAL：`https://www.sqlite.org/wal.html`。
- [E2] SQLite synchronous：`https://www.sqlite.org/pragma.html#pragma_synchronous`。
- [E3] SQLite Online Backup API：`https://www.sqlite.org/backup.html`。

待确认：Broker client_order_id/query 能力；准确费用/税务/交易规则与公司行动范围；最小执行窗口和量限制近似；现金四舍五入；真实账户启动/迁移基准。未完成前只交付相应级别，不以示例参数直接实盘。
