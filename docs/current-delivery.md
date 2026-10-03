# 本轮实现、复用与交付边界

公开设计与教学的唯一编辑源是 axiom-docs。Data 保留源码、配置与本地测量报告；Research 保留实际消费者、Core 编排与研究产物。旧位置只提供导航，HTML 是生成品。适用版本详见 [versions.json](../versions.json)。冻结设计正文定义目标，下面记录真实交付状态。

| todo | 分类 | 已交付与证据 | 当前边界 |
|---|---|---|---|
| 时间扩展、失败恢复、追加稳定身份 | 已支持验证 | Data 既有 monthly merge、Raw-first checkpoint、同计划恢复；相关 bulk/update 验证沿用，受影响 16 tests 通过 | 只处理触及窗口，供应商窗口/限制仍需实际测量 |
| Raw 已有字段的 Canonical 扩展 | 已支持验证 | 原 Raw + 明确合同/单位/映射离线 rebuild；缺源值保留 null；旧输入不变 | rebuild 整个所选域，非自动精细分区修补 |
| Raw 已有其他证券的离线扩标 | 需代码修复，已完成 | Data 0.3.4 显式 canonical_symbols 选择与稳定映射；Raw 请求/receipt、旧 Snapshot/current 不变；未选域复用 | 提供完整域 Raw 闭包及目标选择；Raw 未有值需明确补采 |
| 行情＋财务研究输入、跨实验复用 | 需代码修复，已完成最小路径 | Research 0.1.1 具名查询/多字段/多个财务域；每 cutoff Data PIT，再选最新报告期；Core 执行并持久化；15 tests 通过 | 固定 identity/pct_change/asof 配方；不支持任意 FeaturePlan、派生 TTM、标签/训练 |
| 字典、时间/PIT/revision、缺失/失败说明 | 已支持验证，本轮补文档 | 复用 Data 字典、事件/状态查询和已有实证；同步当前实现状态及中文教程 | 字典是接入合同，不是供应商所有潜在字段，也不是数据完整性证据 |
| 文档拆仓、旧入口、代码版本与同一 HTML | 只补文档，已完成 | 本仓唯一源、Data 与工作区旧入口导航、versions.json、两份生成 HTML | 旧执行输出与本轮 fresh 验证分别标记 |
| 十二年 bulk、一日内任意规模变更 | 限制 | 暂停时保留 1,849 receipt、51 operation JSON，未发布 current，ETF 未开始 | 仍待 bulk 完成与目标规模性能验收；本轮未恢复采集 |

## 真实小样本

[Researcher 末节](../notebooks/researcher_tutorial.html)使用既有真实 Data：两个证券、六个 exchange sessions、两条行情查询、三条财务查询，输出 12 行 × 12 个数值字段。收入流在这六个 session 内实际切换报告期；各流按各自 cutoff 选修订，最新报告缺失/撤回不回退旧值。面板约 0.68 秒构建、0.18 秒复用（该次本机测量）；换 Data 实例复用保持 mtime，并在另一 Python 进程直接重读一致。正式数据根只读、供应商请求为 0。这是 best-effort 供应商假设下的消费实例，不证明严格历史公开证据，不外推多年速度。

[Developer 末节](../notebooks/developer_tutorial.html)用明确标注的合成全市场响应验证离线 A→A+B：新选择记入新 Snapshot，原 Raw/receipt/旧 Snapshot/current 不变。真实数据获取与全市场供应商失败仍需 bulk 验收；合成 fixture 不冒称供应商证据。

只执行这两项新增代码及各自初始化：4 个 fresh code cells，0 errors。其他 93 个代码单元保留此前输出；当前两教程共有 43/54 个代码单元。本轮没有重跑完整教程、全历史测试、Qlib 导出或任何采集。

## 使用与复用

Data query/view 固定 Snapshot、字段、证券、交易日、PIT 与 cutoff。Research 的具名查询固定输出顺序；支持多域、多字段，输入都按 `(security_id, session)` 合并。财务查询范围可以跨多年，financial cutoff 模板在执行时替换为当前 session cutoff。各财务流独立选最新经济报告期，不因旧报告的更晚 receipt 取代新报告。basis 和单位按源保存，TTM/单季仍由既有 Data 稳定派生接口单独提供。

持久产物只有 manifest、Parquet panel 与 evidence JSON，使用既有 FeatureRelease/FeatureBuildIdentity。查询上下文集中保存，来源按引用绑定，避免每格重复整段查询。相同数据、查询、配方、实现包直接重用；改变 lag、字段、查询或实现产生新 build。`load_feature_build(path)` 不需 Data root，可跨进程只读。损坏文件报错并保留原件；写失败不发布半成品。研究空间与 Data 原始事实空间分开。

## 尚未验证或实现

本次支持正常字段/查询扩展，但仍是固定 Core 算子配方，不能称为通用 FeaturePlan/完整研究平台。TTM 联合投影、标签成熟度/训练、模型选择/OOS、账户回测、发布 Runtime/UI 分别由 owner 后续实现。Engine Core 已发布且未修改；本地 Runtime 未提交，UI 不是 Git 仓库。未把这些本地附录称为远端交付。

十二年任务保持原 0.3.3 wheel、plan、Raw、checkpoint。进程已停止，但旧 checkpoint 的 running 字样刻意没有改写；没有 current。普通正文/注释/链接修改不触发全量重算、重导出、采集或全测试，commit 只记录来源。恢复 bulk 必须另行明确决定，使用原冻结包和同一计划；当前 0.3.4 不自动替代原 builder。
