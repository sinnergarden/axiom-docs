# axiom-research 初版设计：信号研究、性能提升与发布验收

> 文档编号：AX-RESEARCH · 专项初版 v0.1 · 所属设计包 v0.2 · 2026-09-05。\
> 状态：实施参考草案，研究方向是待检验假设，不是已验证收益结论。\
> 上位边界：[总体设计](01_axiom_overview.md)。关联：[Data](02_axiom_data.md)、[Core](03_axiom_core.md)、[Trade](04_axiom_trade.md)、[UI](06_axiom_ui.md)。\
> 来源以 signal-centric、Feature inventory、PIT/LLM 专项及历史讨论为主。历史文档中的“已存在”“可用”“有效”仅代表当时记载，未重新核对的内容不能直接 promotion。

2026-09-28 Data 接口实证：ViewRef 的真实 Query 重放和 Research→Core 薄 adapter 已执行；连续成员、完整 FeatureBuild/模型/OOS/策略回测仍不是本次 Data 教程的验收结论。
见 [真实 Developer 教程](../../notebooks/developer_tutorial.html#section-9) 与 [设计对照](../design-conformance.md)。正文继续定义目标合同。

## 1. 目标与最小闭环

Research 让一个假设能够低成本地变成**固定输入、明确标签、时间 OOS 信号、可复用评估与统一回测**，并说明为什么值得或不值得进入 shadow。

用户希望争取 20–30% 年化、回撤控制在约 20% 至最多 30%，属于研究愿望和策略选择约束，不是软件交付的收益保证。收益目标、持仓 Top5/允许空仓等由 ExperimentSpec/StrategyRelease 配置；架构验收不能靠某条曲线达到目标来代替。

```text
Hypothesis / ExperimentSpec
→ Data requirements + fixed Snapshot/View
→ FeatureRelease / FeatureBuild + LabelSpec / LabelBuild
→ TrainingDataset + split / fit state
→ ModelRelease / OOS SignalRun
→ SignalEvaluation
→ Trade 统一 BacktestRun
→ 对照、失败归因、Evidence、候选 Release
```

Research 经常调用同一个 Trade 回测，不另建 fast backtest。改组合/退出只重跑下游回测；模型/数据变了才重算实际受影响阶段。

## 2. 内部模块与数据归属

```text
src/axiom_research/
  experiments/     假设、范围、尝试记录、对照
  features/        定义、选择、发布、构建、诊断
  labels/          目标公式、maturity、构建
  datasets/        sample keys、split、fit state
  training/        train、rolling、模型接口
  signals/         原始/组合 SignalRun、lineage
  evaluation/      IC/ranking/消融/稳健性/研究解释
  releases/        冻结运行包、证据与候选决策
  cache/           内容与依赖绑定的阶段缓存
  queries/         UI 只读研究/图层接口
  services/ cli/ tests/
```

Data 只提供可信事实与稳定派生；Research 不直接读 raw 或未登记 sidecar 进入正式模型。Trade 可以执行发布的 FeaturePlan 并保存 FeatureBuild/SignalRun；合同归 Research，实际产物归该运行空间，不要求 Trade 写 Research 数据库。

Model/Feature 插件发布为独立、冻结的轻量运行包，生产不 import mutable Research 源码树。Research 可调用 Trade 的离线公共 API，Trade 不依赖 Research 训练主包，避免循环依赖。

2026-10-04 当前有界实现：Research 0.2.1 保留联合输入、固定 ETF Feature/Signal 与持久复用，增加固定六特征/五 session 归一化 target/单 fold 股票模型及独立保存阶段投影。Engine 已消费冻结 ETF 信号和股票预测生成有界离线账户/评价，Research 只读登记原 owner 结果；UI 保存件工作台与股票消费源码已亲审合并交付，owner QA、root 亲看像素和用户验收另记。固定源码、实际范围与限制见 [当前交付](../current-delivery.md)；正文中的通用模型/OOS/插件平台仍是目标。

## 3. 核心产物合同（P01、P05、P06）

当前 ETF 公共入口为 `axiom_research.build_rotation_features`、`build_rotation_experiment`、`load_rotation_experiment`。固定 Data 查询、完整日历与 Research 声明的七证券参考集合，复用 Core 执行；不新增特征执行器。参考集合不是 Data 历史成员证据。已保存实验返回 FeatureBuild、确定性 signal run 和实验身份；本路径没有模型、fold、标签或训练，不将其伪装为 R0 的 model/OOS SignalIdentity。源代码及配置入口见 [当前交付](../current-delivery.md#公开加载与持久复用)。

| 产物 | 必需内容 | 不能混淆 |
|---|---|---|
| Hypothesis / ExperimentSpec | 假设、经济机制、对照、范围、主次指标、尝试族、预算 | 写了假设不等于有证据 |
| FeatureRelease | 公式/代码、窗口/lag、字段顺序、单位、missing/outlier、参考截面、依赖/ABI | 定义不是物化结果 |
| FeatureBuild | D/V refs、F release、scope/lookback、PIT/cutoff、stage/fit ref、实际输入和输出 | build 成功不等于有 alpha |
| LabelSpec/Build | 公式/horizon、起止时点/价格、基准、收益口径、成熟条件、结果 refs | 标签可以未来，Feature 不可以 |
| TrainingDataset | Feature/label refs、sample keys、过滤原因、split、purge/maturity、fit state | 同 Feature 不等于同样本或 split |
| ModelRelease | 模型文件、推理实现、Feature/schema、scaler、训练 dataset/recipe、环境 | 模型不是策略 |
| SignalRun | 原始/组合 score、keys、stage、model/fold/source、信息/可用时间、validity | 分数不是目标仓位或成交 |
| StrategyRelease | signal/model/feature 计划、portfolio/rebalance/risk、state schema、兼容要求 | 研究发布不等于真钱授权 |
| Evidence | 被比较对象、协议/基准/成本、指标/稳健性、PIT 暴露、全部变体数量、结论 | 结论仅在所绑定上下文成立 |

Data输入依[个人版设计](02_axiom_data.md)固定Snapshot + QuerySpec，不要求独立DomainCommit/DerivedCommit/View发布系统。FeatureRelease固定配方；FeatureBuild才绑定具体数据与查询。稳定派生可为固定配方函数/缓存；Qlib路径已接入，Research的QlibView薄adapter显式激活Data导出，并保存P04引用。Qlib不重做PIT或自动归一化单位；训练processor和Feature语义由Research明确。

调用链是 `Research 编排 → Data Reader/P02 DataBatch → Research adapter → Core/P05 FactBatch + FeaturePlan → FeatureFrame → Research 保存 P06 FeatureBuild`。Research 的 adapter 按键保留单位、时间、缺失与来源，不另写 Feature 执行器或 PIT Reader。Label 读取使用独立的结果范围与查询上下文，可以包含目标窗口未来事实；Research 检查 maturity/训练 cutoff，禁止这些结果流回决策 FactBatch。账户回测经 P09 调 Runtime，账户指标读取 Runtime 的 P10 输出；UI 经 P12 读取已保存研究产物。

历史 best-effort、系统观察时间和有证据的市场公开时间分别回答不同问题，不是资格晋升链。研究应记录所用 policy、范围和限制；数据检查通过不证明样本池或停牌/缺数排除无偏。财务/股东域按真实 Feature 需求接入，不把全域认证当作市场研究前提。

### 3.1 FeatureRelease 示意

```yaml
feature_release_id: fr_example
business_hypothesis: "示例：质量变化可能改善中期排序"
expected_horizons: [60, 180]
input_requirements_ref: req_example
feature_plan_ref: plan_example
runtime_package_ref: pkg_example
ordered_schema_ref: schema_example
missing_policy_ref: missing_example
reference_universe_policy_ref: cs_example
compatible_core_api: core_api_v1
```

同名 Feature 若公式/lag/输入/revision policy 不同，必须有不同定义身份；旧 registry、Qlib expression、模型 features.json 最终指向同一正式定义，不能各自成为 authority。

### 3.2 Feature stage

至少区分 `base`、`cross_sectional`、`model_input`。UI 请求哪一阶段就返回哪一阶段；模型输入绑定 fitted TransformState/ModelRelease/fold。查看原值不等于查看训练输入。

Column 级 provenance 保存一次公式/输入关系；UI 可追到 source refs 和选中样本，不给每个 cell 都建立昂贵独立收据。

<a id="experiment-records"></a>
### 3.3 实验记录与只读索引

状态：`accepted`（2026-10-04 的有界读取合同）；实现与验收另记[当前交付](../current-delivery.md)。首版复用已有 ETF RotationExperiment、FeatureBuild、SignalRun 和 ArtifactRef，不引入训练、特征执行器或第二套回测。

研究问题保存稳定 `question_id`、内容身份 `question_ref`、`title`、`description`、`hypothesis` 和首次登记的 `created_at`。问题下的版本保存 `version_ref`、`question_id`、同问题的 `parent_version_ref`（首版为 null）、`label`、`explanation`、完整 `parameters`、固定 `input_refs`、人工声明的 `explicit_changes` 和登记时间。问题、版本及运行记录均不可变；参数改变产生新版本，不根据收益或参数替研究者补写意图。

运行记录保存 `run_record_ref`、`question_id`、`version_ref`、`created_at`、`status`（COMPLETE / FAILED / BLOCKED）、`reason`、可选的显式 `outcome`、`output_refs`、`backtest_ref` 和 `evaluation_ref`。失败或阻断必须有原因；缺结果不补零，处理完成不代表策略有效。输入、输出沿用既有 ArtifactRef；FeatureBuild 与 SignalRun 的身份在相应引用中保留。Engine 引用精确保留原字段：`backtest_ref={run_id,content_digest,signal_ref,committed_sequence,uri}`；可选 `evaluation_ref={evaluation_ref,evaluation_content_digest,input_run_ref:{run_id,content_digest,committed_sequence},uri}`。前者信号必须对应输出 SignalRun，后者必须与前者的运行身份、输出 digest 和水位一致；不得把 Document.identity 叫作 run_id，也不改变旧 BacktestRun。

分组、标签、收藏和搁置属于 Research 业务状态。`organization={revision,groups,tags,favorite,shelved}` 以 `expected_revision` 比较后更新，并保留全部旧修订；并发旧值不能覆盖新值。这里的 tags 是整理标签，与预测目标 LabelSpec 无关。首版采用显式路径的一份轻量 JSON 索引，原子替换与写入锁保证一致性，不建立 registry 或数据库平台。

登记修订与实际回测分开：有账户结果的记录按 Engine 原值 `{run_id,content_digest,committed_sequence}` 导出稳定 `saved_run_ref`，仅替换评价或登记说明不产生新的回测。其计算为规范 JSON `{contract_version:'saved_backtest_ref_v1',input_run_ref:{run_id,content_digest,committed_sequence}}` 的 SHA-256；规范化使用 UTF-8、sort_keys、无额外空白。默认 runs 每个 saved_run_ref 一组，保留该问题下全部不可变 `registration_history`，旧 candidate 不删除。组表层使用筛选后最新保存登记作为导航，不能据此声称评价已审核；完整历史可逐条打开。没有账户结果的记录保留独立 `REGISTRATION_ONLY` 项，saved_run_ref 等于 run_record_ref；不把失败、阻断或信号登记计成一次回测。

同一问题可有多次回测，首版支持**运行级**收藏与搁置：可选 `run_organizations` 按稳定 `saved_run_ref` 保存 `{revision,favorite,shelved}` 历史，公开 `update_run_organization(run_record_ref,expected_revision=...,favorite=...,shelved=...)` 将登记引用解析到该稳定目标，再作相同的修订检查。换评价后标记继续生效。runs 投影增加 `saved_run_ref`、`run_kind`（SAVED_BACKTEST / REGISTRATION_ONLY）、`registration_history` 和 `organization`，不改变不可变登记内容。旧索引缺此字段时仅读投影默认 revision=0、favorite=false、shelved=false，不能猜测旧问题收藏代表其中哪些运行；问题分组/tags 及原有组织状态继续可读。

登记已有完整实验时，`ExperimentStore.register_saved_experiment(question=...,version=...,run=...)` 在一次原子写入内保存三类记录。question 使用 create_question 参数；version 使用 create_version 参数但不传 question_id；run 使用 record_run 参数但不传 question_id/version_ref。校验失败不能留下半套问题或版本。单记录入口保留，供显式分步研究使用。Reader 的公共 import 与可选 Data/Core 构建运行环境分离，旧构建入口按需加载。

```python
from axiom_research import ExperimentStore, ExperimentReader

writer = ExperimentStore(index_path)
question = writer.create_question(question_id="etf-momentum", title="ETF 轮动",
    description="固定数据下的规则基线", hypothesis="由研究者明确填写")
version = writer.create_version(question_id=question["question_id"], label="baseline",
    explanation="本版目的与限制", parameters=parameters, input_refs=input_refs,
    parent_version_ref=None, explicit_changes=["首次登记固定基线"])
record = writer.record_run(question_id=question["question_id"],
    version_ref=version["version_ref"], status="COMPLETE", output_refs=output_refs,
    reason=None, outcome=None, backtest_ref=backtest_ref, evaluation_ref=None)
writer.update_organization(question["question_id"], expected_revision=0,
    groups=["ETF"], tags=["baseline"], favorite=True, shelved=False)

reader = ExperimentReader(index_path)
index = reader.index(group=None, tags=[], status=None, favorite=None, shelved=None,
    question_id=None, version_ref=None, run_favorite=None, run_shelved=None)
detail = reader.detail(question["question_id"])
diff = reader.compare_versions(left_version_ref, right_version_ref)
```

公共投影 `experiment_projection_v1` 返回 `store_revision`、索引 `content_digest` 和 `questions:[{question,organization,last_activity_at,saved_backtest_count,registration_count,versions,runs}]`；detail 返回同一投影中的单个问题。saved_backtest_count 是当前投影内 SAVED_BACKTEST 组数，registration_count 是这些返回组及 REGISTRATION_ONLY 项的完整登记历史条数，两者分开命名。筛选 tags 要求全部命中；version_ref 保留对应版本及有匹配登记的组，status 要求至少一条匹配登记，组的完整历史仍保留；未运行版本在未指定 status 时仍可查看。兼容旧 favorite/shelved 参数的问题级语义，当前运行收藏/搁置使用显式 run_favorite/run_shelved，仅保留匹配组，无匹配则不返回该问题。默认近期排序按问题下全部保存 question/version/run 的 created_at 最大值 `last_activity_at`，保留稳定 ID tie-break；老问题新增运行或登记也回到近期前面，收藏修改不伪造运行时间，不取 mtime。版本比较返回声明变动及保存参数、输入引用的逐字段差异，不推断业绩因果，也不重算账户指标。

Reader 构造、索引、详情和比较仅读取并校验索引元数据，不创建目录或文件，不逐次哈希整个产物目录，不导入 Data/Core 执行入口，也不调用训练或回测。外部产物在登记与实际读取时由各 owner 的公开 loader 校验；索引校验不替代产物可用性或真实性证明。旧产物未登记时不自动扫描成研究结论。UI 经此投影浏览，再按 Engine 公共 loader 读取已保存账户与评估结果。

## 4. Dataset、Label 与时序

### 4.1 数据准备顺序

```text
读取足够的连续历史（含历史 union/lookback）
→ 单证券时间特征
→ 当日 PIT membership/industry
→ 当日参考截面变换
→ sample filter（原因显式记录）
→ 按 security/session 键对齐 label
→ 分训练/验证/OOS
→ 仅在训练范围 fit 的预处理
```

不能先只保留在池日期，再计算丢失历史的 rolling。已有持仓若不在候选池，仍由 Trade 跟踪；给池外持仓评分需要明确参考截面和缺数据政策。

模型依赖须声明 domain/字段、历史长度、可接受滞后、required/optional 及缺数策略，引用 [Data 唯一源时序与就绪合同](02_axiom_data.md#source-readiness)。T 日业务事实次晨才可得时，历史与实盘均不能当作 T 收盘已知；Runtime 在冻结时点 C 检查依赖就绪并调用 Core，输出与意图截止 E 对齐。仅行情模型不等待未使用的域；本轮 ETF 不接入两融或 ML。

2026-10-04 长历史裁决保持现有执行 profile、双向限价和固定 7 ETF：159915.SZ、510300.SH、510500.SH、510880.SH、511010.SH、513100.SH、518880.SH。Data 保存的有界来源探测覆盖这 7 个代码各自的 `etf_limit(ts_code, start_date=20141101, end_date=20190625)`：7 次均为空；同代码 `20190626` 单日正控均返回有效双向限价。原 21 个限价响应均低于 3000 行上限；按证券汇总，每只最早返回日均为 2019-06-26。替代 `stk_limit` 使用相同 7 代码和早期窗口、同日控制：14 次 ETF 查询均为空，股票正控返回有效行。结论只适用于这两个端点和明确查询条件，不推断其他来源均无早期历史，不自动换源或放宽价限；若有新增来源或漏采证据，由 Data 显式裁决并固定新 Snapshot。

据此已接受长期评估的共同范围候选 **2019-07-01—2026-09-30**。首个交易 session 2019-07-01 之前，Research 必须从同一固定 Snapshot 的真实交易日历取出截至严格前一 session 的连续 21 个行情与因子观测，7 ETF 均须得到有效 20D 信号；预热期不要求用于交易的限价。先以首周等有界范围检验公共 Data/Core 配方、同输入复现、无事实读取或 Core 执行的持久复用及 Engine 信号合同，并记录耗时、内存、产物大小。全历史构建仍等待最终 09-30 Snapshot 固定，并对其重验起点就绪；旧 Snapshot 的小预检不能代替最终范围验收或多年规模证明。

候选范围内既有两处行情缺失按已冻结的无填补、信号 invalid 和 Engine 执行规则处理，保留原日期与完整 universe；不能静默删除缺失日期、缩小证券集合或调整策略参数。收益与长期统计只由保存账户及 [Trade 长期评价合同](04_axiom_trade.md#long-history-evaluation) 给出，Research 预检不启动账户回放。

### 4.2 LabelSpec

```text
label_id / semantic_version
horizon_sessions
feature_session / decision_time / earliest_trade_time
return_start_rule / return_end_rule
price_basis / corporate_action_policy
absolute_or_excess / benchmark_ref
normalization_policy
maturity_rule / missing_or_delisting_policy
```

改变 horizon 必须改变实际公式与 maturity，不能只改变 manifest。使用真实交易日历，不用工作日近似。前瞻目标起点/终点含不含首日由具体规则固定，不用字符串“未来 20d”隐含定义。

训练 cutoff 为 T 时，只使用 target_end 及必要结果在 T 前已经可用的标签；验证早停和模型选择也需遵守模拟训练时可知性。长期标签重叠时按目标区间做 purge/隔离，不仅比较 feature 日期。

缺价、退市等不能事后删除全部亏损样本使训练/评价偏好幸存者。无有效价格或退出事实时按 label contract 标记并报告覆盖偏差；不能把所有 invalid 都填 0。

### 4.3 Rolling 与 OOS

保存每个 fold 的 train/validation bounds、label maturity cutoff、fit state、ModelRelease、允许预测区间和实际样本。模型“文件今天生成”与“模拟当时允许预测”不是一个时间；后者必须由数据/标签/训练时序证明。

最终 holdout 在研究选择前锁定；不把不断用于选择参数的验证集称作 untouched OOS。Meta/stacking 只能读 base model 的 OOS predictions，禁止把训练内拟合分数当新 Feature。

### 4.4 Baseline 资格

Legacy baseline 可封存并用于 forensic 数值对照，但不因冻结就认定正确。新 baseline 绑定实际消费范围的 Snapshot/QuerySpec、PIT 限制、Feature、Label/Dataset 和执行检查；可接受的历史 best-effort 事前声明，不要求 Data 先建通用认证平台，也不能据探索结果宣称严格历史可见。

不能同时改变 universe、PIT、Feature、模型和执行口径，再把收益变化全部归因模型。CSI800 与 CSI1800 的结果分开记录；source history 不足以支持 strict 长历史时，显式限制范围或 best-effort，不能为了训练 8 年而伪造历史版本。

后续 ETF 长历史消费必须显式绑定 Data 新阶段验收后的最终 Snapshot，保留原固定小样本，不以 current 替换。策略仍沿用现有七证券参考集合、20 session 动量、正值 Top1 和周首交易日/严格前一 session 信号；先核实上市边界与完整交易日历，滚动窗口包含 20 个前置 session。上市前、warmup 与内部缺价/因子缺证分别保留 invalid 及原因，不压缩日历、不补零、不将参考集合伪装成历史成员证据。先用不超过现有 114 sessions 的固定窗口量测耗时、内存与写入体积并声明预算，再开展已授权的多年消费；不重新采集数据，不以短样本推断多年性能。

<a id="stock-qlib-lightgbm-minimal"></a>
### 4.5 股票 Qlib + LightGBM 五交易日最小闭环

2026-10-04 实施范围：先固定训练 2023-10—12、OOS 2024-01（预热另含此前 21 个实际
交易 session），再按月扩展 2024；不按结果选月份、不调参。若固定 Snapshot 不覆盖此范围，
在执行前声明替代短窗口，不能依据收益选择。真实输入通过 Data 公共 Reader 与 P04 Qlib
导出，保存 Snapshot/query/export digest；先连续历史 union 与 lookback，再按每 session
可见 CSI300 dated membership 筛选，不能替换为当前成分。缺成员证据阻断该日期；
best-effort 来源限制原样保留，不声称严格历史 PIT。已核实本机 Python 3.12.14、
Qlib 0.9.7、LightGBM 4.7.0 可导入；依赖已存在不等于股票样本已验收。

**Feature 唯一源**为 Research 机器可读 catalog，列 `group/id/name/formula/dependencies/
lookback/normalization/missing_policy/semantic_version`；模型 config 按 id+version 选择有序列。
ID 按动量、波动、价格、量等意群留号，不连续编号、不重编。首版六项为 1/5/20 session
复权 close 回报、(high−low)/close、close/open−1、amount_cny/5-session 均值；定义编译为既有
Core FeaturePlan，不另写执行器。公式/单位/窗口与实际 plan 同源，文档表自动生成，规划项
不冒充已实现。采用同 session 可见成员截面的 cs_zscore（ddof=0、epsilon=1e−12、无 clip、
缺值跳过且原缺值保留、常量截面 missing、池外 missing）；它不是 beta/行业中性化。
本轮没有拟合型 scaler；以后增加时仅在该 fold 训练分区 fit 并保存参数。

**LabelSpec** 固定 `forward_5_session_open_close_v1`：feature session f 后真实交易日历的
第 1 个 session open 至第 5 个 session close，`close(f+5)/open(f+1)−1`，两端使用同锚点
可见复权价，原始绝对收益、无成本。原始收益保留用于标签证据与 IC/RankIC；训练 target
另按 feature session 的历史可见成员、Feature 全部有效且结果实际成熟的样本执行既有 Core
cs_zscore（ddof=0、epsilon=1e−12、无 clip、缺值跳过且原缺值保留、常量截面 missing）。
保存 raw_return、normalized_target、截面实际 eligible keys/section ref、Core plan/context/frame refs，
以及原始 label_available_at 与归一化依赖的 normalized_available_at；归一化是 outcome-only
结果处理，不将未来标签接入 decision facts。每行保存实际 start/end session、端点价格/
因子来源与 `label_available_at`（所有必要结果事实可用时间最大值），只有它不晚于 fold
fit cutoff 才训练；H=180 也须真实端点与成熟事实，不能自然日减 180 或只解析名称。
结果查询与 decision facts 分离，缺价/因子/终点不填零。每月 fit cutoff 在首个预测日期之前，
扩大训练只能加入当时已成熟历史；本轮无早停或验证选参，后续 validation 必须整日期切分。

**最小持久链**为 `FeatureBuild → LabelBuild/Dataset → ModelRelease → Prediction/SignalRun →
SignalEvidence → 同一 Engine`。CPU LightGBM regression 固定 100 trees、learning_rate=.05、
num_leaves=31、max_depth=5、min_data_in_leaf=20、seed=42、num_threads=1、feature_fraction=1、
bagging_fraction=1、deterministic=true、force_col_wise=true；不搬旧调优参数。模型保存原生
booster、列顺序、训练键/成熟 cutoff、输入与实现/环境 refs，可独立加载预测。缓存身份绑定
这些依赖。完全相同实验复用不得重读事实、执行 Core 或训练；仅修改标签或训练时可复用
已冻结 Feature 与原始 Label，身份绑定原实验/Feature/Label refs，且不重跑 Feature。
明确 prediction_raw、signal_score、rank、target_weight；本模型输出为标准化 target 的预测分数，
`score_semantics=forward_5_session_cs_zscore_prediction`，无量纲，不解释为五日收益率或百分比。
IC/RankIC 仍与保存的原始五 session 收益按日联合有效成员计算（n≥20，
常量/不足为 null），保存覆盖数、排除原因及成熟标签 refs，不当作账户收益。

Research 公开保存件为 `stock_prediction_run_v1`，顶层含 `signal_run_ref`（除自身之外全部
文档的固定 digest）、`signal_stage=prediction_raw`、上述 `score_semantics`、
`score_unit=dimensionless`、`model_ref`、`feature_ref`、有序固定 `universe`、`rows` 和来源限制。
每行 `{security_id, session, knowledge_cutoff, available_at, score, valid, invalid_reason,
member, source_refs}`；键 security_id+session 唯一，所有日期保留完整历史 union。`member`
是该 feature session 的历史可见成员布尔值；池外为 member=false、valid=false、score=null、
invalid_reason=NOT_MEMBER。成员内缺 Feature 也保留 invalid/null；不会移除 union 行或补零。
有效 score 必须有限且 available_at≤knowledge_cutoff，来源 refs 绑定 FeatureBuild、ModelRelease、
catalog 和固定 Qlib view。Engine 从这一已冻结原始预测构建中立 ML 输入，保留 signal/model/
feature 原 refs、完整 union/member/validity 和原截面时钟；不冒用 ETF momentum frame，也不
在 Research 重建排名或 target_weight。

每周首个真实交易 session 使用严格前一 session 预测，降序稳定 security_id tie-break、
Top5 等权，不加正值门槛；不足五个有效成员为 NO_DECISION。Core/Runtime owner 按下述
冻结合同实施中立 ML 信号与动态候选；旧 momentum `signal_frame_v1`/Top1 不改名冒用。Research
不实现撮合。股票事件、T+1、价限、状态、税费、持仓出池与估值准入未齐时，真实模型/
信号/IC 先验收，Engine 保存明确 BLOCKED 原因，UI 只读这些 owner 产物；不能用 ETF
profile 宣称完整股票账户闭环。账户准入通过后才交既有 Engine 运行。

本轮有界账户合同只对上述保存预测施加 `sz_main_a_000_002_003_v1` 执行资格：feature
session 历史 CSI300 成员内、canonical 深市股票代码 000/002/003 子集。过滤结果绑定新
账户 strategy/plan，不重训或改写原 314 union 预测，不把子集收益冒称全市场结果。
先核各周严格前一 session 是否至少五只有效候选，任一资格内 member invalid 为
NO_DECISION；事件/因子核查覆盖完整资格 union，不只最终 Top5，再由同一 Engine
实施冻结股票专用规则；见 [Trade §6.1](04_axiom_trade.md#stock-daily-observed-minimal)。
stock_daily_observed 保留 UNKNOWN 与同日撮合事后证据；严格状态对照同时保留。
stock_action_policy=observed_implemented_only 的行动诊断/阻断边界只由 Trade 主章定义；
六组全非实施歧义保留原 NULL 与证据，不改 Data/预测，不凭诊断换股或补第六名。

验收固定输入再现、冷构建/缓存复用、独立进程模型预测/只读加载、标签晚到与不规则日历
边界、缺失/常量截面，以及 Engine 合同消费。分别记录 Qlib 导出、Feature、Label/Dataset、
训练、预测、账户回放的实测 wall time/规模/峰值内存/文件体积；未运行阶段明确空缺。
以首个真实月的测量再估算 2020—2026 扩展时间，不提供未经测量的理想吞吐估计。

SysQ 固定 [852bcb7 的使用/架构](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/docs/requirements/domains/research.md)
及关键源码已只读核对：**可复用**连续历史后成员过滤、完整日期 validation、信号缓存与账户
回放分离；**要改**逐行 label_available_at、冻结模型归档、派生输入 digest 和明确 score
阶段；**不采用**工作日 fallback、缺失填零、当前成员替代历史、旧调优参数、旧 matcher/UI
建表副作用。具体证据为
[generator](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/research/generators/lightgbm_single_label.py)、
[training](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/signal/alpha_v1/training.py)、
[calendar/maturity](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/research/generators/utils.py)。
借合同与经验，不迁移另一平台；参数可复现范围依
[LightGBM 官方说明](https://lightgbm.readthedocs.io/en/stable/Parameters.html)。

<!-- stock-feature-catalog: generated; source axiom-research/src/axiom_research/catalogs/stock_ml_v1.json -->
# stock_ml_v1

Catalog identity: sha256:41bcf9f3640eabdc375bc9f481d11e163ac10e7eb486bc70b89290df171ca862

Lookback counts the current feature session. Inputs use a visible common anchor; amount remains CNY.

| Group | ID | Name | Version | Formula | Dependencies | Lookback | Normalization | Missing policy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MOM | MOM010 | ret1 | 1.0.0 | adjusted_close[t] / adjusted_close[t-1] - 1; common anchor = feature session | ["market_daily.close","adjustment_factors.factor"] | 2 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; require complete finite positive close window; never fill zero |
| MOM | MOM020 | ret5 | 1.0.0 | adjusted_close[t] / adjusted_close[t-5] - 1; common anchor = feature session | ["market_daily.close","adjustment_factors.factor"] | 6 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; require complete finite positive close window; never fill zero |
| MOM | MOM030 | ret20 | 1.0.0 | adjusted_close[t] / adjusted_close[t-20] - 1; common anchor = feature session | ["market_daily.close","adjustment_factors.factor"] | 21 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; require complete finite positive close window; never fill zero |
| VOL | VOL010 | intraday_range | 1.0.0 | (high[t] - low[t]) / close[t] | ["market_daily.high","market_daily.low","market_daily.close","adjustment_factors.factor"] | 1 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; zero denominator missing; never fill zero |
| PRC | PRC010 | close_to_open | 1.0.0 | close[t] / open[t] - 1 | ["market_daily.close","market_daily.open","adjustment_factors.factor"] | 1 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; zero denominator missing; never fill zero |
| LIQ | LIQ010 | amount_relative_5 | 1.0.0 | amount_cny[t] / rolling_mean(amount_cny, window=5, inclusive_current=true) | ["market_daily.amount_cny"] | 5 | {"clip":null,"constant":"missing","ddof":0,"epsilon":1e-12,"excluded":"missing","group":"session","missing":"skip","op":"cs_zscore","reference":"reference_members","unknown_group":"reject"} | preserve; complete five-session window; zero denominator missing; never fill zero |
<!-- /stock-feature-catalog -->

<a id="stock-saved-stage-report-proposal"></a>
### 4.6 保存股票研究阶段信息的最小投影

状态：`implemented_bounded_saved_projection`（2026-10-04）；Research 0.2.1 经 [PR #3](https://github.com/sinnergarden/axiom-research/pull/3) 亲审后合并为 `3a7451e`，只补实际成熟训练窗口、阶段测量与信号汇总。
现有 StockMLExperiment 公共输出已有配置/预测/逐日 evidence，ModelRelease 已有 fit cutoff、
参数和 Feature schema；实际训练键在已验证 dataset.json，测量在 owner 单独保存的验收
receipt。本轮由独立 stock_stage_report 公共 Reader 输出这些保存值；UI 不越过 owner 读取内部文件或自行统计。

公共入口 `axiom_research.export_stock_stage_report(experiment_path, *,
timing_receipts=(), destination)` 只从公共 loader 已验证的保存件生成独立
stock_stage_report_v1；`load_stock_stage_report(path)` 只验 hash/ref 并返回保存值。
不初始化 Data/供应商/Qlib/Core/LightGBM，不训练、推理或回放；sidecar 在调用方明确的新路径
保存，不改旧 experiment manifest、模型、预测或身份，也不新增实验 registry 或账户运行。
UI 显式提供 report 路径并逐值绑定当前登记，缺报告维持“未提供”，不跟随索引 URI。

报告最小包含 stage_report_ref、content_digest、report_version、implementation_ref，
input_refs={experiment_ref,feature_ref,dataset_ref,model_ref,signal_run_ref,evidence_ref}，
training、signal_summary、measurements、limitations。身份绑定全部 input_refs、测量 receipt
文件 digest、report_version 与 implementation_ref；content_digest 绑定全部保存输出。
训练部分分别保存声明训练 feature-session 范围及 fit_cutoff，和 dataset.training_keys 的
实际首末 feature session/去重 session_count、training_row_count、原 excluded 原因计数。
实际窗口来自已入模键，不以 fit cutoff、配置结束日或首尾自然日推断；原标签成熟规则不改。

signal_summary 从保存 evidence.series 汇总 IC/RankIC 各自非 null 的 session_count 和 mean，
weighting=equal_valid_session、missing_policy=exclude_null_no_fill；空有效集合 mean=null。
保留 evaluation_cutoff、score/label semantics、minimum_pairs 与 rank_ties；预测总行/有效行、
有效/排除配对各自计数，不能混用。不新增 ICIR、显著性或账户收益；UI 只格式化保存汇总。

measurements 只接受调用方明确提供、可绑定当前实验或其已声明 input_reuse 的 owner receipt。
每条保留 receipt 文件 digest、来源 experiment/feature ref、原 metric 字段、阶段、执行模式
（cold_build/saved_input_build/cache_reuse/readonly_load）、实测 seconds 及对应规模/内存/bytes。
复用未执行的阶段标 REUSED_NOT_EXECUTED、展示耗时 null，缺测量标 NOT_PROVIDED；不能把
receipt 中跳过阶段的 0 当作冷构建耗时。原生 total/build seconds 分别保留，不用分阶段之和
补总耗时；当前训练/预测、旧来源同 feature_ref 的冷 Feature、缓存加载分别显示来源和模式。
输入相同的 Feature 历史测量不能冒充当前模型冷训练，也不能拼接成一次实测总耗时。
当前/继承 receipt 的 build metrics.cache_hit=true 不能提供冷构建或 saved-input build 测量；
缓存加载只从独立 cache_reuse 字段读取。解析与 receipt digest 绑定同一字节快照。
真实测量可辅助同配方/环境的更长范围估算，但必须说明规模、缓存、I/O 与观察点不足，
不提供未经执行的吞吐保证。首版验收只读/hash、输入引用、训练键范围、null/非 null 汇总、
测量归属及缺测量；原保存件 hash/mtime 保持不变，不为展示重跑。

保存股票账户完成后，Research 只在原模型版本追加 Engine observed/strict 账户与评价登记，
精确绑定 run_id/content_digest/committed_sequence 和评价 input_run_ref，并关联原模型/阶段报告。
旧 model manifest 及旧登记当时的 BLOCKED_PENDING_STOCK_RUNTIME_ADMISSION 原样保留；
新记录反映后续账户完成，不倒写原研究历史。UI 读取当前 owner 登记与保存 run/evaluation，
图表复用同 Snapshot 的完整 native market-replay DataBatch；本轮已有 OHLCV/amount，
无需新 Data 查询，volume_shares 单位为股，所有共同字段、逐键 metadata 与 Query 绑定原 ref。

<a id="stock-saved-fold-clock-contract"></a>
### 4.7 保存输入的有界滑动 fold 与独立时钟

状态：**合同及固定软件经父任务亲审；旧证明格式兼容修复通过亲审后，两个真实滑动 fold 已保存并通过 owner 验收，教程收尾待协调**（2026-10-05）。本轮只补两个
真正滑动的 weekly fold；旧固定日期试点及其失败/通过证据保留，全年/多年仍暂停。
不建设通用 schedule、自动搜参、多年缓存或平台。现有 Data Reader/价格调整、Research
Label/归一化和原生 LightGBM 后端继续复用，不新增 Feature 执行器或账户路径。
该有界验收包括保存后公共载入、同定义 HIT、Engine v2 中立验证及 saved booster 独立
预测逐值相等；首次格式校验失败证据保留，恢复复用已保存标签，不重读 Data 或归一化。
v2 账户仍未准入；私人产物及完整逐阶段时间、内存、重复父件解析证据留在本地。

**当前约束与最小解法。** 旧 Research `_validate_config` 要求
`fit_cutoff < cutoff_by_session[prediction_session]`；同一映射又用于 Feature 查询/构建，
预测行直接复制 Feature 的 knowledge_cutoff。`build_stock_ml_from_saved_features`
继承原配置，拒绝更换配置，不能把旧 20:30 字符串改成 21:00 后假称原输入。
旧 Engine `validate_stock_predictions` 对 `stock_prediction_run_v1` 还硬要求
`knowledge_cutoff == session + 20:30 +08`，并校验精确字段集合。
同一 Core portfolio `_plan` 也把严格前一 session 的决策 context cutoff 固定为20:30。
本增量保留这些旧规则，用独立 fold 入口和新预测版本表达不同阶段的时钟；
当前 Engine v1 消费不会自动支持新版本，不能转换回 20:30 或放宽旧准入。

**最小公开入口与返回件：**

```python
from axiom_research import build_stock_ml_fold_from_saved_inputs, load_stock_ml_fold

fold = build_stock_ml_fold_from_saved_inputs(
    input_manifest, fold_spec=fold_spec, destination=new_destination, metrics=metrics)
saved = load_stock_ml_fold(fold.path)
saved.identity       # fold_ref，固定 definition 与输出引用的身份
saved.to_dict()      # stock_ml_fold_v1；含 content_digest
saved.predictions()  # stock_prediction_run_v2；完整 union/validity
saved.model()        # stock_model_release_v2 元数据
saved.evidence()     # 原 stock_signal_evidence_v1，OOS 原始标签 IC/RankIC
```

入口只读取显式保存输入、训练/推理和发布新的不可变 fold，不隐式调用 Data/Qlib/Feature。
旧同配置 helper 不放宽。新 fold loader 只读/hash/ref/时钟及关联校验，不导入
Data/Core/LightGBM、不计算预测或统计；损坏、缺父件、配置/时钟不匹配均失败。
模型元数据 loader/独立 predict 兼容新 model v2，旧 v1 读取行为不变。

`input_manifest` 固定为 `stock_ml_saved_inputs_v1`：绑定原 Data.plan_scope 文件/ref、
Snapshot/PIT、完整实际 calendar/有序 union、catalog/selection/列序，完整 Feature parents
的 features 与 input-evidence 文件/hash/ref，以及各 raw/normalized Label 父件的文件/hash/ref、
cutoff 和完整日期投影。旧归一化父件须核验保存 Core plan/facts/context/frame 关联，且
raw_label_ref 必须对应已保存 raw 父件的准确日期投影，不只校验一个人工摘要。
每日期选择完整证券截面，不拼成假的 `stock_feature_build_v1`；原父件/证明原样保存，
每次调用重验，证明解析对象校验后释放。本轮保留显式固定父件位置，不宣称通用存储迁移。

准确 manifest 字段集合为 `contract_version/scope/snapshot/pit_policy/calendar/universe/
catalog_ref/feature_selection/ordered_features/feature_parents/training_labels/evaluation_labels`。
`scope={path,file_digest,scope_bundle_ref}` 引用原保存 request/result/source_proof 包装件，
并验证三部分及其 refs；calendar/universe/Snapshot/PIT 必须与其 result 同值。
普通 Feature/Label 文件描述符为 `{path,file_digest,feature_ref或label_ref}`；path 必须是
显式固定绝对路径。`feature_parents` 每项为 `{features,input_evidence,sessions}`，
其中 `features` 是上述 Feature 描述符，`input_evidence={path,file_digest,input_evidence_ref}`，
`sessions` 是完整原 Feature 父件日期。Qlib 保存源的 Snapshot/PIT/universe 也核对一致。
`file_digest` 绑定原文件全部字节，`input_evidence_ref` 绑定解析内容的规范化 JSON hash；
旧证明的空格、缩进或末尾换行不改变内容 ref，也不改写原件。规范格式可直接流式核验
内容 hash；其他格式复用已解析证明核验内容，仍在读取前后检查原文件 digest。
`training_labels` 每项为 `{raw,normalized,sessions,raw_projection}`，raw/normalized 为
普通 Label 描述符，sessions 为完整原 normalized 父件日期；raw_projection 为 exact bool。
true 时只重建原 raw 精确日期投影及其 `parent_label_ref/feature_parent_ref/date_projection`
身份；false 时 normalized.raw_label_ref 直接绑定完整 raw.label_ref。`evaluation_labels`
是完整原 OOS raw Label 描述符，保持原 outcome cutoff/ref；不借该件作训练。

原 Core plan/facts/context 的输入 plain dict 构造和资格判定提取为共享 helper：原
归一化阶段仍由 Core execute，fold loader 用同一 helper 校验保存输入值、availability、
eligibility、norm 参数和 context cutoff；不计算 zscore。全部原 normalized 日期的 Feature
资格投影可访问，包含新窗口外日期；输出 slice 只取本折所需日期。入模行同时要求
原 valid=true、target 有限及排除原因一致；缺未成熟尾部 Label 时，以完整实际 calendar
证明 endpoint 在 fit 后并保留 LABEL_NOT_MATURE，全证券训练 grid 不缩减。

`fold_spec` 固定为 `stock_ml_fold_spec_v1`，准确字段为
`training_window={unit:'feature_sessions',length:65,end:'previous_fit_session'}`、
`fit_session`、`fit_cutoff`、`simulated_model_available_at`、`oos_trade_sessions`、
`inference_cutoff_by_session`（键为由 OOS 严格前一实际 session 推导的 Feature 日期）和
`evaluation_cutoff`。length 为正 exact int，拒绝 bool；所有日期来自冻结真实 calendar。
窗口取 fit 前 65 个实际 Feature 日期，各折独立移动；先保留完整训练 grid，再按原成员、
Feature validity/有限值及原始 label_available_at/end_session 判断成熟，不缩窗凑样本。
`input_manifest_ref` 和 `fold_spec_ref` 均为外置引用：分别对完整 manifest/spec 的
UTF-8 canonical JSON 取 SHA-256，key 排序、无额外空白、ensure_ascii=false、
allow_nan=false；文档本体不包含自身 ref，避免循环身份。所有后续内容 digest 同规则。

| fit / 训练知识截止 | 声明训练 Feature 首末（各65日） | 理论最后成熟日 | 实际训练键预测 |
|---|---|---|---|
| 2024-02-02 20:30 +08 | 2023-11-02—2024-02-01 | 2024-01-26 | 18,300，保存键已证 |
| 2024-02-08 20:30 +08 | 2023-11-08—2024-02-07 | 2024-02-01 | 18,000已证＋02-01新核有效键；预计18,300 |

两折分别 OOS 02-05—02-08 / 02-19—02-23，完整预测 grid 1,256 / 1,570 行，
沿原 Feature validity 的有效数为 1,200 / 1,500。第二折新增日期的有效 label 数必须实测，
不强填300、不使用02-29事后标签替代 fit 标签。

**模拟时钟闭包：** 两折训练事实选择截止均为 fit 日 **20:30 +08**；显式声明模型
模拟可用时刻 **20:45 +08**，对应每个预测 Feature session 的推理截止 **21:00 +08**，
下一实际交易 session 执行。必须满足 `fit_cutoff < simulated_model_available_at <
inference_cutoff`、Feature 原 knowledge_cutoff/依赖 availability 均不晚于推理时钟，
训练 Feature 的原 knowledge_cutoff/依赖 availability 均不晚于 fit_cutoff。
入模行的原始及归一化训练标签 availability/end_session 必须在 fit 时钟已成熟；归一化父件
cutoff 必须与本折 fit_cutoff 为同一时刻；各日期 section_ref 定义绑定的归一化父件
feature_ref 必须等于该日期在 Feature slice 中选用的准确原 parent ref，
不能借较晚归一化或不同父件标签，不给旧 sections[] 虚构独立 feature_ref 字段。
仍使用 Feature 原 **20:30** knowledge_cutoff/refs，
不重新查询21:00事实、不改父件时钟；使用此前已知事实是允许的。
这些时刻属于显式历史模拟场景；实际 wall time 只作性能测量，不证明模型曾在2024当天
20:45真实完成。新模型/预测明确 `clock_basis=declared_simulation`，原事实时钟依据不改。

输出 `stock_feature_slice_v1` 保存准确日期→原 Feature parent/ref、完整 union、列序及
原 cutoff/availability 绑定；其身份为 `feature_ref`，类型明确为 slice，不冒充重新执行的
FeatureBuild。`stock_fold_label_slice_v1` 保存原 raw/normalized parents、cutoff、实际日期/
eligible keys 与排除证据。`stock_fold_dataset_v1` 绑定上述 refs、fold_spec、实际训练键/
training_rows_ref、原 target/normalization 及完整排除原因。
`stock_model_release_v2` 绑定 dataset_ref、feature_ref、label_ref、raw_label_refs、fit_cutoff、
simulated_available_at、clock_basis、原列序/catalog/selection、固定参数/环境/实现及原生
booster_digest；不调参，原100 trees/seed42/单线程不变。

`stock_prediction_run_v2` 保留 v1 顶层 signal_run_ref/signal_stage/score_semantics/score_unit/
feature_ref/model_ref/limitations/universe/rows，新增 fold_spec_ref 与 clock_basis。
行保留原字段，另存 `feature_knowledge_cutoff`、`feature_available_at`、
`simulated_model_available_at`；前两项从原 Feature 保存行得到，不修改原来源。
`feature_available_at` 取原行 `availability` 数组中所有非 null 时刻的最大值；
全 null 时保存 null 并将预测行标 invalid，不伪造 Feature 发布时间。
行 `knowledge_cutoff=available_at=inference_cutoff` 明确为模拟推理/信号发布时钟，
score 仍为有限 float 或 null、无量纲 prediction_raw，所有日期完整保留 union/member/invalid。
source_refs 包含准确 Feature slice、原 Feature parent/Qlib、ModelRelease/catalog refs。
输出 v2 身份绑定全部时钟和来源；旧 v1 不改，Engine v2 时钟消费须单独协调准入，
本轮不执行账户、不假称新预测已经获得 Runtime 准入。

`stock_ml_fold_v1` 顶层保存 definition、definition_ref、fold_ref、content_digest、status=COMPLETE，
以及 feature_ref/label_ref/dataset_ref/model_ref/signal_run_ref/evidence_ref。
definition 绑定 input_manifest_ref、fold_spec、所有准确输入文件/内容 refs、固定参数/catalog、
实现和环境；definition_ref 为其固定 digest。fold_ref 为 definition_ref 与六个输出 refs
的固定 digest；content_digest 为顶层除自身外全部内容的固定 digest。manifest 绑定全部
新文件的字节 hash，显式引用旧父件且不复制/删减旧 proof。临时目录完成校验后原子发布，
同 definition 的完整保存件才 HIT；HIT 不查询/训练/推理，失败临时件不是 HIT，不覆盖旧结果。
SignalEvidence 只消费原02-29 20:30 OOS raw Label，账户/收益准入与此证据分开。
fold 顶层另存 `engine_admission={neutral_validation:'NOT_PERFORMED_BY_BUILDER',
runtime:'NOT_PERFORMED_BY_BUILDER'}`：构建器不调用 Engine 中立 validator 或账户。
该字段记录本保存件尚未执行准入验证，不能用它判断当前Engine的软件能力。旧产物中的
`runtime:'UNSUPPORTED_V2'` 保留为当时保存值；loader接受这两种完整map，均不作为
已准入凭据，也不允许自行写入ADMITTED。独立验收显式
调用公共 `validate_stock_predictions(StockPredictionFrame.from_dict(saved.predictions()))`；
通过证据由 owner receipt 保存，不倒写 fold。当次合成软件输入已通过已审 Engine
`ac20e086` 的同一中立入口（随后合并 `330903c6`）；真实两折输出尚未验证。
Engine中立结构/时钟校验与账户消费分开。当前Engine PR14已增加明确的schedule准入路径，
Research构建器仍不调用它；调用方须显式校验原fold/model/predictions及完整日历，再执行账户。

新增准备最多两次公共查询：同固定 Snapshot/02-08 20:30 cutoff/purpose=label_outcomes，
读取02-02/05/06/07/08的 market_daily(open,close) 与 adjustment_factors(factor)，原 Data
common-anchor=02-08，补02-01 raw label并调用原公开归一化一次。fold入口只消费保存结果；
供应商/Feature/账户为0，两fold fit/predict各2。单重进程、5.5 GiB停止/6 GiB硬上限、
每阶段120秒/新增总480秒/新文件100 MiB；合同核过前不运行业务。

<a id="two-year-weekly-batch-proposal"></a>
### 4.8 两年训练窗与逐周批次：软件候选与实测边界

状态：`software_candidate_synthetic_verified`（2026-10-05）。Research批次入口和两年窗口已完成
合成定向验收，软件仍待亲审；真实两年父件、四周fit/predict与新账户尚未执行。
用户要求简单 Feature、LightGBM、Top5 全链正确且高效。
独立信号评价与批次优化可并行准备，基础评价结果优先交付；后续指标不阻塞连续四个
真实周的两年滑窗与新账户试点。五年运行在主协调核过
总耗时和数据边界后启动；本节记录方案，未运行新的业务或 benchmark。

**窗口与基线。** 候选四周为 2024-01-02—01-26，fit 分别取冻结日历中的
2023-12-29、2024-01-05、01-12、01-19。每次训练使用 `[fit日期减两年, fit日期)`
内的实际交易日；实际末交易日是冻结日历中严格早于fit日期的最后交易日，
`training_window.end='previous_fit_session'` 表示这一边界，不再额外退一日。
保存实际training_sessions及首末session，由冻结日历核对完整日期列表，不靠字符串猜。
减两年遇2月29日回落2月28日。只纳入 fit 时已经到期且可用的五交易日
标签，晚于 fit 的尾部保留排除原因。模型在上一周最后交易日晚训练，预测下一周各交易日
严格前一 session 的 Feature。Top5调仓日期由显式weekly_first_trading_session政策
决定；fold或model切换本身不触发额外调仓。
继续使用 MOM010/MOM020/MOM030/VOL010/PRC010/LIQ010、100 trees、seed42和现有单线程
LightGBM 参数。训练成员取各日历史资格；批次 union 覆盖两年训练、Feature预热及OOS，
不能固定沿用 January 的314个ID来代表两年CSI300。首轮就绪预检决定该候选是否可用，
选窗依据数据覆盖，不能看过收益后换窗。

**一次验证和每折工作分别做什么。** 批次初始化读取每个唯一保存父件一次，核对文件与
内容身份；共同Feature父件同时核对来源证明、Snapshot/PIT、完整键、列序、成员及原事实时钟。
标签的来源、cutoff与成熟资格仍由各折独立核对。初始化把Feature值装入不可写矩阵，
必要资格和时钟随共享行与索引保留，逐片释放完整proof；Feature行和元数据共用同一解析对象。
各折从同一矩阵按交易日切片，共用一次按完整证券ID和日期建立的索引；
每折仍检查窗口和阶段时钟，筛选
已成熟标签，再从同一合格键集合产生 X/y、训练和预测。各fit的归一化Label父件在准备
阶段调用现有Core保存；批次构建器验证其Core输入、输出与资格闭包，不再次执行归一化。

Raw Label 按原 Query/cutoff 与父件版本分组。不同 fit 所需的标签来源版本不同，就分别
保存并在初始化各读一次；相同文件/ref共用。晚 cutoff 查询出的最终标签按日期截断，
不能冒充较早 fit 的来源。首版保留当前 common-anchor、f+1开盘/f+5收盘及价格/因子
可用时钟规则，先去掉父件重复解析，再依据实测决定标签准备是否需要进一步优化。

**入口与保存件候选。** 首版提供有界 `load_stock_ml_batch_inputs(batch_manifest, limits=...)`
入口，并为现有 `build_stock_ml_fold_from_saved_inputs` 增加可选 `batch` 参数。
首版准确形状为 `{contract_version:'stock_ml_batch_inputs_v1',
folds:[{input_manifest:<原stock_ml_saved_inputs_v1>,fold_spec:<原v1或新v2>}...]}`。
各input_manifest引用同一scope、calendar、Feature父件，以及按fit分组的Raw和归一化Label父件，
普通文件描述符沿用 `{path,file_digest,feature_ref或label_ref}`。该对象只在当前进程和
固定输入定义内有效，构建器核对定义匹配；调用方不能传一个布尔值跳过验证。
退出批次释放矩阵，mmap或分块只在容量测量需要时采用。
入口接受非空、有序、有限的fold列表，不设1–4折产品上限；3–4折只是首轮试点预算。
资源预检按实际fold、行和字节数量执行，后续扩到多年仍使用同一入口。
`limits`准确字段为正整数 `maximum_source_bytes` 与 `maximum_matrix_bytes`，默认分别
8GiB与512MiB。它们限制唯一来源文件和共同float64矩阵的字节数，不能证明JSON解析后的
RSS低于进程预算；Raw/归一化Label父件目前驻留批次缓存，真实准备仍须单独量测峰值内存。
`batch.metrics`给出实际父件读取次数、共同矩阵字节与初始化耗时；`close()`或上下文退出释放缓存。

两年窗口使用新 `stock_ml_fold_spec_v2`，
`training_window={unit:'calendar_years',length:2,end:'previous_fit_session',
start:'fit_date_minus_years_inclusive',leap_day:'clamp_feb_28'}`；其他阶段时钟字段沿§4.7。
新fold/dataset使用v2命名空间并绑定实际训练日期和键，旧65-session v1合同与文件保留。
新Feature slice仅物化OOS行，保留实际training_sessions和各日父件；新Label slice保存
选择摘要、键数、排除原因与父件。Dataset保留实际入模键和联合训练行digest，独立loader
从原父件重建后精确核对这些值。
Feature父件、模型后端及 `stock_prediction_run_v2` 的字段沿用现有接口。每折保存归一化
标签、Dataset、模型、预测和引用原父件的证明，不在每折复制整份两年Feature/proof。
发布时验证新文件字节、引用及每折闭包，复用当前批次已经验证的共同父件。独立进程调用
公共loader仍完整验证文件、父件和时间关联；其成本单独记录，不藏入性能结果。

**Dataset选型。** 首版采用一个共同索引和一个共同mask，继续交给原生
`lgb.Dataset(X,label=y)`。Qlib兼容消费是可选薄适配：若DatasetH能实际减少重复准备且
保持矩阵、成熟标签和推理段语义，就接入；仅更换类型名没有提速收益。Feature独立缓存
继续保留。120/180交易日标签目前只记跨horizon复用备忘，65日训练窗不能提供这类成熟样本。

**Engine依赖。** 各周预测拥有不同Model/Signal refs，交给Engine的是原v2保存件及其
有序引用，不能拼成一个虚构的单模型frame。Engine需要一次明确的v2 Runtime准入和
按决策session选择对应frame的适配，使用其原Top5、账户、行情及执行profile生成新的
连续四周账户。接口对齐[Trade调度提案PR24](https://github.com/sinnergarden/axiom-docs/pull/24)：
`stock_prediction_schedule(folds=[{fold_ref,fold_spec,model,prediction_frame}],calendar=...)`
接收原fold元数据、model.json与v2预测，不搬训练大表。各fold使用同一冻结prediction
union，trade_schedule覆盖账户区间每个实际session，并指向其严格前一session原预测组。
run入口一次校验schedule、model和预测闭包，再建立session索引；session循环只消费
已准入组并核当前账户/决策context。前收和成员保留Feature原20:30 cutoff，21:00
预测在下一实际交易日08:55决策准入。跨fold持仓与现金连续；调仓仍由显式策略政策决定。
该提案冻结并实现后才能验收整链；此前v1账户不是本轮结果。

**新账户与页面范围。** 用户已明确所有后续新回测统一初始现金500000元，即
`initial_account.cash_minor=50000000`。信号和模型可复用，账户必须以该初始值真实运行，
不能缩放旧净值代替。页面撤下旧账户记录，本地保存件、登记原值和审计证据保留。
页面展示原保存执行profile的佣金、最低佣金、税费、滑点和容量假设；滑点为0时明确写零滑点，
不省略费用或把开盘代理成交当成真实开盘流动性证据。此处记录展示与新账户要求，未改写旧结果。

**首轮预算与正确性。** 建议一个重进程，总预算30分钟，5.5GiB停止、6GiB硬上限，
新增私人产物8GiB；达到任一预算就保存阶段证据并暂停。先做键乱序、重复/缺行、一日
错位、未成熟尾部、成员变化与常量截面的定向反例；共同索引下X/y键、列序、null和
排除原因必须精确一致。对同一折比较批次与独立投影的矩阵，保存booster独立预测复核，
随后在新进程加载四折并核对原父件hash/mtime。两年输入准备是否完成也单独报告。

**估时与实施顺序。** 分开计量唯一事实/Qlib/Feature/Label准备、初始化解析与验证、
每折切片/归一化/fit/predict/发布、独立载入、Engine账户及评价。先测一折，再完成四折；
首折初始化和稳态每折分开，记录峰值内存、读写字节及每个父件读取次数。长跑公式为
`唯一冷准备 + 各受控批次初始化 + N个实际交易周的每折成本 + 新账户/评价 + 最终独立核验`。
N取最终冻结日历中有交易日的ISO周数；已有256周证据只适用于2021—2025日历。
每项都有实测或显式未知项才能给总预算；不能用65日窗口的42分钟外推两年窗口。
估计2—4小时可交主协调批准长跑；达到10—20小时先优化最大成本项，再重测。
独立信号评价与批次父件验证/共同矩阵可并行实施，基础评价保存读取优先出结果；随后
完成两年窗口定向验收、四周真实fit/predict和新Top5账户，再审核总耗时。扩展指标、
UI设计与长跑分别后置。

<a id="stock-feature-checkpoint"></a>
### 4.8.1 有界 Feature 准备、公开保存与恢复

状态：方向已由主协调批准，以下合同先于源码固定（2026-10-06）；尚未完成长范围准备。
Research 增加两个公开入口，继续调用 Data 的 Reader、价格调整及 Qlib 导出和原 Feature Core。

```python
build_stock_feature_inputs(data, *, spec, destination,
                           shard_sessions=2, progress=None) -> StockFeatureInputs
load_stock_feature_inputs(path, *, limits=None) -> StockFeatureInputs
```

`StockFeatureInputs` 提供目录 `path`、`identity`、`reused`、`to_dict()` 和复制后的
`feature_parents` 描述符。只读入口不导入 Data/Core/Qlib/训练后端，不运行阶段、不写文件。
`limits` 首版为 `{maximum_parent_bytes: 67108864}`，接受正整数、拒绝 bool；它限制每个
Feature/proof 文件在解析前的字节数，不是 RSS 承诺。旧 monolithic loader 仍按原合同读取。

`spec` 的准确字段为 `contract_version='stock_feature_inputs_spec_v1'`、`scope`、
`snapshot`、`pit_policy`、`calendar`、`universe`、`catalog_ref`、`feature_selection`、
`ordered_features`、`read_sessions`、`feature_sessions`、`cutoff_by_session`。
scope 沿用 `{path,file_digest,scope_bundle_ref}`；其冻结日历和证券 union 必须与 spec 一致。
来源 universe_id 只从已验证 scope.request.universe_id 取得，并核对原 request 的
Snapshot/PIT；入口不默认或另猜指数名称。
日期有序且唯一，read_sessions 覆盖所需的完整交易日区间，预热由实际 plan 的
required_history 推导；当前六特征需要前 20 个实际 session。各日期保留自身 20:30 +08
cutoff。Qlib 按原逐 session 查询导出；每个 Feature 日期的历史窗口仍由 Reader 按该日期
cutoff 选版本，并保留原 float32 值、缺失与修订一致性检查。结束日的信息不能替代历史窗口。

一次准备持有一个 Data 生命周期及一个固定 Qlib view。默认每两个完整 Feature 日期保存
一份原 `stock_feature_build_v1` 与原 canonical proof 数组，末块可只有一个日期；
shard_sessions 是正整数，粒度进入 definition，不构成全局产品上限。每块保留完整 union
证券截面、成员、值/null、validity、原因、时钟、Core 和原批次证明。块按日期有序、互不
重叠，完整 index 的日期及 `(security_id,session)` 网格必须无重无漏；记录行可按键重新
索引，X/y 始终由同一合格键集合选择，不能依靠文件行序对齐。
新完整 index 要求每日期 evidence 的 ID 集合与原 core_plan.sources.id 完全一致，并覆盖
原五个行情输入字段和会员字段；字段、批次、原查询 context 与计划的来源绑定必须一致。

新增组织文件 `index.json` 使用 `stock_feature_inputs_v1`，准确顶层字段为
`contract_version`、`definition`、`definition_ref`、`feature_inputs_ref`、`content_digest`、
`status='COMPLETE'`、`qlib_view`、`qlib_manifest`、`feature_parents`。
definition 包含 spec、shard_sessions、implementation_sources、implementation_ref 和 environment，
沿用当前完整实现审计身份，未引入 §8.4.1(A) 的新 cache key。
qlib_manifest 为 `{path,file_digest,view_id}`；qlib_view 是原保存的路径无关 Qlib 引用。
feature_parents 沿用 `{features:{path,file_digest,feature_ref},
input_evidence:{path,file_digest,input_evidence_ref},sessions:[...]}`。
definition_ref 是 definition digest；feature_inputs_ref 绑定
`{definition_ref,qlib_manifest,feature_parents}`；content_digest 绑定输出除自身之外的全部字段。
这些 parent 可交给原 `stock_ml_saved_inputs_v1`，不合成一个拥有虚构身份的大 Feature parent。

每块先在临时目录完成文件、内容 ref、完整键、schema、来源和时钟核验，再原子发布。
随后原子更新 `checkpoint.json`，其准确字段为 `contract_version='stock_feature_inputs_checkpoint_v1'`、
`definition_ref`、`qlib_manifest`、`feature_parents`、`content_digest`。
只有最终完整覆盖才原子发布 index；checkpoint 或临时目录不能作为完整输入。
恢复须匹配同一完整 spec、Qlib/ref、shard 配置、实现和环境，并逐块重验字节、ref、范围及
文件指纹；损坏、冲突、改变输入均不命中，也不覆写原件。首版 builder 与 index loader
要求所有 parent 绑定同一个完整 Qlib view，并逐块核对依赖和覆盖，不自动吸收不同范围的
旧三日件。旧三日件继续作为独立验收证据；将来混合合法子范围需要单独设计合同。

公开保存与 fold 加载共用原 per-parent validator，一次只解析一块并释放完整 proof。
只读 index loader 验 scope、Qlib 文件与全部块的闭包后仅返回索引元数据，不驻留全部 rows。
公开 fold 单次 load 内，同一 Raw descriptor/ref、完整 query、fit cutoff、日历、universe
与 horizon 可共享一个已验证 Raw 对象及 keyed index；每个 normalized parent 仍独立
核验原 Core/raw/Feature 关联并释放。不同 fit 的标签可见性和已选训练结果不复用。
Raw 在这次 admission 建立日期桶和原行序号，块投影仅选择所需日期并恢复原 Raw 顺序，
保持原 projected label_ref，避免对每个块再次扫描全部 Raw rows。
本增量不改所有 fit Label 字典的缓存策略或训练矩阵；其驻留量先单独测量。

同日最终 adjusted 和 membership wire 可在完整 adapter 核验后用于成员选择与证明 digest，
将重复序列化从九次减至六次。共享对象仅在该日期内部使用，不向调用者暴露可修改的
信任缓存；原 Reader、float32 投影、加入 amount 前后的批次仍保留各自 ref。
float32 投影先按 `(security_id,session)` 重索引，再逐列核对 null 和精确舍入值并赋值；
证券与日期键重复、缺失或修订不一致均拒绝，原记录顺序、wire 类型与来源时钟保留。
验收覆盖分块与整体语义等价、跨块键边界、重复/缺行及 descriptor 日期乱序拒绝、按键
对齐、半写恢复、损坏/变更输入/不同 cutoff 不命中，以及原 v1/fold 字节兼容和 loader 零写入。
通过小型测试与独立 review 后才安排有界 Label/Qlib 成本测量，不启动完整 505 日或五年运行。
性能验收必须记录实际导入的 Data 源码及固定输入。旧三日记录未包含 `06b4bd5`
的 Qlib export 单 Reader 复用，不代表新 main 的成本；旧冷启动五次 manifest
分析也不能作为当前 Data 的成本。后续计时应绑定包含该复用和已合日历优化的新实现，
分别记录阶段耗时与峰值 RSS，在明确预算后执行有界样本。

## 5. SignalRun、表达式与评估（P06/P10）

本轮 ETF 导出 Core 中立 `signal_frame_v1`：顶层固定 `signal_run_ref`、`signal_stage=final`、`score_semantics=momentum_20d` 与完整 `universe`；行包含 `security_id/session/knowledge_cutoff/available_at/score/valid/invalid_reason/source_refs`，score 为有限 float 或 null，键唯一。warmup/缺数保留 invalid，不把缺信号变成零。source refs 固定 FeatureBuild 和逻辑 Data Views；账户消费采用严格前一交易日信号。该确定性配方尚无 IC/标签/OOS 评估结论。

Raw 和 Derived SignalRun 使用同一读取/评估/回测协议。必要字段：security_id、feature/decision session、knowledge_cutoff、simulated_available_at 或实际可用时点、score、score semantics、signal_stage、valid/invalid_reason、model/fold/source refs。

原始 Prediction 与组合 Signal 分层保存。首个组合用例复用保存预测做固定权重加法，变换与精确键对齐遵循 [Core §5.1](03_axiom_core.md#51-signalplan)，Research 管输入引用、运行编排和保存。模型超参通常先比较 1–2 次，随后固定 Signal 比较 4–5 版策略与风控；这些尝试放在同一个 idea 下，沿用现有实验记录，保留每次输入、输出、改动和失败原因。

训练 target 与 evaluationLabel 各自定义和固定。例如以 60 日、180 日目标训练的两份预测，可以同时对同一 Y180 或同一 Y40 评价；每个比较组固定评价目标、版本、共同日期与证券以及共同成熟有效样本键，并另报各 Signal 的自然覆盖。40/180 是后续目标示例，M1 先使用真实已有的五交易日 Label。评价配对沿用已保存预测，生成时的 rank/zscore 参考截面保持固定。完整范围与按预测日期所属年份的下钻都应展示 IC、RankIC、分组标签收益和覆盖；ICIR 使用非年化口径，长 horizon 的重叠样本需保留时间依赖的显著性分析。IC 提升仍需由 Runtime 检验 Top5 扣费收益；分组标签收益作为排序诊断展示，NAV 来自独立保存的账户。

### 5.1 信号评估

<a id="saved-signal-quality-proposal"></a>
**独立保存与批量比较：合成验收通过的源码候选（2026-10-05），待主协调亲审。**
[Research PR7](https://github.com/sinnergarden/axiom-research/pull/7) 固定源码
`1912bb5dd4b9b8e6aa595ebf0fe63b5e82a0d2b1` 基于batch PR6，版本0.2.4；
15项定向合成测试和独立复审通过。原股票
`stock_signal_evidence_v1` 已保存逐日IC/RankIC、有效配对数、Signal/Raw Label refs和
评价cutoff。候选实现沿用该文件和身份机制，提供独立公开评价、保存、载入入口及ICIR
汇总。已验证旧v1、分阶段时钟v2和compact fold v2的来源闭包；真实两年规模尚未验收。
Research包依赖下限为 `axiom-engine>=0.3.0`；Engine PR15的准确源码
`e1fbef2c57ce337a3ca3d90ac3136bfb943798fd` 以0.3.0公开统计和schedule入口。
Research PR7后续单行依赖修订 `220d46cccb897fb77ce9125ec95acfd1dd6087b4` 已通过
版本元数据及公开import核验；本轮沿用源码锁定，不等待wheel发布。

Research定义评价范围和标签版本，按 `(security_id,feature_session)` 拼接保存预测与
成熟Raw Label。同次批量评价共用已选定的Raw Label表；公共owner loader仍逐份验证
保存来源闭包，可能重复读取其Label父件，不能据此声称总文件只读一次或已验证规模性能。
训练所用归一化target与评价所用原始未来收益区分。
信号评价使用独立evaluation_cutoff；较晚才成熟或可用的标签可进入事后评价，
不能回流到此前fit_cutoff的训练样本或改写已经保存的模型。
默认指标为日截面Pearson IC、平均秩处理ties的Spearman RankIC，以及有效日序列的
mean/std(ddof=1)和非年化ICIR/RankICIR。保留当前minimum_pairs=20；不足20、常量
截面或非有限相关值保存null与原因。序列不足2日或std为0时IR为null；无有效日时均值
也为null。五日标签重叠会产生时间依赖，短样本IR是描述值，不能据此声称统计置信度。
这些定义参考[Qlib日截面相关](https://github.com/microsoft/qlib/blob/v0.9.7/qlib/contrib/eva/alpha.py#L160-L183)
和[Signal Analysis记录](https://github.com/microsoft/qlib/blob/v0.9.7/qlib/workflow/record_temp.py#L319-L330)，
不把原始回归分数解释为CTR/CVR概率，也不默认计算AUC或calibration。

Research把已经选定的配对表交给[Core纯统计算子](03_axiom_core.md#signal-statistics-proposal)。
Core计算相关与序列统计，Research负责来源、成熟时钟、资格、范围、版本、编排和保存。
DuckDB可作为同表批量join/group/rank的候选后端，先与基准算子核对键、ties、null、
计数和数值误差，再按实测选型；首版不要求安装OLAP服务或改写Data存储。

候选公开入口是 `evaluate_stock_signal`、`evaluate_stock_signals`、
`save_stock_signal_evaluation`、`load_stock_signal_evaluation`。单个评价对象可以是一份
Signal，或按时间覆盖且键不重叠的weekly Signal列表；后者保留所有原refs及model refs，
不伪装成一个单模型Signal。独立loader只验证保存值和来源绑定，不重新计算指标或账户。
同Signal和同评价定义换TopK时复用原评价，策略各自的账户评价继续由Engine保存。
CAGR、回撤、Sharpe和Calmar均由Engine已实现的
[保存账户分析评价](04_axiom_trade.md#saved-account-analysis)提供，Research读取原保存值。

准确调用形状为：

```python
report = evaluate_stock_signal(signal_input, raw_label_input=raw_label_input, scope=scope)
reports = evaluate_stock_signals(signal_inputs, raw_label_input=raw_label_input, scope=scope)
saved = save_stock_signal_evaluation(report, destination=destination)
saved = load_stock_signal_evaluation(path)
report = saved.to_dict()
```

`signal_inputs` 是保留插入顺序的名称映射，每个值是一份Signal描述符或按时间排序的
不重叠Signal描述符列表。描述符精确包含 `path/file_digest/signal_run_ref`，Raw Label
描述符精确包含 `path/file_digest/label_ref`；路径必须是固定绝对路径。scope精确包含
`sessions/universe/evaluation_cutoff/calendar`，其中完整冻结calendar须与原Raw Label及
Signal所属owner记录相同。保存返回 `StockSignalEvaluation`，提供 `path/reused/identity`
及 `to_dict()`；identity是原evidence_ref。目录内保存signal-evidence.json和manifest.json，
相同报告命中复用，身份相同但输出不同则拒绝覆写。

`stock_signal_evidence_v2` 候选顶层为 `evidence_ref/content_digest/input_signal_refs/
input_evidence/label_ref/label_spec/scope/spec_ref/spec/sample_mask_ref/statistics_input_ref/statistics_ref/series/summary/
coverage/status/limitations/implementation_ref`，另含contract_version。
evidence_ref绑定准确Signal列表、Label、scope、spec、sample mask和统计实现；
content_digest绑定除自身外全部保存输出。scope固定sessions、universe、评价cutoff和calendar，
input_evidence沿用原保存文件的显式path/file_digest/内容ref描述符，供独立loader核对
原Signal和Label的来源闭包；statistics_input_ref绑定送入Core的准确配对表。
label_spec原样展示实际horizon、f+1/f+5、价格口径；原件没有单位字段时保留缺失与限制。
series沿原日行扩充必要计数，
summary提供有效日数、mean_ic/ic_std/icir及对应RankIC值和IR不可用原因。
coverage保存原参考成员键数、成熟有效Label数、有效预测数、实际配对数和排除计数，
不以丢弃无效日来提高覆盖。coverage.native保留该Signal自然样本的计数、series、summary
和统计refs；coverage.common_statistics/native_statistics各保存完整Core统计文档及其
输入ref，供loader验证共同与自然样本绑定。loader重建来源配对、核对哈希、计数及
null/reason规则，不重新执行相关、均值、标准差或IR计算；新进程禁导入Data、Engine、
Qlib、LightGBM、pandas和numpy的载入验收通过。旧v1保存件保持原读取行为。

多Signal比较固定同一scope、成熟Label和历史资格，主比较使用各Signal共同有效键交集，
同时展示各Signal原有覆盖与自然样本评价。共同mask绑定整个比较组，增加Signal导致
交集变化时必须生成新评价身份，不能把自然样本指标冒充共同样本比较。范围没有交集或
样本不足要显式显示原因。UI轻量投影读取上述refs、标签周期、范围、计数、指标与限制；
UI展示与比较交互本轮仅作设计备忘，独立评价结果优先交付。

| 组别 | 输出 | 使用条件 |
|---|---|---|
| 全截面 | IC、Rank IC、ICIR、有效样本数 | 日横截面、horizon、权重、NaN/tie 规则固定；ICIR 年化与非年化分开 |
| 排序头部 | Precision@K、Recall@K、NDCG@K、TopK forward excess | 固定候选池、正例/等级、K、基准、无正例日处理 |
| 分布 | 分位组收益、单调性、coverage、missing | 这是标签条件统计，不伪装成可交易净值 |
| 时序稳健 | 分年/阶段/行业/市值、delayed vintage、跨 horizon | 区分未成熟标签，不能只看最终总均值 |
| 增量 | 消融、相关/冗余、TopK 错误、组合贡献 | 与已固定 baseline 做受控对照 |

Recall@K 的正例集合必须单独定义。例如预测 Top5 对真实未来 Top20，recall 分母是 20，precision 分母是 5；若预测与真实集合都固定 K，则两者数值相同，不能当两项独立证据。TopK 盈利比例、进入真实 TopM 比例、跑赢基准比例要不同命名。

NDCG 的 relevance/gain 映射在协议中固定；不能直接把含负数的原始回报当任意 gain 后仍宣称是标准 0–1 指标。长周期重叠样本不按独立日观测夸大显著性；至少报告时间分段稳健性，并在需要时采用保留时间依赖的区块重采样。

## 6. 策略/模型效果提升：首批研究路线

以下为**实验路线，不是承诺有效的默认实现**。先完成可信 baseline 与统一评估，再逐项对照，不一次开启全部项目。

### 6.1 先把“看起来强”拆开

历史讨论中，当前股票池/PIT 改正后，收益大幅回落且回撤仍高；某个 phase 比其他 phase 好很多。把这些作为待解释现象，不保留“phase0 天然更优”结论，也不为恢复原 CAGR 放松正确性。

拆开三种可变性：训练随机性/数据窗口；再训练起点 phase；换仓起点 phase。分别固定其余变量，在相同股票池、成本、日期和真实标签下比较。输出平均、最差阶段、rank/TopK 重叠、组合/单票贡献，不只选择最好曲线。

### 6.2 60/180 天与调仓周期

历史方案包含 60/180 日信号混合；inventory 还提出“180d 候选池、60d timing/rebalance”。把两者做成两个清楚的 Signal/Strategy 配方比较，不把后者当已证明优于前者。

预测 horizon、重训频率、调仓频率、最短持仓和退出规则是独立参数。短 horizon 配短周期、长 horizon 配长周期只是研究假设；不因预测 180 日就写死必须持有 180 日。

先比较：固定混合基线、长周期候选+中期排序、信号保留/换仓滞回。相同 SignalRun 可比较持仓政策；不同 label/model 则生成各自 OOS SignalRun。最终仍以成本后、回撤和恢复体验验收。

### 6.3 LambdaRank / 头部排序

目的：检验优化头部排序能否改善 Top5/候选池，而非只提高总体 IC。以固定回归 baseline 对照。

初版 RankExperimentSpec：同一 session 的截面作为 query group；标签按事前规定的等级映射为非负整数；明确 gain、K、训练/验证 group 和 head focus。LightGBM 的 LambdaRank 接受整数 relevance，并通过 label_gain 定义等级增益；group 长度与数据排序必须匹配官方接口。[E4][E5]

它优化排序目标，不保证 Recall@K、净收益或回撤一定改善。固定 Feature/Dataset/训练预算，比较总体 IC、头部 precision/recall/NDCG、False Positive、跨 phase 稳健性及同一回测。

历史交流曾报告 top-weighted sample weighting 没有形成预期增量；本版不复述未复核的精确数字，也不把它默认 promote。将其作为需关联旧 artifact 的负面结果，只有提出不同假设才重试。

### 6.4 新信息优先，不盲目加重复变换

既有 inventory 已列大量量价、流动性、相对强度、财务/股东和候选 Feature。先核对真实实现、公式和已尝试结果，避免把旧 Feature 改名当新增。

首批候选按证据条件排序：

| 方向 | 要检验什么 | 依赖与归属 |
|---|---|---|
| 量价/相对强度整理 | 完整既有价量集合与有结构组合是否有增量，而非只用少量旧列 | Research Feature；Data 提供行情事实 |
| 三表质量与风险 | accrual/cashflow-profit、应收/存货、短债/现金、资本开支等减少头部误选 | Data 提供 as-of 三表/稳定 TTM；Research 做预测组合 |
| 财报事件 | 公告 surprise/后续漂移是否只在公告后窗口有效 | event age、source-specific PIT；分别评估事件/非事件样本 |
| 股东与资金数据 | 新鲜度、内容变化是否有增量，是否仅来自不可信 vintage | Data 先证明时间/单位/分组；Research 才做衰减/预测分 |
| 入场与持仓管理 | 长期高分标的的过热/失败突破是否减少大回撤 | 不将三个简单 heat 指标等同完整拥挤度；保留否证实验 |

缺 raw/vintage 时停止对应研究，返回 DataRequirements，而不是 Research 自动补拉或绕过 contract。

### 6.5 稳定性、组合与退出

Seed/fold/phase ensemble、多 horizon blend 可作为候选，不默认“集成一定更稳”。它们要证明 head selection、回撤/恢复、成本和单票依赖的改善；权重不能用最终测试期优化。

“错了快撤、对了多拿”拆成保留/替换、trailing、stale、score change 等可解释政策。用保存的 SignalRun 做成对回测，观察 exit 与 replacement 的增量，而不是只看变动后的总 CAGR；已有仓与新开仓都必须有明确政策。

风险门控、行业/个股上限和现金使用通过 Core policy 发布；研究里不另写交易引擎。单票大牛与单阶段贡献、回撤恢复、最差滚动年度必须保留。

### 6.6 DNN/Transformer 与训练稳定性

作为可插拔后续候选保留，不是完成平台或第一版 alpha 的前提。必须证明相对于固定 LightGBM baseline 的 OOS 增量，记录 seed、重训 phase、输入序列长度、算力与推理成本。

Stock-ID embedding、fine-tune、序列状态要处理新上市/未见证券、warm start 来源与隐藏状态重置。不能借模型更复杂跳过 Feature/PIT/Label 合同，也不预设一定超过树模型。

## 7. LLM 财报因子：独立候选通道

继承原专项方向：候选 Top50/Top100 的财报文本，提取经营解释、需求/订单、库存与回款、风险变化、文本与三表一致性；不先全市场每日扫描，也不让 LLM 直接替代 Trade 决策。

```text
Data 保存文档原文/版本与公开证据
→ Research 固定候选名单、文档 refs、提示词/模型/抽取 schema
→ 保存原始响应、字段、引用文本位置与不确定性
→ FeatureRelease/Build 或冻结外部 SignalRun
→ delayed OOS evaluation
→ 同一回测 / 前向 shadow
```

保存 provider/model identifier、prompt/schema/version、参数、generated_at、文档 hash/来源/可见时间、输出内容 digest、候选池版本。外部模型再调用不保证返回同样文本，复验首先依赖已保存输出，不以重新请求等同重放。

历史 LLM 回填还可能受模型已有知识影响；固定历史文档不足以自动证明无未来信息。限制为有出处的字段抽取，不允许无来源自由预测；历史结果标明限制，优先以前向采集、标签成熟后的 delayed evaluation 验证。文档由 Data 管，LLM 预测性结果由 Research 管，不能标成供应商原始事实。

原专项的 API 权限与 ann_date-only 早期设计不是当前 PIT authority；按 Data 的 revision-bound policy 重新验证。没有证据的文本/财务版本不能因是 LLM 输出就绕过。

## 8. 工程性能：复用，而非第二套快速语义

### 8.1 阶段缓存身份

已实现的 ETF 产物按内容绑定数据/查询/配方/实际实现身份，原子发布；已有目录须验证文件与 digest，冲突或损坏保留原件并拒绝。Core 来源证明表按引用共享保存；`feature_frames()` 可展开已保存表，`signal_frame()` 可导出中立 JSON，均不执行 Core。相同输入缓存命中不读取 Data 事实、不改 mtime；搬移及新进程只读已测。证据 JSON 仍有明显体积成本，本轮小样本耗时/bytes 见 [当前交付](../current-delivery.md)，不推断多年规模。

| 阶段 | 最低 cache/build key |
|---|---|
| 基础 Feature | data/view/derived + FeatureRelease + scope/lookback + universe/reference CS + PIT/cutoff + implementation |
| 模型输入 | base/cross-section build + fitted state/model/fold + sample/schema |
| Label | snapshot + LabelSpec + benchmark/calendar/action policy + scope |
| Dataset | Feature/Label builds + sample/filter/split + fit protocol |
| Model | Dataset + training recipe + seed/environment + actual source |
| Prediction/Signal | Model(s) + FeatureBuild + allowed dates + SignalPlan/stage |
| Evaluation | Signal/Label refs + EvalSpec/scope/benchmark |
| Backtest | Signal/Strategy + MarketView + initial state + execution/evaluation + Core/Runtime |

Cache hit 必须校验 manifest/身份与输出支持范围；prefix/superset reuse 需显式裁剪合同，不能只因文件名相同就命中。研究产物被正式引用后不允许被“同 idea 重跑覆盖”；scratch 可清理，但正式 rerun 用新 attempt/run。

### 8.2 运行效率方案

按列/日期读取，复用固定输入与 Feature panel；已使用 Qlib 时复用其 exports；避免每 fold 重建全历史；label/信号落盘一次供多种分析；SignalRun 变换使用向量化/受控查询；优先 profile 实际 CPU/I/O/内存再优化。

并行层级只选择合适的一层：fold、model 或库线程；显式配置总 CPU/内存/并发预算，防止 worker 与 LightGBM 线程叠乘。checkpoint 从已完成窗口继续，不能把不同数据/配置的旧窗口拼起来。

训练可复现不只固定一个 seed；锁定依赖/编译环境并记录 backend。LightGBM 官方说明 deterministic 不意味着不同版本/编译器/系统结果完全相同，验收需声明环境和容差。[E4]

### 8.3 性能验收方法

固定硬件、样本规模、冷/热 cache 和参数，记录每阶段 wall time、peak memory、bytes read、cache hit/miss、训练/推理次数。首轮测量后确定预算，不在本设计凭空承诺分钟数或倍数。

**本轮有界 rolling 性能基线（2026-10-05）。** 固定原 January 的 314 canonical ID 作为
规模样本、原六特征、五实际交易日 label、模型参数与单线程；月度重训，前置三个月训练，
复用已保存 January 基线后尝试 February/March 两折。各日仍按当时历史成员筛选，固定
January union 不代表后两月完整 CSI300，也不用于策略收益结论。先测 1–3、再 10–20 个
日期，累计预算 15 分钟 / 6 GiB RSS / 1 GiB 新产物，超预算停止本私有任务并保存瓶颈证据。
事实读取、Qlib 投影、调整/adapter、Core、label/Dataset、数组组装、fit/infer、校验/序列化
及缓存分别计时；共同日期只构建一次，每折显式绑定裁剪范围、fit 与预测 cutoff，不借
旧 exact-config 缓存冒充跨折复用。每个 session 原 cutoff 的公共查询是批处理参考，不能
用月末事实回填月初；预热保留实际日历与连续 union，label 按实际 f+1/f+5 和可用时间成熟，
normalization 仍为该日可见成员/有效且成熟样本的既定 cs_zscore，无全期间拟合变换。
允许本次运行内复用不可变 Core 文档的固定 identity、Qlib 引用和已完整校验的保存对象，
DataBatch 适配在本次调用读取一次完整 wire，批引用与逻辑 ViewRef 仍绑定该 wire 原值；
batch_field 来源标识仅按完整 field/batch_ref/qualification/basis 键复用，逐键 provenance
仍完整保留，cell 来源模式维持逐键身份。每次调用重新读取、验证，不继承此前信任。
不省略 hash/ref/来源闭包验证，不跨调用持久信任；先核对逐窗口/批处理的 keys、值、null、
时钟、成员、排名边界及缓存隔离，再报告提速。旧产物不覆盖，5–6 年外推单列历史 union
扩张、重训/窗口重复、证据内存与 I/O；单折 fit 或 Feature 线性参考不能称完整 rolling 实测。

最低硬断言：只改 portfolio 时 train/predict 为 0；只看图或评估不触发训练；同 FeatureBuild 可被多实验并发只读；恢复不重复完成 fold；优化前后 keys/NaN/Feature/prediction 及关键排名边界满足声明一致性。

### 8.4 变更影响与重跑边界

<a id="ml-engineering-current-boundary"></a>
**2026-10-05 当前工程边界与有界验收。** 本文规定 owner 与合同；
[ML 工程 Notebook 初稿](../../notebooks/ml_engineering_tutorial.ipynb)沿固定真实短样本解释输入、
准备、成熟、训练、保存 Signal、唯一账户、评估与展示，不另建一份规范正文。固定配置首建/HIT、两周控制试点与同 Signal Top3/Top5 对照已实际通过，
用户功能确认与源码实现、教学运行验收分开登记。后续先审整体设计及小流程；所有未开始的
全年/多年 ML 构建暂停，不能沿此前条件计划先跑。

Data 的 Raw/Canonical/Snapshot 和 Qlib 导出是事实/格式准备；导出不执行预测 Feature。
Research catalog 编译既有 Core FeaturePlan，调用共享执行器；成熟 Label、Dataset、
LightGBM fit/inference、保存预测目前由 Research 编排。通用 Core ModelHandle/SignalPlan/
组合与正式公开 rolling 恢复仍为目标。本轮完整日期跨 fold parent 复用是有界编排证据，
不是通用持久 feature/cache 平台。

当前单折 builder 身份绑定 Research Python、Data Python、Core Python 的整体实现及环境，
非语义代码也可能造成 MISS；旧保存件可读不代表最新 builder 必须 HIT。公开
`build_stock_ml_from_saved_features` 复用固定同 config 的 Feature/raw Label，免 Data/Feature
执行，仍重新处理 label/norm/Dataset/fit/infer；完全相同目标再次调用才是整实验 HIT。
Qlib 和保存件复用仍有完整解析/hash/ref/证明核验成本，不称零 I/O。只换无账户依赖预测
Signal 的组合，应仅执行 Core 组合/Runtime/Evaluation；TopK 合同已由 Docs PR17 审准且 Engine PR8 已合，
不同组合对照绑定已审来源以证明零 Feature/fit/predict，不以改资金替代。

两项目标方向已接受，最小新增合同仍待冻结：一是把过粗失效身份拆到真实语义依赖，完整实现来源继续用于审计；
二是将长历史 Feature/proof 按完整日期截面持久化、逐片校验并释放，冻结多 parent 与原子
checkpoint/resume 边界。两折通过尚未证明长历史常驻内存有界；教程不据此大重构生产代码。

用户新增五年 **weekly retrain** 规模问题：保存日历的 2021-01-01—2025-12-31 有 1,212 个实际 session、256 个有交易日的 ISO 周。
这只证明日历数量，不证明五年股票源/成员覆盖。已测两周保持 **2023-11-01—2024-01-31** 的 65 个训练日期不变，
成熟日期分别为 62/65，预测为 4/5 日；固定规模、已准备 Feature、相同暖源与 proof 体积的条件外推为 65.15–66.87 分钟，
不是五年滑动训练实测或总耗时上界。总计划还须加唯一冷准备、五年账户/评价、导出展示三个未测项；不能给有限总上界。
逐项公式与假设见 [Notebook §12](../../notebooks/ml_engineering_tutorial.html#section-12)，旧 monthly 3–6 小时不适用，全年/五年仍不启动。代码读取实际 catalog 自动成表，不手写
另一份 Feature 事实源；模型无量纲分数、账户状态缓存、来源限制均保持原合同。

<a id="ml-engineering-review-proposals"></a>
### 8.4.1 四项工程边界与状态

缓存 key/有界 loader 的准确新增合同仍是候选，不改变当前 builder 或旧保存件 loader。
Weekly 有界试点与同 Signal Top3/Top5 对照已通过；TopK 合同已审准且 Engine PR8 已合。全年/五年仍暂停。

**A. 失效身份与复用边界。** 建议把阶段 recipe/cache identity 与完整实现审计 receipt 分开，
在新版本命名空间试验，旧保存件和其身份不覆盖。Feature key 绑定实际输入 batch/view refs、
Snapshot/QuerySpec、cutoff/PIT/价格与单位、完整 reference-members 截面、catalog/plan 语义及
实际用到的 Core 算子实现；raw Label 绑定真实日历、f+1/f+5、价格/因子、可用时点与 label
实现；norm/Dataset 再绑定 fit cutoff、成熟/排除键、列序与 transform；Model 绑定 Dataset、
固定参数/seed/训练后端版本及训练实现；Signal 绑定 Model、Feature、预测时钟及推理实现。
完整 repo/source/environment 仍留作审计，不因 UI 排版或未使用模块改动自动重算所有阶段。
不能只比较人工 semantic_version 而忽略实际计算代码；未证明无关的改动保守 MISS。
相同 key 仍逐次读取并核验原内容/来源闭包，不引入跨次持久“信任缓存”。

只改 portfolio 以原 account-independent Signal 为输入，生成新的 Runtime plan/run 与
Evaluation；不重训或改 Signal 身份。只改 label/model 从实际受影响阶段往下失效；改字段、
Snapshot、PIT/cutoff 或 Feature 语义按真实依赖失效。账户、持仓路径、退出/风险策略状态属于
各自账本，不能借“信号缓存”跨账户复用。首轮小例需证明同目标 HIT、实际受影响修改 MISS、
旧 loader 可读，不能先把新候选身份当成现有公共能力。

最小新增 API 候选仅针对 Feature 阶段：
`feature_stage_key(*, input_refs: dict, plan_ref: str, operator_refs: dict) -> str`，生成新
`feature_stage_key_v2` 固定 digest。input_refs 由已验证 Snapshot/query、完整 batch/view、
日历/成员/单位与实际范围证据构造，不接受省略 cutoff/PIT 的人工摘要。
`load_feature_stage(path, *, expected_key: str) -> dict` 只读取/hash/闭包校验并返回原
`stock_feature_build_v1`，不调用 Data/Core；新 manifest 分开保存 stage_key、完整审计来源和
文件引用。首版仅 exact scope，不建设通用依赖服务、多 parent 拼装或自动 superset。
两个函数仍为待冻结候选，当前没有导出；后续增量单独审阅，今晚不建设完整缓存平台。

**B. 长 Feature/proof 切块、落盘与加载。** 首个最小增量的公开入口和恢复合同已固定于
[§4.8.1](#stock-feature-checkpoint)，仍保留原 v1 parent 格式；以下 proof blob、磁盘矩阵等
进一步方案未纳入该增量。建议本次试验按 **2 个完整 feature 日期**一 shard，
这不是全局固定粒度。每日期保留完整固定 union/历史成员截面与 validity；上下文从实际编译
FeaturePlan 的最大 required_history 推导（当前六特征为前 20 个实际 session），不按证券拆碎横截面归一化。shard 保存 keys/schema/值/null/时钟与 immutable parent
选择；root 只保存范围、列序、各 shard digest、实际父依赖图及覆盖证明，不能驻留全部 rows。
重复 source proof 作为 content-addressed blob 独立保存一次，shard 保存原 batch ref 与精确
projection 描述；原 DataBatch digest/逐键来源不能改成一个未经验证的摘要。
公开有界 loader 尚缺，候选必须先定义完整原 proof 的流式 hash/结构/投影核验，再只物化
当前训练窗口需要的片与前置上下文，处理后释放；每次顶层调用重验，同一调用内每个 proof
blob 仅完整核验一次，依赖它的 shard 复用这次验证结果；不能跨调用沿用信任。
proof 解析对象随校验释放，不常驻全部证明。分别测校验阶段 RSS 与 matrix/fit 阶段 RSS，
并记录矩阵字节；落盘本身不证明 loader 流式化或内存有界。
大矩阵采用声明的磁盘数组/按窗口读取，训练内存另计；此处不宣称实际 LGBM out-of-core。
每个已完成 shard/fold 原子发布，checkpoint 仅引用其冻结身份；恢复时验完整 shard/输出
再跳过计算。缺失、损坏或未完成临时件不作 HIT，不覆写旧结果。
先验证 peak RSS、累计新文件、两 shard 交界 keys/NaN/排名、一次中断恢复与零重复 fit；
预算不够先停止，不能把本轮私有多 parent 编排直接晋升为公共平台。

**C. Weekly 真实小例、fit 窗口与预算（已批准）。** OOS 为 **2024-02-05—02-08** 与
**2024-02-19—02-23**；fit 分别为严格前一实际 session **02-02 / 02-08，20:30 +08**。
教学控制使用此前三个完整日历月 **2023-11-01—2024-01-31** 的固定 Feature 日期，各周重新
筛其 fit 时钟已经成熟且有效的 label；这是固定训练日期控制，尚非完整滑动窗口实现。
不能借 04-15 outcome cutoff 进入训练。日历、成员与
cutoff 从同一固定 Snapshot 的公开合同证明；缺覆盖就 BLOCKED，不用工作日推断。
314 原 January IDs/六特征是规模对照，不称两周完整 CSI300；字段由实际 registry 自动拉取
OHLC/amount/factor 及成员/日历证据，原 Feature 复用需完整 parent 校验。每周推理包括严格
前 session anchor；模型不能回填到自身 fit 之前的时钟。OOS outcome 仅用于事后评价，
与训练 cutoff 分开。本次两周事后 outcome 共同固定到 **02-29 20:30 +08**，共享
完整来源读取/归一化，不供任一训练时钟使用。两周是教学/测量样本，不是全年模型或账户收益证据。
批准上限：1 次同配置 saved-Feature 首建 fit/infer + 实际第二次 HIT；两 weekly folds 各
1 次业务 fit/infer，最多 8 次公共 Data label-outcome 查询、供应商 0；不同组合最多 2 次
账户。初次评价停止后，已批准仅补缺少阶段的分进程恢复，累计 3 次评价尝试（含失败）、2 份完整评价；
已完成 Top5 账户不重跑，失败记录保留，额外恢复共用 480 s 时钟。一个重进程，RSS 硬上限 6 GiB、外部 own-PID guard 在 5.5 GiB
停止；每阶段 120 s、总业务 480 s、累计新产物 1 GiB，超限保存证据停止，不自动扩预算。
保存件解析、norm/Dataset、fit/infer、proof/hash、序列化/文件字节分别计时；冷 Data/Qlib
准备先引用既有实测并明确“历史证据”，不冒称本次新冷跑。五年 weekly fold 数从真实日历
枚举，估计按唯一日期冷准备与各实际 weekly 成本分开汇总；旧 monthly 3–6 小时不适用。

**D. Engine TopK 合同已审准，PR8 已合并。** 合同来源为 Docs PR17，准确字段见
[Trade §6.1](04_axiom_trade.md#61-有界股票日线-top5)。已审源码 `f6d93a1` /
merge `ea9d178` 使用统一新配置 v2 + 通用正整数 k；旧 v1 保留原固定 5（包括少于 5
的旧 NO_DECISION 保存件）。K 为 exact int 且 >0，拒绝 bool/float/零/负值，并不得超过冻结
execution_universe；有效候选不足 K 为 NO_DECISION，不缩选、不添加 score 正值门槛。
公开 `axiom_engine.runtime.stock_portfolio_policy(*, top_k, execution_universe)` 返回原请求的
portfolio_policy，替换此字段后沿 `BacktestRequest.from_dict` / `run_backtest` 唯一账户路径。
`plan_stock_portfolio(..., top_k=None)` 省略参数只解释旧 /1；所有显式 k（含 5）使用 /2。
足够有效成员按原 score 降序/security_id 升序取 K，等权预算/K。K 进入决策/意图和 run
身份/trace；原 Signal/market/初始账户/profile、价格/现金/lot/T+1/费用/UNKNOWN/执行池/
周首调仓政策不改。保存 Signal 的 bytes/ref 及旧 run/evaluation 不重写。
对照固定同一 January 输入实际跑 K5/K3，须有不同目标组合并记录 Data/supplier/Feature/
fit/predict=0；仅 Core 组合/Runtime/Evaluation 有调用。改资金、复制 JSON 或只写断言不算通过。
本轮同 Signal Top3/Top5 账户与原 v2 评价均已保存通过：五个 January 调仓日均有不同目标，
Data/supplier/Feature/fit/predict 全为 0，完整输入与评价引用由 owner 回执逐项核对。
初次评价因旧账户/评价与新账户对象生命周期重叠触发 RSS guard（峰值 5.82 GiB），失败现场保留。
已审恢复按独立进程执行 Top5 保存件核验、Top5 评价、Top3 账户、Top3 评价；核验后释放旧报告对象，
只保留当前阶段所需输入，不删 proof、不重跑 Top5。恢复总计 106.65 s、峰值 4.78 GiB，全部子进程退出。
这证明本样本的生命周期峰值处理，不证明通用 streaming/多年 loader 已实现。
本 PR 不编辑 Trade §04，主章继续由 Engine owner 维护。

| 变更 | 最先失效的阶段 | 可复用部分 |
|---|---|---|
| 只改 UI/报告排版 | 展示缓存 | 数据、Feature、模型、信号、账户评估原值 |
| 只改 EvaluationSpec | 对应信号或账户评估 | 已保存 Signal/Label 或 Backtest 事件/净值 |
| 只改 portfolio/exit/risk | Trade 回测决策后半段 | state-independent SignalRun 及上游 |
| 只改 SignalExpression | 组合信号 | 子 SignalRun、保存模型与 Feature |
| 改模型损失/超参/seed | 模型训练 | 相同 Dataset/Feature/Label |
| 改 Feature 公式/fit state | 对应 Feature/model-input 构建 | 不受影响的事实/基础 Feature/Label |
| 改 Data 单域/contract/PIT | 依赖该域的 derived/view 及下游 | 可证明无关的输入对象；不能只凭同名复用 |

依赖判断由 manifest 中的实际读取集合决定。全局 ruleset 增加新检查时可以复用旧产物字节并补验证，但不继承未经检查的可信状态。

## 9. 受控对照、证据与发布

| 比较 | 固定什么 | 回答什么 |
|---|---|---|
| D1/F1 vs D1/F1 | 输入、代码、参数、环境 | 可复验性 |
| D1/F1 vs D1/F2 | 数据/派生、标签/split、训练与执行协议 | Feature 增量 |
| D1/F1 vs D2/F1 | Feature/模型训练协议、派生规则、执行口径 | 数据/PIT 修订影响 |
| 同 SignalRun，policy A vs B | 信号/市场/初始账户/成本 | 换仓/退出/风控增量 |
| 同 features，model A vs B | 样本/标签/OOS/预算/执行 | 模型增量 |

某个比较需要重训时，模型产物不同是预期；另一类“固定保存模型只改输入”只是该模型的输入敏感性，不能混为一谈。

Evidence 绑定主次指标、scope、baseline、数据资格、变体总数、时间 OOS、头部表现、分阶段/行业稳定性、成本/容量、单票/阶段依赖与限制。保留失败与负结果，不只注册赢家。

生命周期建议 `scratch → candidate → accepted-for-shadow → deprecated`。Feature/Model/Strategy artifact 本体不可变，decision append-only；Trade 另做 deployment admission/real approval。状态描述可调整，但研究通过不得直接切真钱指针。

## 10. StrategyRelease 与公共 API

```yaml
strategy_release_id: sr_example
feature_release_ref: fr_example
model_refs_or_schedule_ref: schedule_example
signal_plan_ref: signal_plan_example
portfolio_policy_ref: portfolio_example
rebalance_policy_ref: rebalance_example
risk_policy_ref: risk_example
state_contract_ref: state_example
data_requirements_ref: data_req_example
runtime_package_ref: package_example
compatible_core_api: core_api_v1
research_evidence_refs: [evidence_example]
```

单纯回测组合政策不必新训模型；规则信号不必伪造 ModelRelease。部署账户、实际资金和券商凭证不在策略包里。

```python
build_features(snapshot_ref, feature_release_ref, scope, policy) -> FeatureBuildRef
build_labels(snapshot_ref, label_spec_ref, scope) -> LabelBuildRef
build_dataset(feature_ref, label_ref, sample_split_spec) -> DatasetRef
train(dataset_ref, train_spec) -> ModelReleaseRef
generate_signal(model_or_schedule_ref, feature_refs, signal_spec) -> SignalRunRef
evaluate_signal(signal_ref, label_ref, eval_spec) -> EvaluationRef
backtest(backtest_request) -> BacktestRunRef  # 调 Trade 公共 API
publish_strategy(strategy_spec, evidence_refs) -> StrategyReleaseRef
query_feature_layers(build_or_run_ref, security, interval, stage) -> ResearchChartLayers
```

View/build 不存在时报告明确缺口；不自动触发 Data collect/repair。查询只读，缺历史 Feature 层可提供独立重建任务规格，但用户单击图表不执行。

## 11. 最小实施路径

M1 固定实际可用的 Data、Feature 和五交易日 Label，逐段完成保存模型、原始预测、组合信号、信号评价与 Runtime 账户。交付先从 CaseC 开始：用当前固定 5D/LightGBM 做 3–4 个周度 fold 和 Top5 小窗口，再沿同一实现进行多年正确性与性能验收；随后逐个小例补齐 CaseA 的窄 TrainSpec 和 CaseB 的保存组合与共同评价标签。每段尽早在 [既有 ML 工程 Notebook](../../notebooks/ml_engineering_tutorial.ipynb) 展示输入、结果和缺口。6、158、300 列的 case 均使用同一正式列式与窗口实现；缺少的定义或接口单独列明，不以教学代码另写 join、IC 或账户来补齐。M1 包含这些用例及多年正确性、性能验收，全部完成后才进入 M1.5。

1. **CaseA：同输入比较两个训练配置。** 目的是验证准备复用和模型参数变化的实际成本。当前有固定 LightGBM 后端、保存输入的 fold 及 HIT 小例，参数仍硬绑定；窄范围可配置 TrainSpec 尚缺，Research prepared 矩阵候选也仍在整改。输入为同一 Feature/Target 矩阵、窗口、成熟样本与两个真实 TrainSpec；输出为两份模型和原始 OOS Prediction，以及准备、HIT、fit、predict 的实际次数和分阶段耗时。首建、完全同配置重试、只改 TrainSpec 分别记录；当前仅完成结构准备，待接口后才执行训练对照。

2. **CaseB：保存预测组合后批量评价。** 目的是比较原始预测与固定加权 Signal，并验证更换评价定义只影响评价阶段。当前 SignalEval 已有经审查的 frozen-input 评价路径；通用组合尚缺，矩阵 OOS-only 与共同评价 Label 适配由原 owner 补齐。输入为固定保存预测、显式权重及同一实际可用的五交易日 Label；先冻结评价输入，再经 `evaluate_stock_signal_inputs` 评价，准确公共调用由 SignalEval owner 提供后接入教学。输出为独立组合 Signal、共同样本和自然覆盖、整体及按年 IC/RankIC、分组标签收益与保存评价。60/180 模型和 Y40/Y180 留待实际目标与成熟范围具备后使用。

3. **CaseC：3–4 个周度 fold 与 Top5 账户，优先交付。** 目的是验证连续窗口的正确性、已完成 Research fold 的重用和资源成本。当前已有固定 5D/LightGBM 的两折真实滑窗历史证据，Engine 有界窗口源码已获父任务审查通过；Research 矩阵整改和实际窗口运行仍待完成。输入为同一正式准备矩阵、固定日历和 fold 时钟、已准入预测、市场回放、执行配置及 50 万元初始账户；输出为每折保存模型/预测、唯一 Runtime 的 Top5 订单与 ledger、扣费 NAV 和账户评价，并报告阶段耗时、读写量、峰值 RSS 及 Research fold 重用前后的实际 fit/predict 次数。v7 Runtime 当前不支持任意账户崩溃恢复，本 case 的中断重用范围限于 Research 已完成 fold。

三个 case 当前只交付教学规划；各段接通并在明确预算下实际运行后，再报告完整验收。Data revision 索引、Core 批横截面、Research 矩阵、Runtime 窗口和 SignalEval 均复用既有增量与原 owner，逐段说明已有能力、实测范围和剩余工作。

M1 的用例及多年正确性、性能验收全部完成后才进入 M1.5，将主开发环境从 Mac 迁到 WSL，日期随完成情况确定。M2 研究目标为 CAGR 25%、最大回撤 25%、Sharpe 1–1.2；这些是待检验的策略目标。M3 使用隔离 shadow；平台回测统一以 50 万元起步。M4 全自动交易后置，复杂模型、LLM 与自动研究按具体用例逐项启用。

## 12. 最小验收标准

| ID | 情景 | 必须结果 |
|---|---|---|
| R01 | D1/F1 重建 | keys、schema、Feature、label 一致，保存模型推理在容差内 |
| R02 | 更换 horizon 参数 | 真实标签起止/公式/maturity 随之变，错误 manifest 被拒绝 |
| R03 | label 未成熟、purge 区间重叠 | 不进入模拟训练/验证；保留排除原因 |
| R04 | 把 in-sample prediction 用作 stacking 输入 | preflight 拒绝或标非正式，正式只接 OOS base signals |
| R05 | 同名 Feature 公式或 fit state 改变 | 新身份/cache miss，旧产物仍可读取 |
| R06 | 加入未来事实、shuffle 行列、改 PIT 截面 | 无穿越/错位；违规输入失败而非 silent fill |
| R07 | cached signal 做两次 policy 回测 | train/predict 次数为 0，结果来自同一 Trade 引擎 |
| R08 | ranker group 错误、负/不支持 relevance、K/正例定义缺失 | 训练/评估拒绝；Precision/Recall 含义清晰 |
| R09 | 只一个 phase 极好 | 报全 phase/seed/window 分布与最差值，不只保留赢家 |
| R10 | D/F/model/policy 多因素同时变化 | 报整体升级，不宣称单因素因果 |
| R11 | Feature 无数据/已知单位或 vintage 错误 | 请求 Data 补能力，不能自动补拉或通过 metrics 洗白 |
| R12 | cache hit、断点恢复、并行读取 | 只复用兼容闭包；无跨版本拼接/覆盖；记录实际执行次数 |
| R13 | 保存发布包移走 Research workspace | Trade 可加载并推理，无训练/源码目录依赖 |
| R14 | UI 查看 base/model_input/score | 与选择的 build/model/fold 一致，stage/source 可回查 |
| R15 | LLM 抽取/复验（启用该能力时） | 记录文档/输出/提示词与时点，重放不重新请求，历史限制明确 |
| R16 | 候选研究完成 | 只生成候选/证据，real deployment 未自动改变 |
| R17 | 性能优化或量化/dtype 变化 | 先测值/键/NaN/排名边界，再报告耗时/内存；无偷改语义 |
| R18 | 失败/负面试验 | 可查询、属于 attempt family，并进入证据变体计数 |

收益未达到用户愿望不代表软件合同没完成；软件通过也不证明策略有 alpha。两类结论必须分别交付。

## 13. 资料依据、证据限制与待确认

主要依据：`qsys_signal_centric_research_architecture.md` §2–8、§12；`qsys_feature_signal_mining_inventory.md` 的 Feature 表和“使用口径”；`qsys_pit_financial_llm_factor_plan.md` §6–10；`qsys_roadmap_v0_3_post_stable_framework.md` 的 Research/Candidate/Shadow 路线；本对话关于 phase、收益/回撤、LambdaRank、IC/Recall、标准回测评估和缓存复用的决定。

本版新增明确协议：Feature stage/fit-state 区分、排名指标正例定义、试验与工程性能分离、LLM 历史知识限制、包依赖与缓存闭包。旧文档的 ann_date-only PIT 与固定目录 artifact 命名以 Data/新版本合同为准；inventory 不作为“所有列当前已实现”的证明。

外部接口核对（2026-09-05；并非指定升级依赖版本）：

- [E4] LightGBM Parameters：`https://lightgbm.readthedocs.io/en/stable/Parameters.html`，ranking objective/label_gain 与 deterministic。
- [E5] LightGBM LGBMRanker：`https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRanker.html`，query group、评估与 fit 接口。

仍需专项确认：当前真实可复验 baseline refs、数据/PIT 可用范围、首个标签公式、phase 定义、相关性/正例等级与主指标、冻结 holdout、资源预算、首批 Feature/model 插件。不要凭本设计重新解释旧结果为已验证结论。
