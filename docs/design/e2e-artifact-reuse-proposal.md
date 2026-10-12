# M1 最短可研究交付：现格式与现 owner 的复用草案

状态：**proposed，尚未实现**（2026-10-12）。本页是 PR76 收窄后的当前路线：先交付下面三项，再验证日常复用。现有 [Research 登记](05_axiom_research.md#experiment-result-discovery)、[训练/PIT 规则](05_axiom_research.md#82-运行效率方案)和 [Engine 输入 owner](04_axiom_trade.md#64-已保存股票输入的一次准入与顺序账户复用)继续有效。当前稳定机制先留在已有 owner；Research 薄边界是长期原则，迁仓不作为本次前置。本 PR 只改设计，不编码、不跑业务。

## 本次结果与成本边界

研究者应能消费同一份已保存 prepared batch，在独立目录换 model，保存后完成轻量登记；同一会话的 market/inputs 供多个策略沿原规则消费。首次准备和改变输入语义仍有真实成本，不能宣称所有配置改动都快。

复盘观测：七年 359 fold 训练约2小时40分钟，统计约81秒；约35MB输出的2MiB默认上限已由 [Research PR24](https://github.com/sinnergarden/axiom-research/pull/24)修为64MiB，但 publish 仍有四轮、部分路径五次 projection/hash，约31.6GB读取，15分钟未完成。这次先消除重复工作，保留现保存格式与轻量列表。

**残余首次成本**仍包括约25分钟 cold load、几十分钟市场 audit/capture；原私有 JSON 载体及其存储开销本次保留。45分钟仅是当前606×88训练含冷加载的待测目标，不是本次承诺，也不覆盖300列、CSI1800或完整账户。

## M1 必交三项

| 工作包与现入口 | 本次修改 | 必须保留的边界 |
|---|---|---|
| A：登记；`result_registration.py` 的 `publish_stock_result`、`stock_result_projection.py`、`result_discovery.py` 的发布校验 | 同次 publish 共享已校验 projection，unique fold 只做一次公共投影/散列；同会话追加统计或账户只验新节点及引用边 | 现 registry、manifest/schema、公共 loader、不可变修订及旧 head 保护不变；不同语义边仍核对，不先造通用 artifact 框架或 manifest v2 |
| B：训练 proof；`stock_training_blocks.py` 的 `training_block_binding`，接回现 `stock_compact_labels`/Feature owner | 每份 Feature proof 首次 `write_part` 后复用原 descriptor；重叠 fold 不再重复调用 `write_part` | 原 `feature_block_ref`、descriptor/file digest 与已有 refs 不变；仅缓存不可变引用，不长期保留全部 proof 解析图 |
| C：正常研究入口；`stock_experiment_entry.py` 的 `build_configured_stock_sequential_experiment` 及 `examples/a01_one_year.py` | prepared 输入位置与 model 输出目录分离；显式消费已保存 batch，接 `load_stock_ml_batch_inputs` → `build_stock_ml_fold_from_saved_inputs(..., batch=...)`；换 model 不再重新准备 Raw/norm/proof | 现 batch/fold/cohort 准入、模型定义与输出身份继续核验；保留首次 preparation 分支、Feature 公共子集读取和已有市场/输入 handle |

A 的共享验证只覆盖本次 publish 及其调用会话。复用项绑定原身份、合同、实际文件 marks 与语义用途，发布前复查变化；不能把不同 scope 或期望引用的检查合并。冷进程首次登记仍执行一次完整去重核验，沿现 loader 的保存输出/引用闭包；磁盘 `verified=true` 或 PASS 不能免验。仅查看列表仍只读索引和 manifest，不打开 payload。

B/C 沿当前训练 owner 保留 Feature 窗口、真实 PIT/anchor、成熟规则与 train-only processor。已保存输入消费成功前先核冻结配置、行列、Label/cohort 与原来源绑定。模型改变产生新的模型/预测与输出目录；不将旧控制件改称新输入。输入选择或 cohort 不同就沿已有准备入口重算相应范围，禁止全历史末期数据 shift 后再 mask 冒充 PIT。配置字段名由编码 owner 核现接口后确定，本草案不发布新函数签名。

## 各种研究操作实际复用什么

| 操作 | 可以复用 | 仍需执行或重算 |
|---|---|---|
| 首次 | 已存在且语义匹配的 Feature/来源覆盖 | 首次准入、实际缺口、Raw Label、归一化、proof、prepared batch，随后训练/预测/评价/账户；分别报告成本 |
| 换 model | 相同 Feature、Label、选列、cohort 与训练计划的已保存 prepared batch；Raw/norm/proof 均不重复准备 | 受支持模型/参数的新拟合、预测及后续评价；新进程仍有冷准入 |
| 换 subset | 已保存 Feature 列，沿公共 `FeatureView.project` 等入口读取；实际版本相同的 Raw Label | 新选列与资格/cohort 核验；cohort 改变时重做受影响日期的 Label 归一化和控制件，再训练；不承诺 norm 恒可复用 |
| 换 label | 不受影响的 Feature 与原始事实；只换评价 Label 时还可直接复用预测 | 训练 Label 改变时按 horizon、实际 PIT/anchor、成熟与 cohort 重算受影响 Label/控制件并训练；评价 Label 改变时只重做相应评价输入/统计 |
| 换 strategy | 同一会话中兼容的已准入 market/inputs 与保存 Signal | 新策略决策、独立账户和账户评价；profile/scope/key 不兼容时按原门禁重新准入或拒绝，冷进程仍需首次 audit/capture |

现 Runtime 的 `admit_stock_market_inputs`、`bind_stock_prediction_inputs`、`run_stock_backtest` 及 `AdmittedStockMarket`/`AdmittedStockInputs` 保持原入口。沿已有 `market_key`、`basis_key`、PID、lease、预算与数学/交易规则复用，不新增同义 handle。源字节、临时存储和进程树 RSS 沿现 limits 分别预检、实测报告；预算不足先停，不按2→4→8盲试，也不把预算字节当RSS保证。

## 并行依赖与小验收

A 与 B 在现模块可并行核量、实现；C 的正常入口消费路径可同时接线，最后接入 B 的 proof descriptor 复用。三项汇入同一批次的小交付；不要求先换格式、迁仓或完成全面 Label 重构。A 先解除重复登记成本，B 减少重叠 fold proof 写入，C 才解除换 model 反复 Raw/norm/proof 的日常成本。编码 owner 尚未核量，撤回工作日初估；父任务按实际修复进展确定时间。

以下为实现后的必要小验证，本 PR 不执行：

| 小验证 | 验收标准 |
|---|---|
| 两重叠 fold 保存/登记 | 各 unique fold 公共 projection/hash 一次；各 unique proof `write_part` 一次，原 refs 保持；追加统计/账户不重验已完成节点 |
| 同 prepared 换 model；另测 subset/label 边界 | 独立 model 输出目录，Raw/norm/proof 新计算或写入为0；prepared/Feature 原 refs、bytes/mtime不变；subset/cohort 或 Label 变化按表重算，不错误套用旧控制件 |
| 同会话两策略/两账户 | 兼容输入不重开源、不重复 audit/capture；各自账本/run 独立，决策、成交、费用、权益和NAV按原规则等价 |
| 冷重开、篡改及恢复 | 冷登记一次完整去重核验；改 proof、descriptor、配置/时钟或发布前 marks 均拒绝；旧 head 可读，半件不发布，恢复不重复已完成计算；列表仍轻量 |

比较沿 Research §8.2.1 既定 exact 项及数值容差；容差内的排名或交易决策翻转仍失败。用两 fold/两账户与上述冷/坏件/恢复对照即可，不七年重跑作单元验收。首次、换 model、换 subset、换 label、换 strategy 分开记录 wall time、读写/散列量、计算次数、RSS与临时存储；只报告实际测过的范围。

## 后置方向与独立正确性问题

全历史 Raw 版本化重构及全面 Label 选择分组、取消 Feature 兼容投影、packed market 载体、通用持久准入、源目录搬迁均为后置方向，不进入本次 M1 前置或关键路径。Qlib 的 [handler 缓存](https://qlib.readthedocs.io/en/latest/reference/api.html#qlib.workflow.task.utils.replace_task_handler_with_cache)和 [RollingGen 分段](https://qlib.readthedocs.io/en/latest/reference/api.html#qlib.workflow.task.gen.RollingGen)可作为后续组织方式的参考；Axiom PIT/anchor/maturity/processor 证据继续保留。

vendor 月度 membership carry 延续到退市后的准入拒绝是独立正确性问题，由独立 Engine 任务及 Data 语义建议处理。本草案不改成员定义或放宽门禁；账户真实对照以该问题解决为前提，A/B 与 prepared 消费的小保存件验证可继续独立推进。
