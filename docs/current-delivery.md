# 当前实现、复用与交付边界

公开设计与教学的唯一编辑源是 axiom-docs。代码、配置和验收报告归实现 owner；本页链接固定提交的报告，不复制生产数据或另一份结果 JSON。专项设计正文继续定义目标，本页记录截至 2026-10-04 的有界交付。适用代码与此前安装包见 [versions.json](../versions.json)。

## 本轮 ETF 消费闭环

固定 Data → Research Feature/Signal → Engine Core/Runtime 账户 → UI 保存结果展示，已完成短样本工程验收。Research、Engine 的代码已推送独立分支供审阅，尚未合并主线，也没有新 wheel 发布证据。UI 本轮实现已进入新 Git 仓的 `publish/ui-readonly` 分支；原本地非 Git 目录只保留旧副本，需后续导航式迁移，不作为另一处编辑源。

| owner | 实际交付 | 固定源码与证据 | 验收边界 |
|---|---|---|---|
| Data | 复用既有 7 ETF 日线、因子、限价、身份、日历、分红 Snapshot；本轮消费者只读 | 已验 Data 0.3.5 `f6b8fad`；[数据合同与原型](etf-rotation-data.md) | best-effort 时间/终态修订假设；状态缺源仍为 UNKNOWN |
| Research | 共同锚点复权 20D 特征、固定确定性最终信号、原子保存与无计算复用；沿用 Data/Core | 0.1.2 [`f88a24f`](https://github.com/sinnergarden/axiom-research/tree/f88a24fdcc6b28f399444c854b1f37702c7a5389)；[交付及对齐清单](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/reports/etf-delivery.json)、[真实样本](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/reports/etf-real-acceptance.json)、[独立复核](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/reports/etf-review.json) | 16 项不同受影响测试；无任意 FeaturePlan、标签/训练/模型/OOS |
| Engine | 中立 SignalFrame、纯轮动意图、冻结信号/market replay 离线回测、Decimal 账本和现金分红、保存/只读加载 | 0.2.1 [`381fe6c`](https://github.com/sinnergarden/axiom-engine/tree/381fe6c2d5e9024a3a62832c6e479b4ff04e2fc6)；[最终日线验收](https://github.com/sinnergarden/axiom-engine/blob/381fe6c2d5e9024a3a62832c6e479b4ff04e2fc6/reports/etf-daily-acceptance.json)、[独立复核](https://github.com/sinnergarden/axiom-engine/blob/381fe6c2d5e9024a3a62832c6e479b4ff04e2fc6/reports/etf-daily-review.json) | 53 tests；日级近似，无 live Broker、SQLite 崩溃恢复、送转/退市支持 |
| UI | 公共 `load_backtest_run` 验证后导出静态 HTML；保留 owner 身份、水位、表格、指标及缺失/近似标记 | 0.1.0 [`d5f097e`](https://github.com/sinnergarden/axiom-ui/tree/d5f097e46580b2794d08ececddccb123d292d3ea)；[展示验收](https://github.com/sinnergarden/axiom-ui/blob/d5f097e46580b2794d08ececddccb123d292d3ea/reports/daily-owner-display-acceptance.json) | 14 tests、独立复核；无重算或 owner 写入；完整 BFF/浏览器产品和截图 QA 尚未验收 |

### 同一输入与两种执行政策

本轮输入固定为 `s_e32f4511b69d4fce9accad609feb4005f371cc5cb833ca260d6ae563b75558d1`。7 只 ETF、114 个交易日（2026-03-18—08-31），其中 2026-06-01—08-31 为 65 个评估交易日。最终信号引用为 `sha256:e2966ff9febf2b72268091f979afbc29a836218dab008305c2ef40c6dcc6b030`：798 行，658 valid，前 20 个交易日共 140 行预热 invalid；评估期 455 行全部有效。Research 另外独立构建、缓存命中、新进程加载及 Engine 中立消费均核对一致，数据源 hash/mtime 不变。

默认 `daily_open_profile()` 仍严格阻断未知状态。同一实现、同一输入的严格对照为 14 orders / 0 fills、期末 10,000 元；它证明阻断政策，不能作为策略收益验收。

用户批准本轮显式使用 `daily_open_profile(unknown_status_policy="etf_daily_observed")`：仅针对已识别 ETF 状态缺源原因，在有效开盘价、正日成交量与合法限价下允许日线模拟，仍保存 UNKNOWN 与 `ETF_OBSERVED_DAILY_ASSUMPTION`。已知停牌、日内停牌、其他未知原因及现金/限价/容量/可卖数量限制继续阻断。全天成交量只是执行侧容量代理，不能证明开盘流动性；实验 T+1/100 基金份额参数未证明为真实 ETF 规则。官方 [suspend_d 说明](https://tushare.pro/document/2?doc_id=214)描述股票停复牌，没有 ETF 完整性承诺，空响应不能改写为正常交易。

| 保存结果 | 65 日内结果 | 身份/用途 |
|---|---|---|
| 显式 ETF 日线近似 | 10 orders / 10 fills；初始 10,000 元，期末 NAV 9,213.64 元，费用 25.26 元，现金分红 163.90 元；committed sequence 85 | run `sha256:c2bed666e2509ed1a8747bfae23f5d94a39f6d6db9227cd2a67f181ffcc3d77b`；短样本工程闭环 |
| 默认严格对照 | 14 orders / 0 fills；NAV 10,000 元；committed sequence 69 | run `sha256:6db153261ab0f6c933959aac448b66b6fbef7162d57d8ad8dcdc4031747b95ea`；未知状态阻断 |
| 合成 golden | 3 fills，现金/持仓/成本/NAV 手算一致 | [原始核算验收](https://github.com/sinnergarden/axiom-engine/blob/381fe6c2d5e9024a3a62832c6e479b4ff04e2fc6/reports/etf-acceptance.json)；不属于供应商或真实收益证据 |

日线近似的 content digest 为 `sha256:21ca7a5e9a7b3aea5435d85d58955dcbe5f3c6cfcb83c788b3372cf3bed4247c`。保存结果固定 signal/market/profile/implementation refs、最终账户及水位；相同输入重复执行一致，UI 表格与 owner 保存值相等。历史 `4a72394` 的零成交报告保留为旧严格对照，当前实际实现以 `381fe6c` 为准。上述结果不证明 alpha、OOS、长期收益、容量或实盘适用性。

最新 daily HTML 已存入 Library 并发送用户，此交付由父任务确认，晚于 UI 仓报告中当时的外部上传阻断记录。用户收到的 daily HTML 可以独立打开；合集入口使用同目录兄弟文件链接，单个附件不能保证跨附件导航可用。UI 无截图视觉验收结论。

### 公开加载与持久复用

Research 公共入口是 `axiom_research.build_rotation_features`、`build_rotation_experiment`、`load_rotation_experiment`。已保存实验的 `signal_frame()` 输出 Core 中立 `signal_frame_v1`，`feature_frames()` 展开保存的共享证明表；加载不读 Data，不执行 Core。API 与固定配置见 [rotation.py](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/src/axiom_research/rotation.py)、[sample config](https://github.com/sinnergarden/axiom-research/blob/f88a24fdcc6b28f399444c854b1f37702c7a5389/examples/etf_rotation_sample.json)。产物位置由调用方指定；本地生成结果没有上传 Git。

Engine 公共入口为 `axiom_engine.core.SignalFrame / plan_rotation` 和 `axiom_engine.runtime.BacktestRequest / MarketReplay / run_backtest / save_backtest_run / load_backtest_run`。Runtime 不 import Research，直接消费冻结 frame 和显式 market replay。UI 使用同一公共只读加载入口；[UI CLI](https://github.com/sinnergarden/axiom-ui/blob/d5f097e46580b2794d08ececddccb123d292d3ea/README.md)导出保存结果，缺数据标 unavailable，不补零、不重新计算账户指标。

本机该固定样本 Research 构建约 9.26 秒、复用约 0.098 秒。产物 39,198,766 bytes（约 39.2 MB / 37.38 MiB），其中 evidence JSON 38,697,312 bytes（约 98.72%）。证明表共享并可逐引用重建；仍有明显证据输出成本。此测量不清 OS 页缓存，不证明多年扩展性能或一天内任意规模变更。

## 此前 Data 与联合输入验收

| 能力 | 已保存证据 | 边界 |
|---|---|---|
| 时间扩展、恢复、稳定追加身份 | Data monthly merge、Raw-first checkpoint、同计划恢复；受影响 16 tests | 只处理触及窗口，供应商规模仍待测 |
| Raw 已有字段/证券的 Canonical 扩展 | Data 0.3.5 显式 canonical_symbols、完整合同/单位/映射；新 operation 默认 rebuild 保留有效选择；17 tests | 所选域完整 Raw 闭包；缺源值保持 null，需补采则显式决定 |
| 行情＋财务联合输入 | Research 0.1.1 `eb6ae3a` 的具名/多字段/多财务域输入、每 cutoff Data PIT、各流最新报告期、Core 执行与持久化；15 tests | 固定 identity/pct_change/asof；累计值不冒称 TTM/单季，无隐式旧报告回退 |
| 字典与文档迁移 | Data 字典/事件/状态合同；本仓唯一公开设计和教程源 | 字典支持不证明 Snapshot 值完整；旧入口只导航 |

[Researcher 末节](../notebooks/researcher_tutorial.html#section-17)保留两证券、六 sessions、12 行 × 12 数值字段的真实联合输入：当次本机约 0.68 秒构建、0.18 秒复用，独立 Data 实例与新进程加载一致。它与本轮 ETF 实验是不同样本/配方，不混用耗时或验收范围。[Developer 末节](../notebooks/developer_tutorial.html)保留合成 A→A+B 离线扩标，原 Raw/receipt/旧 Snapshot/current 不变。

此前新增教学连同初始化只执行 4 个 fresh code cells、0 errors；其余 93 个代码单元保留此前输出，两教程分别 43/54 个代码单元。本轮统一收尾只改 Markdown/入口并从保存输出生成 HTML，执行代码单元为 0；不重跑教程、采集、Qlib 导出或全历史测试。

## 尚未完成的范围

十二年 bulk 未完成全量验收。父任务截至本页更新时确认：行情下载已完成，财务同键冲突仍由原 Data 任务修复；0.3.6 本地修复 `48b8f4f` 尚未推送、显式续接待验。已验代码仍记为 Data 0.3.5，原任务 builder 保留冻结 0.3.3 身份，不把新源码写成正在运行包。本轮 docs/消费者没有检查或改写原计划、进程、Raw、checkpoint、数据根或 current。此前暂停时 1,849 receipts / 51 operation JSON 只作为历史检查点，不能当作现时数量。

任意 FeaturePlan、TTM 联合投影、成熟标签/训练、模型选择/OOS、长期策略验证、跨 OS/多年规模性能、完整浏览器/BFF、SQLite/Broker 恢复与实盘均未因此获得验收。普通说明、注释和链接变更只做文档检查；可执行教学变更只执行受影响单元及前置条件。

本轮文档检查记录见 [docs closeout check](../reports/docs-etf-closeout-check.json)：Notebook 代码、输出与元数据逐单元不变，保存输出重新渲染；新增本地链接、固定 owner 提交/文件与版本引用核对通过。没有新增截图或全教程执行结论。
