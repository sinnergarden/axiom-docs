# Core 列式 Feature 执行入口

2026-10-11 13:03 UTC 起的紧急设计；父已批准初始固定设计 `592676e00db5e9eaedf373b5ebd94c62f0edb1bc` 后进入实现，本页补全可接入的准确承载。Research 实测单日 569 证券、88 列约 193 秒，数值 rolling/截面统计约 0.13 秒；原逐日 Data adapter 和 FactBatch/Context 大图的生成与 JSON 往返成为一年验证的关键路径。本变更只增加列式承载和准入边界，继续执行已有 FeaturePlan DAG 和原算子数学。

## 接口与责任

公共接口为 `compiled = compile_feature_columns(plan: FeaturePlan)` 和 `result = execute_feature_columns(compiled, *, inputs: dict, output_sessions: list[str], max_working_bytes: int)`。编译调用原 `validate_plan`、依赖闭包和 `required_history`，保存原图、列顺序、参数、单位与语义身份。首版覆盖 Research 88 列实际用到的 sessions 域、element、shift/pct_change、rolling 和 session 截面算子；未覆盖的 event/asof 或其他 profile 显式拒绝，不制造替代公式。冻结输入/schema 和执行 profile 均进入新结果身份。

准入要求 `inputs.sessions` 恰为 `sorted(compiled.reference_members)` 的一个连续切片；不能只以升序和逐日成员存在证明日历完整。若冻结日历为 `[d1,d2,d3]`，输入 `[d1,d3]` 会以 `MISSING_SESSION` 拒绝，避免把 shift1 错当成跨 d2 的位移；`[d2,d3]` 等连续子窗口可正常输入。编译阶段一次冻结日历顺序，执行不重建 FeaturePlan JSON。首版 partial profile 在第一条输入 session 对 `inclusive_current=false` 的 rolling 请求会因空窗口显式拒绝；Research 当前 88 列不依赖该情形。

`inputs` 是完整有序 sessions × security_ids 的 NumPy 列矩阵及轻量元数据。精确字段为 `contract_version, calendar_ref, reference_ref, schema, source_bindings, sessions, security_ids, cutoffs_utc_us, values, validity, reason_codes, reason_dictionary, available_at_utc_us, source_codes, source_sets, reference_member, reference_industry, reference_available_at_utc_us, reference_source_codes, input_refs`。数值列以 schema 名索引，float64 或 bool；每列的 validity、reason、available 和 source code 保持相同二维 shape，日期列等未支持类型先拒绝。reference 各矩阵也是同一网格，cutoff 是 session 向量。source code 指向 source_sets，source_sets 指向 source_bindings 内原 id；input_refs 必须是 Research 实际准备的 Data/View/范围准入产物身份，不能以声明已校验代替真实绑定。

精确输入版本是 `feature_column_input_v1`。`sessions` 为日期升序、`security_ids` 为字符串字典序，两者非空且唯一；输入五个列字典的 key 集合恰等于 schema 列名。values 为 schema 指定的 float64/bool ndarray；validity/reference_member 为 bool；reason_codes/source_codes/reference_source_codes 为 int32；三个 UTC 数组为 int64 微秒。reference_industry 为同 shape 的 object ndarray，cell 只能是非空字符串或 null。reason_dictionary 是 `[null, "原缺值原因", ...]`，唯一且 0 只用于有效 cell；无效 cell 必须给非零原因。输入 source_sets 每项为非空、无重复的原 source id 列表，reference code 必须指向单一 id。首版 profile 最多 64 个原 source binding，内部 uint64 集合联合，不支持的数量显式拒绝。所有 metadata 与输入实际 buffers 摘要共同绑定 input_ref。

Research 负责一次读取、准备同单位列及原始来源范围，保留原 PIT、availability、成员与转换证据，直接交矩阵，不再逐日构造 FactBatch/Context JSON。Core 在该入口一次校验 dtype/shape/有限值/缺值、完整日历、列/schema、成员/industry、source codes 与 refs，以及历史依赖与逐 session cutoff；借用数组须一次捕获为只读自有输入，计算和 bytes digest 使用同一份值，避免别名改变。availability 向上、cutoff 向下投影到原 Core 秒精度，继承 Data adapter 当前规则。Core 不再回溯 Data 原始大图，也不选择修订、复权 anchor 或新成员池。

