# 当前实现、复用与交付边界

公开设计与教学的唯一编辑源是 axiom-docs。代码、配置和验收报告归实现 owner；本页链接固定提交的报告，不复制生产数据或另一份结果 JSON。专项设计正文继续定义目标，本页记录截至 2026-10-04 的有界交付。适用代码与此前安装包见 [versions.json](../versions.json)。

## 本轮保存结果消费闭环

固定 Data → Research Feature/Signal → Engine Core/Runtime 账户 → UI 保存结果展示，已完成此前短 ETF 样本、固定长 ETF 范围及有界股票短月的 owner 工程验收，范围各自保留。Research PR #1/#2/#3 已亲审后合并，当前 0.2.1 main 为 `3a7451e`、对应源码 `a8f30d4`；Engine PR #2—#6 已亲审后合并，当前 main 为 `9d0b52c`、对应源码 `cb94d7a`。UI PR #1/#2/#3 已亲审后合入 `publish/ui-readonly`，0.2.0 最终股票 v3 源码 `bcacc5f`、merge `05a1dd8` 包含合法缺 high/low 的降级修复。各次合并源码树与已审 head 一致，不因 merge 重跑。软件源码已经交付；owner 35 tests、默认安全 Chrome 与 wheel 资产独立核验通过，不代表已安装或发布新 wheel。Root 尚未亲看最终截图，用户未验收；本人私有 HTML/截图在 Mac 本地可打开，资料库交付受阻：实际工具返回 Library prepare_uploads is not available，0 文件写入、无文件 IDs；不重试或换通道。原本地非 Git 目录只保留旧副本，不作为另一处编辑源。

