# 首版 UI 公共读取与联调

2026-10-04 · 功能及三视图已确认，先固定小样本，后绑定父任务指定长期 Snapshot 与已保存运行。设计依据为 [PRD](design/08_axiom_ui_research_prd_draft.md)；职责仅引用 [唯一模块边界](https://github.com/sinnergarden/axiom-docs/blob/c22f49342b415290abc7d45d438e4d58013a1c45/docs/design/01_axiom_overview.md#module-boundaries)。本页记录消费方式，不另维护职责表、业务字段表或统计公式。

## Owner 合同与读取入口

Research 的字段与过滤语义以 [Research 主章实验记录合同](design/05_axiom_research.md#experiment-records) 为准。UI 调用 `ExperimentReader(index_path).index()` 读取问题→不可变版本→运行和整理状态，使用 `compare_versions` 读取已声明变化及保存参数/输入差异。收藏、搁置和标签只在本地展示/筛选，不写 Research 业务状态。未运行、失败、阻断或未载入账户结果均保留入口，不生成 Engine run_id、假设或零指标。默认导航沿 owner 的 saved_run_ref 聚合、registration_history 保留登记修订，回测数和登记数分别读 owner counts；运行收藏/搁置按组读取，不因更换评价多算一次回测。旧 `load_rotation_experiment(path)` 只作明确提供的冻结实验验证，不能替代新的问题说明。

Engine 的 [P10 主合同](design/04_axiom_trade.md#daily-evaluation) 定义评价与统计口径。`load_backtest_run(path)` 和 `load_backtest_evaluation(path)` 均仅读取并校验保存结果，UI 不调用执行、评价或保存入口。评价逐原值绑定 `input_run_ref` 的 run_id/content_digest/committed_sequence，以及 signal/market/profile refs；逐 session NAV、水位和成交关联不能混用。Research 索引关联也逐值核对，索引 URI 不自动跟随读取。基准必须保留价格指数不含分红说明，月份 partial/null 与已知/未知分红范围分别标示；不足分布门槛仅展示 owner 逐段值。

UI 同入口兼容 v1 与 [多年评价 v2](design/04_axiom_trade.md#long-history-evaluation)。v2 读取保存的年化区间与账户/沪深300 CAGR、累计收益、同区间最大回撤；保留累计收益展示，年化值及其不可用原因分别按 owner 原值格式化。v1 不补年化字段；短跨度或边界缺失的 null 不填零，也不因报告 COMPLETE、局部月或持仓段资格推断年化可用。窗口选择仍只控制保存点展示，年化区间保持原报告归属；基准仍为不含分红的价格指数。候选保存件只作接口测试并显式标候选，正式验收等待 Engine 最终身份与文件；UI 不按天数、NAV 或指数计算 CAGR、不年化回撤、不增加 Sharpe。具体字段、时钟与公式均只引用 Trade 主章，本页不另维护。

Data 沿用 [Data 公共 Reader](design/02_axiom_data.md) 与 [P12](design/06_axiom_ui.md) 薄投影。UI 接受调用方已从公共 Reader 取得的 `DataBatch(records, field_meta, context)`，不扫描业务根或隐式 Query。原执行 Query 加读 high/low 时，Snapshot、Query 其他语义、reader version、单位、价格口径和共同字段逐键 provenance 必须复现原 DataBatch digest；不能用 current 或新事实解释旧运行。ETF 原生量为 `volume_units`（fund units），原价单位 CNY/fund unit。没有 high/low 时显示明确命名的保存 close/volume 与 K 线不可用，不构造蜡烛或将委托画成成交。

## 组合、验收与交付

展示上下文可由明确输入重建，不成为第二个实验 registry、账户事实表或业务输入。切 run 同时重置图、侧栏和选择；切页签、增加对照和图层开关保留当前上下文。对照差异明确提示，原曲线不静默裁剪或重新归一化。格式转换保留 owner 原金额/decimal；前端只计算图形坐标，不计算收益、回撤、完整持仓段或分箱。

比较时，signal、策略或模型变化列为研究改动，不凭 signal_ref 或 account_id 不同判定条件不兼容。时间范围选择仅控制保存点的显示或高亮，指标仍归原回测范围，不生成区间收益或重算。

本轮以原 fixed daily/strict 与显式合成 fixture 验收，检查公共 Reader 绑定、原文件 hash/mtime、上下文联动、错误来源、缺失、精度、针对性测试、独立 review 和默认安全 Chrome 桌面/手机布局。Owner 尚在 review 的产物标候选，新版本用新路径/digest，不覆盖旧文件。固定短样本通过不能称十二年历史验收；后续只读绑定父任务明确的新长期产物。

工作台 HTML 包含私人结果与 provenance，不得进入公开仓库或公开部署；向用户本人交付时，按其授权使用本地或私有资料库。公开分支仅包含源码、测试、合成样本和清理后的验收说明；合并沿统一 PR 流程由主协调亲审协调。设计正文和图源只在 axiom-docs 维护，UI repo 保留运行与接口使用说明。