完整网格不等于可共享历史面板。Research 必须确保每个历史 cell 的数值、原单位和可见时间等于原执行视图；按输出日变化的复权 anchor 或来源选择必须提供独立结构化视图，不能把一个全范围未来视图伪装成所有历史日。入口允许一个网格内多个 output_sessions；独立视图调用仍复用同一 compiled 数学图，不重复 JSON 解析。实际采用共同面板或独立视图由 Research 的原输入证据决定。

## 原内核复用与输出

现有 `_rolling_value`、`_divide`、`_rank`、`_std`、`_quantile`、`_cs_zscore_scale/_cs_zscore_value` 是数值内核，保持原有顺序、math.fsum、statistics、ddof、并列、零分母和 constant 规则。element 数值部分仅从原 `_element` 提取为共享 helper，旧 row 入口也调用同一 helper；列式调度不得另写 NumPy rolling/std 或替代表达式语言。每个节点的可见时间取原依赖 max，来源取原 union，缺值、issue 与 reason 按原 `_merge`/window/CS 政策传播；历史日自身 cutoff 始终有效。跨截面输入包含完整原 reference cohort。

调度采用二维列数组、中间列的最后使用位置释放和受限工作集，内部只做数值与紧凑 mask/time/source code 运算，不生成逐 cell Python provenance 对象或大图 JSON。输出 `feature_column_result_v1` 为输出 sessions × securities × feature 列的只读矩阵：values、validity、reason_codes、availability、source codes 及字典，附原输出 schema、compiled/plan ref、input_refs、输入 buffers digest、source bindings、calendar/reference ref、implementation ref 和 result ref。Research 直接消费矩阵；若需要旧 FeatureFrame，只对必要的小输出视图显式转换。新 packed 结果不冒称原 FactBatch/FeatureFrame 的字节身份。

准确输出数组 key 为 `values, validity, reason_codes, available_at_utc_us, source_codes`，shape 均为 `[len(output_sessions), len(security_ids), len(plan.outputs)]`，feature 顺序沿原 outputs/schema。values 统一 float64；bool schema 由 `bool_values_encoding="0_or_1"` 明示；无效值规范为 0，必须配合 validity 使用。availability 为已投影整秒的 int64 微秒，`null_available_at_utc_us=-9223372036854775808` 表示没有依赖时钟。reason_dictionary 的 0 为 null；未来 issue 使用 `UNAVAILABLE_AT_SESSION_CUTOFF`。输出 source_sets 的 0 恒为空集合，其余按原 id 字典序列出，来源 union 与旧 Frame 一致。result_ref 绑定原 plan_ref、compiled_ref、input_ref、原 input_refs、实际输入/输出 buffers 摘要、schema、日历/成员、源与 implementation。stats 的准入/数值含元数据/输出耗时和 peak_working_bytes 不进入身份；工作集上限覆盖自有数值数组及保守临时数组预留，排除调用方已持有数组、Python 对象与进程 RSS，不声称完整内存测量。

## 正确性、兼容与交付

只做少量小合成对照：同一原 plan 和实际输入，旧 row 与新列式逐 cell 对照数值、validity、reason、来源及 availability；覆盖嵌套 rolling/shift、截面并列与常数、缺值/未来 cell、暖机与不压缩停牌日。加一个 569 证券的小规模源码性能检查，分别报准备、准入、数值和输出成本，不把快微基准冒称一年端到端完成。Research 再做其原单日真实预检，确认关键路径确实被解除后才继续原一年任务，Engine 不另启动账户或训练。

旧入口、算子数学、旧保存 Feature 和账户不改身份。新入口和承载类型显式新增；全局 implementation ref 在最终源码一次冻结，纳入已亲审 PR30 的 signal_groups 模块，Research 统一固定最终 source，必要的 Derived 迁移沿原规则执行。目标父审后 45 分钟交可集成源码；若受原输入独立视图或内核限制无法达到端到端速度，立即交可用的免 JSON 列式入口及实测瓶颈，不继续局部缓存补丁或声称问题已解决。

当前源码候选为 Engine draft PR32；父已亲读入口和共享 element 改动，独立复审指出的缺中间 session 准入缺口已补校验及单个反例。准确固定 source/implementation 由本轮最终交接给 Research，尚待父审批准合并；真实预检和 OOS 功能闭环由 Research 执行，Engine 的合成性能检查不构成真实一年结果。后续夜间增量缓存另行独立推进，不纳入此候选。
