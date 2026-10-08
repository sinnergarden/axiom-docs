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
Research/UI 不另建账户路径。§6.1 的显式 TopK 已由
[Engine PR #8](https://github.com/sinnergarden/axiom-engine/pull/8) 实现并合并；旧 Top5
仍按原版本加载。无账户依赖的同一保存 Signal 可供多个独立账户/策略消费，但策略与
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

<a id="backtest-shadow-parity"></a>
### 2.1 回测与 daily shadow 无业务差异：原则、时钟与实现缺口

**硬原则。** 继承 [Core §1.2](03_axiom_core.md#12-回测与-daily-shadow-无业务差异的硬原则)：同一冻结输入/source refs、事件排序与逐 session 可见性、账户/策略状态、策略/风控/执行 profile、实现版本及随机种子（若有），batch 回测和逐 session shadow 必须复用同一计算、决策、风控、订单、模拟 Broker 和账本规则。batch/cache 仅作等价优化；adapter 和调度可以不同，但不允许模式分叉的数学、成交约束或核算。不同环境账本仍按 §7 物理隔离。

验收固定同一逻辑 run/account/session/event 对齐关系，逐字段比较保存的 decision/trace、target、intent、order/拒单、fill、fees、公司行动与权益登记、position/可卖数量/成本、cash/receivable、NAV 及 committed_sequence；稳定业务 ID、source refs、cutoff、缺失/拒绝原因也参与比较。只有物理环境定位、墙钟日志和 attempt 包装可在验收 manifest 中明确单列；不能以此豁免业务键或状态差异。分批容器的整体 hash 不替代逐项核验，容差内收益接近也不等于通过。

**`daily_volume_proxy` 的真实可见性。** 当前 ETF `daily_open_profile` 和股票 `retrospective_daily_volume_proxy` 都以当日完整 `volume_units/volume_shares` 乘 participation_rate 约束成交，并使用当日 open/价格限制等执行事实。这是离线研究模拟，不能把完整日量或收盘价送入当日盘前决策，也不能在开盘就宣称已得到该模型的模拟成交。

| 阶段 | shadow 的允许输入与输出 | batch 对照边界 |
|---|---|---|
| 盘前决策 | 原 decision 前的 T+1 结转及 EX/PAY 保留原相位与可见性，再仅消费该 cutoff 内可见的 Feature/Signal、前序市场/事件事实与账户状态；冻结 target/intent，所需执行事实未到时保持待结算，不用当日完整量/收盘价补决策 | 按相同事件排序、decision cutoff 和原账户水位作同一决策；不把 PAY 到账现金整体移到盘后 |
| 盘后模拟结算 | 所需原 open/限制、完整日量及估值事实已按冻结来源实际可见后，按明确 settlement cutoff 调用同一模拟规则；cutoff 前可待结算，到 cutoff 仍缺必需事实则两条路径采用同一缺数/阻断规则，不能 shadow 单独无限等待后补成交 | 原 logical phase/顺序不变：盘前结转/EX/PAY→决策→模拟成交/费用→record 权益登记→盘后拆分/估值与 NAV；实际盘后算出模拟成交不把原 decision 前公司行动移到盘后 |

允许盘后以原 open 为价格参考结算，是同一 profile 的事后模拟，不是盘后真实下单，更不能把实际结算/接收时刻倒写为开盘已知。不是到某个固定收盘/20:30 时刻就自动认为数据可见；settlement cutoff 由版本化运行协议预先冻结，实际接收证据只判定事实是否按期可用，不能因为迟到而顺延 cutoff。后到或修订的数据不得静默改写已提交 session，或进入更早的决策；确需重新研究时另存修订输入与独立 run。真正只用盘中已知量的执行需要另行审准 profile，并让 batch/shadow 同时采用该规则，不能为 shadow 单改规则后继续宣称同 profile 一致。研究近似 profile 不是 live 成交承诺。
若下一次决策 cutoff 已到而前一结算相位仍 pending，两条路径必须依同一冻结协议处理等待/阻断，不能一边使用后到事实提前结清、另一边忽略未决状态。历史 `best_effort_vendor` 或 declared-simulation 时钟不等于当时系统实际收到数据；不得拿现有离线输入证明实时 shadow 当时可知。

**2026-10-06 只读源码现状（Engine main `a18d38ff`）。** 以下是现有源码与未来能力的边界，不是本次实现：

| 已有源码 | 明确缺口 |
|---|---|
| [`run_backtest/_run`](https://github.com/sinnergarden/axiom-engine/blob/a18d38ff0708139b681dd76831013cebd98429cd/src/axiom_engine/runtime/backtest.py) 在一个连续 session 循环中调用原 Core planner、`_simulate`、fee 函数与 `AccountLedger`，并保存决策、订单、成交、账本和 NAV | 尚无公开 daily-shadow session 推进/相位暂停接口；离线函数拿到完整 MarketReplay 即推进，不是实际时钟服务或等待盘后事实的实现 |
| [`AccountLedger`](https://github.com/sinnergarden/axiom-engine/blob/a18d38ff0708139b681dd76831013cebd98429cd/src/axiom_engine/runtime/accounting.py) 已有整型资金、待结算批次、应收、fill/公司行动幂等键和 sequence；循环还维护 quotes/marks、分红权益及拆分登记/basis | 内存状态不等于持久 checkpoint；公开 Runtime 没有旧账本 append/resume、SQLite 事务恢复或持久 inbox/outbox。只保存 final_account 不足以恢复这些状态 |
| `save_backtest_run/load_backtest_run` 保存或校验已有不可变结果 | loader 不推进账户；不能逐日重建新账本再拼接结果，冒充同一账户续跑或跨日恢复 |

现有共享 Feature/有界离线账户证据不等于完整 daily shadow 一致性已经验收；T-M3 仍是未来能力。若未来加入 checkpoint，必须保存日历/相位游标、稳定订单编号与账本水位、待执行 intent/order、pending lots/应收、已应用事件去重状态、报价/估值、分红与拆分权益/basis，以及适用的策略/RNG 状态，并沿原规则恢复；不能只续 cash/position 后丢掉其余状态。这里列恢复要求，不提前宣布新公共 API。

**后续验收顺序（另行实施、父审与资源窗口）。**

1. 先用完全固定的小型合成输入，把未来逐 session 驱动与 batch 绑定到同一原 Runtime 规则，保存逐字段对照 manifest；包含非决策日、T+1/整手、费用、现金不足/限价/容量拒单、缺数及明确晚于 cutoff 的事实，盘后结算前不得向盘前暴露模拟成交或未来量。
2. 在决策后/待结算、fill 应用前后、公司行动与 NAV 提交边界中断并跨日恢复；检查重复与冲突事件、迟到/修订数据、分红 record/EX/PAY/应收、拆分登记/新价格单位及 unsupported-action 阻断，恢复与连续路径的全部业务键、流水、状态与水位逐项一致。
3. 合成资格与恢复能力通过后，再申请独立小资源窗口复用 owner 已保存输入，保存新的 batch/shadow 对照产物；原 run/评价文件保持不可变。当前 ML 最小闭环继续原已批准路径，本轮不新增 Engine 执行器、不跑真实账户或 shadow，不以这份设计宣称目标验收已完成。

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

**保存滑动 fold 的 v2 中立验证（2026-10-05，已实现并有界验收）。** 源码
`ac20e086` 已经主协调亲审及独立复审，经
[Engine PR #12](https://github.com/sinnergarden/axiom-engine/pull/12) 合并为
`330903c6`；新旧预测时钟定向验收通过，未运行账户。与
[Research §4.7 固定合同](https://github.com/sinnergarden/axiom-docs/blob/b343555736f602d4897a6901bdc1d2980048e941/docs/design/05_axiom_research.md#stock-saved-fold-clock-contract)
保持同一字段清单。现有纯函数公共导出为
`from axiom_engine.core import StockPredictionFrame, validate_stock_predictions`；
`validate_stock_predictions(frame)` 仍返回 `(wire, indexed_rows)`，不查询 Data、不训练、
不规划组合或执行账户。按 contract_version 分支：旧 `stock_prediction_run_v1` 的精确
字段与20:30、available_at≤knowledge_cutoff校验完全保留；新
`stock_prediction_run_v2` 顶层仅在 v1 字段外增加 `fold_spec_ref` 和
`clock_basis='declared_simulation'`，每行仅增加 `feature_knowledge_cutoff`、
`feature_available_at`、`simulated_model_available_at`。既有 stage、score semantics/unit、
完整 universe/member/validity、唯一行键、来源 refs 与无效行 null/原因保持原义。
Feature/model/fold refs 固定保存；v2 source_refs 包含对应 Feature slice/model refs。

v2 行 `knowledge_cutoff=available_at=inference_cutoff`（同一 aware instant）表示声明
模拟推理与信号发布；不放宽为晚发布。feature_knowledge_cutoff 与 inference cutoff
均归属行 session 的 Asia/Shanghai 日期，Feature 依赖可用时间可以更早。
非 null `feature_available_at≤feature_knowledge_cutoff≤inference_cutoff`；valid 行
feature_available_at 必须非 null，原依赖全部 null 时仅保留 invalid/null。原 Feature
依赖最大值由 Research 保存/校验，Engine 不从标量倒推出依赖证据。
`simulated_model_available_at<inference_cutoff`；同一 session 的完整 union 使用一致的
Feature/inference 时钟，同一 model_ref 使用一致的模拟模型可用时刻。时间使用 aware
instant 比较并保留原字符串，不把教学20:45/21:00硬编码为通用库唯一时刻。
Research model/fold loader 负责 fit_cutoff<模型可用以及模型/原输入/fold_spec refs 闭包；
Engine 不导入训练库，不从 model_ref 猜训练时间。

本阶段仅解锁中立验证，`plan_stock_portfolio` 与 `validate_stock_request` 明确只账户
消费 v1；v2 在规划/启动 ledger 前以“账户时钟消费尚未准入”拒绝，现有账户与保存件
不变，新增账户执行为0。v2 账户消费合同见 §6.2，主线设计已审、待交接 ACK 和实现：复用唯一 Core planner/Runtime，
决策准入使用推理/发布时间，前收/member/Feature 仍受原 feature_knowledge_cutoff
约束，不把 Data 查询提升到推理时钟，不新增执行器或账户路径。

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

#### 同一冻结预测的显式 TopK 策略参数（已实现）

`BacktestRequest_v3.portfolio_policy.top_k` 与同一 `plan_stock_portfolio`
现接受**显式正整数** k；仅更改原信号或初始资金不能构成另一组合策略。
`type(k) is int`，拒绝 bool，
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

<a id="stock-v2-runtime-clock-proposal"></a>
### 6.2 保存预测 v2 接入同一股票账户（2026-10-05，源码已合并、真实验收待窗口）

主协调已亲审固定源码 `019f9824` 的本节主线合同；账户源码已由
[Engine PR14](https://github.com/sinnergarden/axiom-engine/pull/14) 合并为
`af337ee875297d369cd4a9bb7593619688e297b7`，合成/轻量验收通过，真实账户仍等待统一窗口。
[Engine PR15](https://github.com/sinnergarden/axiom-engine/pull/15) 声明公开包版本 0.3.0；
消费者至少依赖 `axiom-engine>=0.3.0`，并锁定经审阅的源码提交。Research 负责先保存
3–4 个真实连续周的 rolling fold：每折过去两年训练、下周预测、标签在 fit cutoff
前成熟。两年范围、标签成熟、训练键、参数及同批一次 load/validate 由 Research
主章定义；Engine 不改成 65 session，也不导入 Qlib/LightGBM 或另建执行器。
当前 January v1 预测、账户、评价及 §6.1 的 TopK 政策继续保留原身份。

**时钟分离。** 以下为本次账户配置的准确时钟，所有比较采用 aware instant，原字符串
保留；不是把 20:45/21:00 写入通用中立预测校验器：

| 阶段 | 本次约束 | 归属 |
|---|---|---|
| Feature/member/前收 | feature session 当日 20:30 Asia/Shanghai；Feature 依赖最大 available_at 不晚于该 cutoff | Research 保存原依赖，Data 保留原可见性，Engine 校验账户输入配对 |
| fit | fold_spec.fit_cutoff，训练 Feature 和成熟 label 都不得晚于它 | Research 公共保存件 loader |
| model | fit_cutoff < simulated_model_available_at；本次声明 fit session 20:45 | Research 保存模型元数据及声明时钟 |
| inference/publish | 行 knowledge_cutoff = available_at = feature session 21:00；model available 严格早于它 | v2 原预测及 Engine 决策准入 |
| decision | 严格下一实际 exchange session 08:55；预测 available_at 不晚于该时刻 | 唯一 Runtime |
| execution | 下一实际 session 开盘价格代理；执行事实仍按当日 20:30 的事后日线证据解释 | 原股票 profile/模拟器 |

非 null Feature 可用时刻比较 `feature_available_at≤feature_knowledge_cutoff≤inference_cutoff≤decision_time`；
valid 行必须有 Feature 可用时刻，invalid 行的原 null/原因保留、不参与排序。
同时检查 `fit_cutoff<model_available<inference_cutoff`。模型完成/预测发布的历史时刻
仍是 `clock_basis=declared_simulation`，不能把今天的实际训练 wall time 说成历史完成证据。
前收报价和历史 member **仍只准入至原 Feature 20:30**；不得为了消费 21:00 预测，把
Data Query cutoff、原 Feature metadata 或标签成熟截止提升到 21:00。周末/长假用保存
exchange calendar 的严格前后 session 映射，不用工作日或自然日加一。

**保存 fold 调度，保持原预测身份。** 一个 v2 frame 只有一个 model_ref 和一个模型
可用时刻，不能把多个 rolling model 的行拼进同一 v2 并伪造共享 model_ref。拟增加
`axiom_engine.runtime.StockPredictionSchedule` 及纯工厂：

```python
stock_prediction_schedule(*, folds: list[dict], calendar: list[str]) -> StockPredictionSchedule
# folds 每项：{fold_ref, fold_spec, model, prediction_frame}
# prediction_frame 是 Research 公共 loader 返回的原 stock_prediction_run_v2 wire。
# model 是原 stock_model_release_v2 元数据；不包含 booster 或训练大表。
```

调度 wire 的精确顶层为
`{contract_version,schedule_ref,clock_policy,calendar,universe,folds,trade_schedule,limitations}`，
`contract_version=stock_prediction_schedule_v1`；schedule_ref 是除自身之外全部内容的
canonical digest。clock_policy 为
`{contract_version:stock_prediction_clock_policy_v1,feature_cutoff_local_time:20:30:00,
inference_cutoff_local_time:21:00:00,decision_local_time:08:55:00,
execution:next_exchange_session_open,clock_basis:declared_simulation}`。
合同接受非空、有序、有限的非重叠 fold 列表，不设 4 折产品上限；3–4 折仅为本次
真实工程验收的运行预算。入口按实际 fold_count、prediction_row_count、market_row_count
及输入字节规模做资源预检，超出调用方本次预算在创建 ledger 前给明确拒绝原因，
不因未来五年/256 fold 范围而更换接口。每个 frame 保留原
signal_run_ref/Feature/model/fold refs、完整 union、member、validity、分数和全部行；
所有 fold 使用同一冻结有序 prediction union，不静默补行或裁掉池外持仓。

公共入口将预算交给 `run_backtest(request, *, limits=None)` 的可选参数；limits 精确为
`{max_folds,max_prediction_rows,max_market_rows,max_input_bytes}`，各值为非负整数且拒绝 bool。
它统计实际 fold 数、原预测行数、market_replay 行数及 request 规范 UTF-8 JSON 字节数，
逐项超限即在 ledger 创建前拒绝。预算只决定本次工作是否允许启动，不进入 run 身份；
同一输入在充足预算和未提供预算时得到相同结果。原调用方式和旧请求不变，显式 limits
仅准入 request_v4。这四项已随 PR14 审阅合并；带预算时复用同一请求解码的进一步修正
进入 0.3.1 源码候选，仍完整执行准入，不开放公共“已准入”标记。

trade_schedule 每项固定
`{trade_session,feature_session,signal_run_ref,fold_spec_ref}`；覆盖请求账户区间内的每个
实际交易 session，不能仅覆盖有调仓的周首日。每个 trade_session 映射到相应原 frame
的严格前一 feature session；
feature_session 必须是 calendar 中 trade_session 的严格前一项，匹配该 fold_spec 的
oos_trade_sessions/inference_cutoff_by_session。重叠、洞、重复、缺原预测组、原 model
元数据 hash 不符、fit/model/推理时钟冲突或 union 不同，均在创建 ledger 前拒绝。
Engine 校验完整 model.json 自身 ref、与原预测及 FoldSpec 的时钟/ref 关系；训练键、
成熟 label、booster/父 Feature 闭包仍由 Research 公共 loader 验证一次，并交接 fold_ref。
调度只保存这些小元数据和预测，不重复嵌入训练 Dataset、Label 或 Feature proof 大表。

**同一个运行入口和连续账本。** 新计划为 `backtest_request_v4`：沿 request_v3 的
account_id/start_session/end_session/market_replay/initial_account/profile/
prediction_universe/execution_universe/supported_universe_ref/portfolio_policy/
admission_ref/admission_evidence/stock_action_policy，仅以 `prediction_schedule` 替换
`signal_frame`。市场仍为原 market_replay_v3，股票 profile、资格、事件、费用、现金、
整手、容量、T+1、NO_DECISION 和周首调仓政策沿用 §6.1。初始空仓只在窗口开始一次；
跨 fold 不清仓、不重置现金、不拼接独立账户 NAV。`run_backtest(BacktestRequest)` 在原
session loop 取已固定的 fold/frame，调用同一 Core planner、_simulate 和 AccountLedger。
周调仓仅在 §6.1 既有 weekly_first_trading_session 政策触发，fold/model 切换不额外
触发换仓；非调仓日仍保存该 session 的原 frame/group 映射及连续账户观测。
保存元组为 backtest_run_v4/axiom.backtest/4/axiom.stock_portfolio/2；这只是新输入和
时钟合同版本，不增加执行器或 Qlib 回测路径。
run.signal_ref 取 schedule_ref；每个 decision.signal_ref 仍取当次原 frame.signal_run_ref，
不把组合调度身份冒充任一原始预测身份。

Core 公共签名仍为
`plan_stock_portfolio(frame, *, account, context, top_k=None)`。v1 的精确 context、20:30
及旧默认 Top5 输出保持不变。消费 v2 时 top_k 必须显式；context 在原股票字段之外
仅加 `feature_knowledge_cutoff`，knowledge_cutoff 表示原预测 inference cutoff。
Core 校验该组原行时钟一致、available_at≤decision_time；前收 source available_at 改按
feature_knowledge_cutoff 校验。目标预算和 1/k 不变，结果仍为 axiom.stock_portfolio/2，
新 v2 决策顶层另存 `prediction_clock={clock_basis,feature_knowledge_cutoff,inference_cutoff,
simulated_model_available_at,model_ref,fold_spec_ref}`，取原预测时钟及 refs，NO_DECISION 也保留；
意图身份绑定原 frame、所有 context 时钟、k 和账户版本；旧输出不补这些字段。

v2 意图身份通过已核对原 frame 全部内容的 signal_run_ref 绑定预测。公共 Core 调用
完整校验 frame 及自身 ref；Runtime 入口已经完成同一校验，后续决策复用该 ref，
不为每次意图重新序列化整份预测。两种调用对相同 frame/account/context 产生相同决策。

新 `stock_snapshot_pair_admission_v2` 沿用原完整 native DataBatch/Query/Reader 配对
证据，增加 prediction_schedule_ref 及逐 fold
`prediction_refs=[{fold_ref,fold_spec_ref,signal_run_ref,feature_ref,model_ref}]`，取代旧
单 frame 的三个顶层 refs。成员配对覆盖所有原预测行；前收 basis 配对覆盖全部执行
union 和窗口 session，按原 feature cutoff 校验。原 83 只/23 session 的特定计数字段
在新版本按实际 scope 明确保存 checked_rows/paired_rows，不把旧月份的 PASS receipt
用于新日期。实际 Snapshot、完整日历和 owner 配对证据须由 Research/父线程交接后
固定；Engine 不自行采集、不缩到最终成交证券，也不从结果倒推准入。

动态计数的准确字段候选为顶层
`listing_identity_checks={checked_rows,paired_rows,mismatches}`，两项计数均须等于冻结
execution universe 大小，mismatches 必须为空。previous_close_basis_checks 保留
`all_available_at_feature_knowledge_cutoff/all_available_before_decision` 两个时钟结论和
`paired_rows_per_root/checked_rows_both_roots`；新增
`equal_rows/listing_identity_checked_rows/listing_identity_mismatches`。前两项分别等于
execution universe 大小乘完整 market calendar session 数，mismatches 必须为空，
checked_rows_both_roots 等于两倍配对数。新版本不接收旧固定 83/23 布尔标签代替这些
计数；动态计数均要求 int，并拒绝 bool 和浮点数。其余完整 native 字段、Query、Reader、
原 member 配对和 warmup 证明继续逐项校验；
这些字段已随 PR14 审阅合并，真实新日期收据仍由 owner 交接。

**保存预测复用和评价边界。** 同一 schedule_ref/原预测及市场输入分别生成 Top3、
Top5 独立 account_id/run 三元引用；feature/label/fit/predict/供应商调用均为 0，初始
现金相同。Engine 按上述版本增量适配旧公共 save/load、stock_dividend_scope 和保存
评价/成交显示的输入准入；旧 v1/v2/v3 读取保持原值，不重放或升级旧身份。
Engine 账户评价仍负责原 CAGR/DD/Sharpe/Calmar：3–4 周不足一年，CAGR/Sharpe 及
依赖 CAGR 的 Calmar 按原资格为 null，不用 IC 替代账户表现。

用户在 2026-10-05 更新统一基数：今后新 ETF、股票、TopK 和买入持有对照账户均使用
初始现金 500000 CNY，即 50000000 分，并从零持仓开始。Engine 使用真实费用、整手及
容量规则重新运行新账户；旧账户数值不能线性放大为新基数。旧 refs 和文件暂保留作为
兼容证据。用户已澄清旧记录只从页面撤下，本地文件全部保留，不做永久清理。

**一次准入和性能验收。** schedule、逐 fold model/原预测及共享 native 输入闭包在
run 入口各校验一次，建立按 trade_session 定位的已准入 frame/group 索引。session
loop 只定位已准入组，逐次核当前账户版本和决策 context，不重新扫描全部 fold、
验证完整 model/frame payload 或解析大 proof；独立公共 Core 调用仍完整校验输入，
不开放调用方伪造“已准入”标记。实现优先复用既有解码/验证与 pure planner，不先选定
全局缓存框架，不因优化丢 proof、改数值、改变来源身份或放宽拒绝条件。

验收记录 admission_seconds/session_loop_seconds、闭包解码与各 frame/model 校验
次数、实际 fold/row/字节规模和 RSS；3–4 折运行中的完整校验次数不得随 account
session 数线性重复，TopK 两个运行分别满足入口一次准入。fresh 外部公共 loader
按保存合同重新校验闭包一次，返回原保存结果，不训练、预测、账户回放或补算。

Research 的 SignalEvaluation 可独立于策略/账户比较多个保存 Signal，负责 IC/RankIC/
ICIR 等定义、Label refs、maturity、对齐、编排和保存；多 Signal 共用一次 Label 读取
及对齐。Core 若需提供共享纯算子，先复用已有实现，由 Research 提交准确 input/output、
缺失/tie/截面/权重合同后单独父审，Engine 不先抢写其接口或文件。DuckDB/OLAP 只是
候选参考，本提案不引入依赖。UI/Notebook 只显示两类 owner 保存值，不自行补算。

**有界验收与资源。** 先用合成连续两周验 fit=model/模型晚于推理/预测晚于下一决策、
20:30 后前收、长假、重叠/漏 fold、跨 fold 持仓及现金保持、Top3/Top5 和旧 v1 字节
兼容；阻断必须发生在账本写入前。Research 的真实 3–4 周保存预测和完整准入闭包
ready 后，只顺序运行两个 TopK 账户，再读保存评价，记录账户 wall time/RSS、决策/
成交/现金与费用对账及零上游调用。当前不启动新账户，训练先由 Research 独占资源。
不能以冷构建/缓存命中替代真实 rolling，不能为账户演示重做多年 ML。

**Agent 账户阶段交接。** Research 负责完整研究用例和原保存 fold 的公共读取，Engine
提供这一段可复用的账户入口。Agent 先取得 owner 已保存并核验的
`{fold_ref,fold_spec,model,prediction_frame}`，调用
`stock_prediction_schedule(*, folds, calendar)` 构造上述调度，再把原调度、完整市场与
native 配对证据放入 `BacktestRequest.from_dict(request_v4_wire)`。执行只调用
`run_backtest(request, limits=limits)`；Top3 与 Top5 分别使用独立 account_id、相同
50000000 分和零持仓，沿全窗口各维护一个连续账本。冻结 manifest 记录源码提交、包版本、
request.identity、schedule_ref、逐 fold 原 refs、market/admission refs、完整区间和
实际输入规模；预算作为运行收据另存，不能改变确定性身份。未交接完整闭包时保留
INPUT_NOT_READY 状态，不能用合成 fixture 或旧月份收据替代真实输入。

成功后调用 `save_backtest_run(run, path)`，登记原
`{run_id,content_digest,committed_sequence}`，并核对现金、费用、整手、T+1、跨 fold
水位和原预测身份。评价用保存 run 调用 `evaluate_backtest`，再以原 v2 评价和明确
benchmark/spec 调用 `evaluate_saved_analysis`；三个阶段均消费 owner 保存输入，Engine
的供应商、Feature 构建、fit 和 predict 调用数为零。短窗口资格仍按本节保留 null。
单个 run 的入口准入次数不随账户 session 增长；两个独立 TopK run 和后续独立公共
评价或 loader 调用各自核验闭包，不能把“一次”解释为整条研究流程只验证一次。

恢复以保存阶段为边界。已有匹配 manifest 与 run 三元组时，Agent 通过
`load_backtest_run(path)` 读取原结果，继续尚未完成的保存评价阶段。准入异常保留原输入
和准确错误收据，待 owner 修正事实并重新冻结请求、父线程给资源窗口后，只重新运行
有界账户阶段。BLOCKED 结果可保存停止原因、水位和有效前缀，但完整评价只接受
COMPLETE；当前没有追加旧账本或 session checkpoint 恢复接口。不能把截断前缀改成
完整结果，也不能为了重试账户重新训练模型或构建 Feature。

运行收据另存 `wall_seconds`、规范化为字节的 `peak_rss_bytes`、实际 fold/预测/市场行数、
UTF-8 输入字节数、调用方预算和结束状态；耗时与 RSS 不进入确定性 run 内容。Agent
可用单进程计时和资源统计取得入口总耗时与进程峰值，外层资源窗口负责 time/RSS 中止。
公开入口目前没有 admission/session-loop 分段计时回调；开发验收可用有界只读插桩记录
两段耗时及 frame/model/native 校验次数，不能伪称它们是公共 API 返回值。该收据既检验
量化口径的账户连续性和费用守恒，也检验开发实现的批量读取、入口校验与 loop 复用；
Research 的真实新窗口完成前，两者都只标合成或轻量证据。

<a id="etf-review-followup-proposal"></a>
### 6.3 ETF 与基准的第二优先级小方案（2026-10-05，设计已审、源码候选）

本节 API 和保存字段已由主协调亲审，[Docs30](https://github.com/sinnergarden/axiom-docs/pull/30)
合并为 `edef7af896a36afa066d19a74f083cab085f78c4`。Engine 0.3.1 源码候选正在独立审查，
已完成小型合成检查；真实 ETF 长回放仍待父线程释放窗口，不占用 Research 训练或
Notebook 验收资源。未合并候选不作为已完成的真实账户证据。

**七票单位与刻度。** 冻结名单为 159915、510300、510500、510880、511010、513100、
518880，身份继续使用已保存的完整 cn.etf listing identity。Data security_master 均为
exchange_traded_fund，market_daily/price_limits 单位为 CNY/fund unit，volume_units 为
fund units；既有 Data 合同没有 tick 字段，511010 不按每百元债券面值计价。
本实验逐票固定 tick_size="0.001"，依据为上交所
[2012 修订全文 §3.4.10–11](https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20121217_10785167.shtml)、
[2026 规则附件 §3.3.10–11](https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml)，及深交所
[历史规则 §3.3.11–12](https://www.szse.cn/disclosure/notice/general/t20060515_499577.html)、
[基金交易问答](https://investor.szse.cn/knowledge/fund/trade/t20171113_538865.html)。
这是本次冻结执行假设的来源表，不新增 Data domain，也不把 ETF 刻度套给股票或债券。

**新 profile 与 0/5 bps。** 候选签名为
`daily_open_profile(*, unknown_status_policy="block", price_limit_policy="require_both",
slippage_bps="0", price_grid_policy="legacy")`。全部新增参数取默认值时返回原 v1 的精确
字段和值；沿用原 unknown_status_policy 两个取值。显式
price_grid_policy="etf_price_grid_v1" 返回 daily_open_profile_v2；新 v2 只接受
price_limit_policy=require_both/known_only 和 slippage_bps="0"/"5"，非默认限价或滑点
必须同时显式选择该 grid。v2 在原字段外保存 price_limit_policy、price_grid_policy、
price_grid_ref 和 price_grid；grid 为
`{contract_version:"etf_price_grid_v1",price_unit:"CNY/fund unit",rules:[{security_id,
tick_size,source_keys}],sources:[{source_key,url,content_sha256,clause}]}`，按完整身份排序，
source_keys 指向上述规则原文及原附件的冻结字节摘要，price_grid_ref 绑定整个表。
入口校验每个执行证券均在表内且价格单位匹配，缺项或不支持单位在账本前阻断。

v2 先确认原始 open 落在刻度上；不修复离格原价。用 Decimal 计算
raw_slipped_price=open×(1±slippage_bps/10000)，买入 ceil(raw/tick)×tick，卖出
floor(raw/tick)×tick，再检查正价、已知限价、费用与实际现金；容量、100份整手及本实验
T+1 继续用同一个 _simulate/AccountLedger。买价等于已知上限、卖价等于已知下限仍
不成交；known_only 仅跳过缺失的那一侧，null 不变成“无涨跌幅限制”的事实。
新 fill 保存 raw_slipped_price、price_tick、price_grid_ref、price_rounding="adverse_tick"、
rounding_delta=price−raw_slipped_price 和 effective_slippage_bps，后者为相对原 open 的
不利价差比例乘10000；fill.price 是最终价，reference_open 是原价，slippage_minor 仍
仅诊断，不重复扣现金。0.500 买入5bps原计算0.50025、取整0.501，实际20bps，必须披露。

新的2019主基线、5bps对照和持有参考均从零持仓、50000000分开始。0/5两次轮动使用
同一保存 Signal、行情、窗口、v2 grid、require_both、佣金0.0003/min0/tax0及其余政策，
仅 slippage_bps 和独立 account_id 不同；旧0bp保存件及本地文件继续保留，不能把它
按资金线性放大。profile_ref/run身份明确区分所有新政策。
主基线显式调用 daily_open_profile(unknown_status_policy="etf_daily_observed",
price_grid_policy="etf_price_grid_v1",slippage_bps="0")，对照只将最后参数改为"5"。

**一次买入持有。** 新纯 factory
`etf_buy_and_hold_policy(*, security_id, entry_session)` 返回
`{contract_version:"etf_buy_and_hold_policy_v1",security_id,entry_session,budget:"1",
schedule:"entry_session_once",partial_fill_policy:"expire_no_retry",cash_dividend_policy:
"retain_cash",terminal_policy:"mark_open_position"}`。本次固定513100，entry_session 必须
等于账户 start_session；名称为“国泰纳斯达克100 ETF（513100）买入持有”，币种CNY、
SSE日历。Core 候选签名 `plan_etf_buy_and_hold(policy, *, account, context)`，版本为
axiom.etf_buy_and_hold/1；context 精确为 trade_session/reference_session/decision_time/
reference_cutoff/reference_prices/lot_size/commission_rate/minimum_commission_minor/
tax_rate/slippage_bps/account_state_version。Runtime 核 reference_session 为完整日历
的严格前一 session，reference_cutoff 为该日20:30 Asia/Shanghai，决策08:55；Core
核入场日、零持仓、账户版本及原前收来源时钟，目标为
floor(cash_minor/(reference_price×100×lot_size))×lot_size。缺严格前一session收价保存
NO_DECISION/ENTRY_REFERENCE_UNAVAILABLE；合法目标只提交一次 BUY，实际可买量仍由
原 Runtime 的现金/费用/容量裁定。阻断或部分成交不重试、不周调仓、不再投资现金
分红、不结束强平，期末保留开放持仓；2022年1:5拆分继续消费既有单位事实和生效日，
验证正持仓数量/成本与原价账本守恒，不猜 new_price_basis_session。

ETF新入口为 backtest_request_v5：沿 v2 原字段增加 portfolio_policy 和显式
price_unit="CNY/fund unit"，与grid单位核对；market_replay
仍为 v2，原 unit_split_policy 保留，v5只消费新profile v2。轮动 policy 精确为
`{contract_version:"etf_rotation_policy_v1",schedule:"weekly_first_trading_session"}`，
signal_frame 仍为原保存 frame；持有 policy 使用上述factory且 signal_frame=null。
保存元组为 backtest_run_v5/axiom.backtest/5/Core对应版本，另存 portfolio_policy_ref；
持有 run/decision 的 signal_ref=null，不能造恒定 Signal 或借用513100指数曲线身份。
v5 的公共 save/load、评价与成交显示准入按该显式元组验证 null 和 policy ref，旧
v1–v4 loader 保持；两种政策只调用同一个 Runtime loop、成交模拟器和账本。

513100 参考保存独立 BacktestRun/Evaluation，Research 登记上述可读名称及原保存refs，
UI 首版直接复用现有运行对照，读取账户owner保存的收益、回撤及评价值。该账户不
进入市场基准下拉；若未来放入下拉，先由owner另定独立投影合同，UI不能从NAV补算
benchmark。本次不为下拉新增投影层。

**SSE回撤 wire。** 候选签名
`analysis_evaluation_spec(*, risk_free, benchmark_projection_version="benchmark_comparison_v1")`。
默认 spec 精确沿用旧 v3；显式 benchmark_comparison_v2 在新 spec 保存该参数，
使 spec_ref/评价身份改变。report 仍为 v3，新 comparison 保存
projection_version="benchmark_comparison_v2"、max_drawdown；native_series 与账户
series 每点新增 benchmark_drawdown，均为非正收益分数或null。SSE从原anchor close
作首峰，anchor点为0，逐点 close/max(anchor及截至该点已知close)−1；首次缺价后该点
及后续回撤都null，不能忽略潜在缺失峰值恢复计算，max_drawdown 仅完整窗口可取最小值。
CSI逐点复制原 base.benchmark.series.drawdown、最大值复制原 max_drawdown，anchor已知
时为0；不重算旧值。SOURCE_UNAVAILABLE 保存新marker、max_drawdown=null及空序列。
旧 v3 缺 marker/字段仍可原样读取，不补算；UI只显示owner保存值。直接Nasdaq指数/FX
路径仅保留旧保存件及loader兼容，当前新增参考使用上述513100账户运行对照；未来
跨市场方案另议。

**2014独立探索预算。** 2019窗口和require_both仍为主口径；2014探索只用显式v2
known_only、5bp及同一真实执行约束，与2019新5bp结果对照；2019的0bp独立保留，
不额外运行2014零滑点账户。跨窗口/限价政策差异不能归因于滑点。输入/
前段简单动量Signal准备最多5分钟，账户一次最多5分钟，保存核对最多1分钟，单进程
RSS上限4GiB；超限保存实际范围、耗时和阻塞收据结束，不反复重跑。需要Research已有
前段Signal或其有预算补齐，不宣称原2019 Signal包含2014数据。此前1762 session账户
122.2秒、评价3.2秒只是旧测量；真实新账户待主协调给独立资源窗口后执行。

<a id="full-csi300-stock-execution-proposal"></a>

### 6.4 完整 PIT CSI300 股票账户（父审设计候选，待实现）

正式股票 ML 账户先在每个 feature cutoff 的完整 PIT CSI300 成员中排名，再由
同一个 Core 规划组合、Runtime 模拟成交和 Ledger 记账。§6.1 的
`sz_main_a_000_002_003_v1` 是已经保存的工程试点资格，其结果继续以这个范围解释。
本节的新入口覆盖沪深主板、创业板和科创板 A 股，包含深市 001 普通股；它不先按板块
删掉成员、再把剩余集合称为 CSI300。预测 union、每期成员行、score 和 Signal refs
保持原样。完整 union 只说明冻结身份范围，每期实际排名仍取当时 member=true 的行。

#### 最小公共 API 与冻结输入

候选 API 全部导出于 `axiom_engine.runtime`。四个工厂只验证并冻结已有输入，不进行
网络请求、成员查询、feature 构建、fit 或 predict，也不引入另一个策略或账户执行器。

```python
stock_execution_rules(*, universe: list[str], calendar: list[str],
                      identity_input: dict, quantity_rules: list[dict],
                      sources: list[dict], verified_from: str,
                      verified_through: str) -> dict
stock_fee_schedule(*, intervals: list[dict], sources: list[dict],
                   verified_from: str, verified_through: str) -> dict
csi300_stock_portfolio_policy(*, top_k: int, execution_universe: list[str],
                             execution_rules: dict) -> dict
stock_daily_open_profile_v2(*, execution_rules: dict, fee_schedule: dict,
                           unknown_status_policy: str = "block") -> dict
```

`stock_execution_rules` 返回精确形状
`{contract_version:"stock_execution_rules_v1",universe,calendar,identity_input,
identity_input_ref,quantity_rules,sources,verified_from,verified_through,limitations}`。
universe 是排序去重的完整
prediction union，初始持仓必须在其中；calendar 是本次真实执行 session 及所需前边界。
`identity_input_ref` 是内嵌 identity_input 的现有 Document identity。
identity_input 形状为
`{contract_version:"stock_execution_identity_v1",rows,source_refs,source_evidence,limitations}`；
每行精确为
`{security_id,exchange,board,instrument_kind,listing_date,delisting_date,
classification_source_keys,source_refs}`。delisting_date 可为 null，instrument_kind 固定
`A_SHARE`；board 只接受 `SSE_MAIN/SZSE_MAIN/SZSE_CHINEXT/SSE_STAR`，exchange 与 canonical
身份必须一致。旧中小板的历史身份必须有到 SZSE_MAIN 数量规则的显式来源映射。

当前 Data security_master 已有 exchange、上市和退市身份，尚无原生 board 字段。
首版由 Engine 在已有原生身份证据上保存逐证券的板块分类及官方代码分配依据，明确
这是有来源的派生映射；不伪称供应商提供了历史 board。classification_source_keys
引用本规则文档的 sources，source_refs 和 source_evidence 继续沿用已有 Data 引用和
原生批次证据。代码前缀只能辅助核对该映射，不能单独决定账户资格。任何身份未识别、
板块冲突、CDR 混入、规则日期缺口或证据不闭合，都在账户变更前拒绝整个请求，不能
通过缩小 union 继续运行。后续若 Data 提供原生分类，替换冻结输入即产生新规则身份。

security_master 身份批次可作为冻结 Snapshot 中已保存供应商记录的回溯身份基准。
该静态来源使用 Data 现有 operational_pit_v1 和 historical_exploration，cutoff 固定为
本次纳入身份记录的真实 first_observed_at 上界；原生 query、可用时间、revision 和
Raw 引用保存在 source_evidence，identity_input.limitations 明确这不证明 2024 年
当时已公开的身份事实。该基准用于核对 canonical 身份、exchange、上市退市边界并
支持有来源的派生板块映射。成员、交易能力、Feature 和 Signal 继续使用各自原有的
session cutoff；该身份批次不改变它们的历史时钟。替换身份基准会产生新的
identity_input_ref 和规则引用。

quantity_rules 每行精确为
`{board,effective_from,effective_to,buy_minimum,buy_increment,sell_minimum,
sell_increment,full_residual_exit_allowed,limit_order_maximum,
market_order_maximum,daily_proxy_maximum,price_tick,settlement_sessions,source_keys}`。
日期区间为 `[effective_from,effective_to)`，末端可为 null；同一板块的规则不得重叠，
本次每个实际上市 session 必须恰好命中一行。verified_from、verified_through 是已经
取得适用正文并核对的闭区间边界；本次 calendar 必须落在其中。effective_to=null 仅
表示正文未给失效日，不能证明 verified_through 之后仍已验证。首个2024短窗口只冻结
已取得正文的适用区间；补证后扩展同类文档条目和核实范围，产生新 identity。
source_keys 引用 sources 的
`{source_key,url,content_sha256,clause}`；哈希取实际读到的原文或附件字节，不以跳转首页
或空响应替代正文。历史窗口的来源覆盖逐段检查，不能把最新规则发布日期当作所有
历史 session 的生效日。price_tick 为 Decimal 字符串，其余数量字段为拒绝 bool 的
正整数，full_residual_exit_allowed 为 bool，settlement_sessions 固定 1。

新 policy 精确为
`{eligibility_id:"csi300_pit_a_share_v1",top_k,rebalance:"weekly_first_trading_session",
budget_basis:"available_cash_plus_previous_close_positions_excluding_receivables",
candidate_policy:"member_valid_finite_v1",stock_execution_rules_ref}`。
execution_universe 必须等于 execution_rules.universe，
`type(top_k) is int` 且 `1≤top_k≤len(execution_universe)`。Core 继续使用同一个
`plan_stock_portfolio(frame, *, account, context, top_k=None)`；新请求在 context 显式
绑定上述 policy、规则全文和规则 ref，走 `axiom.stock_portfolio/3`。该 context 沿旧
股票字段移除 lot_size，新增 portfolio_policy、stock_execution_rules 及
stock_execution_rules_ref；supported_security_ids 必须等于完整 execution_universe。
旧 policy 工厂、Core v1/v2 和其严格资格校验保持原行为。

#### 按板块和生效日期查数量规则

下表固定所需数值；前两列表示本候选需要冻结的规则区间。正式文档记录原规则的真实
生效日及替代关系，本次只准入来源已经覆盖的账户窗口。

| 板块及适用区间 | 买入最低数量与增量 | 常规减仓最低数量与增量 | 限价／市价单笔上限 | 日线代理报单上限 |
|---|---|---|---|---|
| 沪深主板，已核实区间 | 100／100股 | 100／100股 | 1,000,000／1,000,000股 | 1,000,000股 |
| 创业板，2020-08-24以前的历史区间 | 100／100股 | 100／100股 | 1,000,000／1,000,000股 | 1,000,000股 |
| 创业板，自2020-08-24起 | 100／100股 | 100／100股 | 300,000／150,000股 | 150,000股 |
| 科创板，自其2019特别规定适用起 | 200／1股 | 200／1股 | 100,000／50,000股 | 50,000股 |

科创板的 200 是每笔常规申报最低数量，201、202 股也是合法数量。主板及创业板
常规减仓的100股格保留本代理的保守量化政策，来源条款明确的是买入整手及尾股
一次性申报；这个卖出数量格不作为所有真实卖单的交易所法定增量声明。
普通股 100 股买入整手、尾股一次性卖出和 100 万股上限可核对
[深交所2006交易规则第3.3.8、3.3.10条](https://www.szse.cn/disclosure/notice/general/t20060515_499577.html)；
2024短窗口另核对
[深交所2023规则及附件](https://www.szse.cn/lawrules/rule/repeal/rules/t20230217_598773.html)。
创业板新上限与明确生效日来自
[深交所2020-08-21答记者问](https://www.szse.cn/aboutus/trends/news/t20200821_580924.html)。
科创板最低数量、两类上限及尾仓规则来自
[上交所2019特别规定第二十条](https://www.sse.com.cn/lawandrules/sselawsrules/repeal/rules/c/10118601/files/f6fc4a1d4c1f469183a013c4dc36a535.pdf)，
并核对[上交所2023规则第3.3.8、3.3.9及6.1.7条](https://www.sse.com.cn/lawandrules/sselawsrules2025/repeal/rules/c/c_20250612_10824490.shtml)
及[2026规则第6.7条](https://www.sse.com.cn/lawandrules/sselawsrules2025/trade/universal/c/c_20260424_10816492.shtml)。
SSE2023网页metadata中的2023-02-17是发布日期口径，通知正文明确以注册制首只主板
股票上市首日施行；effective_from 固定真实的2023-04-10，并由
[上交所改革实施说明](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20230810_5725020.shtml)
核对落地日，不采用网页metadata作为生效证据。2026交易规则自2026-07-06生效；
同值规则也保留各自的来源和有效区间。上述早期文本
为历史候选提供依据，2019至2023的完整替代链在多年账户准入前补齐并冻结。

`daily_proxy_maximum=min(limit_order_maximum,market_order_maximum)` 固定为
`min_limit_market_maximum_v1` 的保守研究假设。daily-open 仍是用日线 open 与当日量
近似执行的模型，这个上限不证明真实市价委托、开盘流动性、券商授信或实时交易权限。
价格继续消费同 session 的 native unadjusted open、上下限及原 UNKNOWN 状态；不能
按板块硬编码涨跌幅，也不能因为有 score 就把 UNKNOWN 改成可交易。

Core 完整检查每个 feature session 的 union 行和 PIT 成员来源后，仅从
member=true、valid=true 且 score 有限的行中按 score 降序、security_id 升序解同分
取前 k。个体合法缺feature或未完成预热的 invalid 行保留原 null、invalid_reason
和源refs，排除该行并计数，不冻结其余成员。trace 保存 pit_member_count、
valid_candidate_count、excluded_invalid_member_count，以及原 security_id/invalid_reason
明细。valid候选不足 k 时保存 NO_DECISION/INSUFFICIENT_ELIGIBLE_MEMBERS、实际数量
和要求的 k，保留仓位。缺行、重复、身份或成员来源不一致、未来时钟、refs损坏、
valid=true却非有限score等合同损坏，在账户变更前拒绝整个请求；不能伪装成个体排除。
旧Core v1/v2的一只invalid成员即NO_DECISION仅按其旧策略合同解释。
每只目标预算仍为可部署预算的
1/k，参考价仍为前一 session、cutoff 可见的 native close。对原始目标股数
`raw=floor(单票预算/前收价)`，使用规则向下取数量：raw 小于 minimum 时取 0，否则取
`minimum+floor((raw-minimum)/increment)*increment`，目标取0时保存
TARGET_BELOW_MINIMUM_QUANTITY 原因。当已有持仓时，再对目标与现仓的
差额应用买入或减仓最低数量及增量；不能把合法目标误当作合法增量。科创板持有200股、
目标201股时，不报1股买单；持有401股、目标300股时，不报101股常规卖单。
targets 保留目标值，trace 保存 BELOW_MINIMUM_ORDER_QUANTITY 及未执行差额，也不
换入排名第 k+1 的股票。

尾仓退出仅在该证券**全部持仓可卖**且意图退出全部持仓时适用：余额不足该板块最低
数量，可以一次性申报全部余额；普通股全部退出可同时包含整手与不足100股尾股。
持有500股但只有100股可卖，不得用科创板尾仓例外卖100股。常规减仓不足最低数量
就保留仓位并写原因；T+1 继续由同一 Ledger 的 sellable_quantity 约束。

#### 报单、部分成交、现金与费用共用原 Runtime

每个 intent 只形成一笔本日有效模拟订单。Runtime 按实际 trade session 查询冻结
规则，对 intent 应用单笔上限及合法申报数量，再用本日执行价和同一费用函数把买入
数量缩到可用现金可负担的合法申报数量；未提交的部分记为 unsubmitted_quantity，
不自动拆成多单。买入在板块合法数量格中单调二分：最低数量本身不可负担时
submitted_quantity=0并保存INSUFFICIENT_CASH，不报低于最低数量的买单。
卖单同时受 sellable_quantity 约束，尾仓例外必须完整满足。保存
`requested_quantity,submitted_quantity,unsubmitted_quantity`，其中前者仍是原 intent
数量，order.quantity 等于 submitted_quantity；不能用少量成交掩盖超限报单。
unsubmitted_quantity=requested_quantity−submitted_quantity。上限截断后的小于最低数量的普通报单为0并记录
原因，尾仓则必须一次申报全部余额。卖单先于买单，同侧按 security_id 升序执行。

交易所最低数量约束的是申报，部分成交可以小于最低申报数量。新 profile 显式使用
`partial_fill_quantity_unit="one_share"`：先形成合法报单，再以正整数股计算实际部分
成交；日线量容量为 `floor(native_volume_shares*participation_rate)`，成交数量不超过
submitted_quantity，卖出还不得超过可卖量。因此合法科创板200股报单，在模型容量
199股时可以成交199股、剩余1股到期未成交，不把199股记录成另一笔非法申报。
这仍是日线量代理假设；v1原有按100股量化成交的结果与 loader 不改变。

买单提交数量先完成上述合法数量与现金检查，然后由volume产生部分成交；实际成交
时用同一费用函数再次核对 Ledger 可用现金，不另建券商资金冻结系统。现金仅能支持
199股时，科创板200股买单不提交；现金足够200股而volume只支持199股时才成交199股。
实际成交0股不收最低佣金。卖出检查 `cash+gross≥fee`；费用不足保存原因。只为真实 fill
记现金、费用及T+1仓位；`unfilled_quantity=submitted_quantity-filled_quantity` 表示
到期未成交量，与 unsubmitted_quantity 分开保存。报单及 fill 均保存匹配的
stock_execution_rules_ref 和 quantity_rule_effective_from，
数量相等关系可从真实 intent→order→fill 检查，不能由期末仓位倒推。

v6摘要保留`metrics.unfilled_order_count`为submitted后仍有未成交量的订单数，另存
`unsubmitted_order_count`（unsubmitted_quantity>0的订单数）、`unsubmitted_quantity`
（未提交总股数）及`incomplete_order_count`（未提交或提交后未成交量>0的去重订单数）。
同一订单可同时有未提交和未成交量，前两种订单数不能直接相加。完全拒绝的请求保存
submitted=filled=unfilled=0、unsubmitted=requested，未完成订单数仍计入1；旧保存值不补写。

`stock_fee_schedule` 返回
`{contract_version:"stock_fee_schedule_v1",currency:"CNY",money_unit:"CNY_fen",
intervals,sources,verified_from,verified_through,limitations}`。每个 interval 精确为
`{effective_from,effective_to,sell_stamp_tax_rate,transfer_fee_rate,source_keys}`；
区间语义、核实边界和 sources 形状与数量规则一致，实际成交日必须在已核实闭区间内；
effective_to=null不允许在未核实未来继续计费。费率为非负 Decimal 字符串。本次候选所需
费率如下，买入印花税始终为0，过户费按成交金额双向收取。

| 实际成交日 | 卖出印花税率 | 双向过户费率 |
|---|---|---|
| 2019窗口起至2022-04-29以前 | 0.001 | 0.00002 |
| 2022-04-29至2023-08-28以前 | 0.001 | 0.00001 |
| 自2023-08-28起的已核实区间 | 0.0005 | 0.00001 |

卖出印花税原费率见
[上交所收费说明](https://www.sse.com.cn/services/investors/questions/pay/c/c_20220421_5701222.shtml)，
2023-08-28变更见
[上交所实施通知](https://www.sse.com.cn/aboutus/mediacenter/hotandd/c/c_20230827_5725662.shtml)。
过户费变更可核对参与券商向其客户发布的
[湘财证券收费实施通知](https://www.xcsc.com/main/a/20220429/1022871784.shtml)，其中同时列出
变更前后费率和2022-04-29生效日。已取得正文的
[HKSCC当日通告](https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/HKSCC/2022/ce_HKSCC_SET_017_2022_.pdf)
在互联互通北向范围印证同一变更，其适用范围须保留。中国结算原通知及可冻结的境内
参与券商正文收据尚待补齐；前者旧链接当前返回首页，后者正文读取遇到TLS兼容错误。
这些响应不能列为已取得原文，也不能以北向通告替代境内结算原文。首个2024短账户
采用参与券商通知作为收费依据前须取得正文，在 sources 明确发布主体及此证据限制；
多年正式账户另补历史原文及替代链，不把当前
费率外推到早年，也不把某家券商收费通知称为全部真实账户的最终结算依据。

新 profile 保存精确字段
`{contract_version:"stock_daily_open_profile_v2",stock_execution_rules_ref,
stock_execution_rules,stock_fee_schedule_ref,stock_fee_schedule,settlement_sessions,
commission_rate,minimum_commission_minor,slippage_bps,participation_rate,
decision_time_utc,execution,approximation,unknown_status_policy,
maximum_quantity_policy,partial_fill_quantity_unit,limitation}`。佣金0.0003、最低佣金500分、
滑点0、participation_rate=0.1、decision_time_utc="00:55:00Z"、execution="open"、
approximation="retrospective_daily_volume_proxy" 保持原显式实验参数；status 只接受
block 或原 stock_daily_observed。规则及费用 ref 都是对应内嵌文档的 Document identity，
settlement_sessions=1，maximum_quantity_policy 固定上述 min_limit_market_maximum_v1。
这个候选不再保存单一 lot_size 或固定税率来覆盖四个板块和全部历史。

Runtime 在每笔 fill 的实际 session 查询费率，同时把 fee_interval_effective_from、
stock_fee_schedule_ref 和各项费用写入 fill。现金试算与记账使用同一个原费用函数：
先 `gross_minor=HALF_UP(price*quantity*100)`，佣金取
`max(500,HALF_UP(gross_minor*0.0003))`，印花税和过户费分别用该 gross_minor 乘当期费率
并 HALF_UP 取分。仍是每个模拟订单最多一笔合并 fill 的收费假设，不额外叠加交易所
经手费与监管费到已经声明的佣金上。旧 profile v1 的固定费率继续按原保存合同解释。

#### 保存身份、行动边界及验收顺序

新股票保存元组一次新增为 `backtest_request_v6/backtest_run_v6/axiom.backtest/6`，
只搭配 Core `axiom.stock_portfolio/3` 与本节 profile v2。新请求沿股票 schedule 请求
既有字段形状，加 `stock_execution_rules_ref`；portfolio_policy、profile 和市场
准入证据必须绑定同一个完整 execution_universe 及同一个规则 ref。
supported_universe_ref 继续保存，但按新 eligibility_id 和完整冻结 union 计算，不能
复用旧深市子集 ref。run、保存 plan、decision、order 与 fill 的规则 ref 必须闭合，
run_ref 原三元组、Signal identity、admission ref、implementation identity 同样保留。
已有v1–v5保存件按原显式元组读取，不自动迁移或补字段；新评价和成交显示只增加该
元组的准入，继续消费保存 run，不重跑账户。

#### 上市、成员和持仓的生命周期准入

冻结 union 是所有可能出现证券的身份范围，整张 union×session 网格必须保留完整行键、
原始值、null、missing_reason和来源；数值必需性按实际生命周期判断。成员来源必须在
当日feature cutoff可见，不能把以后入池或上市的信息用来补当日事实。已有原生上市、
退市身份与PIT member行共同决定需要的域，不能将网格上所有null统称为在池缺口。

| 当时状态 | 必需性及处理 |
|---|---|
| 尚未上市、member=false、无持仓或待结算量 | 保留原null和reason，不要求价格、factor或限价非空，不参与排名或成交。此时member=true或存在持仓属于生命周期矛盾，变更前拒绝。 |
| 已上市、非成员、无持仓或待结算量 | 保留完整原生网格和缺口，未使用数值不阻断其他证券；入池前的真实历史可以成为Research已保存Feature的预热依赖，不能用填值完成预热。 |
| 当期成员 | 检查完整成员行及合法保存Feature/预测来源；缺feature按上述策略逐证券排除。入选后，前收定仓和本日交易域必须有合法可见证据，实际缺口保存到该证券，不借排名第k+1替代。 |
| 已持有或存在待结算量，即使退出成员池 | 继续检查公司行动、factor能力、估值和可卖量，Core照常生成退出意图。估值沿原显式stale政策保存价格日期与原因；没有可用估值或持仓行动未解释时保存BLOCKED，不能删仓。 |

首次进入候选域需要原保存Feature证明其真实预热及可用时钟，并需要前一session可见
native close；合法缺失的定仓参考保存NO_DECISION/MISSING_SIZING_REFERENCE，持仓不变。
交易日缺factor或native限价等必要证据时保存该证券阻塞和缺口，不制造成交。factor
只在实际上市的连续、可见原生session间核对变化；遇null不跨缺口解释、不补1，已有
持仓的必要能力缺口或未解释转换沿原BLOCKED。UNKNOWN和原行动blocks仍保留。
准入收据分别计pre_listing_null、listed_nonmember_gap、member_gap、held_gap；完整
行键及双端原生值/reason比较仍覆盖全部union，数值合格数量按所需域报告。

现有纯投影入口仅增加可选参数
`stock_market_from_batches(*, batches, universe, calendar, execution_rules=None,
membership_batch=None)`。两个新参数均缺省时精确保留原market_replay_v3；同时提供时，
消费原六份batch及既有原生PIT成员batch，产出market_replay_v4。新wire沿v3字段增加
`stock_execution_rules_ref,membership_ref,lifecycle_policy:"listing_member_position_v1"`，
成员原文加入已有source_evidence/coverage_bundle闭合，不重查Data。run v6显式只准入
该v4投影和同一规则ref，逐session需要的域仍由同一个Runtime及Ledger判定；保存原生
缺值及metadata，不为生命周期另外造一份行情或撮合器。

完成本次Runtime准入后，既有rules_index在同一调用内供私有Core planner与撮合复用。
周首调仓继续核对当次候选、定仓参考、账户版本和时钟，不重复全规则网格及来源身份准入；
公共Core独立调用仍完整校验规则闭包。该复用不写入保存wire，也不成为跨调用信任缓存。

首个完整CSI300短账户继续使用已有 native unadjusted 行情和行动证据策略。UNKNOWN、
未知行动及未解释 factor 转换按原政策阻塞。现金 EX 与 factor 的解释、送转增股及其
可卖日，分别在实际 native 日期、数量和来源齐全时另行设计和审阅；本候选不从价格
变化猜分红到账或新股上市日。上市前的合法原null按上述生命周期保留，不能补1或
复制首日；多年账户逐所需域报告真正缺口。短账户不必等待
未来全部公司行动完成，但其实际窗口的证据缺口必须如实结束并保存阻塞收据。

实现前先审本节API和数量语义，再做小合成边界检查：科创板200/201股买单、1股增持
和101股减持不报单、199股全可卖尾仓、500股仅100股可卖不得套尾仓例外，以及合法
200股申报后volume只支持199股的部分成交，以及现金只够199股时不提交200股买单。
再核对个体invalid排除后正常排名／不足k、未上市非成员null保持、上市成员矛盾、
退出池后持仓仍估值及合法预热不足。另核对主板100股整手、创业板150000股
和科创板50000股代理上限、两个费率变更日、未知板块及重叠／缺失规则在记账前失败。
通过后，在另获资源窗口的同一保存预测上做完整union短账户及保存／读取核对，证明
全成员先排名、实际入选科创板按其规则执行。多年 ML 和全历史账户另受各自数据与
资源验收限制；本节提交只代表可审的设计候选。

<a id="stock-bounded-v7-proposal"></a>
### 6.5 多年股票账户的窄引用输入与结果片（2026-10-06，draft，未实现）

本候选只为已有股票策略的多年工程测试限制输入驻留和序列化成本。固定源码
[`5d98d70`](https://github.com/sinnergarden/axiom-engine/blob/5d98d70eb4f13d88c263e4a2029f84e3e22e63a1/src/axiom_engine/runtime/backtest.py)
仍一次准入全部 fold/native evidence/market，结果内嵌完整 plan，loader 再验证该图；
只把输出按月保存不足以解决这些成本。候选新增一个小型输入 manifest、一个股票输入
source 和一个结果 sink，接入原 Runtime session 实现、Core planner、模拟成交、费用函数
及同一个 AccountLedger。以下签名和字段供父审；源码、5 GiB 长窗资源核验和多年账户
均未完成。实际时钟 shadow、SQLite、任意相位暂停和进程崩溃恢复仍按 §2.1 的后续边界。

#### 公共入口与 owner

```python
run_stock_backtest(manifest: BacktestRequest, *, source: StockInputSource,
                   sink: StockResultSink, block_sessions: int,
                   limits: dict) -> BacktestRun
audit_stock_backtest_source(manifest: BacktestRequest, *, source: StockInputSource,
                            block_sessions: int, limits: dict) -> dict
load_stock_backtest_projection(path, *, artifact_reader,
                               limits: dict) -> SavedRunProjection
```

三个入口由 Engine/Runtime owner 实现。artifact_reader 只读取调用方明确提供的本地
对象；普通 projection loader 的允许读取范围仅为小型 run/request/source_audit、
结果片及本次评价必需的小型配置/事件，不递归跟随大输入或训练父件。第一个入口只是原执行循环的组装，不能另写一套
按块撮合或账户核算。`audit_stock_backtest_source` 是独立只读的完整来源/数值准入入口，
不创建 ledger；启动 v7 也在创建 ledger 前调用同一审计实现。第三个入口只校验保存件并
读取评价所需业务输出。原 `run_backtest`、`save_backtest_run`、`load_backtest_run` 的
v1–v6 路径与保存身份保留；v7 保存仍可用原 exclusive-create 保存函数，不改写旧件。

Research 提供已经保存的中立 `StockPredictionFrame v2` OOS keyed rows、原
fold/model/feature/source refs 和 clocks；Data 提供固定原生事实及 metadata。
Engine 的 source 薄 adapter 只读这些固定输入，不查询供应商、不执行 Feature、fit 或
predict。训练 matrix、Label payload 和 booster 不进入 Engine。预测的物理存储及读取
接口由 [Research 的保存预测合同](05_axiom_research.md#stock-saved-fold-clock-contract)
和矩阵主路径决定；这里的 ArtifactRef 可定位既有父 manifest 内的对象，不要求另存
每 fold 的证据大图。Runtime 循环由一个 Engine owner 修改；接口冻结后 source 与
sink/投影可在各自文件并行实施，Core/Runtime 仍是唯一账户执行链，Qlib 不执行账户。

#### 小型 manifest 与准确引用形状

请求使用 `BacktestRequest`，精确字段为：

```text
{contract_version:"backtest_request_v7", request_ref, account_id,
 scope:{start_session,end_session,anchor_session,calendar,prediction_universe,
        execution_universe,supported_universe_ref},
 initial_account, portfolio_policy, profile_input, market_input, prediction_input,
 stock_action_policy, clock_policy, limitations}
```

calendar 固定有序 exchange sessions，包含初始前一 session anchor；初始账户沿本股票
路径的空持仓与正整数 CNY 分现金。portfolio_policy、stock_action_policy、时钟与
§6.4 的 Core `/3`、profile v2 实验规则相同。所有 ArtifactRef 精确采用现有
[P01 envelope](01_axiom_overview.md#32-ref-与-manifest-的最小要求)：
`{artifact_type,artifact_id,contract_version,manifest_uri,content_digest}`。
content_digest 校验引用对象的 canonical 内容；其 manifest 再绑定真实文件的字节
digest，不能把 Document identity、原 signal_run_ref 和文件字节 hash 混称一个身份。

| 输入段 | 精确字段与绑定 |
|---|---|
| profile_input | `{artifact,profile_ref,stock_execution_rules_ref,stock_fee_schedule_ref}`。artifact 定位原 `stock_daily_open_profile_v2`，profile_ref 等于该原文 Document identity；规则和费用 ref 与原 profile 内值逐字相同。完整小型配置在一次准入内读取并索引，不在每 fold 重复保存。 |
| market_input | `{contract_version:"stock_market_input_refs_v1",market_ref,model_snapshot_id,execution_snapshot_id,warmup_sessions,price_basis:"unadjusted",projection_version:"market_replay_v4",native_inputs}`。native_inputs 每项为 `{role,artifact,native_ref}`，role 仅为 `prediction_basis` 或 `execution`，同一原件可被两种用途引用而不复制文件。native_ref 是完整原 DataBatch identity；原 QuerySpec、Snapshot、purpose、cutoff、Reader version、单位、null/reason 仍由其闭包提供。 |
| prediction_input | `{contract_version:"stock_prediction_input_refs_v1",prediction_ref,frames}`。frames 每项为 `{fold_ref,fold_spec_ref,model_ref,feature_ref,signal_run_ref,fold_spec_artifact,model_metadata_artifact,prediction_artifact}`；三个 artifact 分别定位原 fold spec、原 model metadata 与原中立 v2 Frame。metadata 中的父引用可以保留，父训练 payload 不读取。frames 按原 OOS 顺序排列，无重叠、空档或缺失的严格前一 session。 |

已有保存 fold 若将 spec 嵌在 `stock_ml_fold_v2` 的 `definition.fold_spec`，
fold_spec_artifact 的 manifest_uri 可采用原本地 `fold.json#definition/fold_spec`；
这个 selector 只允许上述固定子对象路径。该 ArtifactRef 的 content_digest 仍等于原
fold_spec_ref，不能代替完整父 fold 身份。source 对原 wrapper 作有界流式扫描，另核
同目录 `manifest.json` 的 `files["fold.json"]` 字节 hash、wrapper 的 unsigned
content_digest、definition_ref 与原 fold_ref，并核对其 model/feature/signal refs
和请求中原 refs 一致。选中 spec 可作为小对象读取，未选中的训练输入闭包不会整树
decode，也不调用会递归载入训练父件的完整 Research fold loader。

原 canonical JSON 保存文件允许附带一个末尾 LF。对象内容身份仍按 canonical JSON
核验，文件字节 hash 包含这个 LF；两个 hash 分别保留，不修改原文件或重签 Signal。

market 的 execution 原件完整覆盖 §6.4 的状态、原价、限价、factor、PIT membership、
record/ex 两种公司行动读取及其不确定性。prediction_basis 只覆盖本次账户输入配对
所需的原生事实与既定预热，不把模型训练矩阵当执行行情。完整审计保留原双端值、单位、
可见时间、missing_reason、修订/观察/来源配对，以及 prediction.member 与原成员值的
比较。warmup_sessions 与交易 calendar 分开；预热不会推进账户。

native_inputs 与 frames 是小型引用表。日期取片是原对象的读取视图，不发布新的
SignalRun，不把部分 rows 冒充完整父 Frame/DataBatch 并沿用其 hash。若一个父对象
超过预算，source 必须已有受审的有界原文校验路径，否则在账本开始前拒绝；不能先
`json.loads` 完整大图再声称分块。Research/Data 的原文件与源格式不因这张引用表而重写。

#### 输入 source、两遍扫描与身份

```python
source.inventory(manifest) -> dict
source.iter_blocks(manifest, *, block_sessions: int,
                   read_budget: dict) -> Iterator[StockInputBlock]
sink.append(*, session: str, phase: str, rows: Iterator[tuple[str, dict]],
            committed_sequence: int, write_budget: dict) -> Iterator[ResultPartRef]
sink.finish(*, write_budget: dict) -> list[ResultPartRef]
```

inventory 仅读小型 manifest/文件描述表并检查文件尺寸，不打开、解压或解析 DataBatch、
预测或训练父 payload。它返回固定输入引用、文件字节数、声明行数和范围；实际行数、
范围及内容验证留给受预算的第一遍扫描。StockInputBlock 是 Engine 内部读取值，包含当前日期范围、原 market
行/metadata/事件及原 v2 预测行/父 header/时钟，保留其来源绑定。它不是新策略或
Research 产物格式。`block_sessions` 仅是正整数读取组织参数，拒 bool；相同父输入
按日或按月交付都必须产生相同原行与引用。

v7 limits 的精确字段为 `{max_folds,max_prediction_rows,max_market_rows,
max_input_bytes,max_read_bytes,max_block_bytes,max_result_part_bytes,
max_result_buffer_bytes,max_result_bytes}`，各值为正整数、拒 bool。
max_input_bytes 检查去重后的实际输入文件总量，fold 与两类行数分别累计核对；
max_result_bytes 同时用于总输出和评价投影物化前的总结果检查。
Runtime 在两遍读取前均将
`read_budget={max_read_bytes:limits.max_read_bytes,max_decoded_bytes:limits.max_block_bytes}`
传给 source。source 在读取分配前限制单次 byte buffer，并在解压/解码每次增长前检查
剩余预算；未知或不可信的展开尺寸必须用有界读取，不能先无上限 read/decompress/
decode 出整个对象或 StockInputBlock 后才拒绝。库存声明不代替实际增长计数。

Runtime 同样在输出产生和 sink 消费前应用
`write_budget={max_part_bytes:limits.max_result_part_bytes,
max_buffer_bytes:limits.max_result_buffer_bytes,max_total_bytes:limits.max_result_bytes}`。
rows 按原业务组名逐行迭代，不能先拼整个历史结果再交 sink。单片编码/写出与未提交
输出缓冲均受预算限制；空间不足时先封存已有有界片并回报 ResultPartRef，或对超过
上限的单行明确拒绝。sink 仅在文件已写出且字节/内容 digest 校验完成后回报提交，
随即释放该片的编码与行缓冲；Runtime 即时消费回报并 drain 后才继续拉取 rows，
不攒到整个 session 迭代结束再释放。finish 也遵守同一预算。预算是受控 byte/输出体积界限，
不是 Python 对象 RSS 保证，5 GiB 仍另测实际峰值。旧版本 limits 字段和语义不变。

第一遍在 ledger 创建前完整检查所有文件、所有 fold 与全部 union×session 键，包括
最后一块：身份/Query/purpose/PIT/时钟、原值/metadata/单位/投影、双端输入配对、
成员/上市生命周期、规则/费用覆盖、factor 相邻变化、公司行动及重复/冲突事件。
分片间保留前序事实以检验连续性，坏后块不能留到已经成交后才发现。该遍释放大表，
紧凑索引将第二遍实际读取片段的字节范围/row group/键范围及内容 digest 绑定到
原父引用和固定 header，保留审计计数与跨界必要状态；不能只存父 hash，导致每块
再次扫描整个父文件。source 薄读已绑定的 fold spec/model metadata/predictions，
不调用 Research 的 load_stock_ml_fold 递归加载训练闭包；序列化 PASS 不代替检查。
第二遍按原时钟执行，在使用每块前重核实际片段与上述索引。Core 始终接收同一全局
calendar/rule/source refs 及原 Signal header，不能把块内日期表或 delivery digest
替换进业务 context 而改变 ID。预取未来块不使其事实提前进入 Core；执行中发现
输入替换须终止，不能封成 COMPLETE。

identity_view 仅将上述已定义位置的 ArtifactRef 映射为
`{artifact_type,artifact_id,contract_version,content_digest}`，删除 manifest_uri，
保留其他全部字段和数组顺序；不递归删除证据正文中的来源或时间字段。
H 使用现有 canonical JSON 的 UTF-8 bytes 做 SHA256，保留 `sha256:` 前缀。
三个逻辑摘要及 run identity 精确为：

```text
market_ref = H(identity_view(market_input excluding market_ref))
prediction_ref = H(identity_view(prediction_input excluding prediction_ref))
request_ref = H(identity_view(request excluding request_ref))
run_id = H({request_ref,core_version:"axiom.stock_portfolio/3",
            runtime_version:"axiom.backtest/7",implementation_ref})
```

读取块大小、sink 分片大小、limits、墙钟日志与物理根目录均不进入逻辑 run_id。
订单继续 `run_id + ":order:" + global_order_index`，fill 继续该 order_id 的 `:fill:0`；
块边界不重置索引。输入 owner 重新发布原件、Query 或引用产生新输入身份，不属于
改变读取块大小。v7 内两种块大小必须逐字相同业务 ID；v6/v7 的 run identity 不同，
其比较须显式对应语义行，不能强求 order_id 字符串相同或改写旧 ID。

#### 同一账户状态与引用式保存

原 session 相位及事件顺序保持。跨块常驻同一个 ledger 的 cash、持仓/成本/可卖量、
pending T+1 lots、receivables、幂等键和 sequence，以及 Runtime 的 quotes/marks、
stale 日期/来源、record 权益、EX/PAY 状态、事件去重、原规则/费用索引、全局订单编号
和生命周期计数。不能每月重建账户再拼曲线。未解释 factor、池外持仓缺必需能力或
未知数量行动仍可保存 BLOCKED；分块不删股、不忽略行动，也不保证多年完成。

输出行的数值及提交仍归原 ledger/Runtime。sink 持有待写片，已封存片归不可变结果
文件；同一行不能同时成为两份长期历史副本。append/finish 回报的 ResultPartRef 是
释放凭据，Runtime 依据其各业务组 row_counts 和已提交前缀游标，drain 原
AccountLedger.fills/cash_ledger/position_ledger 及 Runtime 的 nav/positions/decisions/
orders 历史列表。只删除已确认写出的前缀；未确认行继续受统一待写缓冲预算约束。
不能只按 sequence 过滤，因为不同输出行可共享水位。写出或校验失败不 drain，也
不发布完整 run；保持原必要幂等/冲突记录、余额、持仓、T+1、应收及跨期权益状态。

全局 order_index、各组 produced/submitted/committed 游标、fill/order 数量和原各项
费用/turnover/未提交/未成交/不完整数量都使用独立累计量；每个新业务事件恰好累计
一次。NAV 的 running peak/max drawdown 也在原 session 提交时更新。编号、metrics
和最终核对不能再使用已 drain 的 len(list) 或扫描历史列表；这些是存储组织调整，
原 v1–v6 的公开列表/返回行为保持。

结果元组为 `backtest_run_v7/axiom.backtest/7`，run 精确字段为：

```text
{contract_version,run_id,account_id,status,request_manifest,request_ref,
 source_audit,source_audit_ref,signal_ref,market_ref,profile_ref,core_version,
 runtime_version,implementation_ref,committed_sequence,initial_nav_minor,
 final_account,stopped,lifecycle_admission,metrics,limitations,result_parts,
 account_events,account_events_ref,content_digest}
```

request_manifest 只保存上述小型请求，signal_ref 等于 prediction_ref；metrics、
final_account 和生命周期字段沿原 v6 业务义。原运行三元组仍为
`{run_id,content_digest,committed_sequence}`。
source_audit 精确字段为 `{contract_version:"stock_input_audit_v1",request_ref,
market_ref,prediction_ref,profile_ref,implementation_ref,counts,limitations}`，
source_audit_ref 是其 Document identity。成功返回才产生该结果，准入失败抛出明确
ContractError；counts 保存本次实际检查计数，不内嵌原大图。其 implementation_ref
必须是本次 run 的同一固定实现；它不成为跨调用免审凭据。

评价需要 record 权益及原现金行动的经济字段。为使普通 projection 不必读取大的
Data 父件，run 小头另保存 Engine 在完整准入中已生成的 account_events，其精确
字段为 `{contract_version:"stock_account_events_v1",request_ref,market_ref,profile_ref,
cash_dividends,source_refs,limitations}`。cash_dividends 逐字保存原准入现金行动，
包括范围内尚未 EX 的已知行动；source_refs 保留两份原 record/ex 行动输入的引用，
不携带原 native records、field_meta 或 coverage。account_events_ref 等于该对象的
Document identity，并由 run 的 content_digest 绑定。它是保存的账户行动视图，
完整数值来源检查仍由本次第一遍 source audit 完成。cash_actions、action_diagnostics
与 action_blocks 的实际数目记录于 source_audit.counts。

小事件对象和最终 run 小头均在序列化前检查 max_block_bytes，超限即拒绝，不先
组装巨大 Document；原大事件输入也不能因此免于受预算的完整第一遍校验。
普通 loader 核事件摘要、request/market/profile 绑定、行动字段/日期/原 refs 及
已保存 EX/PAY 关联，并把该小视图交给原 episode 算法。无完整小事件视图时明确拒绝
行动评价，不能从成交、应收或余额倒推 record 权益与未知 PAY。

`stock_dividend_scope(projection)` 沿用原函数签名，生成新的小型
`dividend_scope_v3`：精确字段为 `{contract_version,start_session,end_session,
knowledge_cutoff,universe,coverage,actions,source_refs,account_events_ref,limitations}`。
其 coverage 仍为 observed_records_only，actions 是保存现金行动中 record_session
落在账户范围内的原对象，cutoff 仍为 end_session 的 12:30:00Z。评价入口核其
account_events_ref 和全部经济字段与该投影一致；它不声称重新校验 native 来源，
不把 observed records 变为完整行动历史。原 v1/v2 scope 和旧 loader 字段保持。

ResultPartRef 精确为 `{artifact,part_index,start_session,end_session,
first_committed_sequence,last_committed_sequence,previous_part_digest,row_counts}`。
artifact 定位 `stock_backtest_result_part_v1`，其内容为
`{contract_version,run_id,part_index,rows,content_digest}`；rows 的精确键为
`nav,positions,decisions,orders,fills,cash_ledger,position_ledger,session_phases`。
前七组保留原保存行，session_phases 每项精确为
`{session,phase,committed_sequence}`。本增量的 phase 仅为 SESSION_COMMITTED 或
STOPPED_BEFORE_NAV，用于封存日末或阻断日原流水；不新增任意相位暂停接口。
part 内容的 content_digest 覆盖除自身之外的全部字段，artifact.content_digest 则
校验包含该字段的完整 Document。row_counts 对这些组逐一计数，part_index 从零连续，
首片 previous_part_digest 为 null，其后等于上一片 artifact.content_digest。
最后水位包括终止日已经提交但尚无 NAV 的原流水，不制造停止日 NAV。sink 只保存同一
ledger 产生的行，原 ledger 的必要幂等状态不随输出缓冲释放。

最终 manifest 只有在全部已产生结果片完整、顺序/字节/内容和水位闭合后才封存，
content_digest 覆盖其全部内容除自身；临时片不是完成账户或可恢复 checkpoint。
不同分片包装可改变 content_digest，但原业务行和逻辑 ID 不变。原 v1–v6 文件、
loader 分支、profile 及 Signal 身份不迁移、不补字段。

#### 保存投影、完整源审计及首个里程碑

普通 projection loader 只校验小型 run/request/source_audit 的内容与引用身份绑定、
结果片的顺序/内容/row_counts/水位，以及实际评价需要的小型 profile/规则/费用/
行动配置。输入的大 Data/预测对象及未消费的训练父件仅保留 refs，不递归读取、
hash 或解码；该读取边界也约束配置/事件中的父引用。结果片按同一有界 byte 预算
读取，核对 decision→intent→order→fill 的保存关联及小型配置可核对的费用。
它不重跑 planner、撮合或 ledger，不把已保存 source_audit 的内容绑定称为重新
完成数值来源审计，也不声称已检查 fill 原价与大原生输入的数值配对。需要原生值、
PIT、来源闭包或投影的完整检查时，显式调用独立 source audit；启动新 v7 的第一遍
完整安全准入仍在 ledger 创建前执行全部检查，不能用保存 PASS 省略。

物化 SavedRunProjection 前，从小型 run 声明和实际结果文件尺寸核对总结果预算、
row_counts 与必需配置体积，拒绝超限后才逐片有界解码；读取中继续核对实际累计量。
投影仍物化原指标所需业务行，独立测其 RSS；本增量不重写全部指标算法或把 byte
预算当 RSS 保证。SavedRunProjection 只含该 run 三元组及 refs、小型 calendar/
anchor/profile/行动配置，
以及已校验的 NAV、fills、positions、现金/持仓流水、decisions/orders。它不是伪造的
v6 BacktestRun。v2/v3 共享同一份投影，复用原指标实现；episodes、集中度和 execution
trace 所需业务行保留，缺字段仍按原 null/状态解释。完整行情、训练证据和所有预测
不进入评价投影，也不由 UI 补算。投影可供读取 BLOCKED 的诊断，但 v2/v3 仍要求
COMPLETE 账户，不把阻断期间的部分收益当完整评价；原不足年/缺值语义保留。
原评价/显示引用须精确绑定新 run 三元组。评价入口保持原参数签名，仅增加对该
Engine loader 产出的投影的准入，调用方式为：

```python
projection = load_stock_backtest_projection(path, artifact_reader=reader, limits=limits)
v2 = evaluate_backtest(projection, benchmark=benchmark, spec=v2_spec,
                       dividend_scope=scope)
v3 = evaluate_saved_analysis(projection, v2, benchmarks=benchmarks, spec=v3_spec)
```

| 实施项 | Engine 净工时估算 | 必要验收 |
|---|---:|---|
| 小合同和身份固定 | 1–2h | 父审精确字段、source 交接与旧版本边界 |
| source、完整准入与日期/成员/事件索引 | 3–5h | 坏末块先拒绝，键/值/来源/时钟及跨界检查 |
| 原循环接入与 sink | 3–5h | 单 ledger、全局 ID/sequence、跨块状态及终止片 |
| saved loader 与评价投影 | 1–2h | 验片与业务关联，v2/v3 共用小投影 |
| 必要回归、独审和修订 | 4–6h | 等价边界、原保存件不变及独立小资源核验 |

首个可审小里程碑约 6–10h 净工作：固定小合成输入的单块/两块交付跨月界、周决策
和 T+1，逐字段核对业务 ID、提交/成交/费用、cash/position/NAV/sequence，并证明坏
最后输入块在 ledger 创建前拒绝、坏结果尾片被 loader 拒绝。另检查压缩展开和 sink
缓冲超限在增长前拒绝、普通 projection 不打开大父件、跨片 drain 后业务 ID/metrics
不变，以及失败写出不提前释放未提交行。完整候选估算 12–20h，
不含 Research/Data 输入准备、父审等待、资源窗口或多年实际运行。其后补 record/
EX/PAY、factor/null、池外持仓、现金/STAR 数量约束与 BLOCKED 边界，再在另获窗口
只读复用原短输入保存独立 v7 对照；v6/v7 按原 session、全局订单序号、security/side
及原 event_id 对应，并建立 run 衍生 order/fill ID 的显式映射。费用/现金/NAV/水位须
exact，来源、数量和 reason 不豁免。独审、draft PR 父审及 merge 后方可申请多年执行窗口。原输入无法有界校验或
历史规则/行动覆盖不足会延长工期或导致真实 BLOCKED，不能用预算估算替代验收。

### 6.6 已保存股票输入的一次准入与顺序账户复用 <a id="64-已保存股票输入的一次准入与顺序账户复用"></a>

股票 v7 可将固定输入完整准入一次，捕获为 `AdmittedStockInputs`，供多个账户顺序消费。
账户仍由唯一 Core/Runtime/SimBroker 执行，各自拥有 ledger、sink、account 与 run 身份。
实现见 [Engine PR21](https://github.com/sinnergarden/axiom-engine/pull/21) 与
[PR22](https://github.com/sinnergarden/axiom-engine/pull/22)，均已合并；Qlib 不承担账户执行。

```python
admit_stock_inputs(manifest: BacktestRequest, *, source: StockInputSource,
                   block_sessions: int, limits: dict,
                   max_owned_bytes: int) -> AdmittedStockInputs
StockInputSource(*, scalar_cache_bytes=0, file_parse_mode="stream",
                 max_file_parse_bytes=None, max_file_parse_rss_bytes=None,
                 max_file_parse_spool_bytes=None, max_file_parse_seconds=120)
```

返回对象作为 `run_stock_backtest(manifest, *, source, sink, block_sessions, limits)` 的
`source` 使用，`block_sessions` 与导入一致；支持 `with`/`close()`。
对象仅由创建 PID 顺序使用，所有公开入口在触锁或存储前拒绝异 PID，包括 fork 继承；
并发执行及执行期间 close 拒绝。可变解码副本不影响后续账户。

复用比较既有 manifest 的逻辑 ArtifactRef；除 `request_ref`、`account_id`、
`initial_account` 与 `portfolio_policy.top_k` 外，其余全部字段保持一致。
URI 不改变逻辑输入身份；复用读取已捕获的字节，不转读新路径。
这是进程内能力，不新增公开 input ref、receipt 或持久 validated 标记。

| 变更 | 处理 |
|---|---|
| account_id、正整数初始现金、合法 TopK | 可复用；初始持仓为空；资金与 k 绑定各自请求/run |
| profile、费用、滑点、UNKNOWN、规则、clock/action policy | 重新准入 |
| universe、calendar、anchor、区间、warmup、scope | 重新准入 |
| Snapshot、native/query/projection、fold/model/feature/prediction refs | 重新准入 |
| 其余 policy、合同/实现版本或其他 manifest 字段 | 重新准入或按原合同拒绝；未定义参数拒绝 |

导入保留完整原 file/content SHA、canonical JSON、字段/单位、时钟、PIT 与全范围行审核；
捕获成功前不创建账户。私有有界存储在每次写入前检查 `max_owned_bytes`，无公开路径或写入口；
导入后释放原索引，账户只解码当前块，原 input/fold/row/result 限额继续生效。
canonical decoded 预算含 globals/块/索引/decoder 预留，是字节核算，不是 Python RSS。
`source.statistics` 记录原扫描与选中行消费；`inputs.statistics` 分开记录 audit/capture 和复用。

默认 `file_parse_mode="stream"`、`scalar_cache_bytes=0`；标量缓存仅显式 opt-in。
显式 `file_parse_mode="cjson"` 仅处理原 native Data JSON，去重后一次一物理文件；
profile/fold/manifest/model/prediction 保留 stream。调用者必须提供文件、进程树 RSS、
累计私有 spool 三个正整数预算（拒 bool），helper 秒超时也为正整数，默认 120 秒。
RSS 包含 owner/helper 子树，spool 与 owned quota 独立；不把 decoded 预算当 RSS 或扩账户限额。

CJSON helper 只解析及验证，保留完整 finite/Unknown/depth<=128、重复/键序、canonical 字节相等
和全部原业务 gate；path/fd/stat 与文件 cap 在整读前复核。选中行仅写私有 spool，不发新 Data ref。
尺寸、规划 RSS 或监控能力不足时，只能在 helper 启动前明确选择 stream。
helper 已启动后的语法、身份、业务、MemoryError、RSS、超时或 spool 失败均停止准入，
关闭 helper/fd 并丢弃未提交存储，不返回 handle、不创建账户，也不自动重跑 stream。
RSS 估算与采样不是逐分配硬上界；成功后释放整图，父进程保留有界索引并建立 owned handle。

固定 `2842ca9` 的有界真实验收：完整 cold admission 43.22 秒，9 个 native 全部 CJSON，
17 个非 native 按约定 stream，观察峰值树 RSS 1.88 GiB。Top5/Top3 复用同 Signal、同资金，
得到不同账户；全部业务 header/八组行对旧保存 oracle exact（仅约定 provenance/ID 归一）。
audit/capture 各一次，账户阶段原输入重开为零；无 Data/Research/Feature/fit/predict/supplier
调用，原输入、旧结果与源码不变，handles/helpers 已关闭。这只证明该有界窗口。
benchmark 口径、合成检查和逐文件计时见 [软件测试说明](https://github.com/sinnergarden/axiom-engine/blob/63b032cf5158a2abfc28ed87eef73acc64665b4f/tools/stock_input_benchmarks.md)。

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
### 11.3 已保存账户的有界分析评价（已实现并有界验收）

本节只为一个已有、完整的 BacktestRun 与同一 run 绑定的已保存 v2 评价增加新
`evaluation_spec_v3 / evaluation_report_v3 / axiom.evaluation/3`。旧账户、旧 v1/v2
spec/report、金额分桶、来源与实验登记不覆写；新报告复制已核验的 v2 指标和限制，
再保存下述新增事实。新公共入口固定为
`analysis_evaluation_spec(*, risk_free)`、
`evaluate_saved_analysis(run: BacktestRun, base_report: EvaluationReport, *,
benchmarks: dict[str, BenchmarkSeries | None], spec: EvaluationSpec) -> EvaluationReport`，
只消费已保存的账户/
评价及独立的真实基准输入；`save_backtest_evaluation` 与
`load_backtest_evaluation` 继续负责独立新路径保存和按版本只读验证。
[Engine PR #9](https://github.com/sinnergarden/axiom-engine/pull/9) 已实现并合并。

`benchmarks` 精确包含 `CSI300/SSE_COMPOSITE/NASDAQ100` 三键；CSI300 必须与
base_report 的原 `benchmark_ref/benchmark_input` 完全一致，不能静默替换原评价基准。
SSE_COMPOSITE 使用下文已准入的 Data 固定原生输入；NASDAQ100 尚无已核来源，
显式传 None，输出 SOURCE_UNAVAILABLE。新原生指数输入继续由 Data owner 固定
来源合同后交接，不让 UI/Research 查询供应商。
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
订单未成交时 fill_ids=[]，旧股票/ETF trace的`requested_quantity`来自原order.quantity；
v6取原order.requested_quantity，并新增原order的`submitted_quantity/unsubmitted_quantity`，
与原filled/unfilled一并保存五段数量，校验requested=submitted+unsubmitted及
submitted=filled+unfilled。已有旧格式报告仍按原wire读取，不推导或补写新字段。
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
这两个增量入口已完成父审、源码独立复核与定向验收。

**上证事后比较最小准入（2026-10-05，已实现并有界验收）。** Data 已交接
`benchmark_daily` 原生保存 DataBatch（仅 close），证券 `000001.SH`、单位
`index points`、原 `series_kind=price_index`，不是全收益指数；独立新观察 Snapshot、
`operational_pit_v1`、`historical_exploration` 和共同观察 cutoff C 保留原值。
它不能通过 CSI300 的旧 same-Snapshot/历史 cutoff 合同重新标记为策略当时已知。

准确最小入口为 `read_sse_benchmark(native_path, *, receipt, run_key)`，其中 receipt
是 Data 的完整固定 handoff，run_key 为其已登记的账户条目；以及无 I/O 工厂
`retrospective_sse_benchmark(*, native_batch_text, receipt, run_key)`。两者返回现有
`BenchmarkSeries` 类承载的新合同 `retrospective_benchmark_v1`：原生 UTF-8 文本、
byte SHA/长度、完整 receipt/ref、原 Snapshot/query/C 与每条 close 的原日期、
`usable_from`、missing_reason/provenance 均进身份。公共 loader 只读固定文件并验证
receipt 中 byte ref；不查询 Reader 或供应商、不改写 Data 原生 payload。

准入检查 close 单位、唯一完整 query 键、timezone-aware 原收据/usable_from≤C、
当前观察政策/用途、原价无 adjustment_anchor 的 query、receipt 的
domain/snapshot_id/contract_id/reader_version 与 batch context 相等、原始行与逐键
metadata。C 可以晚于账户交易日期，必须披露为
当前观察的事后对照。receipt 中 run 三元组/首末日期/前 anchor 必须对应所消费的
原 v2；CSI300 仍逐字绑定原 v2输入，两个账户仍只读。新增 SSE input/ref 后另保存
v3 报告；旧 v3（SSE=None）、旧 v1/v2 均可加载，不改旧报告或身份。

SSE 元数据明确 CNY 成分价格指数、Asia/Shanghai、本地 session 与观察 C。精确原生
日期对齐，不 forward-fill/asof；缺边界/缺价为 null。使用原账户保存累计收益计算
事后价格指数相对财富，UI 不计算收益。同图所需 `benchmark_cumulative_return`
由 Engine 同时保存于原生与账户日期投影点，值为 `normalized_index - 1`，沿用同一
anchor 与 null 规则；旧 v3 无该字段仍可读，UI 明确使用净值指数模式或不可用，不补公式。
Nasdaq100 继续 `SOURCE_UNAVAILABLE`，整体
`PARTIAL`；来源和许可未核准前没有新准入，也没有原币/FX 数据的替代造数。

Data 显示投影消费另走 `build_fill_display(run, *, display)` 与独立保存/加载入口，
消费 [Data §7.3.5 固定设计](https://github.com/sinnergarden/axiom-docs/blob/b36f6a75e0a55c1c407026e38f3704485a22d1fb/docs/design/02_axiom_data.md) 的
`review_display_v1`；对应章节合入 main 后归回相对入口。准确入口如下：

```python
display = read_review_display(directory, *, manifest_sha256=receipt_hash)
report = build_fill_display(run, *, display=display)
save_fill_display(report, new_path)
report = load_fill_display(new_path)
```

`read_review_display` 仅委托 Data 公共 `load_review_display` 检查 manifest 与其所列
文件的原字节 SHA/长度，返回 Engine 的 `SavedReviewDisplay`；不调用 Reader、供应商
或 transform。`display_ref=sha256:<manifest 原字节 SHA>`，manifest 原 UTF-8 文本与
文件 refs 保留为绑定证据。build 使用 `ohlcv.records` 的唯一 `(security_id, session)`、
`native_open` 与 `display_scale`，并消费 `field_meta.native_open.unit`、
`field_meta.open.unit`、`field_meta.display_scale.by_key` 的原因和原生 provenance。
完整跨度与末日 A 来自 `context.derivation.price_query.sessions` 与
`context.anchor_session`；共同 C 为 `context.knowledge_cutoff`，用途必须为
`retrospective_review`，原价基准为 `unadjusted`，显示基准为
`common_anchor_adjusted_v1`。Data context 固定 Snapshot；不能以当前默认 Snapshot 替代。

Data 实际 multiplier 保存为 float64；Engine 将这一**已保存标量**用
`Decimal(str(display_scale))` 编码，40 位 ROUND_HALF_UP 下乘实际 `fill.price`，
不重新求 `factor(t)/factor(A)`。`CNY/share` 或 `CNY/fund unit` 分别须与保存账户的
股票或 ETF 单位合同一致，且 `native_open` 与原 `fill.reference_open` 一致；不一致
时坐标 null，保留缺行、缺因子、单位不符、原价不符等明确原因。对已知单位替换，
仅使用 Data 保存 `fund_share_conversions` 和账户原事件的显式
`new_price_basis_session`；缺失或不一致时相关新单位坐标 null，不从价格、effective_date
或下一交易日推断。

独立结果合同 `fill_display_report_v1`/`axiom.fill_display/1` 的身份绑定
run 三元组、Data display_ref、消费事实 ref、实现版本；内容保存 manifest 原字节文本、
完整原 fill、对应行的原生 open/scale/单位/provenance 与显式单位事件证据，以及
`display_price`、Decimal multiplier、status/reason。仅保存所消费的行事实，完整 OHLCV
仍由 manifest 文件 ref 绑定，不重复内嵌到结果。save 拒绝冲突覆盖；loader 仅校验
合同、ref/hash、链接与保存字段，不读 Data 或重算坐标。原 run、fill.price/fee/cash/
positions/NAV 及身份保持不变，显示不能成为决策或模型输入。

**本轮完成边界（2026-10-05）。** 显示消费
[Engine PR #10](https://github.com/sinnergarden/axiom-engine/pull/10) 与上证比较/基准收益百分比
[Engine PR #11](https://github.com/sinnergarden/axiom-engine/pull/11) 均已父审、独立 review 并合并。
最终联合验收固定源码
[`023c001`](https://github.com/sinnergarden/axiom-engine/commit/023c001b2f7ce9332168780761212f5be87d3e83)
和 implementation_ref `sha256:6cf5a0b8886270634b6f0a907c3e7385f4196d7a28d728c28fc9492ae41f1605`。
合成边界与 19 项相关回归通过；这是工程合同验证，不是收益有效性结论。
另对**已保存真实账户**只读验收：ETF 长账户 1762 sessions、280/280 原 fill 坐标可用；
当前 UI 股票 Jan 账户 22 sessions、40/40 原 fill 坐标可用。股票新结果绑定当前账户原
run 三元组，Data 保存原生输入经 owner 核对等价后给出独立 consumer binding；不替换
旧账户或旧报告 ref。两组 CSI300/SSE 比较均 COMPLETE，NASDAQ100 为
SOURCE_UNAVAILABLE，总报告 PARTIAL。原 run、v2 评价、Data 显示及基准输入的
SHA/mtime/大小全部不变，旧评价指标与原账本值原样保留；验收禁止 Data 查询/transform、
账户执行、旧 evaluator 和 loader 指标/坐标重算。新产物独立保存，旧 v3 未覆写。
UI/Research 只读消费这些 owner 保存值；最终像素与用户复验另由其 owner 验收。

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


## 16. M1：raw／derived 保存输入与同一账户路径（2026-10-08）

适用候选：Engine 合并接线候选 [`defc3dd42a81d47ba407edee7423d52840f2a32d`](https://github.com/sinnergarden/axiom-engine/commit/defc3dd42a81d47ba407edee7423d52840f2a32d)，基于已审 A `a59f3b4`。前一 `70b1eee` 的实际行数和 context 生命周期两项 P1 已通过集中复核；本次统一交付批量收益 API、typed LabelSpec v2 与保存 clock 降级修复。28 项定向测试（1.85 秒）及实际 Research 合同／两个合成 fold 的真实 Core 入口接线通过。7 项 native 测试仍缺 Data 包；集中复审、Research 真实长窗口和 Data native 联合验收仍待完成。

### 16.1 小型引用输入

现有 `BacktestRequest` 的 `backtest_request_v7` 继续使用同一 Core planner、SimBroker、费用、现金、股份整手、T+1、corporate-action 处理和账户 ledger。新增内层 `stock_prediction_input_refs_v2`，精确字段仍为 `contract_version/prediction_ref/frames`，每个 frame 显式声明 kind。旧 `stock_prediction_input_refs_v1` 原路径保留。

raw frame 精确字段：

```text
kind="raw" fold_ref fold_spec_ref model_ref feature_ref signal_run_ref
fold_spec_artifact model_metadata_artifact prediction_artifact
```

derived frame 精确字段：

```text
kind="derived" signal_run_ref signal_plan_ref score_ref implementation_ref
signal_stage signal_artifact parent_inputs
```

`parent_inputs` 是 alias → 上述完整 raw frame binding，绑定真实 model／fold／prediction 原件；本增量没有递归 Derived 执行框架。Derived 的小型绑定同时冻结 plan／score／implementation refs 和输出 stage，供保存结果 loader 不重开大 Signal 文件也能核对实际 trace。`prediction_ref` 和 request_ref 的 logical identity 仅排除这些已知 ArtifactRef 位置的 manifest_uri，包括真实父 raw artifacts；业务字段和 refs 全部保留。

公开 Runtime 入口保持原签名：

```python
admit_stock_market_inputs(spec, *, source, block_sessions, limits, max_market_bytes)
bind_stock_prediction_inputs(market, request, *, source, limits, max_signal_bytes)
run_stock_backtest(manifest, *, source, sink, block_sessions, limits)
load_stock_backtest_projection(path, *, artifact_reader, limits)
```

Research 负责已保存预测及 SignalPlan 生成和保存；Runtime 校验完整 raw/derived 原件 SHA256、model／fold／LabelSpec／训练归一化链接、原始 session grid 和真实父 refs。派生分数、validity、来源与最大依赖 clock 在准入时逐 session 用同一 Core 数学核验后，账户直接消费保存分数。对多个 portfolio/资金配置，已准入 market／Signal owner 只保留一份 invocation-local 私有数据；每账户独立执行和保存。禁用 supplier、feature build、fit、predict 均不影响此路径。

### 16.2 时钟、Data 成员与预算

v7 此增量仍使用明确 `stock_prediction_clock_policy_v1`：Feature cutoff 当地 20:30、inference cutoff 21:00、下一 exchange session 08:55 决策、open 执行，declared_simulation。中立 Core 的一般 aware 时点不等于 Runtime 支持其他账户时钟；其他政策未实现时拒绝，旧 v2 不放宽。

每个 Derived context reference 的 member 和 `available_at` 必须与准入的 Data membership／原 `usable_from` 完全一致；`source_refs=[该原 membership native_ref]`。缺原 availability、猜测 membership 时间或伪造 source 均在账户启动前拒绝。完整参考截面包含 excluded 成员，不能为省预算删掉依赖。

所有真实父 fold／model／prediction、派生 output artifacts 和原 descriptor 均纳入 inventory/read/row 限额。`max_prediction_rows` 包含去重的原父 rows 和 Derived rows，`max_folds` 包含去重后真实 raw bindings。新引用 envelope 不含可信 OOS 行数时，预扫 `declared_rows.prediction_rows=null` 表示待原有有界扫描确定；不是零行，也不按每个 fold 乘全日历。准入以原 fold OOS scope 限制索引增长，扫描同一原文件一次后填入实际计数；两个不重叠 fold 共 18 行可在 18 行限额下准入，不因虚构 36 行上界拒绝。此修正不增加全量读取或提升 caller 限额。

完整 Derived header／context 的 decoded quota 在原件准入时计入，深不可变的逐日 reference/member 索引另在构建前计费。普通 source 的全 context 校验一次，逐日仅校验原行与相应索引，首次消费各日用既有 Core 数学校验真实父分数；同次 source 后续消费保留文件不变和当日 span 检查，不再重建全范围 context。market+bind 与 combined admit 也走该准入逻辑：私有文件仅保存一条完整原 Derived 元数据记录，账户的 offset 列表不包含它；小 globals 保存 SignalRef→小 header，逐日块只保存 `{session, signal_ref, rows}`。账户按 ref 找小 header，不解码完整 context，不再逐日复制它。byte／decoded／index 限额和 source 关闭、PID、exclusive lease、borrow 保护继续生效。所有 h、Feature 宽度、TopK、weights 和既有 CS 参数均由明确输入决定，示例规模不成为生产配置。

### 16.3 Trace 与保存读取

股票数量 planner 仍是 `axiom.stock_portfolio/3`，该增量只扩展输入和 trace。旧 v2 的 prediction_clock 字段保持原样。v3/derived trace 为 `stock_signal_clock_v2`：

| 公共字段 | 每种输入的真实绑定 |
|---|---|
| `contract_version/kind/clock_basis/feature_knowledge_cutoff/inference_cutoff/signal_stage` | raw／derived 明确区分；原账户 clock 与 stage |
| raw 附加字段 | `model_ref/fold_spec_ref/simulated_model_available_at/label_spec_ref` |
| derived 附加字段 | `parent_signal_refs/signal_plan_ref/score_ref/implementation_ref`；不添加虚构单 model ref |

新输入合同保存 `stock_input_audit_v2`：原 audit 的 `contract_version/request_ref/market_ref/prediction_ref/profile_ref/implementation_ref/counts/limitations` 加上 `prediction_targets`。该小型 map 为真实原 raw `signal_run_ref → label_spec_ref`，包含去重 Derived 父；原 raw v2 无显式目标时存 null。map 在原件准入时冻结，key 必须与 request 中完整 raw bindings 一致。旧 input refs v1 继续保存和读取原 `stock_input_audit_v1` 字段。

保存 loader 将 trace refs 与 request 的小型 frame binding 核对。已准入 `prediction_targets[signal_ref]` 非 null 时，强制 raw 决策声明 `stock_signal_clock_v2`，并将其 `label_spec_ref` 与该真实目标相等比较；不能由待验 trace 的版本自行选择是否核验目标。错误目标重新签名后再删除、替换或降级 clock version 仍拒绝；只检查 SHA256 格式不足以通过。它继续核对决策 → intent → order → fill／实际费用／cash 和 position ledger。只读取已保存 run、结果 parts 和小型 profile；不重开 Research 训练、预测、大 native Data，不重新执行账户。删除原 Signal／model／fold 文件后该核验仍有效。公共结果目录保持账户独立，旧保存账户与结果不改写。

合成验收包括非五日 h、不同 Feature 宽度、原 typed plan 语义身份、key 乱序、inner/outer join、missing/constant、excluded clock 的微秒边界、错误 units/stage/weights、真实父 ref 绑定、伪造 Derived score／membership 拒绝、同一 Signal 的 Top3/Top5 以及 source／owner 路径精确结果一致。真实预测接入和长窗口证据由 Research 与资源窗口另行记录，不能以这些合成回归替代。
