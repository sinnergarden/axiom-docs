# axiom-data：个人维护版设计与实施边界

> 文档编号：AX-DATA · 个人版修订 v0.4 · 2026-10-03。\
> 状态：目标合同；生产来源按用户最新决定统一为 Tushare，外部 cross-check 只产生 warning，不改写事实或阻断发布。约定的Data代码范围及两份真实教程已验收，证据见实现仓库交付说明；十二年全量尚未验收，最新行情/财务修复状态见[当前交付](../current-delivery.md)。\
> 上位边界：[总纲](01_axiom_overview.md)、[补丁 A](07_重要补丁_A.md)、[补丁 B](07_重要补丁_B.md)。本次个人版约定已同步相关文档；四仓分工与 Engine/Core、Runtime 的逻辑边界不变。\
> 阅读示例：[For Quant Researcher](../../notebooks/researcher_tutorial.html) · [For Quant Dev](../../notebooks/developer_tutorial.html) · [Notebook 与复运行说明](../../notebooks/README.md)。两种视角使用同一套设计。教程只证明其实际运行范围，不构成全部供应商能力或生产回测验收。

## 0. 本文与两份 Notebook 的关系

本文件是 Data 的存储、时间与公共读取合同。总纲及已同步补丁约束四个物理仓库和五个逻辑域；Core、Research、Runtime、UI 各自拥有计算 ABI、研究产物、运行/账户与组合展示协议。Researcher Notebook 讲研究使用，Dev Notebook 展开实现审核，二者用同一批留存的真实市场数据及当前产品 API 解释本文，不另行定义一套跨仓 schema。HTML 从同名 `.ipynb` 生成。

教程通过实际 Reader、来源映射、跨仓薄接口与离线重建展示本文，分别使用一年工程样本和完整来源小窗口。生产成员与生命周期来自 Tushare；旧版官网调样与独立公告的结果是外部检查记录，不作为新版数据或发布条件。真实演示不代替晚到、撤销等反例测试，示例省略不等于合同豁免。跨仓接口调整须同步总纲索引、owner 文档和两份 Notebook。

当前施工证据另见 [Researcher 教程](../../notebooks/researcher_tutorial.html)、[Developer 教程](../../notebooks/developer_tutorial.html) 与
[实现合同和支持边界](../local-implementation-contract.md)：已贯通 Raw、Parquet、Snapshot、
日频/成分/事件 Reader、单季/TTM、状态与范围规划、分段 PIT、跨仓薄 adapter 和 portable bundle。
逐条验收见 [D01–D18 清单](../demo-acceptance.md)。真实来源完整性和历史 vintage
并未因此得到证明；固定 1800 标的一年真实采集、核对、离线重建和搬移已完成；范围、未完成事项与教程证据见 [设计对照](../design-conformance.md)。本次来源政策调整来自用户明确决定，覆盖先前“供应商基线＋官网调样必须闭合”的要求。

## 1. 判断与范围：小而严谨的数据底座

单人维护、A 股日频、沪深300及 CSI1800 历史成员、退出成员与指数基准，以及明确启用的7ETF日线轮动；研究输出起点可选 2020 年或 2014-11-01。输出起点与 lookback 采集起点分开，结束日为来源可提供的已完成交易日。真实验收使用一年行情工程样本、双证券完整源和7ETF日线；独立安装、恢复与离线搬移已验证，十二年全量尚未完成采集与验收。

值得保留的是：旧输入可恢复、单位和证券身份正确、使用供应商历史成员并集避免只选今天成员、缺数可解释、时间资格诚实。供应商快照可能遗漏月内临时进出股，这一来源限制明确报告，不据此停止初始化。把 DomainCommit、DerivedCommit、View、Validation、Admission、CodeBundle 都做成独立发布和登记系统，对当前规模不划算。

首版用户体验是：显式更新一次，固定一个 Snapshot，用几行 Python 读取，再在 Notebook 中研究和解释异常。不要求用户每天操作多个产物生命周期。

Data 保存事实、时间、来源和稳定变换；Research 定义 Feature/Label/样本/模型；Engine/Core 执行共享计算；Engine/Runtime 处理时间推进、成交与账户；UI 只读组合展示。数据检查通过不代表策略有效或可以实盘。

## 2. 首版只有三类持久对象

```text
SourceProfile + 请求
  → Raw 原响应 + fetch 日志
  → 版本化 Canonical Parquet
  → 一个 Snapshot manifest，内嵌按域的完整分区映射
  → Reader(snapshot, QuerySpec)
  → DataFrame + schema + refs + 时间/缺失元信息
```

| 概念 | 个人版实现 | 何时再扩展 |
|---|---|---|
| RawBatch | 一条请求/观察日志，引用原响应 | 无需独立注册服务 |
| DomainCommit | Snapshot 内的域段：contract、来源、实现和完整 partition map | 确有独立域发布/共享需要时，才抽成独立 manifest |
| Snapshot | 一份不可变 JSON 固定事实状态；是主要持久发布单位 | 不包含 Feature、模型或账户 |
| FactView / MarketReplayView | 固定 Snapshot 的 QuerySpec + Reader；可作为内嵌 ViewRef | 不为每次查询发布文件；物化只因真实性能或格式需求 |
| Derived | 版本化纯函数；必要时缓存，键包含 Snapshot/输入域、配方、scope、PIT/cutoff | 昂贵且跨任务复用后，才需要独立 DerivedCommit |
| QlibView | 显式导出固定数字日频Query；Research薄adapter使用实际Qlib读取 | 不成为日更或普通Reader查询的前置；新cutoff/字段生成新版本 |
| SourceEvidence | 可选原文/附件/引用与具体 revision 的绑定 | 按目标研究需要补证据，不建设全历史证据管理平台 |
| Coverage / quality | 请求与成功范围、异常列表、实际检查结果 | 不建立通用认证、资格撤销或 admission 平台 |
| Catalog | 首版读 manifest；索引可后加 | 查找成本确实出现时加可重建 SQLite |

Ref 表达可恢复的确定引用，不意味着独立目录、数据库记录或发布流程。域引用可以是 `snapshot_id + domain`；逻辑 ViewRef 可以在实验/run manifest 中内嵌 Snapshot 与 QuerySpec。保留语义版本轴，不人为增加持久对象。

建议目录：

```text
data/
  raw/objects/<digest>/payload.*
  raw/fetches.jsonl                   一行一次请求，按 batch_id 引用
  canonical/<domain>/<partition>/<version>.parquet
  snapshots/<snapshot_id>.json
  cache/                             可选 derived 缓存
  exports/qlib/                      显式导出的固定消费者格式，可存放于独立目录
  current.json                       可选默认 Snapshot 指针
```

实际数据不进代码 Git；数据根可配置，manifest 使用相对路径。相同内容与未变分区复用，不复制全历史。旧 Snapshot 和它引用的文件不可原地改写；不做自动 committed GC。单机单写者足够。

## 3. Raw、合同与规范事实

### 3.1 Raw 是低成本保险

保留原 JSON/CSV/附件字节；SDK 返回表格时保存原字段和单位，并声明序列化方式。不能换单位、丢字段、把空值变零后称为 Raw。

fetches.jsonl 每行按 batch_id 标识一次请求，记录：endpoint、参数/证券/日期范围、SourceProfile 版本、retrieved_at、成功/空结果/失败、分页是否完整、payload 路径及摘要。重复响应可复用内容对象，每次观察仍留日志。Raw 已成功而转换失败，不回滚 Raw。

今天重拉的终态响应不能替代以前保存的输入。摘要用来发现内容变化或损坏，不能替代文件与备份。

### 3.2 合同只定义当前需要的字段

每个来源/域的配置明确：经济键与 revision 身份、字段映射、单位/dtype、证券映射、空值/撤销含义、可用时间规则和分区。来源和字段合同可以是源码中的版本化配置，Snapshot 内嵌本次实际使用的内容；无需独立 contract 文件或通用 schema 注册平台。

- 日期/证券/单位只在一个转换入口处理；不按数值大小猜测手/股、千元/元或百分数。
- 同一经济键的内容变化保留 revision；同一内容重复观察保留最早 first_observed，不因重建而后移。
- 修订顺序由明确来源规则决定，不以文件顺序或“最后一次抓到”任意选赢家。
- `value / not_provided / retracted / source_missing / parse_error` 按实际源能力表达；不能统一前填。
- `pre_close` 保留供应商口径，不无条件替换为上一行 close。

### 3.3 从真实研究需求选域

所有默认生产数据来自 Tushare：行情、财务、日历、身份、上市/退市日期、停牌、成员与基准。接受供应商内容，不重新认证其每条历史事实。外部来源可单独 cross-check，结果是 warning，不替换 Canonical 数值，不成为 prepare/run/current 的必需门槛。

Axiom 仍负责自己的请求、单位、键、类型、时间与文件映射。请求失败、已知截断、文件损坏或本地错误不能冒称成功；供应商数值异常、外部来源分歧和来源精度不足分别记录为 warning/limitations。PIT 表达实际知识边界，不把信任供应商解释为今天的终态必然是当年的版本。

| 范围 | 内容与必要语义 |
|---|---|
| 市场研究首批 | security_master、trading_calendar、market_daily、历史 membership、指数基准；只启用当前研究用到的字段 |
| 账户回放所需 | security_status、price_limits、corporate_actions 和规则适用时间；进入该用途前补齐受影响范围 |
| 财务/股东（本轮已明确启用） | 财报按证券+endpoint+报告期+报表类型+revision 保存，股东报告保留报告组与完整性；接源单位、公告与修订时间、真实输出及单季/TTM 纳入完整 Data 验收 |
| 其他候选域 | 不预搬两融、资金流、全部公告等候选数据 |

