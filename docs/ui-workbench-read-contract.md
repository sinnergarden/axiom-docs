# 首版 UI 公共读取与联调

2026-10-05 · 当前线上用户验收未通过，已授权集中整改并今晚重新验收。先交主协调亲审整页设计，再实施新 PR；当前线上保持，后续统一通过 https://sinnergarden.github.io/axiom-ui/ 交付。设计依据为 [PRD](design/08_axiom_ui_research_prd_draft.md)与 [整页交互](design/06_axiom_ui.md#8-本轮整页交互与视觉规范)；职责仅引用 [唯一模块边界](https://github.com/sinnergarden/axiom-docs/blob/c22f49342b415290abc7d45d438e4d58013a1c45/docs/design/01_axiom_overview.md#module-boundaries)。本页记录消费方式，不另维护职责表、业务字段表或统计公式。

## Owner 合同与读取入口

Research 的字段与过滤语义以 [Research 主章实验记录合同](design/05_axiom_research.md#experiment-records) 为准。UI 调用 `ExperimentReader(index_path).index()` 读取问题→不可变版本→运行和整理状态，使用 `compare_versions` 读取已声明变化及保存参数/输入差异。收藏、搁置和标签只在本地展示/筛选，不写 Research 业务状态。未运行、失败、阻断或未载入账户结果均保留入口，不生成 Engine run_id、假设或零指标。默认导航沿 owner 的 saved_run_ref 聚合、registration_history 保留登记修订，回测数和登记数分别读 owner counts；运行收藏/搁置按组读取，不因更换评价多算一次回测。旧 `load_rotation_experiment(path)` 只作明确提供的冻结实验验证，不能替代新的问题说明。

Engine 的 [P10 主合同](design/04_axiom_trade.md#daily-evaluation) 定义评价与统计口径。`load_backtest_run(path)` 和 `load_backtest_evaluation(path)` 均仅读取并校验保存结果，UI 不调用执行、评价或保存入口。评价逐原值绑定 `input_run_ref` 的 run_id/content_digest/committed_sequence，以及 signal/market/profile refs；逐 session NAV、水位和成交关联不能混用。Research 索引关联也逐值核对，索引 URI 不自动跟随读取。基准必须保留价格指数不含分红说明，月份 partial/null 与已知/未知分红范围分别标示；不足分布门槛仅展示 owner 逐段值。

UI 同入口兼容 v1 与 [多年评价 v2](design/04_axiom_trade.md#long-history-evaluation)。v2 读取保存的年化区间与账户/沪深300 CAGR、累计收益、同区间最大回撤；保留累计收益展示，年化值及其不可用原因分别按 owner 原值格式化。v1 不补年化字段；短跨度或边界缺失的 null 不填零，也不因报告 COMPLETE、局部月或持仓段资格推断年化可用。窗口选择仍只控制保存点展示，年化区间保持原报告归属；基准仍为不含分红的价格指数。历史候选保存件只作接口测试并显式标候选，正式展示绑定父任务指定的最终 Engine 身份与文件，页面验收单独登记；UI 不计算 CAGR、年化回撤或 Sharpe，新增风险分析须读新评价保存值。具体字段、时钟与公式均只引用 Trade 主章，本页不另维护。

账户公共 loader 同入口兼容 `backtest_run_v1/v2/v3`；v2 消费差异只引用 [ETF 份额拆分主合同](design/04_axiom_trade.md#etf-unit-split-application-proposal)，v3 股票消费只引用 [Trade §6.1](design/04_axiom_trade.md#stock-daily-observed-minimal)。UI 原样保留保存的 `unit_split_applications`、position `mark_basis_event_id` 及 order `announced_suspension_event_ids`，连同固定计划事件与来源在账户变化/持仓/委托详情展示；只将事件 source_refs 对应的已保存 fund_share_conversions 原生 source_evidence 原样带入折叠详情，保留 Snapshot、EventQuery cutoff/PIT 与逐键元数据，不扩展其他市场输入；应用日期可定位保存点，但拆分不是买卖成交，不新增 fill、B/S 标记、权益、复权价或指标。`APPLIED` 是 Runtime 模型应用状态，不改 issuer 的 planned/implemented、not_stated/null 或原始 Data 状态；停牌/缺价类型始终按最终 owner 状态与证据显示，不由缺行、因子或旧样本推断。v1 不补事件字段。明确 synthetic 的 1:5/持有人 ceil 保存件只用于 Reader 与显示验收；真实长期展示绑定固定最终账户、评价、Research 登记和同 Snapshot OHLCV，视觉/用户验收独立；不重跑、不算权益、不修正 owner 产物。

股票 ML 尚无账户结果时，仍用同一 Research 实验索引列出已有登记；调用方显式提供目录，经 `load_stock_ml_experiment` 与 `load_stock_model` 公共 Reader 验证后，按登记中的 StockMLExperiment、模型、信号及证据原值引用绑定研究阶段面板，不跟随索引 URI。只展示 owner 保存的 fit cutoff、声明输入/预测 session 窗口、Feature ID/版本、标签成熟与标准化语义、逐日 IC/RankIC/有效及排除配对、模型配置与限制；相关均值、实际成熟训练窗口及耗时只有 owner 公共输出提供才显示，否则标未提供，不从逐日值或运行时间计算。股票账户原状态与原因保持未执行/阻断，研究登记 COMPLETE 不代表账户完成；无 BacktestRun 时没有净值、成交、账户收益或账户对照，不把预测分数当收益率，不训练、执行特征、采集或另做回测。该面板仅消费 [Research 主章](design/05_axiom_research.md) 的已保存产物，缺少公开读取形状由主协调向 owner 对齐，本页不另造业务合同。

股票阶段面板可显式附加保存的 `stock_stage_report_v1`，消费只引用 [Research §4.6](design/05_axiom_research.md#stock-saved-stage-report-proposal)。经 `load_stock_stage_report(path)` 公共 Reader 校验后，将全部六个 input_refs 与当前已载入的 StockMLExperiment 和 Research 登记逐值绑定；不匹配或重复输入拒绝附着，不跟随索引或 receipt URI。只格式化 owner 保存的训练声明/实际窗口及规模、IC/RankIC 有效 session 数与均值、各模式/状态/seconds 和来源；缺报告保留旧“未提供”行为，null 不填零，REUSED_NOT_EXECUTED 不算冷跑，继承的 Feature/Qlib 冷构建单列来源，不代表当前模型冷训练；build/total 不相加，整体 receipt 的内存/规模不摊到各阶段，不计算 ICIR 或吞吐预测。

股票账户沿既有 `load_backtest_run` 和 `load_backtest_evaluation` 显式路径接入已保存 `backtest_run_v3` / evaluation v2；执行资格、两类时钟、状态政策、税费与现金行动只引用 [Trade 股票主合同](design/04_axiom_trade.md#stock-daily-observed-minimal)。保留 quantity_unit=shares、price_unit=CNY/share（显示股、元/股）、预测全 union 与深圳执行资格子集、模型/执行 Snapshot 分列，以及 strict UNKNOWN 拒单和显式股票日线事后近似两份结果的身份与限制；不沿用 ETF 近似/份额标签，不重算费用、收益或 CAGR。已有实际账户且 Research 登记按原值关联后，当前账户状态与结果取自该保存 run/登记，模型 manifest 的旧 account_status 只作为当时研究阶段的历史证据；无 BacktestRun 的旧行为与 ETF v1/v2 保持。

股票原生证据经 Engine 公共 loader 完整校验后再投影；页面仅保存显示需要的行情、逐键元数据、上下文和引用，不嵌入全 coverage 表、压缩 payload 或完整非显示批次。OHLCV 可直接使用该 run 已保存的原生 market_daily 事实，保留原完整 DataBatch reference、Query/PIT/cutoff/字段单位与选中点来源，明确它是显示投影而非重新认定的完整批次；不查 Data，不跟随 URI，不给未提供的高低价造 K 线。评价与公司行动完整证据仍由原 evaluation/run 引用追溯；其保存指标、cash action/诊断和缺失限制保留，不因省略大表推断完整性。

股票 v3 费用读取原保存组件，tax_minor 是 stamp_tax_minor 别名，不重复相加；非实施行动诊断仍保留，不解释为已实施现金/数量事件。读取合同与最终视图完成分别按[当前交付](current-delivery.md)记录。

Data 沿用 [Data 公共 Reader](design/02_axiom_data.md) 与 [P12](design/06_axiom_ui.md) 薄投影。UI 接受调用方已从公共 Reader 取得的 `DataBatch(records, field_meta, context)`，不扫描业务根或隐式 Query。原执行 Query 加读 high/low 时，Snapshot、Query 其他语义、reader version、单位、价格口径和共同字段逐键 provenance 必须复现原 DataBatch digest；不能用 current 或新事实解释旧运行。原冻结批次已有完整 OHLCV 时直接复用并核验原 reference，无需新查询。ETF 原生量为 `volume_units`（fund units），原价单位 CNY/fund unit；股票原生量为 `volume_shares`（shares），原价单位 CNY/share。没有 high/low 时显示明确命名的保存 close/volume 与 K 线不可用，不构造蜡烛或将委托画成成交。

## 本轮 UI 读取需求与 Owner 对齐

以下是消费需求，准确 shape、版本和保存身份以对应 Owner 主章为准；不在本页创造新字段权威或私有 sidecar。

- **Data 薄显示事实：**固定证券中文名称/代码及身份范围；调整后 OHLCV 与未复权切换、价格单位/口径、锚点、knowledge cutoff、source refs；事件和原成交价在同一显示口径的固定映射。UI 只渲染公共投影/映射，不能自行复权。后验显示锚点与旧决策可知时钟分开，显示产物不返回给历史决策。未提供时明示缺口；原账户/成交不变。
- **Engine 新独立评价：**主协调已通过 evaluation v3 方向，待 [Trade 主章](design/04_axiom_trade.md)冻结准确 shape。需要最大回撤峰/谷/恢复区间、净收益率百分比分布、保存风险指标/可用性、多真实基准及可追溯执行链；旧 run/评价保持兼容，不改写。滚动表现、换手、费用、集中度及段收益/持有期分析放次级展开区，不堆首页；不足样本/null 原因和本币/日历/时间/缺值必须读保存状态。无 FX 的跨币种比较不生成人民币超额。
- **收益轴与原值：**主图按 Owner 保存收益百分比序列显示，只有 nav_index 的旧报告仍称净值指数；不得由 UI 把 nav_index-1 补成业务收益序列。跨基准同日缺值保留缺失，不插值/邻日填充。新报告与旧账户按 input_run_ref 原值三元组绑定，新增报告登记不增加回测次数。
- **保存交易依据：**当前股票显示投影已有 Core targets/intents/trace、订单 quantity/intent_id 与 fill order_id/quantity/price/fee，优先保留可公开展示的窄依据并按真实关联连链。运行方不足的批次 ID、目标/买卖理由和 ETF 关联由 Owner 明示未提供，UI 不把同日记录造成因果链。Research 保存的说明/版本差异与运行自然标签用于摘要，无说明不猜意图。

新 Owner 文件由调用方显式提供并通过公共 Reader 校验，然后进入 UI 显示投影。浏览器不 import Owner、不自动 evaluate/query/build、不沿 index URI 补读。UI 对既有文件做只读/hash/mtime 检查，页面验收不要求 Owner 重跑账户、训练或 bulk。

## 页面交互应用

完整交互仅引用 [UI §8](design/06_axiom_ui.md#8-本轮整页交互与视觉规范)。UI 可将已保存点按日期/证券进行索引、按年/月折叠、稳定排序筛选及分页，并计算绘图坐标、十字线吸附和窗口；这些显示操作不产生业务批次、指标或复权值。

最近保存日 hover 预览与点击锁定分开；统一窗口控制收益/回撤/K 线可见点和交易定位，原报告指标/区间不变。最大回撤定位使用 Owner 保存区间，价格口径切换使用 Data 已固定映射。页签/左栏开关保留当前上下文，切 run 清除旧点/侧栏。深层 JSON 在独立原始记录入口按所选对象查看，默认摘要与差异来自保存说明。

## 组合、验收与交付

2026-10-05 基线：UI 0.2.0 已经 [PR #4](https://github.com/sinnergarden/axiom-ui/pull/4)亲审合并并免费静态发布。已审源码 `0260cb35a8d02d57170ee58fc4b9504edcc39ca5`、合并 `f0e913bfaa01dee7903a7f397d17a96c7634f8fb`、Pages 发布 `5e843e3731b0e20476bb86d80926bc2f4635a079`；匿名 HTTPS 与已审静态字节一致、正常安全 Chrome 可打开，不表示产品通过。用户本次验收明确未通过，全部反馈已授权修正；本设计与后续实现用新 PR，主协调亲审设计和实际页面后才更新原地址。当前线上提交保持，不逐条零碎发布。

展示上下文可由明确输入重建，不成为第二个实验 registry、账户事实表或业务输入。切 run 同时重置图、侧栏和选择；切页签、增加对照和图层开关保留当前上下文。对照差异明确提示，原曲线不静默裁剪或重新归一化。格式转换保留 owner 原金额/decimal；前端只计算图形坐标，不计算收益、回撤、完整持仓段或分箱。

比较时，signal、策略或模型变化列为研究改动，不凭 signal_ref 或 account_id 不同判定条件不兼容。时间范围选择仅控制保存点的显示或高亮，指标仍归原回测范围，不生成区间收益或重算。

验收先复用现有固定小样本/已验证显示投影，再检查已保存长 ETF 和有界股票 observed/strict；软件改动做针对性检查，不重跑无关 suite 或 Owner 任务。检查原值绑定、原文件 hash/mtime、全绘图区 hover/锁定/拖动、时间窗口联动、交易链分页/缺失、精度、固定组件/许可和默认安全 Chrome 桌面/手机体验。Owner 尚在 review 的产物标候选，新版本新路径/digest、不覆盖旧文件；短股票样本不能称多年股票或十二年历史验收。主协调必须亲审实际新页面；接口/截图通过不替代用户今晚重新验收，未补齐项单列。

后续默认交付入口是同一 [GitHub Pages](https://sinnergarden.github.io/axiom-ui/)，不默认让用户打开本地路径。公开构建只包含用户明确授权的精选结果、相关显示点及清理后的说明；不得混入完整 Owner 文件、全训练输入、无关私人研究、机器路径或凭据。每次静态导出明确选择运行和范围、保留来源身份/口径，审阅清理后的实际字节；不能因允许精选结果就公开原始全部数据。本人私有交付按授权使用本地或私有资料库，资料库可用性不阻挡已授权 Pages。设计正文/图源仅在 axiom-docs，UI repo 保存实现说明；新 PR 合并/更新由主协调亲审协调。

### ETF v5 精选公开投影

公开导出沿用显式 `run_ids`、已选账户窗口及相关证券的行情/保存 OHLCV、评价 v3 的逐路径 schema，以及已绑定的 Data review display / Engine fill display。私人页面可看不等于自动公开。`backtest_run_v5` 在旧展示字段之外，只增加 `run.portfolio_policy_ref`、`configuration.portfolio_policy`、ETF profile 的 `tax_rate/price_limit_policy/price_grid_policy/price_grid_ref`、position 的 `mark_basis_event_id`、order 的 `announced_suspension_event_ids/raw_slipped_price/price_tick/price_grid_ref/price_rounding/rounding_delta/effective_slippage_bps`、fill 的同组六个价格网格/滑点字段，以及引用到的 `run.unit_split_applications` 和 `market.unit_splits`。轮动政策只准 `{contract_version,schedule}`；一次买入持有只准 `{contract_version,security_id,entry_session,budget,schedule,partial_fill_policy,cash_dividend_policy,terminal_policy}`，允许保存的 `signal_ref=null`；买入持有账户不是市场基准。

公开拆分应用只准 `{event_id,security_id,session,phase,status,sequence,record_sequence,record_quantity,before_quantity,after_quantity,before_sellable_quantity,after_sellable_quantity,cost_minor,rounding_extra_fraction,original_quote,normalized_quote,before_market_value_minor,after_market_value_minor,rounding_value_minor,source_refs}`；`original_quote/normalized_quote` 各只准 `{session,price,available_at,source_refs}`。`market.unit_splits` 仅取所选运行引用的事件 ID，每项只准 `event` 与 `source_refs`；其中 `event` **完整允许字段**为 `{event_id,security_id,event_type,record_date,effective_date,effective_phase,ratio_numerator,ratio_denominator,quantity_rounding,quantity_rounding_scope,new_price_basis_session,suspension_start,suspension_end,suspension_scope,resume_session}`。所有 `source_refs` 仅准已保存的 digest 引用，不带原生证明正文。未知路径、嵌套类型、错位字段均拒绝，股票 v4 白名单保持。

公开页不包含原 `plan`、完整 DataBatch、`market.source_evidence`/`unit_split_source_evidence`、profile 的完整 `price_grid` 或来源 URL、Research 输入、Data coverage、本地路径或凭据。价格、单位、缺值、账户及评价只转录 Owner 保存值，不计算新 NAV/收益/指标。启用前做合成 v5 正例与私有字段反例，并审阅三账户选定公开 HTML 的实际字节；此合同和测试通过不代替页面亲审或部署授权。
