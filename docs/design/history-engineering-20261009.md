# 工程试点历史记录（截至 2026-10-09）

本页保留从设计正文移出的早期试点、预算和暂停决定，供追溯当时的工作范围。文中的“当前”“本轮”“已批准”和“暂停”只适用于其原日期。后续执行以当前任务授权及[交付记录](../current-delivery.md)为准；目标路线见[总纲 §13.1](01_axiom_overview.md#131-实施顺序)。


## Core：2026-09-28 至 2026-10-05 的交付边界

2026-09-28 Data 接口实证：Research 所有的 adapter 已将真实月末 DataBatch/成员结果映射为 FactBatch、ExecutionContext 和 FeaturePlan，并执行 identity/lag/return；这不是全部策略或决策算子的真实验收。
见 [真实 Developer 教程](../../notebooks/developer_tutorial.html#section-9) 与 [设计对照](../design-conformance.md)。正文继续定义目标合同。

2026-10-05 当前边界：共享 FeaturePlan 执行与股票中立预测验证、固定 Top5 决策已有有界实现；
LightGBM fit/inference 仍在 Research。正文中的通用 ModelHandle、SignalPlan/组合参数与正式
rolling 恢复不因固定样本通过而成为已实现 ABI。TopK 合同已由 Docs PR17 审准且 Engine
PR8 已合：显式正整数 top_k 使用 Core /2；省略参数仍解释旧 /1 Top5。准确工厂、版本
与边界见 [Trade §6.1](04_axiom_trade.md#61-有界股票日线-top5)。
不同组合须保存独立账户，不能用改资金代替。
已实现/规划图及教学顺序见 [ML 工程 Notebook 初稿](../../notebooks/ml_engineering_tutorial.ipynb)。


## Research：2026-09-28 的 Data 教程边界

2026-09-28 Data 接口实证：ViewRef 的真实 Query 重放和 Research→Core 薄 adapter 已执行；连续成员、完整 FeatureBuild/模型/OOS/策略回测仍不是本次 Data 教程的验收结论。
见 [真实 Developer 教程](../../notebooks/developer_tutorial.html#section-9) 与 [设计对照](../design-conformance.md)。正文继续定义目标合同。


## Research：2026-10-04 的有界实现

2026-10-04 当前有界实现：Research 0.2.1 保留联合输入、固定 ETF Feature/Signal 与持久复用，增加固定六特征/五 session 归一化 target/单 fold 股票模型及独立保存阶段投影。Engine 已消费冻结 ETF 信号和股票预测生成有界离线账户/评价，Research 只读登记原 owner 结果；UI 保存件工作台与股票消费源码已亲审合并交付，owner QA、root 亲看像素和用户验收另记。固定源码、实际范围与限制见 [当前交付](../current-delivery.md)；正文中的通用模型/OOS/插件平台仍是目标。


## Research §8.3：2026-10-05 rolling 测量方案

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


## Research §8.4：2026-10-05 暂停与历史估计

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


## Research §8.4.1 C：Weekly 试点及运行预算

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
