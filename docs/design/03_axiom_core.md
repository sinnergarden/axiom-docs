# Engine/Core 初版设计与最小验收标准

> 文档编号：AX-CORE · 专项初版 v0.1 · 所属设计包 v0.2 · 2026-09-05。\
> 状态：实施参考草案；模块名与接口为本版实现约定，不代表现有代码已经具备。\
> 上位边界：[总体设计](01_axiom_overview.md)。关联：[Research](05_axiom_research.md)、[Trade](04_axiom_trade.md)、[Data](02_axiom_data.md)。

本专项描述 axiom-engine 内的逻辑模块，物理仓库按[补丁 A](07_重要补丁_A.md)执行；Data 输入与首版范围已同步 2026-09-27 个人版，不改变本模块的计算或交易职责。

2026-09-28 Data 接口实证：Research 所有的 adapter 已将真实月末 DataBatch/成员结果映射为 FactBatch、ExecutionContext 和 FeaturePlan，并执行 identity/lag/return；这不是全部策略或决策算子的真实验收。
见 [真实 Developer 教程](../../notebooks/developer_tutorial.html#section-9) 与 [设计对照](../design-conformance.md)。正文继续定义目标合同。

2026-10-05 当前边界：共享 FeaturePlan 执行与股票中立预测验证、固定 Top5 决策已有有界实现；
LightGBM fit/inference 仍在 Research。正文中的通用 ModelHandle、SignalPlan/组合参数与正式
rolling 恢复不因固定样本通过而成为已实现 ABI。TopK 合同已由 Docs PR17 审准且 Engine
PR8 已合：显式正整数 top_k 使用 Core /2；省略参数仍解释旧 /1 Top5。准确工厂、版本
与边界见 [Trade §6.1](04_axiom_trade.md#61-有界股票日线-top5)。
不同组合须保存独立账户，不能用改资金代替。
已实现/规划图及教学顺序见 [ML 工程 Notebook 初稿](../../notebooks/ml_engineering_tutorial.ipynb)。

## 1. 一句话定义

Core 是一套可被 Research 和 Trade 调用的**共享计算与投资决策库**。同样的已知事实、信号、账户、策略状态、参数与时间，应该得到同样的目标仓位和订单意图。

Core 不是一个总调度进程，不拥有账户数据库，不读取“最新模型”，不撮合订单。它通常不单独启动，也不因每个新 Feature 或策略点子而修改。

### 1.1 范围

| Core 内 | Core 外 |
|---|---|
| 中立 Frame/Context/Result 类型与插件执行 ABI | Data Reader、Qlib 初始化、路径发现 |
| 通用 Feature 算子、固定计划执行 | 具体 Feature 配方、候选研究、历史物化与缓存 |
| 模型推理接口与已拟合变换的执行 | 模型训练、搜索、OOS 切分、模型发布审批 |
| 信号组合、标准化和候选约束协议 | SQL 文件读取、signal registry/default 解析 |
| 目标仓位、换仓、策略风控、订单意图规划 | Broker、撮合、SQLite、现金与股份入账 |
| 策略状态转换与解释 trace | 系统时钟、event loop、调度、恢复和对账 |

Data 的个人版输入合同见 [Data §7](02_axiom_data.md#7-一个-reader薄的消费者映射)：ViewRef 可以内嵌 Snapshot + QuerySpec，不要求独立 Data View/DomainCommit 发布服务。Core 仍只消费中立 Frame；只为真实接入的消费者做薄 adapter，不以 Data 的通用认证系统作为 Core 前置依赖。

P02 的 Reader 返回 Data 所有的 DataBatch；P05 的 FactBatch 是 Core 所有的中立计算 ABI。Research 和 Runtime 各自在调用侧映射，两者不能因都叫“事实表”而合并 owner。映射保留键、字段顺序、单位、可见性、缺失与来源；不重复执行 Data 的 PIT/复权，也不从 Label 结果补 Feature。共享列缓冲可以避免复制，不要求建立额外服务或落盘格式。

稳定边界不代表不许改 Core。新增通用语义才升级 Core；某策略“60/180 如何加权、何时减仓”应由冻结插件或配置表达，不能堆成很多 `if strategy_name`。

### 1.2 回测与 daily shadow 无业务差异的硬原则

2026-10-06 新增用户原则：除为更快的 batch/cache 做等价优化外，Engine 怎么做回测，就必须怎么做 daily shadow，原则上不允许业务 diff。在同一冻结输入及其 source refs、逐 session 时钟/可见性、账户与策略状态、策略/风控/执行 profile、实现版本和随机种子（若有）下，两者共用原计算、决策、风控、订单、模拟 Broker 与账本规则，逐项输出一致；输入 adapter、运输分批及调度可以不同，不能另写一条近似计算或账户路径。

Core 的 Feature/Signal、目标、约束、Intent、策略状态和 trace 均在此约束内；dtype、单位、缺失/拒绝原因、availability/source refs、参考截面及 tie-break 不能因 batch/shadow 模式改变。batch/cache 只能改变等价的计算组织与性能，不能省校验、变更可见性、引入未冻结随机状态或用数值容差掩盖业务差异。

此条是新增设计与验收要求，不是已实现的 shadow 能力声明。当前 Core 已有共享执行和有界规划；完整账户逐 session 推进、盘后模拟结算与持久恢复的现状、缺口和验收顺序统一见 [Trade §2.1](04_axiom_trade.md#backtest-shadow-parity)。不据此扩建第二执行器，也不改变或重跑当前保存结果与正在进行的 Research ML 闭环。

## 2. 与其他模块交互（P05、P07、P08）

```text
Research：FeaturePlan / FactBatch / frozen transform / ModelHandle
          → Core → FeatureFrame / PredictionFrame / SignalFrame

Trade：SignalFrame / AccountState / StrategyState / DecisionContext
       → Core → TargetPortfolio / OrderIntent[] / NewStrategyState / DecisionTrace

Trade：Fill/Account notification + StrategyState
       → Core → NewStrategyState / trace
```

Data 不直接调用 Core；Data 的固定事实由调用方 adapter 转成 FactBatch。Core 不 import Research/Trade 项目。生产执行的是 Research 发布的轻量策略包，不是 mutable Research workspace。

UI 不提交交易计算请求；它读取 Research/Trade 已保存的 trace。原因码与 schema 可随 Core release 提供，不需要 Core Web 服务。

## 3. 主要类型与最小语义

2026-10-04 有界实现：`axiom_engine.core.SignalFrame` 提供中立 `signal_frame_v1` JSON Document 验证，Research/Runtime 通过公开合同交接。finite score、行键唯一、完整 universe、validity、cutoff/available_at 和 immutable source refs 是消费前提；具体保存身份与证据见 [当前交付](../current-delivery.md)。没有把任意 SignalPlan/model plugin ABI 宣称为已完成。

| 类型 | 最少包含 | 约束 |
|---|---|---|
| FactBatch | `(security_id, session)` 键、typed columns、单位、可见时间、来源 Snapshot + QuerySpec（逻辑 ViewRef）、missing metadata | 由调用方按 cutoff 裁剪；不能含未声明未来数据 |
| FeatureFrame | 行键、有序 schema、stage、FeatureRelease、input refs、validity | 禁止位置 `.values` 静默拼接 |
| TransformState | 拟合参数、fit scope/ref、实现版本、输入输出 schema | 推理不重新 fit |
| ModelHandle | 已加载推理对象、ModelRelease、expected schema、backend version | 不能在 predict 内寻找模型文件/指针 |
| PredictionFrame | 行键、数值、目标语义、model/fold refs、validity | 回归值、排名分数、概率不同义 |
| SignalFrame | 行键、score/stage、cutoff、模拟可用时点、source refs、reference universe、invalid reason | 已组合信号不能再次无意归一化 |
| TargetPortfolio | 证券目标权重/数量、剩余现金目标、intent kind、约束结果 | 区分 no-op、keep、liquidate、明确 target=0 |
| OrderIntent | security、side、quantity、价格约束、有效期、reason、稳定 logical key | 不是券商订单，不代表已成交 |
| StrategyState | contract/version、策略记忆、last processed logical event | 不保存权威现金/持仓 |
| DecisionTrace | 原始分数/目标、约束后结果、舍入/拒绝原因、输入 refs | 对“未买/未卖/未换”也有说明 |

唯一证券键使用 security_id；显示代码来自有有效期的映射。时间/session/数量精度、列顺序、空值与 tie-break 都属于 contract。

### 3.1 DecisionContext

```yaml
decision_id: dec_example
decision_time: "2026-09-04T00:55:00Z"
knowledge_cutoff: "2026-09-03T15:59:59Z"
feature_session: "2026-09-03"
trade_session: "2026-09-04"
event_sequence: 42
strategy_release_ref: sr_example
universe_ref: universe_example
market_rule_ref: rule_example
account_state_version: 17
execution_constraints_ref: constraints_example
rng_seed: null
```

示例时间不是默认交易时刻；实际 cutoff 必须由版本化日历和运行协议决定。Context 中没有 `mode=backtest/shadow/real`。

账户、成交和行情会随事件变化；“固定输入”指这一次决策的显式输入。运行中接到新成交时，可以基于新的 AccountState 做下一次决策，不是把开盘账户锁死一整天。

## 4. Feature 与推理的共享实现

### 4.1 FeaturePlan

Research 发布 FeaturePlan，包括输入字段/稳定派生、lookback、算子图、lag、输出列、缺失/异常处理、参考截面、执行版本和插件引用。Core 执行同一个计划，批量研究与逐日推理不能分别实现两个近似公式。

```text
连续历史 FactBatch
→ 每证券时序算子
→ 按当期 PIT membership 选择横截面
→ rank / zscore / neutralize 等声明变换
→ base / cross_sectional FeatureFrame
→ 已拟合 TransformState
→ model_input FeatureFrame
→ ModelHandle.predict
```

跨证券 rank 的参考集合必须显式，即使只请求一个 UI/持仓证券也不能用这一个证券重新归一化。UI 本身不走此计算链。

### 4.2 Fit 与 transform

拟合逻辑由 Research 在训练期调用并生成 TransformState；Core 只负责通用算子或已冻结插件的可重复执行。若加入新学习型预处理，应明确 fit 接口与结果归属，不把隐式 fit 藏进 transform。

同一 base FeatureBuild 可以被不同训练 fold 的 scaler 转成不同 model_input；因此后者必须带 TransformState/ModelRelease/fold 身份，不能共享一个不分 fit 的 cache。

### 4.3 插件包

```text
Strategy runtime package
  manifest / dependencies.lock
  feature_plugins/       纯计算实现
  inference_plugins/     保存模型的推理适配
  signal_plugins/        纯信号变换
  portfolio_plugins/     组合/换仓/风控
```

发布包不得 import 训练工作区、联网、读取系统 current/latest、使用未固定全局随机状态或直接写文件。禁止 I/O 是合同、依赖检查和隔离测试要求，不声称普通 Python 类型系统能自动提供安全沙箱。仅加载受信任、已审查的发布包，拒绝外部不可信模型序列化文件。

可后端下推的 Qlib/向量化计算由调用方 adapter 执行，需与基准算子 golden case 等价。性能优化必须报告主键、NaN、dtype、误差和排名边界影响，不只比较相关系数。预测数值在容差内但 TopK、意图或约束结果翻转，仍属于行为变化，不能用数值容差掩盖；需要固定 tie-break/稳定计算或单独批准语义变更。

<a id="signal-statistics-proposal"></a>
### 4.4 保存信号评价的纯统计增量：待主协调与Engine亲审

Research管理[独立信号评价定义与保存](05_axiom_research.md#saved-signal-quality-proposal)，
Core提供相关与序列统计的共享纯计算。当前股票IC/RankIC由Research现有helper计算；
新增算子经审准后，该编排调用Core，不在Research保留另一份数值实现。

候选公共函数为 `evaluate_signal_statistics(input, *, spec)`。input固定
`contract_version='signal_statistics_input_v1'`、有序 `sessions/signal_keys` 和 `pairs`；
每个pair是 `{signal_key,security_id,session,score,outcome}`，由Research选好共同评价范围、
成员和成熟标签后传入。score/outcome均为有限无量纲数，三字段键唯一；没有有效配对的
日期仍在sessions内。signal_key绑定一份Signal或不重叠weekly Signal列表的准确refs。
pair输入可以乱序，Core先按signal_key/session/security_id稳定排序，再绑定input_ref；
重复键报错，不能由后写行覆盖前行。
来源闭包、未来标签可用时间和资格检查由Research负责，Core不读取文件、查询事实、
加载模型或执行账户。

首版spec固定 `minimum_pairs=20,rank_ties='average',std_ddof=1,
time_weighting='equal_valid_sessions',annualization='none'`。Core按日期计算Pearson和
Spearman，并对有效日序列计算均值、样本标准差及mean/std。输出
`contract_version='signal_statistics_v1'`、`input_ref/spec_ref/statistics_ref`、
`series=[{signal_key,session,valid_pair_count,ic,rank_ic,reason}]` 和
`summary=[{signal_key,valid_ic_session_count,mean_ic,ic_std,icir,icir_reason,
valid_rank_ic_session_count,mean_rank_ic,rank_ic_std,rank_icir,rank_icir_reason}]`。
输入和spec使用既有规范JSON身份；statistics_ref绑定除自身外全部统计输出。

不足20对、常量截面和非有限相关值给null与原因；不足2个有效日或std为0时IR为null。
Pearson/Spearman使用同一批配对，ties取平均秩，日权重一致。DuckDB等批量后端只能
执行同一算子语义，经键/null/计数精确一致及相关值绝对误差≤1e-12的golden核对后采用。
最低验收包含乱序、重复键、单日错位、ties、常量、缺失日及多Signal共同样本。
本节是有界纯函数候选，不改变当前FeaturePlan执行器或Engine账户评价。

<a id="neutral-cs-batch-proposal"></a>
### 4.5 中立批量截面入口候选

> 此候选已在独立 Engine 提交 `999552fea6bc712f9400a2ab304f88d9ad2eea39` 实现并审阅，尚未合入 main。§4.6 的后续分支以它为基线并保留此入口，接入须固定实际完整代码提交，不能把候选当作 main 已发布能力。既有 `execute_feature_plan`、FactBatch/FeatureFrame wire 和数学语义不变。调用侧 prepare/packed loader 见 [Research §8.2.1–8.2.2](05_axiom_research.md#821-固定输入矩阵与滚动训练)。

唯一新增入口候选：

```python
from axiom_engine.core import execute_cs_zscore_batch

def execute_cs_zscore_batch(
    batch: dict, *, params: dict,
    clock_projection: str = "ceil_to_core_second_v1",
) -> dict:
    ...
```

这是现 cs_zscore 数学的中立批接口，不是 Data/Label/训练 service。实现复用同一 Core 算子规则/基准；Research processor 仅负责合规选择与 carrier 映射。无路径、Data对象、Research对象、Qlib handler、模型或 I/O 参数；无 fit/状态学习。初版只实现 group=session 的现 ddof0/epsilon/constant-missing/no-clip profile，不扩通用算子平台。Core 模块导入保持中立，不因该入口隐式加载 Data/Research/训练包。

`batch` 为新 opt-in 中立 carrier，**不是声称现 FactBatch 已接受数组**。字段：

| 字段 | 精确含义 |
|---|---|
| `contract_version` / `calendar_ref` / `schema` / `output_schema` | `core_cs_zscore_batch_input_v1`；calendar_ref为固定sha256绑定。schema/output_schema均沿现中立列 schema且各一列；输入float64，输出float64/dimensionless/cross_sectional，missing=preserve。 |
| `sessions` / `security_ids` | 有序、唯一；完整 D×U 网格，day-major 后 security-order；既有 row-index digest/keys exact。 |
| `values` / `value_validity` | readonly contiguous float64 / bool buffers，长度 D×U；false槽代表 logical null，不以NaN本身替代missing policy。 |
| `value_reason_codes` / `reason_dictionary` | 同长reason codes和固定词典，保留原 Core 输入缺失原因；不改原因优先级。 |
| `fact_available_at_utc_us` | 未取整 UTC integer微秒，同长。label调用映射：eligible格为原raw可用时刻；excluded格value=null、时钟为精确fit cutoff，对应原offline eligibility事实，不冒充原raw事实时钟。原raw时钟仍在Target中。 |
| `reference_member` / `reference_available_at_utc_us` | 同长资格/membership及其未取整时钟；label调用沿原映射：member=完整本fit资格mask，reference clock=精确fit cutoff。 |
| `selection_cutoff_utc_us` | 每session一个未取整cutoff（长度D）；label批为同一fit cutoff，不能先ceil后判断真实availability。 |
| `source_bindings_by_session` / `fact_source_codes` / `reference_source_codes` | 沿现 Source binding字段及本次data/view refs；同长source-code buffers按session词典解析。只来源/clock变化仍进入本次input_ref。 |

以上表格枚举输入dict的全部字段，不接受额外字段。schema每列精确为 `{name,dtype,unit,stage,missing}`；label适配使用原 `raw_return` fact列和 `normalized_target` cross_sectional列。`sessions` 按日期升序，`security_ids` 按稳定ID升序，均非空；第 `i*U+j` 个槽对应 `(security_ids[j],sessions[i])`。buffers为标准buffer protocol兼容的一维、C-contiguous、readonly对象，不要求调用方传NumPy对象：values为little-endian float64，validity/reference_member为bool（字节0/1），reason/source codes为little-endian int32，所有UTC微秒时钟为little-endian int64；除selection_cutoff长度D外均长度D×U，无null clock sentinel。missing值槽使用canonical +0.0，独立validity=false；present值有限。`reason_dictionary=[null,*sorted(unique_reason_strings)]`，code0表示无原因；输入present仅code0，missing仅非零合法code，保留本次原原因文字。

`source_bindings_by_session` 精确为 `{session: {bindings: [...], source_sets: [...]}}`，session覆盖同一sessions。每个binding精确为 `{id,data_ref,view_ref,revision_policy,qualification,availability_basis}`，规则沿现Source binding；bindings按id升序且不重复。source_sets是非空、去重的source-ID集合列表，每个集合为排序非空ID列表且全部ID在bindings中；集合列表按ID tuple字典序固定。每槽fact/reference code索引本session的source_sets；reference的集合恰一ID，沿原reference.source。excluded/invalid槽同样有真实映射后的来源和时钟，不能用-1跳过依赖。

所有buffer采用明示dtype和维度，Core检查shape、keys、bool/code域、有限valid值和时钟边界；readonly输入不得在调用期间修改。schema admission与现Core相同：按mask把槽还原为有限值/null后校验列的dtype/unit/stage/missing，不因packed输入绕过 `missing='reject'`；首版label profile明确为preserve。operator params与现规范逐字段一致，不接受trusted/skip-admission flag。调用侧先按native时钟检查PIT/endpoint/maturity/完整cohort，Core再验证映射后的fact/reference原始时钟≤selection cutoff，然后执行projection。

首版共用原 `_std` 与 `math.fsum`，eligible值及依赖按冻结grid的security顺序进入原算术，不先改成NumPy/pandas reduction。undefined scale判定保持 `std is None or std == 0 or std < epsilon`，不是≤epsilon。已审Core按组统计一次的复用优化可沿用，但不改变有序参与值、std、均值和输出依赖。输入reason codes保留缺失/资格原因；输出reason codes独立生成，当前profile的missing/constant/excluded输出为原 `_merge` 的 `REFERENCE_MISSING`，present输出无原因，不能把raw原因直接复制为CS输出原因。

`ceil_to_core_second_v1` 定义为UTC微秒向上取整至整秒，等于原 `core_clock`。fact、reference、cutoff分别投影；输出每格available_at沿原 `_merge`：参与cohort的全部fact clocks、全reference组（含被排除键）的clocks及本格fact clock取最大值。label映射的reference为cutoff，所以输出normalized时钟为projected fit cutoff。缺失/constant/excluded也按原规则输出，不用raw本行时钟替代group依赖；保持原raw label clock在Research父件中，不被改写。

`result` 返回owned float64值buffer、validity、reason codes/dictionary、available_at_utc_us及输出source-code映射，与输入同完整网格；不返回文件路径或拟合状态。metadata为 `core_cs_zscore_batch_result_v1`，包含input_ref、numeric_input_ref、spec_ref、keys_ref、schema/source/context refs、values/flags/clocks digest、implementation_ref和result_ref。`numeric_input_ref`只标明有序值/资格/数学定义同一，不授予来源或时钟复用。`result_ref`绑定本次完整input_ref+参数/clock mode+实际Core实现+全部输出digest；Core自己校验/生成，不接受caller自报的正确结果。

精确输出dict字段为 `contract_version,sessions,security_ids,schema,values,value_validity,value_reason_codes,reason_dictionary,available_at_utc_us,source_bindings_by_session,source_codes,metadata`；contract_version=`core_cs_zscore_batch_result_v1`，schema=输入output_schema，所有输出buffer由Core拥有并以readonly返回，dtype/order/长度沿上文。输出source_sets记录原 `_merge` 依赖source的排序并集，source_codes按本session词典解析；输出原因遵守原Core输出规则（如REFERENCE_MISSING），原输入原因另由input_ref绑定，不把eligibility原因冒充Core输出原因。metadata精确为 `{input_ref,numeric_input_ref,spec_ref,keys_ref,schema_ref,source_ref,context_ref,values_digest,flags_digest,clocks_digest,implementation_ref,result_ref}`。

引用一律为 `sha256:` 加64位小写hex。每buffer的摘要输入为严格canonical JSON `{dtype,shape,bytes_digest}`；bytes_digest散列规范字节，不散列进程地址。input_ref散列完整输入字段，buffer替换为该摘要描述；keys_ref散列 `{sessions,security_ids,order:'session_security'}`，schema_ref散列输入/output schema，source_ref散列本次bindings/source_sets和fact/reference code描述，context_ref散列calendar_ref、keys_ref、reference_member/reference clocks、selection cutoff描述。spec_ref散列 `{abi:'axiom.feature/1',semantics:'axiom.operators/1',operator:'cs_zscore',operator_version:'1',params,clock_projection}`；params全部显式，首版固定 `{group:'session',unknown_group:'reject',missing:'skip',ddof:0,epsilon:1e-12,constant:'missing',clip:null,excluded:'missing'}`。numeric_input_ref散列keys_ref、schema_ref、spec_ref、有序values/validity/reasons和reference_member描述，故仅剥离来源/时钟、不剥离cohort。values_digest散列values描述，flags_digest散列validity/reason code描述及词典，clocks_digest散列available_at描述。implementation_ref绑定实际参与Core代码/算术backend版本，不接受caller指定；result_ref散列完整输出字段（同样把buffer替换为摘要描述，metadata仅移除result_ref），输出source映射同样在闭包内。保存时该canonical result与物理文件descriptor分离，Research索引wrapper负责绑定二者；路径不混入Core输入/结果，见Research §8.2.2。

buffer digest codec固定：day-major float64 little-endian（null槽canonical0、独立valid mask），bool0/1、UTC int64微秒及code词典/keys/source metadata严格canonical JSON；不通过object repr或未知scalar stringify作身份。读取packed父件验证上述codec/digest与selector闭包；不重新执行数学。

新结果不是旧 FeatureFrame，不能将旧frame_ref重贴到新输入。调用侧保存到prepared-view内部表/分区，loader、FoldManifest独立绑定当前lineage。首版每fit可廉价批算一次而仅复用相同物理值文件；不新增数学缓存registry。有限数值容差、exact flags/keys/clocks及排名边界验收按Research §8.2.1；浮点顺序变化必须声明backend/实现与新身份。

<a id="feature-plan-batch"></a>
### 4.6 同一 Feature 数学的有界多输出候选

实现候选固定在 Engine `0b98c1a`，直接基于已审但尚未合入main的 `999552f`，
保留§4.5的cs_batch。当前已做小型合成与原Frame对照，供父亲读；真实Research
接入仍待此次源码审准，不把该候选视为main已发布能力。

候选公共入口为 `execute_feature_plan_batch(requests, *, reuse_budget_bytes)`。
requests 是非空固定 tuple，每项为原 `(FeaturePlan, FactBatch, ExecutionContext)`。
每项只请求一个输出日的完整证券网格，输出日严格递增；各项使用同一编译后的
DAG、输入/输出 schema、算子参数、history policy 与证券列表，完整 membership
可以变化。首版要求 sessions observation domain、空 event schema/events。
H(t)、cutoff、adjustment anchor、原输入身份及来源绑定仍逐项独立，不能合并
冲突键或用较晚 anchor 替代较早选择。列数来自 Plan，6、158、300 列沿同一
执行路径，不在 Core 增加另一套 Feature 定义。

返回精确为 `{frames,stats}`，frames 是与 requests 同序的普通 FeatureFrame tuple。
每个 Frame 的完整 wire、identity、原 plan/fact/context identities、值、有效性、
原因、availability 与 sources 必须与原输入单独执行 exact。旧入口与批入口
共用同一私有执行路径，每个视图都完整验证并传播自己的依赖。Research 继续
使用已有每日 proof、input_evidence 和实际 Frame/Plan source refs；本候选不增加
Research selection、shared-panel receipt 或 execution-slice 实体。单日 shadow
传一个 request，使用同一数学路径。

reuse_budget_bytes 必须为 strict 非负 int，拒绝 bool；0 禁用全部数值 ID/key
构造与复用。首版仅尝试 rolling std 和 cs_zscore scale 的较长数值单元
（missing policy 后至少64个参与值）；便宜的 pointwise 和其他 reduction 保持
原算法。调用内的数值 ID 绑定原完整键、列/节点、精确 float64 bits、null 与
issue 有效状态；CS另绑定完整成员/industry及原 reference 顺序。复用 key保留
全部有序依赖 ID，不能以近似 hash、窗口起止或最终 scalar 代替依赖。仍使用
原 `_std`、`math.fsum` 和浮点顺序，每个视图独立执行 `_merge`、schema和cutoff
检查。memo仅保存必要的精确key/数值ID及纯数值结果，不保存 `_Cell`、来源、
availability或原因。它仅存在于一次调用中，结束或异常时释放。

数值 ID backing、memo mapping、key构造/插入工作区均计入该预算，采用保守的
Python graph charge与工作区预留；预算不足时清空复用状态或直接按原helper计算，
不拒绝原本有效的视图。复用仅在CPython启用；其他backend沿原计算。首个视图
填充memo，此后若某op无命中或测得开销超过估计节约，可在本次调用内保守禁用。
这只改变性能统计，不改变 Frame。该预算不覆盖调用方持有的原输入、解析图、
返回 Frame、Data/Research工作集或整个进程RSS；这些仍由调用方的有界输出块和
合并 resident guard计入。没有零拷贝或全300列容量通过的承诺。

stats是非业务诊断，包含views、逐helper的requested/computed/reused/disabled、
key尝试/构造次数与charged bytes、numeric IDs数、key构造/算术/复用开销及总
纳秒、预算峰、fallback/逐出和禁用原因。总时间包含准入、Frame构造及清理；
budget peak为保守工作区charge而非RSS。stats不进入原Frame或Research每日证据
身份，不能将一次公开调用或简单逐日wrapper loop本身作为批收益。验收须核实
实际helper调用减少、完整Frame exact、总开销与实际RSS，并覆盖anchor数值变化、
revision/null/visibility/cohort/顺序变化、零/不足预算和异常释放。重叠历史中间
数值可能节约算术；新的输出窗口和截面仍按原算法计算，Data选择、复权、来源
合并、原生hash及每日保存不会因此消失。合成收益不能替代真实接入验收。

## 5. 信号与策略协议

### 5.1 SignalPlan

允许单模型、规则信号、多个模型或已保存 SignalRun 的组合。固定输入 alias、source stage、horizon、键对齐、缺失/过期规则、变换版本与 reference universe。

支持基础算术、rank、zscore、条件组合即可。Research 可用受控 SQL/表达式编译计划；Core 执行已验证表示，不直接 `eval()` 任意字符串，也不读取数据库。

每条 signal 有 `score_semantics`，例如 rank_score、standardized_return_prediction、calibrated_probability。没有校准证据不生成“80% 会涨”的解释字段。

### 5.2 Portfolio/Rebalance/Risk 三类职责

| 插件 | 回答问题 | 例子，仅为可配研究策略 |
|---|---|---|
| PortfolioPolicy | 想持有什么、各占多少 | TopK 等权、持仓漂移、现金缓冲、行业/个股上限 |
| RebalancePolicy | 今天是否调整、何时保持不动 | 周频/20 session、分相位、持仓保留/替换规则 |
| RiskPolicy | 投资组合允许哪些风险 | 集中度/暴露限制、回撤门控、持仓退出 |

第一版提供一个简单 TopK 等权与明确的 rebalance policy 作为贯通基线；Top5、60/180 混合、止损/止盈等是 StrategyRelease 参数/插件，不是 Core 全局规则。

用户的“最多五只、允许空仓、错了快撤/对了多拿”作为研究意图，由策略与实验评价决定具体实现。Core 不把它变成未经验证的收益承诺。

## 6. 订单规划与边界案例

本轮 `plan_rotation` 是纯函数：完整候选信号经时间/有效性验证后，正动量 Top1，分数并列按 security_id 升序；没有正值则目标现金。Runtime 每个 ISO 周首个交易日传入严格前一 session 信号和真实模拟账户，使用已知前收进行数量估计，附 account version。Core 输出 intent/trace，账户变动只由 Runtime 的模拟成交入账。缺候选信号拒绝，不从未来价格补信号；不是通用挂单/Broker 规划器。

规划以**真实 AccountState**为基础，包含现金总额/可用/冻结、总持仓/可卖/冻结、未完成订单及其状态。不能把目标或前次 OrderIntent 当作真实持仓。

建议固定次序：

```text
validate inputs/context
→ candidate/held-symbol coverage check
→ portfolio proposed target
→ rebalance decision
→ strategy risk constraints
→ account-aware delta including outstanding orders
→ lot/tick/available inventory/estimated cash checks
→ deterministic priority/rounding
→ OrderIntent + revised target + trace
```

仍有效的未成交买单/卖单要计入投影暴露和现金占用；状态不明的外部订单不能当零。是否撤旧单/修改目标由策略与运行协议明确，不能在重跑时重复发同一需求。

同一账户批次内由 Trade 串行或采用 account version compare-and-apply；Core 输出附 expected account version。状态变了应明确重新决策，不把基于旧现金的两个计划直接都提交。

### 6.1 不可混淆的情况

| 情景 | 行为要求 |
|---|---|
| 当前无 signal | invalid/no decision 或固定保守策略；不能默认 score=0=卖出 |
| 股票退出选股池但还持有 | 保持账户跟踪；依冻结的 exit/hold policy 处理 |
| 目标为零但无法卖出 | 记录未完成退出与原因，不能假装清仓 |
| 有未完成委托 | 计入冻结与投影数量，去重/撤改规则明确 |
| 无可用成交价格 | 可返回无可执行意图；不得用未来 close 补开盘价 |
| 规则/数量不适用 | 显式 invalid 或拒绝，不套统一 100 股/10% 规则 |
| 预算不足 | 固定优先级和舍入规则；现金缓冲保留，可少买/空仓 |
| 相同 score | 稳定 tie-break，例如 secondary metric 后 security_id |

Core 使用 Data 提供的有效规则和 Trade 提供的账户约束。交易所/券商规则资料需实施时核对；这里不硬编码跨板块和跨时期都相同的规则。

## 7. 状态转换：意图和成交分开

StrategyState 保存上次目标、冷却、已知追踪高点、策略阶段等。生成订单不应增加真实持仓；只有 Trade 处理确认成交后提供新 AccountState。

Core 可接收 Fill/Account notification 来更新持仓 episode 的策略记忆。重复事件处理的水位与持久化归 Trade；Core reducer 仍应对 event_id/sequence 有明确前置条件，不依赖隐含“肯定只会调用一次”。

StrategyState contract 改版时必须提供显式 migration/reset policy；不能用新代码随意解释旧状态。状态切换在批次/发布边界执行并记录，而不是在半个决策过程中加载新插件。

同一逻辑事件回放允许 envelope 中 run_id/墙钟日志不同，但业务目标、意图 logical key、状态与 trace 语义必须一致。用于去重的稳定逻辑键与用于区分实际执行尝试的 attempt_id 是两件事。

## 8. 纯接口与依赖规则

```python
# 初版协议示意；不要求每个接口单独建类。
execute_feature_plan(plan, facts, transform_state, context) -> FeatureResult
predict(model_handle, feature_frame, context) -> PredictionFrame
combine_signals(signal_plan, frames, context) -> SignalFrame
make_decision(strategy, signal_frame, facts, account, state, context) -> DecisionResult
reduce_strategy_state(strategy, state, event, context) -> StateTransition
```

```text
src/axiom_core/
  contracts/         neutral frames, states, context, intent
  operators/         tested general transforms
  execution/         plan/inference/plugin executors
  policies/          interfaces and minimal generic policies
  planning/          account-aware intent compilation
  validation/        schema/time/rule preconditions
  tracing/           typed reasons and decision output
  tests/             fixtures and conformance
  docs/              Core-specific implementation and tests
# Shared design: axiom-docs/docs/design/ (one authoritative cross-repo index)
```

不得依赖 `axiom_research` 或 `axiom_trade` 主包；不可 import 券商 SDK、数据库或 scheduler。Data 的 domain schema 仍归 Data；中立 Frame 是 adapter 层映射结果，不强迫 Data 引入整个 Core。

## 9. 错误、解释与可观察性

建议原因码：`MISSING_REQUIRED_FEATURE`、`SCHEMA_MISMATCH`、`FUTURE_INPUT`、`UNKNOWN_RULE`、`STALE_SIGNAL`、`INSUFFICIENT_CASH`、`UNSELLABLE_POSITION`、`PENDING_ORDER_CONFLICT`、`STATE_VERSION_MISMATCH`。

错误返回必须区分：计算无法成立的 hard error、合法无交易、策略风险阻断、输入质量允许的显式降级。禁止 catch-all 后返回空表并宣称成功。

DecisionTrace 至少可解释：候选分数与 rank、入选/排除、原目标与约束后目标、数量变化、舍入、缺数据、风险限制、未完成订单影响。解释是计算路径事实；模型 Feature attribution 可作为独立分析，不能冒充因果原因或替代实际规则 trace。

Trace 由调用方写入 run artifacts，UI 按 P12 读取。只要保存的 refs 与输入仍可恢复，不能因为看图而执行新一轮投资决策。

## 10. 最小实现顺序

| 阶段 | 交付 | 约束 |
|---|---|---|
| C-M1 | Frame/Context/Intent/State schema 与验证、通用 Feature/信号算子 | 先用纯夹具，不接券商或真实数据根 |
| C-M2 | 保存模型推理 + 一个 FeaturePlan + TopK/Rebalance/Risk + intent planner | 跑通一条冻结策略，不迁全部旧策略 |
| C-M3 | Research 批量与 Trade 逐日一致性，状态 reducer 与 trace | 通过相同输入的语义回放 |
| C-M4 | 插件发布 ABI/兼容拒绝、依赖/I/O 门禁 | 接受新 Feature 不要求改 Core |

## 11. 最小验收标准

| ID | 夹具/操作 | 必须结果 |
|---|---|---|
| C01 | 相同显式输入、不同进程运行 | 目标/意图/状态/trace 语义相同；无墙钟或目录依赖 |
| C02 | 改系统时间、latest/model 指针、工作区 | 已加载计划和 handle 的计算不变 |
| C03 | 输入行被打乱、列错序、重复 key | 只按明确 key/schema 安全对齐或拒绝，绝不静默位置拼接 |
| C04 | Research 批量与 Trade 按日执行同 FeaturePlan | 各日 Feature、NaN、rank 和推理输入一致 |
| C05 | 加入 cutoff 后事实或未来标签列 | 因果检查拒绝或不可见，过去决策不变 |
| C06 | fit state 不同但 Feature 名相同 | 输出与 provenance 区分，推理不重新 fit |
| C07 | 当前持仓退出 universe 或缺信号 | 按冻结政策处理并有解释，不丢账户状态 |
| C08 | 部分成交/挂单冻结后再次规划 | 不重复买卖；AccountState 版本冲突可发现 |
| C09 | 最小单位、限价、不可卖、现金不足 | 计划满足声明规则；剩余现金/未完成目标可解释 |
| C10 | 无交易 vs 清仓 vs risk block | 三者输出和 trace 可区分 |
| C11 | 收到同一成交通知/乱序通知 | reducer 与 Trade 去重/水位合同一致，不重复状态作用 |
| C12 | cached 与 model source 提供同一最终 SignalFrame | Core 决策完全相同，无重复组合/标准化 |
| C13 | 新增冻结 Feature/策略插件 | Core 无需修改；发布包不依赖 mutable Research |
| C14 | 插件试图联网/读 latest/写 DB | 静态依赖与隔离 conformance 测试失败；不把普通执行宣称安全沙箱 |
| C15 | 保存 trace 后供 UI 查询 | 图上目标/原因与真实运行一致，UI 不调用决策引擎 |

性能验收单独记录 batch/逐日耗时与内存，不通过删校验、改 dtype 或改变算子来达标。具体预算在固定硬件和代表性数据上确认后冻结。
Core 可在每次 `execute_feature_plan` 内复用一次构造的 history 键集合及校验后 refs 的 session/industry 保序索引以减少重复扫描，但不跨调用或 cutoff 复用结果，完整验证、算子数学及 FeatureFrame payload/identity 必须保持逐字一致。

## 12. 依据与未决项

继承上传的 Axiom 总纲 v0.1 §5–7，以及 signal-centric 文档关于模型与策略解耦、组合表达式和 target-based plan 的设计。本版进一步明确 Feature stage、插件 ABI、AccountState 版本及 pending order 的职责。

尚待专项确认：首个模型 backend、插件打包方式、具体 portfolio 基线、state migration 规则、日级事件时间表和实际交易规则覆盖。不得因这些未决项引入多个 mode-specific 决策实现；缺支持时明确拒绝。