| owner | 实际交付 | 固定源码与证据 | 验收边界 |
|---|---|---|---|
| Data | 固定 ETF/股票 Snapshot 的 native daily、因子、限价、成员、身份、日历与行动证据；消费者只读 | 原已验 0.3.5 `f6b8fad` 安装身份保留；最新 0.3.8 源码 [`aae9b23`](https://github.com/sinnergarden/axiom-data/tree/aae9b23d0e223b0221fb946b2e9daa9332cd622c) 经 [PR #37](https://github.com/sinnergarden/axiom-data/pull/37) 合并为 `44bad96`，含已审官方 fund_share_conversions 与新 Snapshot；[来源与事件边界](design/event-ambiguity-continuation.md) | 原 0.3.3 bulk builder/operation 绑定不改；PR #36 日历审计作为历史来源保留；best-effort/终态修订/成员来源限制保留，不声称十二年所有用途完整 |
| Research | 确定性 ETF 信号；固定六特征/五 session 归一化 target/单 fold 股票模型；成熟训练键、信号汇总与计时 sidecar；不可变登记及只读投影 | 股票模型 [PR #2](https://github.com/sinnergarden/axiom-research/pull/2)：`091189e` → `fec9270`；阶段报告 [PR #3](https://github.com/sinnergarden/axiom-research/pull/3)：`a8f30d4` → `3a7451e`；[读取合同](design/05_axiom_research.md#stock-saved-stage-report-proposal) | 原 ETF/登记验收保留；股票模型 75 tests、阶段报告 25 项定向 tests 与独立复审。固定模型证据不扩为通用模型选择或预测收益承诺 |
| Engine | 冻结信号/market replay 离线账本；ETF 份额拆分；有界 SZSE Top5 与股票费用/现金行动；保存 run/evaluation 公共 loader | ETF 拆分 [PR #5](https://github.com/sinnergarden/axiom-engine/pull/5)：`59a4e1c` → `1df81dc`；股票 [PR #6](https://github.com/sinnergarden/axiom-engine/pull/6)：`cb94d7a` → `9d0b52c`；[Trade §6.1](design/04_axiom_trade.md#stock-daily-observed-minimal) | 原账户/P10/v2 验收保留；股票 owner 114 source tests、独立复审及真实短月 observed/strict 保存件通过。日级事后近似，无 live/SQLite 恢复或完整股票数量行动/退市支持 |
| UI | 公共 Reader 的保存运行导航、显式 diff、阶段报告与 ETF/股票 v3 静态只读展示 | 0.2.0 最终源码 [`bcacc5f`](https://github.com/sinnergarden/axiom-ui/tree/bcacc5febafc4a4938a64f0fa45ef3cd5f4c79d4) 经 [PR #3](https://github.com/sinnergarden/axiom-ui/pull/3) 合并为 `05a1dd8`；[owner 展示验收](https://github.com/sinnergarden/axiom-ui/blob/bcacc5febafc4a4938a64f0fa45ef3cd5f4c79d4/reports/stock-account-v3-display-acceptance.json)、[只读接入](ui-workbench-read-contract.md) | 35 tests、默认安全 Chrome 桌面/手机及 wheel 资产独立核验通过；root 源码亲审，最终像素未亲看、用户未验收。本人资料库交付受阻，Mac 本地可打开；不重算或写 owner，无完整 BFF/live 产品验收 |

### 同一输入与两种执行政策

本小节仅记录此前 65 日 ETF 短样本的输入、运行与当时登记，不代表下文新增长期 ETF 或股票的当前总数。

Engine [PR #4](https://github.com/sinnergarden/axiom-engine/pull/4) 将 [有界长期评价](design/04_axiom_trade.md#long-history-evaluation) 的固定源码 `8876946` 合并为 `f0fd977`。定向边界测试、独立 review 及 731 自然日合成手算通过；旧 65 日保存账户仅生成新的 v2 评价，原 v1 结果与账户保持不变，94 自然日窗口两腿 CAGR 均为 null / `INSUFFICIENT_SPAN`。Research 当时按原 input_run_ref 追加同一账户的评价登记历史，该历史短样本的保存回测数为 1；不将合成两年样本或该短期 v2 输出称为多年真实收益验收。

该历史短样本输入固定为 `s_e32f4511b69d4fce9accad609feb4005f371cc5cb833ca260d6ae563b75558d1`。7 只 ETF、114 个交易日（2026-03-18—08-31），其中 2026-06-01—08-31 为 65 个评估交易日。最终信号引用为 `sha256:e2966ff9febf2b72268091f979afbc29a836218dab008305c2ef40c6dcc6b030`：798 行，658 valid，前 20 个交易日共 140 行预热 invalid；评估期 455 行全部有效。Research 另外独立构建、缓存命中、新进程加载及 Engine 中立消费均核对一致，数据源 hash/mtime 不变。

默认 `daily_open_profile()` 仍严格阻断未知状态。同一实现、同一输入的严格对照为 14 orders / 0 fills、期末 10,000 元；它证明阻断政策，不能作为策略收益验收。

用户批准本轮显式使用 `daily_open_profile(unknown_status_policy="etf_daily_observed")`：仅针对已识别 ETF 状态缺源原因，在有效开盘价、正日成交量与合法限价下允许日线模拟，仍保存 UNKNOWN 与 `ETF_OBSERVED_DAILY_ASSUMPTION`。已知停牌、日内停牌、其他未知原因及现金/限价/容量/可卖数量限制继续阻断。全天成交量只是执行侧容量代理，不能证明开盘流动性；实验 T+1/100 基金份额参数未证明为真实 ETF 规则。官方 [suspend_d 说明](https://tushare.pro/document/2?doc_id=214)描述股票停复牌，没有 ETF 完整性承诺，空响应不能改写为正常交易。

| 保存结果 | 65 日内结果 | 身份/用途 |
|---|---|---|
| 显式 ETF 日线近似 | 10 orders / 10 fills；初始 10,000 元，期末 NAV 9,213.64 元，费用 25.26 元，现金分红 163.90 元；committed sequence 85 | run `sha256:c2bed666e2509ed1a8747bfae23f5d94a39f6d6db9227cd2a67f181ffcc3d77b`；短样本工程闭环 |
| 默认严格对照 | 14 orders / 0 fills；NAV 10,000 元；committed sequence 69 | run `sha256:6db153261ab0f6c933959aac448b66b6fbef7162d57d8ad8dcdc4031747b95ea`；未知状态阻断 |
| 合成 golden | 3 fills，现金/持仓/成本/NAV 手算一致 | [原始核算验收](https://github.com/sinnergarden/axiom-engine/blob/381fe6c2d5e9024a3a62832c6e479b4ff04e2fc6/reports/etf-acceptance.json)；不属于供应商或真实收益证据 |

日线近似的 content digest 为 `sha256:21ca7a5e9a7b3aea5435d85d58955dcbe5f3c6cfcb83c788b3372cf3bed4247c`。保存结果固定 signal/market/profile/implementation refs、最终账户及水位；相同输入重复执行一致，当时 UI 表格与 owner 保存值相等。历史 `4a72394` 的零成交报告保留为旧严格对照，原账户验收基线为 `381fe6c`；该短样本加入 P10 时的源码为 `e74cefb`，合并提交 `ef2f693` 的源码树与其完全相同。后续已合源码见上表，原短样本身份不倒改。上述结果不证明 alpha、OOS、长期收益、容量或实盘适用性。

此前 daily HTML 已存入 Library 并发送用户，此交付由父任务确认，晚于 UI 仓报告中当时的外部上传阻断记录。该附件可以独立打开；合集兄弟文件链接不能保证跨附件导航可用。这是历史附件交付，不代表当前工作台已通过最终验收。工作台功能与三视图已确认，稳定保存运行分组、阶段报告和股票/价量视图分别随 PR #1/#2/#3 合并。Owner 浏览器 QA 与 root 亲看像素、用户验收分别登记；后两者尚未完成，当前本人资料库交付受阻，Mac 本地文件可打开。新增视觉与只读接入需求见 [PRD](design/08_axiom_ui_research_prd_draft.md)及[应用说明](ui-workbench-read-contract.md)。

### 后续固定长 ETF 与有界股票交付

7 ETF 的共同范围 **2019-07-01—2026-09-30** 已在最终固定 daily Snapshot 完成 Feature/Signal、账户和保存评价 owner 工程验收；它与此前旧 Snapshot 的首周预检分别保存，不再将预检写成最终范围结果。PR #5 加入份额拆分；长 ETF 实跑两次拆分均为 NO_ENTITLEMENT/零持仓，只验证参考价桥接，正持仓比例与 ceil 由 golden 验证。原缺数、执行限价、UNKNOWN 与日线近似仍保留。Research 只关联原保存账户/评价，UI OHLCV 的共同字段及逐键 metadata 重建完整原 DataBatch digest；保存行情包含前边界，不用仅 NAV 日期另造查询。私人结果/数据没有提交 Git；该固定范围不证明 alpha、其他股票的多年性能或一般吞吐保证。

股票仅覆盖统一 [Trade §6.1](design/04_axiom_trade.md#stock-daily-observed-minimal) 的 2024-01 有界 SZSE 主板三前缀账户窗口：原 314 预测 union 和模型身份不改，账户事件核验覆盖完整 83 资格 union。Engine 保存显式 observed 与严格 UNKNOWN 对照及各自评价，22 个 NAV sessions 的 CAGR 仍为 null/INSUFFICIENT_SPAN；源码与 owner 保存件验收通过，不在此复制私人收益明细。Research 在原 normalized 模型版本追加两条账户登记、关联原阶段报告，旧 model manifest/历史登记当时的 blocked 状态不倒写。原行情批次已包含 OHLCV/amount，直接复用同 Snapshot、同 Query 与 source reference，volume_shares 为股；此次交接没有新 Data 查询、训练或账户执行。

股票证据保存支持 bundle 内 coverage 去重/压缩，重建后仍绑定完整原 native batch hash，不借存储压缩宣称来源完整。Owner 测得该短样本公共 loader 约 29 秒、峰值约 4 GB，市场证据约 103.9 MB；这些是当前保存件的解码成本，并非已完成多年股票规模验收。原 Source、模型、manifest、账户和评价保持不变；UI 只展示明确绑定的保存值。

扩长耗时只作线性参考：同环境、同配方、固定 314 标的 union 与六特征，实际 81 个 Feature sessions / 25,434 行冷建 1,020.77 秒（约 17 分钟）；假设一年 250 sessions，Feature 约 53 分钟，2020—2026 七年量级约 6.1 小时。250/年是规模假设，不替代真实冻结日历；历史成员 union、缓存、证据和分区 I/O 会改变成本。当前归一化模型训练实测约 0.048 秒，训练不是该短样本瓶颈；上述估计仅指 Feature，不包含尚未验证的多年证据内存、训练计划或账户 I/O 扩展。22 日账户 Reader 的约 29 秒 / 4 GB 已显示保存证据成本，暂不能保证多年账户或全链在一天内完成；本轮未实际运行长股票或新增性能框架。

### 公开加载与持久复用

Research 公共入口是 `axiom_research.build_rotation_features`、`build_rotation_experiment`、`load_rotation_experiment`。已保存实验的 `signal_frame()` 输出 Core 中立 `signal_frame_v1`，`feature_frames()` 展开保存的共享证明表；加载不读 Data，不执行 Core。API 与固定配置见 [rotation.py](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/src/axiom_research/rotation.py)、[sample config](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/examples/etf_rotation_sample.json)。产物位置由调用方指定；本地生成结果没有上传 Git。

Engine ETF 公共入口为 `axiom_engine.core.SignalFrame / plan_rotation` 和 `axiom_engine.runtime.BacktestRequest / MarketReplay / run_backtest / save_backtest_run / load_backtest_run`；股票入口为 `StockPredictionFrame / plan_stock_portfolio` 及 [Trade §6.1](design/04_axiom_trade.md#stock-daily-observed-minimal) 的专用 request/profile。Runtime 不 import Research，消费冻结 frame/prediction 和显式 market replay。公共 loader 兼容已保存 v1/v2/v3，评价 loader 兼容 v1/v2；UI 使用这些只读入口，缺数据标 unavailable，不补零或重算指标。[已合工作台 README](https://github.com/sinnergarden/axiom-ui/blob/e819e604a708efa8c3149b289db97682ebb66165/README.md)与历史 daily CLI 分别记录其原交付范围。

Research 0.1.3 的 `ExperimentStore / ExperimentReader` 登记已有产物，保存显式问题、版本、状态与差异；Reader 仅读索引，冷启动不导入 Data/Engine。已保存同一账户的历史评价与当前通过复审的 P10 关联均留在本地，未重跑账户。登记修订与同一回测的聚合、运行级收藏及近期活动口径见 [Research 主章](design/05_axiom_research.md#experiment-records)；0.1.4 修正 `59c45a1` 已通过 16 项定向测试和独立复审并经主协调亲审后以 merge commit `e612430` 合入 PR #1；远端没有 check-runs，不称 CI 通过；此前 32 项全套及原配方验收保留，不重复无关全套或账户。

Engine P10 `load_backtest_evaluation` 仅读取/hash/ref 校验独立保存报告，冻结沪深300价格指数、回撤/月边界、完整持仓段和有界分红证据，按 [统一合同](design/04_axiom_trade.md#daily-evaluation)展示缺失与样本限制。68 tests、输入闭包修复后的独立复审及既有 65 日账户消费通过；私人评估 JSON 未提交。合并只改变 Git parents，未重复回放。

UI 价量输入只读同一冻结 Snapshot，精确复用保存账户的 market_daily query，除字段扩充 OHLCV 外保持其余值，包括 66 sessions 的 05-29 anchor。462 行及逐键 metadata 的共同 open/close/volume 重建 digest 与原 source.reference 相同；两次公共读取一致，原 Data 文件、账户和评价的 hash/mtime 不变。新增事实文件及登记仅在本地，未重算指标或采集。

本机该固定样本 Research 构建约 9.26 秒、复用约 0.098 秒。产物 39,198,766 bytes（约 39.2 MB / 37.38 MiB），其中 evidence JSON 38,697,312 bytes（约 98.72%）。证明表共享并可逐引用重建；仍有明显证据输出成本。此测量不清 OS 页缓存，不证明多年扩展性能或一天内任意规模变更。

## 此前 Data 与联合输入验收

| 能力 | 已保存证据 | 边界 |
|---|---|---|
| 时间扩展、恢复、稳定追加身份 | Data monthly merge、Raw-first checkpoint、同计划恢复；受影响 16 tests | 只处理触及窗口，供应商规模仍待测 |
| Raw 已有字段/证券的 Canonical 扩展 | Data 0.3.5 显式 canonical_symbols、完整合同/单位/映射；新 operation 默认 rebuild 保留有效选择；17 tests | 所选域完整 Raw 闭包；缺源值保持 null，需补采则显式决定 |
| 行情＋财务联合输入 | Research 0.1.1 `eb6ae3a` 的具名/多字段/多财务域输入、每 cutoff Data PIT、各流最新报告期、Core 执行与持久化；15 tests | 固定 identity/pct_change/asof；累计值不冒称 TTM/单季，无隐式旧报告回退 |
| 字典与文档迁移 | Data 字典/事件/状态合同；本仓唯一公开设计和教程源 | 字典支持不证明 Snapshot 值完整；旧入口只导航 |

[Researcher 第 7 节](../notebooks/researcher_tutorial.html#section-7)保留两证券、六 sessions、12 行 × 12 数值字段的真实联合输入：当次本机约 0.68 秒构建、0.18 秒复用，独立 Data 实例与新进程加载一致。它与本轮 ETF 实验是不同样本/配方，不混用耗时或验收范围。[Developer 第 7 节](../notebooks/developer_tutorial.html#section-7)保留合成 A→A+B 离线扩标，原 Raw/receipt/旧 Snapshot/current 不变。

此前新增教学连同初始化只执行 4 个 fresh code cells、0 errors；其余 93 个代码单元保留此前输出，两教程分别 43/54 个代码单元。此前统一交付收尾只改 Markdown/入口并从保存输出生成 HTML，执行代码单元为 0；不重跑教程、采集、Qlib 导出或全历史测试。

## 尚未完成的范围

Data 已完成第一阶段股票/ETF 来源采集与显式续接，0.3.8 固定源码 `54e98c6` 保留不可裁决事件的 cutoff 可见缺失范围；这属于有明确限制的来源交付，不能当作所有研究/交易用途均完整。事件裁决见 [Data 补充](design/event-ambiguity-continuation.md)。此前财务冲突修复待验和暂停 checkpoint 数量仅是历史状态。日历审计修正 `e62774c` 经 PR #36 合并为 `93872ac` 的历史来源保留；最新已亲审官方 fund_share_conversions 源码 `aae9b23` 经 PR #37 合并为 `44bad96`，版本仍为 0.3.8，并提供新的固定 Snapshot。更正覆盖报告与最终固定输入已被上述有界 ETF/股票消费者使用，不沿用旧待完成 Snapshot 状态或失效缺口数字。既有安装包、原 0.3.3 builder 和续接 operation 的具体绑定各自保留，不因新源码或消费者结果改写。本轮 docs/消费者没有改写原计划、进程、Raw、checkpoint、数据根或 current；完整十二年所有用途覆盖仍未获得验收。

长历史先依据 Data 的有界 `etf_limit` / `stk_limit` 探测选择上述共同范围，再固定 final Snapshot 并完成 owner 消费；精确代码窗口、正控、来源推断边界及起点门槛见 [Research 数据准备](design/05_axiom_research.md#41-数据准备顺序)。保持执行限价/profile、原日期和固定 7 ETF。旧 Snapshot 的首周小预算预检仍只是历史起点证据，不冒充 final 范围；两处范围内行情缺失按原 invalid/执行规则保留。私人输入与产物继续只保存在本地，不为状态收尾重复多年 Feature、训练、账户或教程。

任意 FeaturePlan、TTM 联合投影、通用模型选择/跨 fold OOS、股票多年策略或规模性能、跨 OS、完整浏览器/BFF、SQLite/Broker 恢复与实盘均未因此获得验收。固定股票六特征/五 session label/单 fold 训练与保存件验收是已交付的有界能力，不再统称为未实现。股票 UI 修复源码已合并交付，owner 图表 QA、root 亲看最终像素和用户验收分别登记，后两者尚未完成；本人资料库交付最终回执为 BLOCKED/0 文件写入，Mac 本地文件可打开。普通说明、注释和链接变更只做文档检查；可执行教学变更只执行受影响单元及前置条件。

统一交付收尾的检查记录见 [docs closeout check](../reports/docs-etf-closeout-check.json)：该轮 Notebook 代码、输出与元数据逐单元不变，保存输出重新渲染；新增本地链接、固定 owner 提交/文件与版本引用核对通过。

后续[教程叙述重编排](../reports/tutorial-narrative-check.json)保留全部 97 个代码单元、执行计数与保存输出，调整 Markdown、单元顺序和展示元数据。研究篇沿取表、财报时间、特征复用与交接展开；开发篇沿接入、发布、日更、修正和恢复展开。HTML 只渲染保存输出，默认折叠长来源与工程核对；本轮没有执行教学代码、采集或写正式数据根，没有新增截图结论。

随后完成[教学页面 Chrome 抽查](../reports/tutorial-chrome-review.json)：实际查看 Researcher 第 2/5/7 节与 Developer 第 2/3/8 节的折叠前后展示，小表可读，宽表提示、横向滚动及方向键操作通过。三张关键截图内嵌在独立审阅 HTML 中。此结论仅覆盖教学页面，不追认 owner 业务测试、完整 notebook 执行或 UI 产品视觉验收。