Canonical 日频是 `(security_id, session, revision)` 的宽表；事件按经济身份保存，再按 cutoff 投影，不在每个交易日复制事件。起步按域/月分区，财报可按 endpoint/报告年；测过真实尺寸后再优化，不按每股每字段预建小文件。

ETF轮动新增范围使用基金身份、未复权日线、fund_adj、分红与涨跌停专用来源；复用相同存储和读取合同。用户已确认只用日线，消费者约定每周首个交易日使用上一交易日的21交易日窗口计算20D动量，在当日开盘价执行；Data仅采集与提供对应原始数据，动量/排名/信号归Research，成交/账户归Runtime，不称精确复刻09:35成交。详细采集与消费者合同见 [ETF日线轮动](../etf-rotation-data.md)。

## 4. 一个 Snapshot 足够固定事实

下面是结构示意，不表示真实数据或已实现 API：

```yaml
snapshot_id: s_example
parent_snapshot: s_parent
schema_version: personal_data_v1
build_context:
  code_ref: recoverable_git_commit
  dependency_lock_ref: recoverable_environment_lock
  config: {operation: update, market_partition: month}
checks: {usage: market_research, issues: []}
domains:
  market_daily:
    contract: {contract_id: market_v1, logical_key: [security_id, session], fields: declared_fields}
    source_profile: {id: supplier_daily_v1, units: declared_units, availability: declared_policy}
    build_context: {code_ref: market_builder_commit, config: actual_market_config}
    raw_batch_ids: [b1]  # 对应 raw/fetches.jsonl 中的请求，日志再引用原响应
    partitions:
      - partition: "2020-01"
        uri: canonical/market_daily/2020-01/p1.parquet
        file_sha256: "..."
        rows: 100
    coverage: {requested: requested_range, completed: completed_range, gaps: []}
  universe_membership:
    contract: {contract_id: membership_v1, interval: "[from,to)"}
    source_profile: {id: supplier_membership_v1}
    build_context: {code_ref: membership_builder_commit, config: actual_membership_config}
    raw_batch_ids: [b2]
    partitions:
      - partition: "history"
        uri: canonical/universe_membership/history/u1.parquet
        file_sha256: "..."
```

每个域段保存完整分区映射与该域实际构建来源。更新目标域时保留其他域段及其原 provenance，不能把旧域冒称用新代码重建。相同事实/coverage/时间语义未变时，新 fetch 日志不强迫创建新 Snapshot。

需要改变事实、coverage、单位/时间语义或 provenance 时生成新 Snapshot；仅补一个检查报告不改变事实版本，可在实验或操作记录中保存。新增派生配方或 Feature 不改变原 Snapshot。

build 的代码来源须可恢复：保存已提交源码的 Git 历史、依赖锁与实际配置，从确定版本构建。不能只记一个已经丢失的 SHA，也不能用未保存工作区修改假称该 commit 的结果。日常不建立 dirty 捕获/源码打包系统；重要发布或移机时可另存源码归档。运行中读取的合同和配置也固定。

当前写入在启动时验证干净 commit 或留存安装 wheel 的 origin/digest，并把真实 builder、依赖锁与环境绑定到操作和新建域；未变化域保留原来源。Snapshot 回放只选其引用的 Raw；历史字段扩展另用显式域/成功状态/receipt cutoff 选择预览。Snapshot bundle 是依赖闭包，完整 Raw 备份须显式选择截止接收时刻，见[恢复路径](../data-change-and-recovery.md)。

## 5. PIT：两个问题，不是三个晋升等级

经济时间回答事实属于何时；具体 revision 的公开时间回答市场何时可能知道；first_observed 回答本系统何时收到；cutoff 是本次允许使用的边界。公开证据并不证明数值正确。

| Policy | 回答的问题 | 可见性规则 |
|---|---|---|
| `operational_pit_v1` | 本系统当时实际拥有什么信息？ | 从实际 first_observed 起可见 |
| `market_pit_safe_v1` | 有何依据认为市场当时能知道？ | 有具体 revision 公开证据用 source_available；否则保守采用 first_observed |
| `best_effort_vendor_v1` | 来源终态历史在明示假设下可以怎样探索？ | 按声明的 vendor date/发布规则投影，承认缺少历史 vintage |
| `bootstrap_hybrid_v1` | 历史探索与上线后观察怎样组合？ | 明确分段 policy、范围与限制，不标成纯 strict |

`verified / observed / best_effort` 是本次输入范围的证据依据，不是 policy，也不是全库等级。上线积累 observed、选择性补公开证据是两种能力；verified 不替代 operational。补证据可以改变新 Snapshot 对市场历史的解释，不能伪造本系统更早收到数据。synthetic 是数据性质，另行标注。

2026 才采到 2020 终态历史不可能仅靠架构恢复 2020 信息集。允许用于明确的历史探索；严格结论不得借此成立。对需要的少数财务/成员事件补证据，胜过追求全历史认证。

读取顺序：按 policy 过滤可见 revision → 每个经济事件选择版本 → 再做 TTM/单季/日频投影。只有公告日期没有时刻时，使用明确保守规则，例如下一交易日开盘；日线的 OHLC/量额不能提前给当天开盘决策。UTC 表达绝对时刻，session 使用市场日历。

