# 首版 UI 公共读取与联调

2026-10-04 · 功能及三视图已确认，先固定小样本，后绑定父任务指定长期 Snapshot 与已保存运行。设计依据为 [PRD](design/08_axiom_ui_research_prd_draft.md)；职责仅引用 [唯一模块边界](https://github.com/sinnergarden/axiom-docs/blob/c22f49342b415290abc7d45d438e4d58013a1c45/docs/design/01_axiom_overview.md#module-boundaries)。本页记录消费方式，不另维护职责表、业务字段表或统计公式。

## Owner 合同与读取入口

Research 的字段与过滤语义以 [Research 主章实验记录合同](design/05_axiom_research.md#experiment-records) 为准。UI 调用 `ExperimentReader(index_path).index()` 读取问题→不可变版本→运行和整理状态，使用 `compare_versions` 读取已声明变化及保存参数/输入差异。收藏、搁置和标签只在本地展示/筛选，不写 Research 业务状态。未运行、失败、阻断或未载入账户结果均保留入口，不生成 Engine run_id、假设或零指标。默认导航沿 owner 的 saved_run_ref 聚合、registration_history 保留登记修订，回测数和登记数分别读 owner counts；运行收藏/搁置按组读取，不因更换评价多算一次回测。旧 `load_rotation_experiment(path)` 只作明确提供的冻结实验验证，不能替代新的问题说明。

Engine 的 [P10 主合同](design/04_axiom_trade.md#daily-evaluation) 定义评价与统计口径。`load_backtest_run(path)` 和 `load_backtest_evaluation(path)` 均仅读取并校验保存结果，UI 不调用执行、评价或保存入口。评价逐原值绑定 `input_run_ref` 的 run_id/content_digest/committed_sequence，以及 signal/market/profile refs；逐 session NAV、水位和成交关联不能混用。Research 索引关联也逐值核对，索引 URI 不自动跟随读取。基准必须保留价格指数不含分红说明，月份 partial/null 与已知/未知分红范围分别标示；不足分布门槛仅展示 owner 逐段值。

UI 同入口兼容 v1 与 [多年评价 v2](design/04_axiom_trade.md#long-history-evaluation)。v2 读取保存的年化区间与账户/沪深300 CAGR、累计收益、同区间最大回撤；保留累计收益展示，年化值及其不可用原因分别按 owner 原值格式化。v1 不补年化字段；短跨度或边界缺失的 null 不填零，也不因报告 COMPLETE、局部月或持仓段资格推断年化可用。窗口选择仍只控制保存点展示，年化区间保持原报告归属；基准仍为不含分红的价格指数。历史候选保存件只作接口测试并显式标候选，正式展示绑定父任务指定的最终 Engine 身份与文件，页面验收单独登记；UI 不按天数、NAV 或指数计算 CAGR、不年化回撤、不增加 Sharpe。具体字段、时钟与公式均只引用 Trade 主章，本页不另维护。

账户公共 loader 同入口兼容 `backtest_run_v1/v2/v3`；v2 消费差异只引用 [ETF 份额拆分主合同](design/04_axiom_trade.md#etf-unit-split-application-proposal)，v3 股票消费只引用 [Trade §6.1](design/04_axiom_trade.md#stock-daily-observed-minimal)。UI 原样保留保存的 `unit_split_applications`、position `mark_basis_event_id` 及 order `announced_suspension_event_ids`，连同固定计划事件与来源在账户变化/持仓/委托详情展示；只将事件 source_refs 对应的已保存 fund_share_conversions 原生 source_evidence 原样带入折叠详情，保留 Snapshot、EventQuery cutoff/PIT 与逐键元数据，不扩展其他市场输入；应用日期可定位保存点，但拆分不是买卖成交，不新增 fill、B/S 标记、权益、复权价或指标。`APPLIED` 是 Runtime 模型应用状态，不改 issuer 的 planned/implemented、not_stated/null 或原始 Data 状态；停牌/缺价类型始终按最终 owner 状态与证据显示，不由缺行、因子或旧样本推断。v1 不补事件字段。明确 synthetic 的 1:5/持有人 ceil 保存件只用于 Reader 与显示验收；真实长期展示绑定固定最终账户、评价、Research 登记和同 Snapshot OHLCV，视觉/用户验收独立；不重跑、不算权益、不修正 owner 产物。

股票 ML 尚无账户结果时，仍用同一 Research 实验索引列出已有登记；调用方显式提供目录，经 `load_stock_ml_experiment` 与 `load_stock_model` 公共 Reader 验证后，按登记中的 StockMLExperiment、模型、信号及证据原值引用绑定研究阶段面板，不跟随索引 URI。只展示 owner 保存的 fit cutoff、声明输入/预测 session 窗口、Feature ID/版本、标签成熟与标准化语义、逐日 IC/RankIC/有效及排除配对、模型配置与限制；相关均值、实际成熟训练窗口及耗时只有 owner 公共输出提供才显示，否则标未提供，不从逐日值或运行时间计算。股票账户原状态与原因保持未执行/阻断，研究登记 COMPLETE 不代表账户完成；无 BacktestRun 时没有净值、成交、账户收益或账户对照，不把预测分数当收益率，不训练、执行特征、采集或另做回测。该面板仅消费 [Research 主章](design/05_axiom_research.md) 的已保存产物，缺少公开读取形状由主协调向 owner 对齐，本页不另造业务合同。

股票阶段面板可显式附加保存的 `stock_stage_report_v1`，消费只引用 [Research §4.6](design/05_axiom_research.md#stock-saved-stage-report-proposal)。经 `load_stock_stage_report(path)` 公共 Reader 校验后，将全部六个 input_refs 与当前已载入的 StockMLExperiment 和 Research 登记逐值绑定；不匹配或重复输入拒绝附着，不跟随索引或 receipt URI。只格式化 owner 保存的训练声明/实际窗口及规模、IC/RankIC 有效 session 数与均值、各模式/状态/seconds 和来源；缺报告保留旧“未提供”行为，null 不填零，REUSED_NOT_EXECUTED 不算冷跑，继承的 Feature/Qlib 冷构建单列来源，不代表当前模型冷训练；build/total 不相加，整体 receipt 的内存/规模不摊到各阶段，不计算 ICIR 或吞吐预测。

股票账户沿既有 `load_backtest_run` 和 `load_backtest_evaluation` 显式路径接入已保存 `backtest_run_v3` / evaluation v2；执行资格、两类时钟、状态政策、税费与现金行动只引用 [Trade 股票主合同](design/04_axiom_trade.md#stock-daily-observed-minimal)。保留 quantity_unit=shares、price_unit=CNY/share（显示股、元/股）、预测全 union 与深圳执行资格子集、模型/执行 Snapshot 分列，以及 strict UNKNOWN 拒单和显式股票日线事后近似两份结果的身份与限制；不沿用 ETF 近似/份额标签，不重算费用、收益或 CAGR。已有实际账户且 Research 登记按原值关联后，当前账户状态与结果取自该保存 run/登记，模型 manifest 的旧 account_status 只作为当时研究阶段的历史证据；无 BacktestRun 的旧行为与 ETF v1/v2 保持。

股票原生证据经 Engine 公共 loader 完整校验后再投影；页面仅保存显示需要的行情、逐键元数据、上下文和引用，不嵌入全 coverage 表、压缩 payload 或完整非显示批次。OHLCV 可直接使用该 run 已保存的原生 market_daily 事实，保留原完整 DataBatch reference、Query/PIT/cutoff/字段单位与选中点来源，明确它是显示投影而非重新认定的完整批次；不查 Data，不跟随 URI，不给未提供的高低价造 K 线。评价与公司行动完整证据仍由原 evaluation/run 引用追溯；其保存指标、cash action/诊断和缺失限制保留，不因省略大表推断完整性。

股票 v3 费用读取原保存组件，tax_minor 是 stamp_tax_minor 别名，不重复相加；非实施行动诊断仍保留，不解释为已实施现金/数量事件。读取合同与最终视图完成分别按[当前交付](current-delivery.md)记录。

Data 沿用 [Data 公共 Reader](design/02_axiom_data.md) 与 [P12](design/06_axiom_ui.md) 薄投影。UI 接受调用方已从公共 Reader 取得的 `DataBatch(records, field_meta, context)`，不扫描业务根或隐式 Query。原执行 Query 加读 high/low 时，Snapshot、Query 其他语义、reader version、单位、价格口径和共同字段逐键 provenance 必须复现原 DataBatch digest；不能用 current 或新事实解释旧运行。原冻结批次已有完整 OHLCV 时直接复用并核验原 reference，无需新查询。ETF 原生量为 `volume_units`（fund units），原价单位 CNY/fund unit；股票原生量为 `volume_shares`（shares），原价单位 CNY/share。没有 high/low 时显示明确命名的保存 close/volume 与 K 线不可用，不构造蜡烛或将委托画成成交。

## 组合、验收与交付

2026-10-04 软件状态：UI 0.2.0 最终源码 `bcacc5f` 经主协调亲审后随 [PR #3](https://github.com/sinnergarden/axiom-ui/pull/3) 合并为 `05a1dd8`，源码树相同；包含合法缺 high/low 时保存 close/volume 的明确降级。35 tests、默认安全 Chrome 桌面/手机和 wheel 资产独立核验通过。Root 尚未亲看最终截图，用户未验收，本人资料库交付受阻：Library prepare_uploads is not available，0 文件写入、无文件 IDs；Mac 本地 HTML/截图可打开。这一文件交付限制与软件已交付分别记录，原 wheel 安装/发布边界不变。

展示上下文可由明确输入重建，不成为第二个实验 registry、账户事实表或业务输入。切 run 同时重置图、侧栏和选择；切页签、增加对照和图层开关保留当前上下文。对照差异明确提示，原曲线不静默裁剪或重新归一化。格式转换保留 owner 原金额/decimal；前端只计算图形坐标，不计算收益、回撤、完整持仓段或分箱。

比较时，signal、策略或模型变化列为研究改动，不凭 signal_ref 或 account_id 不同判定条件不兼容。时间范围选择仅控制保存点的显示或高亮，指标仍归原回测范围，不生成区间收益或重算。

验收按原 fixed daily/strict、明确合成 fixture、固定长 ETF 及有界股票 observed/strict 各自范围登记，检查公共 Reader 绑定、原文件 hash/mtime、上下文联动、错误来源、缺失、精度、针对性测试、独立 review 和默认安全 Chrome 桌面/手机布局。Owner 尚在 review 的产物标候选，新版本用新路径/digest，不覆盖旧文件。固定短股票样本不能称多年股票或十二年历史验收；只读绑定父任务指定产物的接口通过，也不替代最终个人视觉/用户验收。

工作台 HTML 包含私人结果与 provenance，不得进入公开仓库或公开部署；向用户本人交付时，按其授权使用本地或私有资料库。公开分支仅包含源码、测试、合成样本和清理后的验收说明；合并沿统一 PR 流程由主协调亲审协调。设计正文和图源只在 axiom-docs 维护，UI repo 保留运行与接口使用说明。
