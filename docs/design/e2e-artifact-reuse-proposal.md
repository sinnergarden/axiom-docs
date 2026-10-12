# 端到端产物复用与有界载体：集中改造草案

状态：**proposed，尚未实现**（2026-10-12）。本页是下一次集中改造的唯一路线草案，交总协调亲审后再固定实现合同。现有 [Research 登记](05_axiom_research.md#experiment-result-discovery)、[训练/PIT 规则](05_axiom_research.md#82-运行效率方案)及 [Engine 输入 owner](04_axiom_trade.md#64-已保存股票输入的一次准入与顺序账户复用)继续有效；本 PR 不编码、不重跑业务，也不改变已验证状态。

## 问题与目标

本次父任务确认的七年 359 fold 训练耗时约 2 小时 40 分钟，信号统计约 81 秒。约 35 MB 的保存输出曾被 2 MiB 默认读取上限拒绝，[Research PR24](https://github.com/sinnergarden/axiom-research/pull/24)已将该上限修为 64 MiB；发布仍会对这些 fold 重复约四轮、部分路径五次投影和散列，累计读取约 31.6 GB，运行 15 分钟仍未完成。这是登记过程的观测，不是训练耗时，也没有完整发布总耗时。

账户已有 `AdmittedStockMarket`、`AdmittedStockInputs` 可供同一 handle 顺序运行两个策略。其主要开销在首次 audit 之后：native 行情、factor、membership 和运行视图再次展开为约 5–6 GiB 私有 JSON。已实现的轻量列表读取和 Feature 内存窗口应继续保留。

目标是让保存后的工作量随实际新增节点、所需块和新增账户增长。**45 分钟仅为当前 606 证券 × 88 列训练、含公共冷加载的待测目标**；尚无达标证据，300 列、CSI1800、首次来源准备、全部账户及全链总耗时各自预算。

## 统一路线与 owner

| 部位 | 保留 | 简化或替换 | owner |
|---|---|---|---|
| 事实与时序 | Snapshot、Query、真实 PIT/anchor、成员与生命周期证据 | 消费所需块及实际依赖；事实定义沿原接口 | Data 提供事实，现有稳定 source owner 准入 |
| 训练与标签 | Feature 窗口、原数学、成熟规则、train-only processor | 共享 proof descriptor；按相同真实选择分组复用 Label 块 | Engine/Core 或已有稳定准备 owner；Research 提供研究配置 |
| 保存与登记 | 唯一 registry、不可变修订、轻量列表、旧 head 保护 | 保存不可变块与收据；调用内共享验证；增量核验新节点和边 | 稳定存储/验证能力归 Engine 或已有 owner；Research 薄编排 |
| 账户输入 | 原 owner、`market_key`、`basis_key`、租约与交易数学 | 将私有展开 JSON 替换为有界 typed/packed 块 | Runtime；复用原 handle，不增同义 handle |
| 结果查看 | 已保存结果公共 loader 与 UI 刷新索引 | 仅读取所选结果需要的块 | 对应结果 owner 和 UI |

Core 继续只承担数学和纯合同校验；文件读取、块保存、资源计费及会话生命周期由 Engine 或已有稳定 owner 实现。Research 只配置和编排这些能力。

生产者先原子保存不可变块，再给出绑定原逻辑身份、schema、范围、物理摘要和依赖引用的保存收据。收据证明发布内容与依赖关系，不是永久准入许可。小 manifest 只组织引用，不复制完整 proof 或逐行图。

同一顶层调用共享验证会话，依附既有 owner 的生命周期。同一 artifact 的实际字节只解析、散列一次；相同合同与选择范围的语义核验也只执行一次。不同用途、选择、schema 或校验版本仍分别核验其语义和引用边，不能仅按路径或值相同合并。会话保存已消费对象的身份和文件 marks，在发布前复查；任何变化都使相关验证失效并阻止发布。marks 只用于调用内变更检查，不能替代新进程的实际字节摘要核验。关闭、PID、borrow 与 exclusive lease 保护沿现有 owner 保留。

生产者保存后，登记、fold projection 和发布检查复用同一会话的验证结果。追加评价或账户只检查新节点、新边以及与既有稳定身份的绑定；发布失败时旧 head 仍可读。新进程先验证小 manifest 和实际要消费的块及其必要依赖。陌生旧保存件首次接入须完整去重验证一次，旧 loader 保留；只有显式 **full audit** 才为来源审计目的遍历完整去重闭包。磁盘上的 `verified=true` 或 PASS 不能让另一个进程跳过所需字节及语义验证。

训练按实际 PIT revision、endpoint、factor、anchor 和 cutoff 选择分组保存 Label 块；只有实际选择、可用性及 cohort 相同才共享其结果。成熟筛选和归一化继续按各 fold 的真实依赖执行。禁止将全历史末期版本 shift 后再 mask 当作历史 PIT。值恰好相同仅可共享物理 buffer，当前来源、时钟、selector 与 lineage 仍分别绑定。

Runtime 首次安全准入仍在账户创建前检查该请求全部必需块，坏后块不能留到成交后才发现；audit 和捕获在同一有界遍历中共享校验值，直接写 typed/packed 块，避免再次展开完整 JSON 图。消费只解码当前块，跨块必要状态与紧凑索引受预算管理。复用兼容性仍由原 market/basis key 和 profile/scope 门禁决定，不兼容配置沿原规则重准入或拒绝。保持原数值类型和精度、金额/数量单位、null/valid/reason、键、行序、时钟与来源引用，不重新舍入。物理分块摘要不替换业务 context、market/basis key 或原输入身份。

Qlib 可借鉴 [handler 缓存](https://qlib.readthedocs.io/en/latest/reference/api.html#qlib.workflow.task.utils.replace_task_handler_with_cache)和 [RollingGen 分段](https://qlib.readthedocs.io/en/latest/reference/api.html#qlib.workflow.task.gen.RollingGen)的组织方式；它承载 Axiom 已选择并准入的窗口。Axiom 继续保存 PIT、anchor、maturity 和 processor fit 证据，Qlib 缓存不成为来源或时间语义的 authority。

## 资源预检与小验收

昂贵准入前分别估计去重源字节、临时存储与进程树 RSS。临时存储包括 capture、未提交块和恢复所需空间；RSS 包括解码、索引、当前窗口、模型及 helper 同时驻留峰值。声明的库存先用于预检，读取时继续计量真实增长。未知展开比先用有界小样本确定预算；不足时在昂贵读取前拒绝并报告缺口，避免按 2→4→8 GiB 盲试。phase 报告同时列 parse/hash/语义核验次数、实际读写字节、wall time、RSS 和临时存储峰值。

以下是实现后的验收标准，本 PR 不执行：

| 小用例 | 必须证明 |
|---|---|
| 两 fold 训练、保存和发布对照 | 原值、键、clock、valid/reason、成熟 cohort 与排名行为一致；同一会话中相同 artifact 的 parse/hash 为一次，语义核验按唯一合同/选择计数；不按发布轮数重读 proof |
| 同一 market/Signal owner 两账户 | 第二账户不重开源、不再 audit/capture；保留各自账本和 run 身份，订单、成交、费用、权益与 NAV 按原精确单位等价；换块大小仍等价 |
| 冷重开及追加评价/账户 | 新进程核验实际所需块；陌生旧件首次完整去重接入；追加只验新节点/边；轻量列表不打开 payload |
| 篡改和恢复 | 改块、descriptor、来源/时钟或发布前 marks 均拒绝受影响路径；预算不足先停；中断不发布半件，旧 head 可读，恢复不重复已完成计算 |

比较沿 Research §8.2.1 的既定 exact 项和数值容差，键、时钟及金额/数量精确比较；即使底层浮点在容差内，排名或交易决策翻转也失败。两 fold/两账户及冷重开、篡改、恢复足以验这一集中改造；七年重跑不作为单元验收。通过后，由总协调决定是否用原固定大范围测量 45 分钟目标，并分别报告冷加载、Label 准备、训练、保存、登记、市场准入和账户成本。新格式或实现版本需要新身份时按原规则生成，旧保存件与 refs 保留；不能用身份变化放过业务差异。

## 交付顺序与独立开放问题

实施量按现有边界拆分如下。天数为初估有效工作日，依据是要贯通的入口和验证范围；假设 Research 与 Runtime 各一位熟悉现实现的 owner、复用已有小 oracle、无需业务语义修复。编码 owner 核过实际模块后再确认排期，不从七年耗时推算开发时间。

| 工作包 | 集中改造量 | 初估 | 解除的日常成本 |
|---|---|---|---|
| A：共同合同与发布会话 | 一个稳定 owner 内的验证会话/收据约定；贯通生产者、公共 projection、发布三个边界及增量节点/边检查 | 1–2天 | 先消除登记的四/五轮重复 parse/hash；不依赖 Label 或市场载体改完 |
| B：训练复用 | proof descriptor 复用与真实 PIT/anchor 选择分组 Label 块两条路径；继续使用现 Feature 窗口和数学 | 2–3天 | 消除逐 fold 重读 proof 与重复准备等价 Label；为45分钟目标提供可测路径 |
| C：账户载体 | 替换一个私有载体及 audit/capture、消费适配；接回现 market/bind/run 三个入口，保持 key/门禁 | 2–3天 | 消除首次准入后的5–6GiB JSON展开；第二账户沿原 handle 复用 |
| D：小对照与交付 | 上表四组小验收、损坏/恢复边界、公共 loader 兼容与使用说明 | 1–2天 | 证明可持续冷重开、追加、恢复，而非仅一次 warm 提速 |

关键路径为 A 的共同合同及会话贯通 → B/C 并行 → D，按上述假设初估4–7个有效工作日；串行实施则约6–10天，等待裁决和资源窗口另计。A 可先独立解除日常登记成本；B/C 共享其合同并在一个集中改造批次交付，阶段验收不另起局部缓存补丁。成员正确性处置独立推进，可阻断 C 的真实账户对照，不能阻断 A/B 的小保存件验证。若 codec、兼容层或安全准入需要更大改动，owner 在编码前调整范围和估算。

Research 不继续另写逐入口验证缓存，Runtime 不增加另一套输入 handle。父审通过前，签名、codec 和保存版本均未冻结，当前代码与已验证合同保持有效。

**成员生命周期是独立正确性开放问题。** 当前账户因 vendor 月度 membership carry 延续到退市后而被准入拒绝。该问题由独立 Engine 任务推进，Data 提供来源语义与修复建议；本提案不裁剪成员、不放宽 gate、不把该拒绝归为性能失败。Data/Engine 明确适用规则后，另行记录受影响输入、旧结果、失效范围和小复验；账户真实运行仍以正确性问题解决为前提。