正常单行分红的完整实施行同时包含原公告日与实施公告日时，以较晚日期作为整行best-effort可见性的下界：股票按下一交易日09:30，ETF按当日20:00；只查询现金字段也遵循此边界。严格政策仍使用实际receipt或精确版本证据，不把该日期假设当作历史公开版本证明。歧义整组的有限值资格与缺失范围提示另按 [§6.1](#event-ambiguity) 分开检查，不能用较晚候选时钟遮蔽已可见缺失范围。

加入 usable_from 晚于 T 的数据不能改变 T 前 safe 输出。合法新证据证明更早公开时，新 Snapshot 可以改变历史解释，需说明影响；旧 Snapshot 不变。PIT 证据不足与单位错、日期错、错配证券等处理缺陷不是一回事，后者必须修复。

## 6. 范围、状态与派生的必要边界

三个集合分开：读取集合是历史成员 union 加 lookback；当天决策集合是当日可知 membership；账户跟踪集合还包括池外持仓/挂单。成员用半开区间 `[from,to)`，退出再进入不能合并成持续区间，且有效时间与可知时间分开。

成员生产来源为 Tushare `index_weight` 的实际 dated 名单。2026 年 6 月三个指数的实测中，6 月 12 日和 15 日均为空，整月查询只返回 6 月 30 日的 300、500、1000 行；每日调用不会凭空得到每日名单。历史初始化按月批量请求，保存供应商实际返回的所有 `trade_date`；空响应不清空已存在名单。CSI1800 按供应商三组名单的并集定义，不用官网调样改写。

名单观察日期、研究 session 和可知时间分别表达。两份快照间默认采用用户已确认的“截至该日最近一份供应商快照延续”：只选 trade_date 不晚于研究 session 且按所选 PIT policy 可见的完整快照，没有任何此前快照时为 unknown。不能把月底新名单回填月初，也不能称已恢复精确官方每日成分。原始快照是事实，日频投影是读取政策；两者使用相同 Raw 与 Snapshot。严格 PIT 仍受实际 receipt 约束，best-effort 才使用明示的供应商日期假设。

prepare 保留全部供应商历史快照候选并集、lookback 与池外跟踪证券，不能截成今天的 1800 只。月度观察不能证明未遗漏月内短暂成员；此项及外部比对差异以 warning/limitations 表达，不阻断生产初始化。先前必须闭合官网原始调样链的要求已撤销。

先看 Tushare 交易日历和身份，再看供应商停牌记录、请求覆盖。闭市不生成交易 session；未上市、退市、有记录停牌、未知缺数分别解释。上市/退市按供应商日期的声明语义处理；外部公告不覆盖供应商日期，分歧只记录 warning。有记录停牌可以零成交量，不能把缺行当停牌或补零价。Runtime 的最后有效价估值带时间与陈旧说明，不写回新的成交事实；退市存量及后续权益仍跟踪。

发现缺数时，修复、停止相关用途，或在研究政策下明确排除并报告影响；自动删掉缺数/停牌股票会改变样本，不能声称结果无偏。数据可追溯也不证明选样、成本和执行假设科学。

复权序列、TTM 等稳定派生先实现为纯函数，绑定输入 Snapshot、配方/实现版本、scope、PIT/cutoff。缺期、口径不兼容、撤销要显式缺失。Feature/Label 定义归 Research；缓存不是事实来源。

复权声明锚点与行动范围；严格 Feature 不静默用未来锚点。历史探索若采用来源终态复权，明确限制。账户回放使用未复权价格与公司行动，避免重复分红。复杂公司行动未支持时，只限制实际受影响用途，不能假装已支持。

一次决策的价格窗口内，各历史点使用同一个明确锚点，并仅使用该决策 cutoff 已知的行动/因子。不能把每行按本日锚点得到的价格拼起来算跨期收益。不同历史决策分别冻结各自窗口，后来的行动不能修改旧决策输出。例如假设 1 股拆成 2 股且无经济涨跌，价格由 10 变 5；以拆股后时点为共同锚点，窗口两端都应为 5，收益为 0，而不是 -50%。

统一事实字典入口为 `Data.dictionary(snapshot=固定ID, domains=...)`，由当前 adapter 合同/profile 与该 Snapshot 的实际合同生成字段、类型、单位/转换、时间和查询方法；中文含义只作展示注释。省略 Snapshot 看代码支持，指定版本看已声明字段，不将声明误作非空/PIT可见或完整覆盖。默认只读元数据；显式一个 Raw ID 才列出该响应未映射字段，不扫描全库。数据字典归 Data，Feature 配方归 Research，见[阅读入口](../overview.md)。

累计复权因子在没有新行动时可以保持非1值；价格变换使用 `factor(t)/factor(anchor)`，因子相同才使比值为1。合法行情空值、事件零行和季度不足分别保持结果与原因，不能统一填零；数据依赖、单位、身份和文件错误则修正实际受影响范围。

<a id="event-ambiguity"></a>
### 6.1 原生事件歧义

状态：2026-10-04 已裁决，源自固定分支 `01f0adc`；实现验收另见当前交付。

#### 财报字段歧义

财报保留证券、endpoint、报告期、报表类型及真实披露日。来源在同一披露组返回多行时，
若存在一条实际返回、包含全组一致非空字段的完整记录，可以使用这条记录。不能把互补
部分行拼成一份供应商从未返回的报告。不存在可用完整记录时，只保留全组一致的字段；
冲突字段标记 `source_missing`，原因是 `ambiguous_same_disclosure`。

公司类型或报告期上下文冲突会使数值字段不可用。`update_flag` 本身不能证明修订顺序；
不以行顺序、文件顺序或任意摘要挑选版本，不伪造公告日。缺失应传递到单季/TTM，不能
退回较早报告取得一个非空值。其他证券和请求继续处理。

旧 Raw 未捕获上下文字段时保持这一事实。新请求可以增加字段，但不得宣称旧响应捕获
了这些字段，也不为补齐上下文字段重采历史。单位、类型和文件完整性错误仍须纠正，
不能用供应商歧义掩盖本地转换失败。

来源字段含义见 [Tushare 利润表](https://tushare.pro/document/2?doc_id=33)。来源文档是字段
解释；它没有赋予本地未捕获数据一个可判定的版本顺序。

#### 分红的整个经济事件不可用

分红的当前原生键包含证券、来源报告期、公告日、进度。同键下返回不同实施日、除权日
或送股比例时，不能仅凭这些可更正字段断言是两笔合法行动，也不能断言其中一条是较新
修订。缺少稳定 action ID 或明确版本证据时保留全组 Raw，整个事件不可用。

这与财报字段一致性处理不同：所有经济数值和可更正经济日期均为 `source_missing`，包括
全组共同的现金零值及登记日。原因是 `ambiguous_action_identity_or_revision`。原生键
保持不变；不通过扩大日期键或改变接收时间解除冲突。完全相同的重复源行可以去重。
不同证券、不同原生键及不同进度的事件继续使用自己的来源证据。

候选经济日期摘要只固定“当前留存组有哪些可能日期”的诊断范围，不是行动身份或事件
日期。它属于状态内容：后来的候选日期集合改变时，即使全组仍不可用且候选数相同，也
须保留新 observation。旧 Snapshot、原始接收时间及完整 Raw 组保持不变。

字段解释见 [Tushare 分红送股](https://tushare.pro/document/2?doc_id=103)。该字段清单并未
提供用于裁决本轮身份与修订歧义的稳定行动标识。

#### Reader 的候选范围与时间边界

##### 已认可的范围行为

歧义事件的 `ex_date` 等轴为空时，不能直接过滤为“没有公司行动”。查询范围与留存候选
日期相交，或某候选日期未知而不能排除相交时，应返回缺失日期标记、字段缺失原因及
`unavailable_event_scope`。账户因此能区分“本范围证据不足”和“未观察到行动”。

候选日期已知且全部在查询范围外时，不连带阻断其他日期。其他证券独立。对不可用经济
字段的过滤不能证明行动不存在；共同现金零不能让账户绕过此缺失状态。此诊断也不证明
供应商历史完整性。消费者必须处理缺失标记和范围限制，不能填零后应用该行动。

##### 已裁决：缺失范围不能被较晚的候选时钟吞掉

以下是合同反例，非生产数据：同一原生键有候选 A、B，无此前单行观察。

| 候选 | 实施公告日 | 除权日 |
|---|---|---|
| A | 2015-07-16 | 2015-07-21 |
| B | 2018-07-31 | 2018-08-03 |

查询 `ex_date=2015-07-21`，`best_effort_vendor_v1` cutoff 为 2015-08-01。
仅按全组最晚实施公告日控制整行可见性，会得到空结果，且没有受影响范围。这会让历史
账户误把可能存在但无法判定的 2015 行动当作不存在。Data 0.3.7 当时已提交的实现有此缺口；
它不能据此通过完整事件用途验收。Data 0.3.8 按下列裁决修复，并保留此反例。

裁决：有限值资格与缺失范围提示分别检查。分红整组始终没有可应用数值；在
best-effort 假设下，只要任一候选按其原公告/实施通知规则可见且覆盖查询范围，就必须保留
不可用标记，而不能被另一候选的更晚通知遮蔽。这是在检查可能范围，不是选赢家或确认
该候选为独立行动。按 cutoff 只输出可见候选的必要范围，不能提前暴露迟候选的经济日期、
候选数量或有限值。存储里的完整候选摘要保留为诊断证据，不直接投影为早 cutoff 的事实。

如果存在此前单行观察，也不能让旧值掩盖当前来源口径下已经可见的歧义范围。先选择
可见的来源 observation，再判断受影响日期范围；不能先按日期过滤而回退旧值。

严格 `operational_pit_v1` 仍使用真实接收时间，接收前不回填此提示；revision-bound
证据另按统一 PIT 合同处理。best-effort 提示明确是留存终态来源下的回溯不确定范围，
不是宣称当年公开知道了整个组。正常单行实施事件的原通知时钟不变。

本节已按 2026-10-04 裁决定稿；不能只修改反例期望来接受空结果。

<a id="etf-unit-split-proposal"></a>
### 6.2 ETF 份额拆分的最小事实合同

状态：2026-10-04 有界语义裁决与 Data 准确合同已对齐，本节独立提交供亲审；
Trade 保存 shape 另行对齐。实现与验收仍未完成，当前账户不据此解锁。首轮只接入、验收以下两条官方事件；实现按
有明确比例、生效阶段和取整规则的 ETF 份额拆分合同处理，不写证券代码或日期特判。
未来同语义事件可由 Data 追加；现金补偿、份额合并等未支持类型仍明确 unsupported。
不建立通用公司行动平台。表内公告结论由协调方核对，正式输入仍需固定原件与修订证据。

| 证券 | 登记与生效边界 | 官方比例与取整 | 后续价格尺度 |
|---|---|---|---|
| 513100.SH | 2022-01-12 登记；01-13 拆分并全天停牌；01-14 复牌 | 1 份变 5 份，精确比值 `5/1` | 01-14 首个拆分后交易 session；01-13 原行情缺行保留 |
| 510500.SH | 2022-08-26 收市后折算 | 精确比值 `114539/100000`；按同一持有人合计份额向上取整 | 08-29 首个折算后交易 session |

Data 唯一负责事实与来源，窄域名统一为 `fund_share_conversions`，走正常
Raw → update → Snapshot → `Data.events`，复用修订机制与通用 Reader；不混装既有
Tushare `corporate_actions` profile，不增加私有读取路径。合同 ID 为
`local.fund_share_conversions.reviewed_disclosure.v1`，source profile 为
`issuer_fund_disclosure_supplement_v1`；逻辑键为 `security_id + event_id`。

| 准确字段名 | 初版值、类型与边界 |
|---|---|
| `security_id`、`event_id` | 非空 string；稳定证券与经济事件身份，不由可修正比例、日期、阶段或文档 hash 重新生成 |
| `event_type`、`process_status` | `unit_split`；`planned / implemented`，同事件保留计划与结果修订 |
| `announcement_date`、`announcement_precision` | 非空 date 与 string；精度枚举为 `day`，没有原始日内发布时间 |
| `record_date`、`effective_date`、`effective_phase` | 非空日期；阶段为 `end_of_day / not_stated`。513100 为 `not_stated`，不能改作官方 pre-open 或可卖事实 |
| `new_price_basis_session`、`new_price_basis_basis` | nullable date/string；513100 为公告折算/复牌关系，510500 为收市后折算加固定日历的 next-open 单位解释，非独立价格认证 |
| `ratio_numerator`、`ratio_denominator` | 非空 int64、无量纲正整数的最简分数：一份旧单位对应的新份额数，不从因子倒推 |
| `quantity_rounding`、`quantity_rounding_scope` | 513100 为 `not_stated / null`；510500 为 `ceiling_to_whole_fund_unit / registered_holder_units`；NAV 四位小数规则不是数量取整规则 |
| `suspension_start`、`suspension_end`、`suspension_scope`、`resume_session` | nullable 日期/string；513100 为 01-13 全天 `full_session`、01-14 复牌。510500 全部 null 表示未提供，不表示正常交易；协议回购限制不等于二级市场停牌 |
| `document_refs`、`extraction_version` | 非空 string；前者是 Raw 内文档 ID 的 canonical JSON 字符串，后者固定为 `reviewed_fund_share_conversions_v1` |
| `revision_id`、`revision_sequence` | 非空 string/int64；序号 1/2 为审阅后的计划/结果文档顺序，不是供应商版本号、receipt 顺序或完整修订链证明 |
| `first_observed_at`、`raw_batch_id` | 非空 timestamp/string；由实际完整 bundle 接收与正常归一化赋值，例子不伪造生产 ID |
| `source_available_at`、`evidence_ref` | nullable timestamp/string；首版均为 null，不升级 strict 历史可见性 |

两个稳定事件 ID 为 `gtfund:513100:unit-split:2022-01` 与
`nffund:510500:unit-split:2022-08`；修正日期或比例不改身份。原件 bytes、发行人、URL、
检索 host、hash、真实捕获时间与字段 locator 一次保存在 Raw bundle，`document_refs`
在同一 bundle 内解析，不建文档 registry。公开证据 attachment 须与目标修订全部认证
字段精确匹配；不能借结果认证计划，或把 Engine 模型可卖时点/不再次 T+1 一起认证。

公开输入摘录如下，字段全集与约束以上表为准；示例不含生产 Raw/revision ID 或本机路径，
`first_observed_at`、`raw_batch_id`、`revision_id` 由真实 ingest/归一化生成。原件 bytes 按
Raw bundle 保存，不以内嵌示例替代原件。

```json
{
  "record": {
    "security_id": "cn.etf.SSE.510500.20130315",
    "event_id": "nffund:510500:unit-split:2022-08",
    "event_type": "unit_split",
    "announcement_precision": "day",
    "record_date": "2022-08-26",
    "effective_date": "2022-08-26",
    "effective_phase": "end_of_day",
    "new_price_basis_session": "2022-08-29",
    "new_price_basis_basis": "declared_next_open_price_unit_interpretation_after_issuer_end_of_day_conversion",
    "ratio_numerator": 114539,
    "ratio_denominator": 100000,
    "quantity_rounding": "ceiling_to_whole_fund_unit",
    "quantity_rounding_scope": "registered_holder_units",
    "suspension_start": null,
    "suspension_end": null,
    "suspension_scope": null,
    "resume_session": null,
    "extraction_version": "reviewed_fund_share_conversions_v1",
    "announcement_date": "2022-08-23",
    "process_status": "planned",
    "document_refs": "[\"510500-plan-20220823\"]",
    "revision_sequence": 1
  },
  "source_document": {
    "document_id": "510500-plan-20220823",
    "issuer": "南方基金管理股份有限公司",
    "source_url": "https://www.sse.com.cn/disclosure/fund/announcement/c/new/2022-08-23/510500_20220823_1_aMMa3ZNB.pdf",
    "sha256": "2c933c4c0fddf34b5e90ab711990d34be0644d66275a7d8ea9a40467ebdb586c",
    "locator": "PDF p1 §一1-3: Aug26, ratio1.14539, end-of-day registered holdings, holder-unit ceiling; p2 §一4: next business Aug29; p3 signature Aug23"
  }
}
```

四条记录分别保存计划与结果，不把结果知识前移。next-open 为明确 best-effort 假设，
使用 Asia/Shanghai 09:30，按每条 revision 的公告日单独计算：

| 事件 | 计划公告 → usable_from | 结果公告 → usable_from |
|---|---|---|
| 513100 | 2022-01-04 → 01-05 09:30 | 2022-01-14 → 01-17 09:30 |
| 510500 | 2022-08-23 → 08-24 09:30 | 2022-08-29 → 08-30 09:30 |

两份计划已各自披露精确比例；生效日前可见计划足以提供本轮安排，结果仍不可见时不应
过滤成没有事件。`Data.events(EventQuery(...))` 使用 `time_field='effective_date'`，
先按 policy/cutoff 选择可见 revision，再过滤经济日期；不能先筛 `implemented` 而丢掉
可见计划。本轮有界读取包含两事件生效日期，随后检查其可见停牌范围；不新增通用范围
重叠查询。结果后来可见时独立核对，不改变此前 cutoff 输出，见
[Trade §9.2](04_axiom_trade.md#etf-unit-split-application-proposal)。

真实接收仍在 2026；文档路径日期/签名日或本次抓取不证明历史发布瞬间。
`operational_pit_v1` 与没有精确修订 public evidence 的 `market_pit_safe_v1` 在 2022
均不可见；next-open 只属于 best-effort 探索。Raw-first 保存完整 bundle，验证 bytes hash、
引用、比例、取整及审阅顺序，再归一化；重试/同 bundle rebuild 保留原 receipt，不重复抓取。
新 Snapshot 的有界验证、旧域等价与独立审阅后才按既有发布流程处理，不重采日线。

首版不改 `Data.states`。Engine 从同一固定 Snapshot 与明确 cutoff 读取公共事件，将
有证据且当时可见的停牌安排作为额外禁止成交条件；原 `UNKNOWN` 保留，展示具体事件依据，
不能将事件覆盖外的 UNKNOWN 改为正常交易或声称已恢复完整停牌历史。

比例来自公告，不能从 `1→5.0019` 或 `.2803→.3211` 倒推。Data 固定事件与供应商新价格
尺度的日期关系、精度及已知限制，Engine 审计只接受已支持且证据匹配的映射；其他跳变
仍阻断。追加事实须发布新 Snapshot，旧 Snapshot/Raw/行情缺行/产物不变，不手改因子。
读取范围覆盖登记、生效及新价格尺度；缺失或冲突字段不能投影为空事件或零行动，有限
公告证据也不证明全历史完整。Research 复用现有共同锚点复权与 Core 配方；账户应用归
Trade，UI 只读 owner 保存事实与流水。

## 7. 一个 Reader，薄的消费者映射

默认同机 Python，不建微服务。以下是接口提案：

```python
data = Data(root=ROOT)
result = data.update(base_snapshot=BASE_OR_NONE, request=UPDATE_SPEC)
rebuilt = data.rebuild(base_snapshot=BASE, raw_batch_ids=RAW_IDS, domains=DOMAINS)
snapshot = data.resolve("current")  # 本次任务只解析一次
batch = data.read(snapshot=snapshot, query=QUERY)
members = data.members(snapshot=snapshot, query=MEMBERS_QUERY)
events = data.events(snapshot=snapshot, query=EVENT_QUERY)
replay = data.read_market(snapshot=snapshot, query=MARKET_QUERY)  # Runtime 执行侧
issues = data.inspect(snapshot, required_scope=SCOPE)
```

表格读取统一返回 `DataBatch(frame, field_meta, context)`。frame 是带键的 DataFrame；context 保存 schema、实际 Snapshot/查询 refs、query 参数、Reader/派生版本和 quality/limitations。UI JSON 仅把 frame 转为 records，返回 `records + field_meta + context`。field_meta 按键与字段关联来源/revision、usable_from、first_observed、依据和缺失原因；同源同时间字段可共用元信息，不逐单元格复制全套 manifest。update/rebuild 返回 Snapshot ID、changed、issues 与本次操作 ID；失败不返回成功的新版本，inspect 返回范围与问题摘要，无需强行塞成行情表。

QuerySpec 固定 Snapshot、字段、scope、PIT/cutoff、价格/复权口径和派生配方；结果 context 再记录实际 Reader/派生实现版本。实验保存这个结构即为逻辑 ViewRef，不需要为查询发布另一个 artifact。按用途保留 Fact/Market 的区别；首次只实现真实消费者需要的方法。

context 的 `contract_version` 标识 DataBatch 返回结构，独立于 Snapshot schema 与 Reader 实现版本；`generated_at` 是这次响应生成时间，不是行情新鲜度或历史可用时间。实际数据时间由 session、field_meta 和域覆盖表达。 本地 DataBatch 的 `to_json()` 保留可复现的语义内容；API 传输使用 `to_response()` 添加 context.generated_at，UI/P12 另有自己的响应生成时间。生成时间不进入逻辑 ViewRef 或缓存身份。UI 映射保留这些字段，同时使用自己的 P12 组合协议版本；未知必要字段/不兼容版本明确报错，不靠列位置或静默默认解释。

同一次 scope/Reader 调用可复用已校验、Snapshot ID 一致的 manifest 对象，避免内部重复加载；不同 Snapshot 不共享该对象，不引入跨调用的全局信任缓存。manifest 完整性校验的分块编码须保持既有 canonical JSON 字节及 Snapshot hash 身份，损坏仍须拒绝；不得为节省内存省略校验、改 PIT/缺失语义、重写旧 Snapshot 或新增持久格式。结果缓存的容量不代表 manifest/临时编码的内存上限；性能验收分别记录 wall time 和进程 peak RSS。

Research/Runtime adapter 按同一合同映射为 Core FactBatch；Core 不读 Data 磁盘。Runtime 给决策与成交模拟注入不同 Reader 权限：开盘决策不能提前看完整日线，simulator 只能随时钟推进读取随后行情。UI 后端将同一结果转为 JSON，保存 query context；不重算 Feature、不联网补数。

### 7.1 用途查询的共同语义

上述 QUERY 均为用途明确的 QuerySpec：固定具体 Snapshot、scope、字段/事件选择和时间规则。成员查询包含 universe、生效 session 与 knowledge cutoff；事件查询包含事件种类、经济时间范围与 knowledge cutoff；两者都显式选择 PIT policy，不能只传 cutoff 后让 Reader 猜政策。scope 可用显式 sessions；使用区间时声明端点含义。QuerySpec 内若也含 snapshot_id，必须与函数参数一致。

MARKET_QUERY 绑定执行用途、证券/区间、未复权价格与所需状态/行动/规则，以及事件时间和所选历史修订解释。Runtime 可以预读固定回放文件，但按执行时钟释放事件，不能把后来完整日线或事件反送给早期决策。记录回放近似与来源限制；仅有 session 范围不构成完整的执行时间合同。

Research 构建 Label 时可以显式查询未来结果范围，保存独立 QuerySpec/上下文，由 Research 定义收益口径、maturity 与训练 cutoff。它不是该样本决策时的事实输入，不能进入 Feature FactBatch。Data 不解释 Label 公式，Runtime 不用 Label 代替成交回放。

### 7.2 四仓之间的数据与协议

| 路径 | 调用和交换内容 | 协议与 owner |
|---|---|---|
| Data → Research | Python Reader 返回 DataBatch；Research adapter 映射事实供 Core 计算，保存 FeatureBuild | P02 Data；P05 Core；P06 Research |
| Data → Engine/Runtime | 同一 Reader 提供决策事实与执行回放；Runtime adapter 注入 Core | P02/P03 Data；P05/P07 Core；P11 Runtime |
| Research → Engine | 冻结 Feature/Model/Strategy 运行包；BacktestRequest；返回 BacktestRun/EvaluationReport | P06 Research；P09 与账户 P10 Runtime |
| Data → UI BFF | records + field_meta + context，作为事实图层输入 | P02/P03 Data，P12 组合归 UI |
| Research/Runtime → UI BFF | 已保存 Feature/Signal/trace/委托/成交/账户/评估的只读投影 | P06/P08/P10/P11 各 owner；P12 UI |

物理仓库为 axiom-data、axiom-engine、axiom-research、axiom-ui；Engine 内 Core 与 Runtime 逻辑分开。Data 不依赖 Core 或 Research；Research 与 Runtime 各自拥有消费 Data 的 adapter，Core 拥有 FactBatch ABI。DataBatch 的 schema 归 Data，FactBatch 的 schema 归 Core；adapter 按键映射并保留单位、cutoff、缺失和来源，不重做 PIT、复权或 Feature。

Research 负责研究编排与训练，Feature/推理/信号共享执行由 Core 完成；正式回测只调用 Runtime。生产 Runtime 加载冻结的轻量运行包，不 import 可变 Research workspace。FeatureBuild/SignalRun 的合同归 Research，研究时写 Research 产物空间，运行时生成的写对应 Trade run 空间，均不写入 Data Snapshot。

UI 浏览器访问只读 BFF；BFF 调用各 owner 公共查询包，不直接拼 Raw/Parquet/账本来重新解释业务。Data JSON 不是完整 P12：ChartContext 还固定 run/build/stage、价格/时间口径及实际 refs；ChartLayer 组合各来源、缺失/重建状态，账户部分带 committed watermark。具体格式由 [UI §5–7](06_axiom_ui.md) 定义。首版同机函数调用足够，不要求每仓提供 HTTP 服务。

固定版本的粒度是一项离线实验，或长服务中的一个 session/决策批次。下一批可重新解析并检查新版本；已开始批次不变。长 run 保存 batch/session → Snapshot/QuerySpec 的实际映射，UI 重放沿此映射读取，不能只用最终 Snapshot。尚未进入 Data 的实时输入以 Runtime feed log 为来源，不冒称来自事后 Snapshot。

read 不采集、不修复、不隐式物化。Qlib已纳入本轮交付：显式export_qlib保存文件清单、完整开放日历/身份映射、原始单位、scope/PIT cutoffs、float32容差与exporter版本；实际Qlib读取与Reader等价。价格仍未复权，不暗中套训练归一化口径；财务/分红保持原生事件，不自动前填为日频bin。Research拥有Qlib初始化和消费adapter，P02/P03不依赖Qlib。详见[Qlib接口](../qlib-interface.md)。

<a id="review-display"></a>
### 7.3 复盘显示所需的固定事实与投影

状态：2026-10-05 设计提案，待总协调亲审；本节不表示新增接口、采集或实现已经验收。
本轮需要真实沪深300、上证指数和 Nasdaq100 基准、默认复权且可切未复权的 K 线，
以及中文证券名称与代码。Data 保存事实查询结果和稳定显示变换；账户、比较收益及
成交标记组合仍由各消费者 owner 保存，UI 读取这些结果，具体组合协议归 UI。

本轮只读盘点以固定版本为准，没有执行全历史 Reader 或新增来源请求。现有
[benchmark/master adapter](https://github.com/sinnergarden/axiom-data/blob/1bb85e354b70200946049b937ba023f60e5fe310/src/axiom_data/provider_local.py#L53)
的指数合同只保存 `close`（指数点），股票身份合同未声明名称或 `source_code`；
[ETF adapter](https://github.com/sinnergarden/axiom-data/blob/1bb85e354b70200946049b937ba023f60e5fe310/src/axiom_data/provider_etf.py#L36)
已保存这两个身份字段。固定 ETF 版本的146个基准分区 footer 只有 `000300.SH`，
日期外包络为2014-08-18至2026-09-30，共2,947行；这是存储索引盘点，不证明唯一键数、
中间无缺口或任意 cutoff 可见。该版本的7条 `security_master` 均有中文简称。
股票固定版本仅复用已有审计索引核了2026-09的基准小分区：`000300.SH / 000905.SH /
000852.SH` 各21条日期键；身份分区3,497行的 schema 没有名称，既有 Raw 抽样也未捕获
`name`。本轮未核整个股票历史基准映射，不能据9月小分区宣称其他历史分区不存在。

<a id="benchmark-facts"></a>
#### 7.3.1 真实基准的来源和时间口径

| 目标 | 目标事实口径 | 现有保存与官方来源边界 |
|---|---|---|
| 沪深300 | `000300.SH`；人民币价格指数；单位为指数点 | ETF 固定版本已有上述范围，股票9月小分区也有；复用固定版本内的 `index_daily`，具体 UI 范围再做有界 Reader 检查 |
| 上证指数 | `000001.SH`；人民币价格指数；单位为指数点 | ETF 基准分区未保存，股票已核9月分区未保存；官方 `index_daily` 支持按确认的指数代码和日期取数，不据此推定现有完整历史已保存 |
| Nasdaq100 | NDX；美元价格指数；美国本地交易 session | 固定 ETF 基准未保存，当前代码没有国际指数 adapter；Tushare `index_global` 公开列表列出 IXIC，未列出 NDX，Nasdaq100 的可用 Tushare endpoint/code 与账户权限尚未确认 |

沪深300与上证指数的名称、人民币口径及分别存在的全收益版本见
[中证沪深300资料](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000300factsheet.pdf)和
[上证指数资料](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/000001factsheet.pdf)。
价格与总收益是不同序列，不能给价格指数加一个 TR 标签；是否展示总收益及与策略账户的
可比口径由 Research/Engine 明示。Nasdaq 官方将 NDX 定义为美元价格收益版本，
XNDX 为美元总收益版本，见 [NDX 版本表](https://indexes.nasdaqomx.com/docs/NDX%20Versions.pdf)。
本轮所需为 Nasdaq100，不用 Nasdaq Composite、513100 基金价格或由ETF收益反推的
序列替代真实指数。[Tushare 国际指数](https://tushare.pro/document/2?doc_id=211)的已列能力
不能证明供应商其他接口一概没有 NDX；当前结论是来源未确认，应明确报告不可用原因。

基准事实导出输入固定 Snapshot、确认的指数身份、原生日期范围、字段、PIT policy 与
knowledge cutoff。输出保留原生 `session + close`、指数点单位、来源/revision/receipt、
缺失原因和实际 query refs，并明确指数名称、`return_basis`、币种、日历与时区。
这些口径元信息是待补的 Data 合同，不声称当前 close-only schema 已具备。比较基值、
净值、超额收益和评估指标由 Research/Engine 计算并保存其配方，不写回原生指数。
美元指数与人民币账户比较须明示原币种；若要人民币换算，另绑定真实汇率事实、固定
cutoff 与消费者换算配方，缺汇率不能静默按1处理。本轮不新增付费来源或汇率采集。

国内来源沿用固定交易日历与 `Asia/Shanghai`；国际来源保留美国本地 session 与
`America/New_York` 的时区解释，不按中美同一日期直接拼成同时可知事实。美股当地
收盘值用于国内决策时须检查实际绝对可用时刻；消费者若作 as-of 对齐，保存真实源
session、陈旧程度和对齐规则，不能前填为新的交易事实或提前送入信号。
[Tushare 指数日线](https://tushare.pro/document/2?doc_id=95)未承诺固定刷新时刻；当前国内
profile 的20:00仅为既有 best-effort 假设，不是官方 SLA 或历史 PIT 证据。
[us_tradecal](https://tushare.pro/document/2?doc_id=253)只提供开市日期与前一交易日，
没有交易所参数、收盘时钟或半日市字段，不能据它构造全年固定 UTC 收盘时刻。
未确认国际 source readiness 前，不沿用国内20:00假设；实际 receipt 与日更就绪仍按
[§8.1](#source-readiness)区分。

<a id="display-price-projection"></a>
#### 7.3.2 事后复盘的共同锚点价格显示

这是事后回看的显示产物。图表绑定一个固定知识截止 C，可晚于历史成交；它不替换
原实验/模型的逐决策 PIT 输入，不改变历史 cutoff、真实成交价或账本。Data 显式生成
并保存投影，BFF/浏览器读取已有文件；普通 Reader 不因此要求物化，也不在浏览或缩放
时补采、重新复权或改 `current`。复用普通 typed 文件与附带 context/refs 即可，不新增
发布 registry、通用缓存治理或一套新的对象生命周期。

| 输入/输出 | 准确边界 |
|---|---|
| 固定输入 | 一个 Snapshot、稳定 security_id、完整显示跨度、明确 anchor session A、一个共同截止 C、PIT policy、未复权 OHLC、原始量额与同源日频 `factor` 的公共 QuerySpec |
| 固定价格输出 | `display_price(t) = native_price(t) × factor(t) / factor(A)`；只变换 open/high/low/close，保留并可切换 native OHLC。可选 pre_close 须保留供应商原口径说明 |
| 量额与映射 | 原始 `volume_shares` 或 `volume_units`、`amount_cny` 按原单位保存；不乘价格复权比。另保存按 security/session 的实际变换比、价格单位和价格/因子/anchor refs |
| 可复现上下文 | 输入查询、Snapshot、配方与实现版本、A、C、价格基础、政策、源限制、缺失原因；生成时间不是历史可用时刻。UI 只切字段与截取已保存范围 |

现公开纯函数
[`adjust_prices`](https://github.com/sinnergarden/axiom-data/blob/1bb85e354b70200946049b937ba023f60e5fe310/src/axiom_data/derived.py#L118)
可复用，配方为 `common_anchor_price_v1`；实际 canonical 字段是 `factor`，调用须显式
传 `factor_field='factor'`。价格/因子必须同 Snapshot、政策、用途、身份与共同 cutoff，
因子范围精确覆盖价格范围并包括 A；函数没有 I/O，不自动保存量额、事件或名称。
保持其未来 anchor 拒绝规则：本节首次生成的完整价格跨度终止于 A，以 A 为该次纯函数
输入的最晚 session；这里的参数不是历史策略决策时刻。随后展示较早 viewport 只裁切
这个固定输出，不随 viewport 重定锚点，也不通过放宽函数检查把未来锚点送回模型。

价格、因子或 anchor 缺失/无效时保留 null 与原因；不能把缺因子补1、以价格跳变推因子，
或为图形连续造停牌价。供应商因子终态的 vintage 限制随产物保留。官方拆分等事件从
同 Snapshot、C 与政策下的公共 events 查询读取，保留经济日期、revision、进度、公告
精度与 refs；事件标记不意味着已覆盖全历史。份额比例、新价格尺度 session 与已支持
的两项 ETF 事件按 [§6.2](#etf-unit-split-proposal)解释，不把公告份额比例再次乘到已经
使用供应商累计因子的显示价格上。

Data 提供事实变换比及其适用 session/价格单位。Engine 负责将其与真实成交流水的
security_id、成交 session 和单位对齐，并保存 B/S 的显示坐标；同尺度时坐标为真实
成交价乘该固定比值，真实成交价、数量、费用、现金、持仓和损益均保持原账本事实。
发生份额拆分时须检查新价格尺度 session，不能仅按 effective_date 猜开盘或收盘单位；
日内尺度无法由现有日线/公告判定，或因子/单位不匹配时，显示坐标缺失并说明原因。
Data 不读取账本来裁决成交，UI 不临时把成交标记挪到蜡烛上。

<a id="security-display-identity"></a>
#### 7.3.3 中文名称、代码和有效期

输入为固定 Snapshot、稳定证券集合、展示日期与知识截止，明确选择“该 Snapshot 的
名称标签”或有证据的历史名称。Data 输出 `security_id + source_code + name`、名称
种类/来源、名称有效起止（未知为 null）、原生区间端点语义、可用时间与 refs/缺失原因。
名称有效期与上市/退市生命周期分开；2026才收到的简称不能标成2014即已有效，上市日
不是名称起始日，名称变更也不改变稳定证券身份。浏览器不从 ID 拆代码、不维护手写
中文映射；缺名称时显示 owner 给出的代码和名称未提供状态。

7ETF 已有 [fund_basic](https://tushare.pro/document/2?doc_id=19) 的固定简称与代码，先
复用作版本标签；当前没有名称历史区间证据。[etf_basic](https://tushare.pro/document/2?doc_id=385)
另有中文简称、交易所扩位简称和跟踪指数代码/名称，但未接入，也不是历史指数行情
接口，不能仅为已有简称重新采7ETF。[stock_basic](https://tushare.pro/document/2?doc_id=25)
官方支持名称；当前请求字段与 canonical 未捕获它，先检查目标 Raw，确有留存字段才
能复用原 receipt 显式重建。缺少字段时只补本轮显示/持仓证券的身份资料并保存新观察，
不改写旧 Raw 或旧名称可见性；已有 ts_code 由 Data 的固定身份映射提供。

需要准确历史名称时，再对明确证券启用
[namechange](https://tushare.pro/document/2?doc_id=100)，保存 start/end 与 ann_date。
该接口请求的 start/end 参数筛的是公告日期，不是输出名称的生效区间；只取图内公告
可能漏掉图前已生效的名称，须包含必要的前置记录。保留供应商端点语义，若转成半开
区间则明确转换；日期精度也不证明历史日内公开时刻。ETF 现有简称源没有这个能力时
报告未知历史区间，不扩建全市场名称历史平台。

#### 7.3.4 亲审后的最小执行顺序与验收

1. 先冻结本轮 UI 已绑定 run/build 的证券、展示起止、比较基点、A、C、政策与币种。
   新显示投影另存引用，原 run/model 输入与账本绑定不变；把重型读取/导出与 Research
   Notebook 错开。全股票 manifest 或长范围 Reader 的 fresh 验证另排，不与小索引盘点混称。
2. 先复用已有行情、因子、7ETF名称、事件和 `000300.SH`。检查固定版本仅在该范围内的
   可用性；复权显示本身不要求重采日线。上证指数缺口以 `index_daily(ts_code='000001.SH',
   start_date=..., end_date=...)` 显式补本轮展示范围及必要的首点前一交易日；先一个不超过
   31自然日的小窗口核身份、单位、日期与 receipt，再仅补已确认范围缺口，不自动十二年重采。
3. 股票名称先用目标 Raw 的字段检查；没有 name 时只请求该证券集合的 stock_basic 身份
   字段，包含已退出但在本轮显示/持仓中的证券。历史名称非本轮标签必需时可后做；不得用
   当前简称伪造历史有效期。
4. Nasdaq100 先确认官方可用 Tushare endpoint、准确供应商 code、价格/币种与现有账户权限；
   如需跟踪元信息，只对513100作有界 `etf_basic`/确认代码的
   [etf_index](https://tushare.pro/document/2?doc_id=386) 查询，并声明各自
   官方8000积分权限要求。元信息不证明日线可取。确认行情接口后才安排最多10个 session
   的来源/美国日期/receipt 小探测及同范围日历；没有权限或确定来源则保留该基准不可用，
   不购买新源、不盲试未列代码、不自动换 IXIC。长范围补采须另给准确 selectors 与预算。
5. 验收只覆盖实际范围：核保存投影与公共 `adjust_prices` 一致、缩放不换 A、量额/native价
   保持原单位、两次已支持拆分的标记与尺度关系、缺因子/缺价/缺名称/缺基准可解释；由
   Engine 核 B/S 坐标及原成交/账户不变，Research/Engine 核跨市场比较口径和可用时间。
   当前终态假设不升级历史 PIT，缺口不隐藏。通过后交付固定文件/查询 refs 与范围报告，
   不以文档通过代替实现验收，不触发全年或多年 ML 扩跑。

## 8. 日更、修复与最小检查

<a id="source-readiness"></a>
### 8.1 数据源刷新与依赖就绪

状态：2026-10-04 已确认的运行设计；具体调度时刻仍为可配置建议，未验收成服务 SLA。不把采集、校验和模型推理统一设在收盘后。Data 分别报告每域请求完成、业务截止日、实际观察时间、字段/键覆盖、就绪质量及限制；Research 声明模型所需 domain/字段、历史长度、允许滞后、required/optional 和缺数策略；Runtime 按该依赖契约检查可用性，必需依赖就绪后调用 Core。仅用行情的模型不等待无关两融，UI 和 Data 不替模型猜是否可用。

下表是本设计的唯一接口时序表。时间为 Asia/Shanghai；官方说明是请求计划依据，不是某条 revision 在模拟 cutoff 前可知的证据。详情和总表不一致时保留双方来源；没有固定时刻就明确未承诺，不能从成功一次请求推导通用保证。接入列只表示已有 adapter 能力，不代表所有 Snapshot 有完整范围或字段，依据 [Data 0.3.8 固定源码](https://github.com/sinnergarden/axiom-data/tree/54e98c62cb594da2e4bd83d71b1167d4ba1877bf/src/axiom_data)核对。

| Endpoint | 业务日或期间 | 官方刷新说明 | 当前接入 | 就绪检查 | 来源与核对日期 |
|---|---|---|---|---|---|
| daily | 行情日 T | 详情 15–16；总表 15–17，计划保留较宽窗口 | 是 | 目标日证券/字段与缺失原因，不只看请求成功 | [27](https://tushare.pro/document/2?doc_id=27)、[总表108](https://tushare.pro/document/1?doc_id=108) · 2026-10-04 |
| fund_daily | ETF 行情日 T | 仅说明收盘后，未给完成钟点 | 是 | 固定 ETF 范围、OHLC/量额、当日覆盖 | [127](https://tushare.pro/document/2?doc_id=127) · 2026-10-04 |
| index_daily | 指数行情日 T | 总表 15–17 | 是 | 所需指数与 anchor/session 价格覆盖 | [总表108](https://tushare.pro/document/1?doc_id=108) · 2026-10-04 |
| adj_factor | 因子日期，可为执行日 D | 当日盘前 09:15–09:20 | 是 | 请求日期、因子与可知时点；不能用 D 日钟点回填 T 收盘 | [28](https://tushare.pro/document/2?doc_id=28) · 2026-10-04 |
| fund_adj | ETF 因子日期 | 总表每日 17:00 | 是 | 实际日期、单位/price basis、缺因子和观察时间 | [总表108](https://tushare.pro/document/1?doc_id=108) · 2026-10-04 |
| stk_limit | 当日执行限价 D | 约 09:00 | 是 | D 日证券限价，保留实际可用时间 | [183](https://tushare.pro/document/2?doc_id=183) · 2026-10-04 |
| etf_limit | ETF 当日执行限价 D | 约 08:40 | 是 | D 日 ETF 限价、缺源及执行用途 | [491](https://tushare.pro/document/2?doc_id=491) · 2026-10-04 |
| suspend_d | 停复牌事件日 | 不定期 | 是 | 事件/范围覆盖；空结果不能直接证明正常交易 | [214](https://tushare.pro/document/2?doc_id=214) · 2026-10-04 |
| dividend | 公告及登记/EX/PAY 日期 | 详情每日 20–21；总表写实时更新 | 是 | 经济日期与公开/观察时间分离，晚到修订保留 | [103](https://tushare.pro/document/2?doc_id=103)、[总表108](https://tushare.pro/document/1?doc_id=108) · 2026-10-04 |
| fund_div | ETF 公告及权益日期 | 无固定钟点；总表定期更新 | 是 | 当时已知事件范围，不声称源完整 | [120](https://tushare.pro/document/2?doc_id=120)、[总表108](https://tushare.pro/document/1?doc_id=108) · 2026-10-04 |
| trade_cal | 交易所自然日期范围 | 详情未承诺固定钟点 | 是 | 目标交易所、T→D 与月边界覆盖 | [26](https://tushare.pro/document/2?doc_id=26) · 2026-10-04 |
| stock_basic / fund_basic | 证券基础及上市范围 | 详情未承诺统一钟点；基金总表定时更新 | 是 | 证券身份、上市/退市边界与实际版本 | [25](https://tushare.pro/document/2?doc_id=25)、[19](https://tushare.pro/document/2?doc_id=19) · 2026-10-04 |
| income / balancesheet / cashflow | 报告期和公告日 | 详情未承诺统一钟点；总表实时更新 | 是，含已有 VIP 路径 | 固定报告范围、revision 可知性和查询 cutoff | [33](https://tushare.pro/document/2?doc_id=33)、[36](https://tushare.pro/document/2?doc_id=36)、[44](https://tushare.pro/document/2?doc_id=44) · 2026-10-04 |
| fina_indicator | 报告期和公告日 | 详情未承诺固定钟点；总表随财报更新 | 是，含已有 VIP 路径 | 报告类型、所需字段及可用版本 | [79](https://tushare.pro/document/2?doc_id=79) · 2026-10-04 |
| top10_holders | 报告期和公告日 | 详情未承诺统一钟点 | 是 | 完整组和 revision，缺组不补零 | [61](https://tushare.pro/document/2?doc_id=61) · 2026-10-04 |
| index_weight | 月度成员/权重 | 月度，不要求每天有新值 | 是 | 使用的有效范围和成员限制，不能假装日级快照 | [96](https://tushare.pro/document/2?doc_id=96) · 2026-10-04 |
| margin | 上一业务日 T | 交易所约 08:30；接口称最晚 09:05；深/北周五数据下周一上午 | 否，未来延迟源示例 | 按业务日和交易所检查；假日完整发布日历未定义 | [58](https://tushare.pro/document/2?doc_id=58) · 2026-10-04 |
| margin_detail | 上一业务日 T | 详情未作 09:05 承诺；深/北周五数据下周一上午 | 否，未来延迟源示例 | 不沿用 margin 的完成钟点；保留缺口/实际观察 | [59](https://tushare.pro/document/2?doc_id=59) · 2026-10-04 |

统一时序以 T（特征业务交易日）、D（由交易日历计算的下一执行交易日）、C（输入冻结时点）、E（意图有效截止）表述。可分盘后行情预计算、夜间事件、次晨迟到源及执行日事实，随后按模型 required 依赖冻结 Snapshot/query，再调用 Core infer。C/E 要留实测计算和执行预算，不能通用写死 09:10；例如模型确需 D 日股票因子时官方窗口可至 09:20。到 C 必需输入仍缺失则跳过或阻断；optional 严格按事前缺数合同处理，不隐式补零、使用未来值或替换模型。原始观察时间不回填，迟到/修订产生新 Snapshot，不改旧决策。两融仍未接入，本轮 ETF 不扩展到 ML 或新的调度系统。

### 8.2 日更发布与修复

```text
固定 parent Snapshot、请求范围、代码/合同/配置
→ 请求并保存 Raw/fetch 日志
→ 转换与实际范围检查
→ 写受影响分区新对象，复用其他文件
→ 形成完整候选 Snapshot，current 仍指向固定 parent
→ verify 检查请求完成、来源绑定及文件完整性
→ source audit 核对映射、单位与来源范围
→ 保存紧凑质量摘要及相对 parent 的版本差异
→ 技术校验无错后，按固定 parent 显式原子更新 current
```

单写者和一个操作 checkpoint 足够。成功 Raw 可续用；必需范围失败不切默认版本。可选域沿用旧段并说明其数据时间/缺口，不阻断无关研究。开始读取时解析 current 一次；下一任务才使用新版本。无须每天人工审批。

bulk 与 daily 使用相同的作业验收顺序。利用已有 `plan --no-promote`、候选版本的 `verify`/`audit` 和显式 promote 能力即可；不要为此新增登记或审批框架。请求未完成、错误映射/单位/类型、来源或文件绑定错误不得推广。供应商缺行、UNKNOWN 和不可裁决事件允许 `limited`，保存具体范围及原因后推广；这不等于任意研究或成交用途的覆盖已完整。每个最终作业候选验收一次，不在每个 chunk 重复全历史审计；未变化的对象及其已有检查证据可复用，报告注明复核范围和引用。

每次质量摘要至少记录候选与 parent 的具体 Snapshot、实际 builder/合同/profile、各域最新经济日期与原生覆盖范围、实际 receipt、上市开市范围内未解释行情缺口、因子与双向限价缺失、UNKNOWN 状态、事件歧义及版本差异。日频证券×session、原生事件组和财报字段分别给分子分母；未上市、退市、明确停牌和普通来源空值不混作异常。空响应和最新目录名不证明数据已完整或可交易，不从价格推造限价，也不把 UNKNOWN 改成正常。

按实际 endpoint 分别保存业务日期、供应商可请求/更新窗口、PIT 可用规则和实际收到时间；这些时间不能由“收盘”或一个统一发布小时替代。profile 中用于 best-effort PIT 的假设时刻不等于供应商已就绪的证据。作业先依据声明来源和范围判断已到获取窗口，再核对实际响应的业务日期/字段/键；未到窗口或供应商暂未更新记录为该作业的待就绪状态，保留空响应及重试记录，不把它裁决成永久缺失或改写 Canonical 缺失状态。

候选收集成功和模型所需范围已就绪分别记录。模型或任务声明必需域/日期/字段；其中待就绪的项不得提前推广为该用途的完整版本，infer 固定通过该范围检查的 Snapshot。可选域沿用旧版本时说明数据日期与缺口。已到窗口但仍缺行、来源不能证明完整、事件有歧义的情况保持 `limited`，并明确它是否满足当前声明用途；不因 `limited` 统一阻断所有事实发布，也不据此绕过必需范围的就绪检查。使用现有作业/checkpoint 和显式检查即可，暂不新增调度框架或未接入的来源。

来源分别定义发布时间、可请求日期、分页和重查策略；不能假设只扫近几天能发现所有历史修订。修复优先从 Raw 重建受影响分区；必要人工 patch 保存目标稳定键、旧值、新值、原因及来源，不改旧 Raw。所有入口走同一更新/重建函数，不预建通用 patch DSL 或证据工作流。

日更回看窗口之外的供应商改值可能不会被发现。正常复核保存当次实际 selector/Raw 与覆盖，按来源风险选择小范围历史抽样或明确的修订窗口，发现差异后再扩到受影响证券、日期或域；不自动重拉全历史。历史 daily 验收使用独立根或明确截止的候选，同区间 bulk/daily 比较值、缺失/状态、revision 与 PIT 可见性，并检验重复运行复用、断点恢复不推进 current 和旧 Snapshot 不变。回放保留真实收到日期，不能冒充当时已采集；设计确认与实际执行验收分别记录。

检查直接服务用途：

| 检查 | 最小证明 |
|---|---|
| 请求与转换 | 证券/日期/分页范围、键唯一性、单位映射、空值含义 |
| 时间与修订 | 晚到修订、旧公告日、重复观察、开盘不能看日线的反例 |
| 实际需求覆盖 | 请求与成功范围、必需字段、lookback、成员/持仓集合及缺口；freshness 单列 |
| 不变与恢复 | S2 发布后 S1 数值不变；换目录、无网络也能读旧 Snapshot 与来源 |
| 消费者 | 第一个真实消费者的键、单位、时间、缺失一致；其他消费者实际接入时再检 |

结果只需 `可用于指定用途 / 有明确限制 / 不可用于该用途` 与具体问题。小型合成反例加一个真实窗口验证语义；正式任务检查实际需要范围。日更只检查新增与受影响范围，文案/UI 小改不重扫全历史。抽样不能说明全范围完整，但不因此建设通用 certification/admission 平台。

数据损坏时从备份恢复，不能重新算 hash 洗白。备份 Raw/fetch、规范文件、Snapshot、合同/实际配置、可恢复源码与依赖锁；缓存可重建。做一次恢复演练比增加一套登记系统更有价值。

<a id="explicit-continuation"></a>
### 8.3 新 builder 的显式续接

同一未完成 operation 不可悄悄更换 builder。修复经独立审查后，以新 operation 显式
绑定新的 clean commit，以及停止来源 checkpoint 的精确内容。已停止的 continuation
也可以成为来源；保留至原 reference/market/calendar 根的可验证链，不伪造旧子任务成功。

源请求、选择范围、原始字节、单位、身份和原接收时间保持不变。复用请求添加明确链接
到原 receipt 的解释记录，声明新合同/producer；原 receipt 及旧 checkpoint 不改。已有
成功但未发布的响应同样复用，不以转换异常为由重拉已采行情或事件。

当前明确边界是留存 chunk 未含 cap 拆分的续接；不能把 capped 响应重标为完整，也不能
声称任意历史失败状态都支持自动续接。独立检查全部原 selector、复用链接、后续 cap
图、publication 链及继承域；审计候选后才发布 current。失败保留 Raw 和断点。

这是现有本地批处理机制的显式分支，不引入 registry、迁移服务或额外 admission 系统。
完整股票验证审计通过后，再按独立 ETF 范围执行采集与验收。

## 9. 从零实施顺序与工期

本节保留从零规划时的粗估，假设AI持续实现、人工及时确认来源语义、一个主要来源和权限可用。它描述最初行情闭环的实施顺序，不是当前剩余工期或交付范围。当前已约定并完成的Data范围包括财务/事件和Qlib，实际代码、运行时间与验收证据见[交付说明](https://github.com/sinnergarden/axiom-data/blob/f6b8fad9684caad7e25abfb7fa695785258e0a5c/DELIVERY.md)；完整Engine/UI产品和实盘由各owner负责。

| 累计里程碑 | 范围 | 估计 |
|---|---|---|
| 假设数据闭环 | 三层存储、Snapshot、Reader、关键语义夹具 | 1–3 天 |
| 真实小窗口 | 一个来源、实际字段合同、增量/失败续跑与关键验证 | 3–7 天 |
| 首版行情研究可用 | 扩到沪深300历史范围、必需状态/价格口径、缺口解释和一次恢复 | 约 1–2 周 |
| 财务、股东、Qlib | 先明确原生事件/PIT与数字日频导出合同，再真实接源和消费 | 当前已纳入完整Data交付并验收；无剩余工期承诺 |

原先 6–9 周混合了人工兼职项目推进、联调和运行观察，不再作为 AI 首版实施的等待时间。来源限流、下载量、历史能力缺失与授权等待可能改变实际工期；运行观察可以和研究并行。实施从真实小窗口开始，边接源边明确合同，通过后扩范围。

最大风险依次是历史成分/退出证券覆盖、公司行动与复权口径、财务 revision 可知时间，以及范围不断膨胀。AI 可加速接口包装和测试，不能补造供应商不存在的历史 vintage。真实数据正确性通常比性能框架更早成为瓶颈；以测量决定分区/缓存，首版不做多机 writer、消息总线、通用 Feature Store、全公告 OCR、自动 committed GC 或全历史证据补齐。

### 9.1 开始实现只需补齐的交接内容

设计已足够启动实现，内部类和中间函数由实现者组织，不再编写完整内部设计。接源时补齐四项：

1. 实际供应商合同：endpoint、请求证券/时间范围、主键、单位、空值、分页与修订/可用时间。未知能力明确限制，不由 AI 猜测。
2. §7 的少量公共接口：表格形状、查询上下文及读写副作用；不需要预建所有消费者。
3. 固定 Raw 样本和独立核对的预期：单位、晚到修订、停牌/缺数、历史成员与日线 cutoff；不能从实现输出反推所有测试答案。
4. 可重复运行的完成命令：真实小窗口从 Raw 构建、读取、增量更新、重读旧版本、换目录恢复；如某步未支持，结果明确指出，不以假设输出替代。

Agent harness 首版就是上述固定夹具、测试命令和 Notebook 端到端运行。实现仓库的 AGENTS.md 保持一页导航：职责边界、公共入口、运行命令、来源与时间规则；不复制整套设计，不增加审批流程，不预建专用 Agent 平台。

## 10. 小而必要的验收

这些编号是可执行语义场景，不要求独立认证报告服务；可记录在测试输出或操作/实验日志中。

| ID | 场景 | 应得到的结果 |
|---|---|---|
| D01 | 发布 S2 后读取 S1 | 旧文件和值不变，新旧同时可读 |
| D02 | 同 Raw/合同/代码/配置重建 | 键、单位、值及缺失语义一致 |
| D03 | 重复观察后供应商改值 | fetch 日志完整，旧 revision 保留，首次观察不后移 |
| D04 | 单位/证券/日期映射反例 | 确定转换；未知映射明确失败 |
| D05 | 变更合同或修复实现 | 从明确输入生成新 Snapshot，不覆盖旧文件 |
| D06 | 晚到修订与日线开盘读取 | safe/operational 不倒灌；best-effort 限制明确 |
| D07 | 财务/股东接入时的撤销、多期与缺行 | 不压扁事件、不盲目前填或聚合；接入该域时执行 |
| D08 | 入池/退出/再入与池外持仓 | 集合正确，lookback 与账户跟踪不丢失 |
| D09 | 单域修复/补证据 | 其他域文件、数据与 provenance 复用 |
| D10 | 必需范围更新失败 | Raw 可留用，current 不变 |
| D11 | 换目录且无网络恢复 | 旧 Snapshot、来源和实际查询可恢复，无需 catalog |
| D12 | 文件损坏 | 明确失败并恢复，不改摘要冒充正常 |
| D13 | 新鲜但用途覆盖不足 | 报具体缺口，不获得全库通过结论 |
| D14 | 本轮Qlib读取与搬移 | 需要字段的键/日历/单位/NaN/数值和成员区间按固定Query合同等价 |
| D15 | 停牌、缺数、闭市、未上市、退市 | 状态可区分，不统一填零或删行 |
| D16 | UI 实际接入后查询旧 run | 用原 Snapshot/QuerySpec，读取无写副作用 |
| D17 | 真实消费者接入 | 同键、同单位、同时间与缺失语义，薄 adapter 不另算事实 |
| D18 | 外部配置/current 在运行中变化 | 已开始任务使用已固定的版本和配置 |

### 10.1 事件歧义与续接反例

| 反例 | 必须观察到的行为 |
|---|---|
| 财报同日字段冲突、行顺序改变 | 一致字段不变，冲突字段明确缺失；无拼接或排序猜测 |
| 单季/TTM 使用缺失报告 | 传播缺失，不回退旧报告 |
| 同键分红返回两个不同候选 | 整个事件不可用，现金共同零也不可用，Raw 全组留存 |
| ex_date 相交或候选日期未知 | 返回缺失标记和受影响范围；不能变成可正常记账的空结果 |
| 不相交日期/其他证券 | 不被此歧义组连带阻断 |
| 相同候选数、日期集合更正 | 新 observation 保留，旧 Snapshot 仍可读 |
| §6.1的只有冲突 Raw 的历史反例 | 2015 范围返回不可用标记，不依赖此前单行记录 |
| 早 cutoff 的提示、晚 cutoff 的两范围 | 早期不暴露未来候选日期或数量；晚期两范围分别提示 |
| 此前单行观察与已可见歧义并存 | 不能用旧值覆盖歧义，也不能按日期过滤后回退旧值 |
| 严格 cutoff 在实际 receipt 前 | 不伪造当时已知的事件或提示 |
| 发布后中断、新 builder 或连续修复 | 明确新绑定，缓存响应零网络复用，旧 operation 不改 |
| 搬移 Snapshot | 原 receipt 链完整，缺失原因和范围读取不变 |

实现锚点：[Data 财报修复](https://github.com/sinnergarden/axiom-data/commit/48b8f4f92a63736e35cf351a43ec999d0ced6191)、
[显式续接](https://github.com/sinnergarden/axiom-data/commit/4bf02118849309ed579bd65f89ab2457dc36a763)、
[分红整事件及链式续接](https://github.com/sinnergarden/axiom-data/commit/a0ae046c4cf1279ef27f2e2d31a96d0c5469d4ea)、
[cutoff 内缺失范围](https://github.com/sinnergarden/axiom-data/commit/54e98c62cb594da2e4bd83d71b1167d4ba1877bf)。
这些链接用于核对实际状态，不代替本设计。针对性反例和小范围离线回放不构成十二年
股票和 ETF 完成证明；全量交付须另核对其保存的完整验证及来源审计报告。

用户已明确本轮交付完整Data，2026-10-03进一步要求Qlib纳入：财务接源、PIT与证据、退市边界、历史股票池、Qlib导出/实际读取等价及Researcher/Developer教程须完成。完整账户撮合和UI产品由各自owner负责，Data消费协议与薄接口必须真实执行。未完成的来源决策应讨论，不得通过缩小验收范围宣称完成。
