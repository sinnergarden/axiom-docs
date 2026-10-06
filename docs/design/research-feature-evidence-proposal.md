# Research Feature 执行证据与共享 coverage：有界候选

状态：**候选，待 dot 冻结；尚未编码或替代主章合同。** 本文用于对齐
[Research §8.2.2](05_axiom_research.md#822-opt-in-调用与保存布局)，不创建竞争主章。
现有 v1 文件、identity、默认 API 和 loader 行为保持；新增字段仅走明确的新
metadata/carrier contract。不得把 descriptor 填进原生 Data context 后继续声称
它具有原 DataBatch/RawLabel digest。

## 1. 已实现范围与实际阻碍

Research PR13 修复基线为 `32bbb478c3568440f5af6c25eeeb2f8d6daa94ff`。
新的隔离 Feature producer 已实现按输出块读取 Qlib native 窗口，不保留全期
values 字典。每个输出 t 仍调用原公共 Data Reader，选择 H(t)@C_X(t)，再按 t
复权、保持完整成员 cohort，调用既有 Core。当前实际 multi-output group 数为
**0**。诊断只比较同块相邻视图，不能据此声称全期 batchable fraction。

小型 MemoryStore / Data exporter / Reader / adjust_prices / 六特征 Core 测试
使用真实公共实现；仅 Qlib activation/read 以读取实际导出 float32 bytes 的
显式替身实现。16 项测试与独立审阅通过；未运行真实 Data、PyQlib runtime、
训练、账户或进程 RSS 验收。

普通数据也存在不能直接并成一个现有 FactBatch 的反例。关闭修订、因子均为 1
后，同键 `A / 2026-02-09` 的两个原输入 close 均为
`11.704999923706055`，但 t=02-11 的 available 为
`2026-02-11T08:15:01Z`，t=02-13 为 `2026-02-13T08:15:01Z`；原 source ID、
view_ref 和成员 reference binding 不同。现有 Core 的一个键只有一组
value / availability / source / reason，不能把两个不同来源时钟压成一个键。
必须 fallback，或由 Core owner 审核第 4 节的最小执行增量。

另一个独立阻碍是 coverage 保存重复：固定 Data Reader e321a665 在每次 Query
context 中 deepcopy 完整 domain coverage；adjust_prices 保留它。当前每个训练
Label chunk 的 RawBuild、raw metadata、normalized metadata 各含一次同 coverage，
evaluation chunk 含两次；Feature proof 与 contents 也重复 source context。
不同 Query/cutoff 导致整个父件 digest 不同，现有整件 CAS 不能消除此重复。

## 2. 同一 publication root 的共享原生内容

以下字段为精确候选，`H(v)` 沿现有 canonical JSON digest：sort_keys、紧凑
separators、ensure_ascii=False、allow_nan=False、UTF-8，无尾 LF。
既有 `Desc(ref_key)={path,file_digest,ref_key}` 保持；path 是实际固定绝对路径，
内容 ref 与文件 bytes ref 分开，拒绝 symlink、越界路径、冲突描述符和缺件。

### 2.1 SharedJson：完整内容，按 bytes 分块保存

`stock_matrix_shared_json_v1` 精确字段：

```text
{contract_version, codec, logical_ref, logical_bytes, chunks, shared_json_ref}
codec = 'canonical_json_utf8_no_lf'
logical_ref = H(原生 JSON 值)
logical_bytes = 原生 canonical UTF-8 总字节数（正 int）
chunks = [{path, file_digest, byte_offset, byte_count}, ...]
shared_json_ref = H(本件仅除自身)
```

logical_bytes、byte_offset、byte_count 必须是 strict int，拒绝 bool；实际 chunk
file size 必须等于 byte_count。chunk 使用同 publication root 内按原 bytes SHA
的 immutable CAS 文件，按顺序连续完整覆盖 `[0,logical_bytes)`，固定每块 1 MiB
且仅末块可短，不重叠、不缺字节、不加 LF。
chunk 边界可在 UTF-8 字符中间，合并流再 UTF-8 decode；不能逐块单独解释 JSON。
逐块校验 file_digest，再校验完整 canonical bytes 的 logical_ref；解码拒绝
duplicate keys / 非有限数，并验证它确实是 canonical bytes。
因此 205 MiB coverage 不需要一个超过既有 64 MiB parent 限额的大 JSON 父文件。
manifest 本身仍受 parent 限额，所有 chunk 与 manifest 都进入 source-record closure。
独立 logical byte 上限候选名为 `maximum_shared_json_bytes`，归属新 codec 的
VerifiedMatrixStore 内部准入配置，首版默认 256 MiB，实际使用
`min(256 MiB,maximum_source_bytes)`。原公共 limits 字典字段不增加，旧文件不受此
新增 codec 限额影响；超过本首版上限须报告，不能编码时自行放宽。该默认值也待
dot冻结，不把205MiB示例当解码内存证明。在读取/解码前核 declared bounds、encoded
backing和 decoded graph 的预算，不能用 parent 限额作为原生总长度限额。

同内容只编码/发布一次，同 admission 中按实际 descriptor 与 logical_ref 共享
一次校验/解码对象；全部已解码共享对象计入 retained budget。无法在预算内
解码时明确拒绝，不能将 encoded bytes 大小当成解码内存保证。原生父 digest
仍需按原 canonical bytes 计算，不能换成 Merkle/hash-of-hashes；可复用已验证
coverage bytes，仍须记录实际喂入原生 parent hash 的字节数。

去重只承诺**同一 publication root**。原 Feature root 与稍后 prepared-view root
不同，不声称跨根全局只存一次；已有不可变文件不移动或改写。

### 2.2 ContextCarrier：保留 absent 与 null

`stock_matrix_context_carrier_v1` 精确字段：

```text
{contract_version, context_without_coverage, coverage_state, coverage,
 native_context_ref, context_carrier_ref}
coverage_state = 'absent' | 'present'
coverage = Desc(shared_json_ref) | null
native_context_ref = H(原生完整 context)
context_carrier_ref = H(本件仅除自身)
```

`context_without_coverage` 精确保留原 context 中除 coverage 的所有字段，包括
query、derivation、limitations、Reader version、数字投影等；不改数组顺序或 null。
absent 时 coverage=null，重建不增加该 key；present 时必须有 SharedJson Desc，
原值为 null 也保存 H(null) 的共享内容。恢复后 native_context_ref 必须相等。
拒绝 context_without_coverage 仍有 coverage key，不通过 overwrite 消除矛盾输入。

### 2.3 SelectedWireCarrier：DataBatch 的原三字段 wire

`stock_matrix_selected_wire_carrier_v1` 精确字段：

```text
{contract_version, records, field_meta, context, native_source_ref,
 selected_wire_carrier_ref}
context = Desc(context_carrier_ref)
native_source_ref = H({records,field_meta,context:恢复的原生 context})
selected_wire_carrier_ref = H(本件仅除自身)
```

records、field_meta 按原顺序与原字段完整保存；不删除 metadata header/by_key。
调整后 DataBatch 与 membership 同样走这个 carrier，native_source_ref 仍是原
实际 Data wire identity，不是 carrier ref。该小窗口 carrier 本身受 parent/budget
限制；不以重复物化全期 records 解决 carrier 问题。

### 2.4 RawLabelCarrier：原 RawBuild identity 不变

`stock_matrix_raw_label_carrier_v1` 精确字段：

```text
{contract_version, native_payload, source_context, native_label_ref,
 raw_label_carrier_ref}
source_context = Desc(context_carrier_ref)
native_payload = 原 RawBuild 仅删除 label_ref 及 source_evidence.context
native_label_ref = 原 RawBuild.label_ref
raw_label_carrier_ref = H(本件仅除自身)
```

恢复 source_evidence.context 后，H(native_payload) 必须等于 native_label_ref；
再添加 label_ref，得到原 RawBuild。原 Raw contract_version、LabelSpec、calendar、
source_ref、records_ref、field_meta_ref、recovery 与逐行叶 refs 不改变。
Raw/normalized metadata 均引用同一个 Raw carrier，重复的 selected wire / context
通过 carrier 复用，不能重塞 inline 大 context。
拒绝 native_payload 残留 label_ref 或 source_evidence.context。

### 2.5 Feature proof 的原生身份与存储身份

`stock_matrix_feature_proof_carrier_v1` 精确字段：

```text
{contract_version, packed_map, native_proof_ref, feature_proof_carrier_ref}
packed_map = 原 source_evidence map，仅将各 query_context 改为 ContextCarrier Desc
native_proof_ref = H(恢复各原生 query_context 后的原 source_evidence map)
feature_proof_carrier_ref = H(本件仅除自身)
```

packed_map 的存储身份不能代替原 selected_versions_ref 或原 proof digest。
必须分别核 carrier ref 与 native_proof_ref，并沿恢复后的原 Query/context 核
source ID、batch_ref、view_ref。source_evidence 字段引用本 carrier Desc，不能
把 carrierized map 的 SharedJson.logical_ref 叫原 native map identity。

### 2.6 最小 loader 分派与 OOS 小型可达证据

旧 inline metadata 与原 Raw descriptor 路径保留。新增 carrier 只按上述精确
contract_version/descriptor ref_key 分派，不能依靠“看起来像 dict”隐式升级。
新 Label metadata 用明确 `stock_matrix_label_metadata_v2`；逻辑字段沿现 v1，
raw_build 改为 Desc(raw_label_carrier_ref)，contents 中原 native ref 指向相应
carrier descriptor。Feature source_evidence 沿 §2.5 proof carrier，不改变原生
source ID 的计算输入。

Reader 校验顺序为 physical chunks/manifest → carrier refs → 恢复的 native context
→ native selected wire → 原 Raw label_ref → 原叶证据/Query/clock/cohort/selector。
现有 `_outcome_query`、Raw maturity、eligibility、normalized Core closure 复用原
语义，只在进入它们之前解析已验 carrier。完整 proof 在当前片 admission 后释放。
不能沿旧 _RawAdmission / evaluation 的 deepcopy 路径把恢复的完整 coverage
复制到每份 Raw 摘要或 OOS lease。

因此原 native-inline OOS provenance 合同保持，另明确分派
`stock_matrix_raw_provenance_v2`，精确字段如下：

```text
{contract_version, native_contract_version, raw_build, label_spec, calendar_ref,
 source_ref, source_evidence, label_ref}
raw_build = Desc(raw_label_carrier_ref)
native_contract_version = 原 RawBuild.contract_version
source_evidence = {context:Desc(context_carrier_ref),records_ref,field_meta_ref,recovery}
label_ref/source_ref = 原 native refs，不是 carrier refs
```

新的 provenance 只保留上述小型可达证据。OOS 的 raw_provenance 和
fold_binding.training_raw_provenance 按 contract_version 明确分派，SignalEval owner
须同步冻结/适配，不在原 stock_label_build_v1 summary 里静默替换 context。
必要的 query/derivation 字段从已验 ContextCarrier.context_without_coverage 读取；
原完整 context/selected/Raw hashes 在 admission 时核验，之后依保存绑定与当前
fingerprints 复用，不为每次 OOS 恢复完整 coverage。source_record_indices 必须包含
当前 fold 所有递归可达 carrier/chunks，不能只把 children 放进总 source 表。
在一次 admission 建立路径绑定，不每次 OOS 重走全图。

共享 decoded/canonical backing 必须从 store roots 可达并计入32b retained预算；
临时proof clear不误删后续消费者真实借用的 backing，lease不暴露可变native图。
不能容纳时明确拒绝，不能仅凭 encoded 205MiB 宣称默认512MiB admission可行。
若本轮尚未冻结/适配新 OOS provenance，则 large coverage 的驻留复用仍是阻断，
不能称 carrier 单独已解决全部解码/驻留重复。

这解决 Research 重复 JSON 保存/解码；**不消除 Data Reader 内部每次 deepcopy**，
也不自动证明 5.5 GiB RSS 达标。若 Data 原生 Query 峰值仍超预算，另报实际证据，
由 Data owner 决定必要的窄增量；本合同不新增 Data API 或裁剪 coverage。

## 3. 真正 shared-panel Core 执行的证据桥

首个候选仅支持既有 `execute_feature_plan` 一次调用的 `shared_panel_v1`。
不能把生产 daily calls 包装成一个组，也不能借原 per-day Frame identity。
以下 `NativeDoc={artifact:Desc(shared_json_ref),native_ref}` 中 native_ref 必须等于
SharedJson.logical_ref，即原 Core Document.identity。

`stock_feature_execution_v1` 精确字段：

```text
{contract_version, mode, definition_ref, catalog_ref, selection,
 ordered_features, output_sessions, universe, plan, facts, context, frame,
 outputs, implementation_ref, execution_ref}
mode = 'shared_panel_v1' | 'daily_v1'
plan/facts/context/frame = NativeDoc（真正执行的四件）
outputs = [{session, selection, frame_row_indices}, ...]
selection = Desc(feature_output_selection_ref)
execution_ref = H(本件仅除自身)
```

daily_v1 是一次原每日执行的真实 receipt；shared_panel_v1 必须至少两个输出日，
恰好一个实际 Core 调用。输出日严格有序，universe 为完整冻结证券列表。
frame_row_indices 是实际 Frame.rows 的非负整数索引，逐组并集完整等于实际
Frame 输出键，不重复、不缺键；不能只选有效成员子集。

`stock_feature_output_selection_v1` 精确字段：

```text
{contract_version, session, history_sessions, cutoffs, adjustment_anchor,
 qlib_view_ref, query_refs, adjusted_input, membership, source_evidence,
 selection_plan, selection_facts, selection_context,
 group_fact_row_indices, group_reference_row_indices,
 feature_output_selection_ref}
adjusted_input/membership = Desc(selected_wire_carrier_ref)
source_evidence = Desc(feature_proof_carrier_ref)（§2.5显式存储/native双身份）
selection_plan/selection_facts/selection_context = NativeDoc
feature_output_selection_ref = H(本件仅除自身)
```

selection 三件是原 Data 选择适配后的**输入**，shared-panel 模式不声称它们已
单独执行或存在旧 Frame。每 t 的 H(t)、C_X(t)、anchor=t、完整 cohort、原生
query/selected wire/source refs 保持。group 两种 row indices 按实际 Fact.rows /
Context.reference 的键映射；逐 cell 的 values、null、availability、reasons、sources
与原 selection 完全相等。不能只比较数值或使用最晚视图替代早期 selection。
映射索引是 strict int，拒bool，范围合法。映射是 total bijection：selection 每行
有且只有一个 group 索引，完整行/键与逐cell binding相等，同 t 不重复，
可跨 t 共享同一行。group sessions 必须是各原 H(t) 的完整日历 union，保留全部
交易 session；共同 compiled semantic recipe/DAG 必须相同。首版 events 必须为空，
不通过本候选新增事件映射。
若各H的union不是冻结calendar中[min,max]的连续切片，则fallback，不能只对
union排序后冒充完整group calendar。
group Plan除来源/日历/reference绑定外的语义字段、节点与outputs必须与所有
selection Plan完全相同，不只比较recipe_ref。
group cutoff(s) 取覆盖该 s 的原 selection_context.cutoffs[s] 的最小值，每个
output cutoff 必须等于它原 selection_context.cutoffs[t]；原 Query cutoff 与
矩阵 knowledge_cutoff 仍保留 native C_X(t)，Core秒级时钟沿已有 cutoff向下取秒、
availability向上取秒的 adapter口径绑定，不能改舍入或要求微秒字面相等。
原输入三件保存为有界 immutable children；增加的审计 bytes 必须真实记账，
不能声称不同原生 input graph 已因数值相同全部去重。

新 `stock_matrix_feature_metadata_v2` 的精确字段为现 metadata v1 删除
`input_evidence,original_feature_ref,contents` 后，增加
`output_evidence,executions,feature_slice_ref`；其他字段/顺序语义保持。
output_evidence 为逐日 `{session,selection:Desc(feature_output_selection_ref),
execution:Desc(execution_ref)}`，executions 是本块去重的实际 execution Descs。
每个矩阵 row.source_refs 必须为 `[实际 frame.native_ref,实际 plan.native_ref]`。

feature_slice_ref 使用新逻辑 `stock_feature_execution_slice_v1`：
`{contract_version,catalog_ref,selection,ordered_features,qlib_view,
output_evidence,rows,feature_ref}`，feature_ref=H(仅除自身)。全块与每一天分别
按相同公式形成 ref；metadata 的 row_references 仍保存逐日 feature_ref 与原
qlib_view_ref。不得称它等于旧每日 stock_feature_build_v1 identity。
feature_slice_ref 精确等于重建 slice.feature_ref；row_references[d] 仅使用 [d]
的 output_evidence 和该日 universe 全行生成。
index 仍为 opt-in stock_feature_inputs_v2，新源码进入已有 implementation_ref；
旧 definition 与 index 文件不补写。后续 compact Feature projection 使用本分支
已验的逻辑 slice/原 rows，新身份贯穿 Dataset/预测，不复用旧父件 ref。

最小 validator 增量：

1. `_validate_feature_matrix_block` 按 metadata v1/v2 精确分派。v1 原逻辑不改；
   v2 校验上述实际执行/逐日 selection 闭包及新 slice refs。
2. `_validate_feature_block` 中原 H(t)/cutoff/anchor/query/source-ID/member 检查
   提取为输入 selection 校验并复用；不能把包含多日的 group plan.sources 塞入
   原 per-day proof，放松旧 Query.sessions==H(t) 的规则。
3. 新分支只读解析实际 Plan/Fact/Context/Frame JSON；核 Frame.plan_identity /
   fact_identity / context_identity 与实际 children 相等，并核 calendar_ref /
   reference_ref / recipe_ref / schema / source_bindings。Frame.rows[i].cutoff 等于已验
   selection_context.cutoffs[t]；daily模式实际输入三件等于唯一selection三件。
   Fact的schema/sources/calendar、Context的完整history/output/reference grid
   与实际Plan闭包一致。receipt definition_ref/implementation_ref/catalog/selection/
   ordered_features/universe绑定保存的definition，不要求当前实现；executions
   精确等于output_evidence去重的消费集合。
   member 从原 Context.reference 核验（Frame没有member字段），逐键匹配输出 value/
   validity/reason/availability/member 和冻结 row.source_refs。不导入 Data/Core
   或重算 Feature。Core 数学正确性由同输入小 golden 对照验收。
4. FeatureMatrixInputs admission/source_selection 与 compact projection 按上述
   新 metadata 分派，保存原可达 children 并沿32b的 hash/fingerprint/retained
   budget/lease规则去重与释放。不绕过完整 scope 或 SourceSelection。

## 4. 普通 anchor 冲突的最小 Core 候选，未批准实施

上述 shared-panel 条件在正常 daily anchor 下仍可能全部 fallback。已固定的
反例无需真实 Data 或大任务重跑；它说明现有一个 FactBatch 无法表示该组，
不说明 Research 应放宽 source/clock 校验。

建议 Core owner 审核一个有界、同 compiled recipe 的
`[(FeaturePlan,FactBatch,ExecutionContext), ...]` 执行入口，每个原窗口返回其
**真实 FeatureFrame**，保留原输入 identity、来源、时钟、掩码与完整 cohort。
Core 内部只共算已证明数值依赖相等的 DAG 单元，同时逐窗口构造原有 provenance；
等价依赖包括可见性后的null/valid mask、完整cohort及顺序，不能只比较scalar值。
修订、anchor 数值或 cohort 差异使用原执行规则。禁止 Research 另写 Feature 数学。
这不是通用 multiview PIT/provider，也不是把 N 次 execute_feature_plan loop
包装成一调用就算批执行。函数名、版本及可核实际复用计数须由 Core owner 冻结。
该入口若被批准，另冻结 execution receipt 模式；本节不擅自增加模式或解锁源码。

## 5. 下一轮有界验收

先使用相邻输出日、相同值但来源时钟不同、真实 revision/null/restore、anchor
因子差异、membership变更和跨块边界小 fixtures。记录全输出计划的 group 数、
group size、实际 Core 调用/数值单元复用、fallback原因与耗时；兼容 panel 黄金
对照须 value/null/reason/availability/member 精确相同，新 Frame identity 如实保存。
正常所有输出 fallback 时明确报告比例0，不只报 classifier局部计数。

coverage carrier 验收包括 absent/null/dict、两个不同Query共享同 coverage、
raw+normalized+evaluation+Feature引用、chunk缺失/篡改/次序/边界、native digest
恢复、旧inline读取、源bytes不变、超预算拒绝与GC/close租约归还。
记录 coverage逻辑字节/唯一物理字节/原生父hash实际输入字节、metadata物理字节、
encode/hash/decode次数、admitted retained bytes与duplication ratio。

真实 Data/长训练/账户及RSS仍须 dot 明确批准窗口后执行；当前小型源码验证
不能替代该验收，也不因 Engine 窗口已空闲自动启动。
