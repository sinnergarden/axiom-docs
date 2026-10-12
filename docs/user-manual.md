# Axiom 使用说明书
本说明书面向研究者和代为执行实验的 agent。先按研究问题选择用法，再修改对应配置。Notebook 提供少量完整演示；这里说明每种任务需要什么、会做什么、得到什么，以及哪些内容可以复用。
## 当前可用范围
本文首次编写于 2026-10-11，当前状态核对至 2026-10-12。增量特征库的已验证范围和测量统一记录在 [versions.json](../versions.json) 的 `incremental_feature_library_candidate` 条目；操作与边界见[增量特征库指导页](design/incremental-feature-library-v1.md)。T01原七年用例（2019-01-02至2025-12-31，历史CSI300的606只证券、88列、LightGBM）已完成359个周fold训练、每日推理、1699日信号评价、原双账户及账户评价，并已正常登记到Research索引，在UI查看。共享输入baseline与SMA120 gate对照已完成两账户、评价及正常Research索引/UI；baseline逐业务行与旧结果一致，本轮未重训。保存输入换策略性能已实测。准备件跨模型复用的小范围验证已通过，PR26长期换模型性能仍未测；M1其他验收项尚未全部完成。
已经保存的五年六特征案例证明了该案例的训练、预测和账户链路。短样本宽特征工程案例使用历史CSI300成员并集中的569只证券、88个价量特征；预测区间为2023-01-03至2023-02-07，共21个交易日，母特征覆盖120个日期，模型进行两次训练。新增的可复用库已准备2016-10-13至2025-12-30共2242日、88列的 raw/base 和原历史CSI300每日截面标准化结果，正式训练投影含606只证券；另32只仅用于暖机历史，不进入训练。上述特征准备证据覆盖准备与读取，训练和账户另按各自保存结果验收。88列是可实现的Alpha158子集加中长期趋势及量额特征；CSI1800全特征库、历史行业及其他缺少字段或算子的特征仍未准备。
## 先准备一份研究计划
一个实验由以下独立配置组成。入口只引用这些配置，避免把几百项参数塞进一个文件。
| 配置 | 研究者决定什么 |
| --- | --- |
| 时间 | 研究区间、训练长度、重训频率、预测频率、评价时间 |
| 股票池 | 历史成员规则、证券范围、资格过滤及数据版本 |
| 特征 | 特征目录版本、入选特征ID、变换和缺失值规则 |
| 标签 | 收益起止时点、期限、价格口径、成熟条件和训练目标变换 |
| 模型 | 算法、参数、随机种子、训练配置 |
| 信号 | 原始预测或组合公式、缩放、共同样本和缺失值处理 |
| 策略 | 信号如何转成持仓，检查频率、权重、退出和重新入场规则 |
| 评价 | 比较的标签、日期和股票范围、指标及分组规则 |
运行前应能回答：研究什么现象，用什么信息预测，怎样交易到这个预测。若只是检查平台能否工作，明确标为工程案例，不用其收益推导策略有效。
## 用法一：首次运行一个研究实验
**输入**：上述配置、已经保存的数据版本、可用的历史成员和交易日历。
先检查全部入选特征所需的字段和算子是否齐全。训练历史必须覆盖特征回看和标签成熟所需日期；只选择一年评价区间，不意味着只需读取一年历史。
平台准备可复用特征矩阵及标签，按训练计划拟合模型，保存预测，计算信号评价，再通过策略生成目标持仓并运行账户。每个阶段保存自己的结果与输入版本。
**输出**：展开后的实验配置、实际样本覆盖、特征和标签引用、模型与预测、信号评价、账户净值和成交，以及各阶段耗时。
**完成判据**：指定范围运行完成，结果可重新打开，缺失与排除原因可见。遇到错误时说明停在哪一步、哪些产物仍有效。禁止把成功的前几周当成全年结果。
## 用法二：从已有特征集挑一个子集
**输入**：已保存的特征母矩阵、需要的有序特征ID、新的实验配置。
例如，已有88列，下一次只用中期趋势和量额列。在新的dataset配置中填写有序的 `model_feature_selection`，options保留原 `feature_result` 或 `feature_library_training_view`，设置新的 `output_root` 和 `prepared_destination`。清除 `prepared_batch`，以 `reuse_raw_from_batch` 指向原完整batch回执，从 `train` 开始。平台复用母矩阵和兼容的Raw输入，为实际入选特征与有效样本重新准备截面资格、标准化和fold控制，再训练和预测。旧normalized cohort不能直接搬到新子集。
特征语义、实际输入revision、每日时钟及参考池相同且已有覆盖时，Feature计算为0；新的样本准备、矩阵投影和训练仍有成本。筛选训练或交易证券使用 `sample_universe`；若同时改变截面标准化使用的参考成员，相关截面结果需要重新计算。
**输出**：子集清单、新模型与预测、与原实验可比的评价，以及实际复用情况。母矩阵中的其他列不被删除。
缺少某一列时，应在运行前指出名称和原因；不能静默补零或更换表达式。
## 用法三：更换模型或模型参数
保持特征、训练标签、fold计划、准备参数和入模特征顺序相同，只改 `model.yaml` 中支持的模型配置，由新的experiment配置引用它。options保留原Feature入口，设置新的 `output_root`，以 `prepared_batch` 指向已保存的COMPLETE batch manifest，清除 `reuse_raw_from_batch`；运行 `validate`、`train`、`evaluate`，跳过 `features`。入口先核对完整输入身份，兼容后复用准备件并重新拟合、保存预测；不兼容时停止该复用路径。
这一路径不重新打开Data准备输入，小范围验证中Data、Raw、Core准备及proof写入均为0；新进程冷加载、准入、矩阵投影、模型训练和预测仍需时间。比较信号时使用同一个评价标签及共同有效样本，同时保留各自覆盖率。
当前已验证的模型后端为LightGBM，可以在支持的配置字段内改变参数。新增算法可通过现有模型扩展接口接入，但仍须实现并验证训练、保存和推理适配；接口可扩展不表示任意算法已经实现。适用版本见 [versions.json](../versions.json)。
## 用法四：更换标签期限或评价目标
训练标签和评价标签分别配置。
- 改训练标签：修改 `label.yaml` 及其experiment引用，保留兼容的Feature入口，使用新的输出和准备目录，清除旧 `prepared_batch`。Label期限或成熟条件变化时，重新准备必要标签、样本资格、标准化及fold控制，再训练和预测；旧Raw是否兼容也须由公共入口核实，不能只改期限就强行复用。
- 只改评价标签：复用保存的预测，用公开 `build_stock_evaluation_label_inputs` 保存新评价Label，再以 `save_stock_signal_evaluation_inputs` 显式绑定原预测owner与共同Label，交 `evaluate_stock_signal_input_analysis` 计算。配置与保存形状见[独立评价Label](design/05_axiom_research.md#stock-evaluation-label-owner)和[多owner评价](design/05_axiom_research.md#stock-multi-owner-signal-evaluation)。A01的 `evaluate` 消费已保存评价输入，单改训练 `label.yaml` 不会替换那份输入里的Label。
例如，60日模型和180日模型都可以对照同一个180日真实收益标签。比较时统一评价日期、成员与有效样本。每个标签只有在其终点及必要数据都已可知后才成熟；训练只能使用拟合当时已经成熟的标签。
收益名称必须说明起止价格和复权口径。因子复权价格收益与另计现金权益的账户收益分开解释。
## 用法五：组合已经保存的信号
**输入**：多个预测结果、共同日期和证券范围、组合公式、缩放及缺失值规则。
例如先在当日截面标准化两个信号，再等权组合。组合产生一个新的信号结果，保留来源引用；基础模型无需重训。组合公式只能使用当时已知的预测和变换参数。
**输出**：组合信号及来源引用。已保存组合信号可自动登记、刷新索引查看，实际评价/账户仍需相应owner完成；评价保存后可查看固定标签下的结果和覆盖变化。不同量纲信号直接相加必须有明确理由；对负数开平方等表达式须有明确数学定义。不要在缺失来源时擅自改权重。
## 用法六：同一个信号尝试不同策略
**输入**：保存的信号、当时账户状态、可见市场参考信息和策略配置。
策略输出目标权重、需要保留的数量、退出要求、下一状态和原因。唯一执行引擎负责整手、费用、可卖数量、成交约束、现金及权益账本。目标持仓与实际成交分别保存。
此前短样本的三个例子已完成相同21个交易日的真实账户运行，保留其原验收范围：
1. TopK等权：按信号排序选K只，各分配1/K预算。K可配置。
2. 排名缓冲：旧持仓仍在前十时保留，空位由高排名候选补足；候选不足留现金。
3. TopK加周频收盘止盈止损：使用上一完整交易日的持仓价格收益触发退出，下一交易日执行；冷却完成后才允许重新入场。
第三种只在配置的周频检查点判断，不能写成每日或盘中止损。收益成本口径包含买入费用及已确认股票权益数量，现金分红不从成本扣除。卖不出的持仓仍占槽位，不能假定已卖出后买入更多证券。
更复杂的策略应实现同一个规划接口，继续交给现有执行引擎。持久运行入口只接纳已经实现并可重建的策略类型；新增类型需要小范围接入，不把任意Python函数塞进保存配置。
换策略时只编辑对应策略配置，复用已保存的 `prediction-bindings.json`、市场输入和初始资金，以独立目录保存新账户及评价。用Engine公共工厂绑定原执行规则，或调用Research公开的 `stock_request_with_saved_predictions`、`run_saved_stock_strategy`、`evaluate_saved_stock_strategy`；这些入口继续消费Engine owner及其准入检查。A01 CLI只有validate/features/train/evaluate四个阶段，账户另由这些公共入口执行。
T01原七年双账户及评价已完成；共享输入baseline与SMA120 gate对照的两账户、评价及正常索引/UI已完成，baseline逐业务行与旧结果一致，本轮未重训。Engine [PR38](https://github.com/sinnergarden/axiom-engine/pull/38)提供跨进程保存与重载。以下调用均来自 `axiom_engine.runtime`，market和inputs须已完成准入，两份destination各用独立目录；保留返回的ArtifactRef回执。new_request由原公开请求入口构造，只改变策略并保持兼容输入：

```python
market_ref = save_stock_market_inputs(market, market_destination, limits=limits)
prediction_ref = save_stock_prediction_inputs(inputs, prediction_destination, limits=limits)
reopened_market = load_stock_market_inputs(market_ref, StockMarketSpec.from_request(new_request), limits=limits, max_market_bytes=max_market_bytes)
reopened_inputs = load_stock_prediction_inputs(reopened_market, prediction_ref, new_request, limits=limits, max_signal_bytes=max_signal_bytes)
```

重载仍核验保存分片、范围和语义；每个新账户继续检查策略与risk绑定，以 `reopened_inputs` 为 `run_stock_backtest` 的source，沿原独立sink和账本执行，完成后依次关闭预测、市场owner。原祖先不会因重载而重新采集或训练，冷加载和新账户仍有成本。Engine main [306b26d](https://github.com/sinnergarden/axiom-engine/commit/306b26d3ec513fa6422b5647ec6fa3e03dfacf1e)的共享及重载market/predictions账户路径当前仅支持CSI300；CSI800/1800不能仅改 `universe_id` 启用，也不属于已完成的通用M1交付。
## 用法七：评价信号和交易结果
评价模块的输入输出保持独立。
| 类别 | 输入 | 输出 |
| --- | --- | --- |
| IC、Rank IC | 按日期与证券对齐的预测、成熟标签、有效样本及范围 | 每日指标、总体和分期汇总、样本数与排除原因 |
| 分组收益 | 相同输入，加分组数和并列处理规则 | 各组收益、头部相对股票池收益、各组覆盖 |
| 账户表现 | 净值、现金、持仓、成交和费用 | 收益、最大回撤、费用、换手及已有风险指标 |
分组收益衡量排序效果，不包含完整账户的执行约束。评价读取保存的必要输入；增加指标不应重新训练，也不应重新读取整棵训练来源文件。以后新增指标沿此模块扩展。
## 用法八：比较实验、排查异常和继续迭代
每次只改变有明确目的的一组配置。先确认范围和样本可比，再看差异。信号改善但账户变差时，检查换手、费用、仓位、持有时间和退出行为。异常收益先检查数据与交易口径，不能直接归因为模型能力。
结果应显示实际完成区间和缺失状态。中断后只复用已经完整保存、可正常读取且输入相符的结果；未完成文件不能作为成功缓存。恢复失败时报告可恢复阶段，不擅自重跑全部准备。
## 用法九：管理实验，并在 UI 打开结果
**当前可用**：普通 A01 训练与评价自动登记，Engine 保存账户可关联到同一结果。已保存组合信号可自动登记、刷新索引查看，实际评价/账户仍需相应owner完成。首次配置研究目录及 Engine 结果目录，之后运行实验或保存组合信号，打开 UI 点击刷新即可查看对应 idea 的结果。
同一 idea 下可以有多个实验版本；每次运行有稳定的结果编号。一个结果可以关联多份预测、信号评价和策略账户。比如同一预测跑 Top5、排名缓冲和退出策略，页面显示三个账户；后来追加年度评价，更新对应账户的评价，不增加一个重复实验。
Research 负责保存结果并自动登记到现有实验索引。登记内容包括配置、运行状态、实际覆盖、产物类型、版本和位置；完整产物保存成功后才发布对应引用。失败或只完成部分阶段时，页面显示已完成内容和未完成原因。
首次运行前在 `result_discovery.required_stages` 声明完成条件；完整账户用例填training、signal_evaluation、accounts、account_evaluation，并在 `result_discovery.strategy_refs` 声明原策略引用。默认只要求training与signal_evaluation，因此索引显示COMPLETE也不代表账户完成；已经冻结的同一次尝试不能中途改完成条件。同一idea的变体沿用 `result_discovery.question` 中的question_id，用 `version` 说明本次配置与明确改动；否则默认问题编号随配置变化。
各目录配置一次后，Research正常登记到result index的实验，在 `--serve-results` 页面点击“刷新保存索引”即可发现；无需逐实验拷贝或静态导出。选择结果默认打开summary摘要，任意fold数量都沿同一读取方式：读取保存的账户评价，校验支持的账户header（元数据），显示登记状态、保存指标及各项可用性。训练、信号评价和账户结果分片明确标为“未展开”，缺件或校验失败各自标注。摘要打开成功只说明这部分读取通过，不代表完整原件验收或M1完成。
需要检查登记的全部原件时，点击“显式验证全部保存原件（可能较慢）”进入该结果的 `/full` 页面；展开摘要卡片不会切换读取模式。CLI在已刷新目录使用 `--open-result <result_id> --detail-mode full`，并提供 `--workspace-config` 与 `--output`。完整读取可能较慢，具体失败仍按保存件标注。刷新及两种查看模式都不触发采集、训练或回测。
**已验证范围**：正式 Research v2 索引中的一个主结果包含两折、两个 Signal 和三个策略账户，页面指标与所属模块保存值一致；读取不执行训练或回测。小型回归覆盖重试保存、发布失败保留旧结果、缺件隔离和账户阻断状态。另一次公开静态双组合只读联验中，两个组合 Signal 均通过公共 loader 验证，19 个原 JSON 未变；临时缺一件时，另一件仍正常。此次组合联验仅覆盖保存件发现与读取，未新增组合数学或真实策略收益验收。
**后续覆盖**：多个 idea、多版本、其他规模和组合仍按实际验证逐项补齐；具体评价及账户的完成状态以所属模块保存值为准。

### 最小操作

首次将根目录配置保存为本地 JSON，例如 `/private/axiom-roots.json`。以下为示例路径，请替换为本机目录；两项都是目录，`research_root` 内须有 `index.json`。私有配置留在本地。

```json
{
  "research_root": "/private/research-results",
  "engine_root": "/private/engine-results"
}
```

启动前使用 [Research PR27](https://github.com/sinnergarden/axiom-research/pull/27)（main合并版本 [699fa6a](https://github.com/sinnergarden/axiom-research/commit/699fa6a706dbce074510d40b22eb48accc9aa4ba)，保留PR24/25/26及原组合信号入口）与 [UI PR15](https://github.com/sinnergarden/axiom-ui/pull/15)（默认 `publish/ui-readonly` 分支合并版本 [c3b2966](https://github.com/sinnergarden/axiom-ui/commit/c3b29666c9286c30c4664b33f2531ad5396b4727)）对应的源码及其兼容依赖。历史版本清单中的条目仅记录各自证据，不能证明本机已安装这个入口。将下面的源码路径替换为本机路径后启动：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/path/axiom-ui/src:/path/axiom-research/src:/path/axiom-engine/src python3 -m axiom_ui --serve-results --workspace-config /private/axiom-roots.json
```

打开命令打印的 `127.0.0.1` 地址，点“刷新保存索引”再选择结果；按 Ctrl-C 停止。

## 实际入口与运行顺序
配置字段和完整用例见[研究用例说明](design/m2-one-year-executable-case.md)；源代码入口为 Research 的 `examples/a01_one_year.py`。`options.json` 的 `experiment_file` 引用本次experiment配置，后者引用独立dataset/model/label文件。填好本地路径和预算后，在已安装对应Data、Engine、Research版本的环境中运行：
```sh
python examples/a01_one_year.py --options /absolute/path/options.json --stage validate
python examples/a01_one_year.py --options /absolute/path/options.json --stage features
python examples/a01_one_year.py --options /absolute/path/options.json --stage train
python examples/a01_one_year.py --options /absolute/path/options.json --stage evaluate
```
首次 `features` 保存母矩阵和 `feature-result.json`。训练前设置 `prepared_destination`，将可复用准备件与本次模型的 `output_root` 分开。训练将 `experiment-result.json`、`batch.json`、`prediction-bindings.json` 保存到新的不可变回执目录，现有实验索引定位当前版本；评价阶段从该索引读取已登记回执。`prediction-bindings.json` 交策略入口，`batch.json` 是后续复用的manifest。具体准备目录位置以owner回执为准，不假定它一定是 `prepared_destination/batch.json`。

在完整模板中编辑以下相关字段；表格只列本次需要改变的项目，其余时间、股票池、Label和预算配置仍保留。`time.yaml` 填入dataset的 `periodic_schedule`，evaluation配置填入options的 `evaluation`；实际文件消费关系见[用例入口](design/m2-one-year-executable-case.md#可运行入口)。

| 场景 | 配置与options | 从哪个阶段开始 |
| --- | --- | --- |
| 首次准备 | 独立experiment/dataset/model/label；`output_root` 为本次模型目录，`prepared_destination` 为准备目录；不设 `prepared_batch` 或 `reuse_raw_from_batch` | validate → features → train → evaluate，账户另执行 |
| 换模型 | 新model及experiment引用、新 `output_root`；原Feature入口和COMPLETE `prepared_batch`，清除 `reuse_raw_from_batch` | validate → train → evaluate |
| 换入模子集 | dataset的 `model_feature_selection`；原Feature入口和 `reuse_raw_from_batch`，新输出及准备目录，清除 `prepared_batch` | validate → train → evaluate |
| 换训练Label | 新Label及experiment引用；保留兼容Feature，新输出及准备目录；清除旧 `prepared_batch`，Raw复用须另核实 | validate → train → evaluate |
| 换策略 | 新策略参数、原保存预测及市场、独立账户输出目录 | Engine公共策略/账户入口，再评价与登记 |

已保存母矩阵使用 `feature_result`；增量库已保存训练视图使用 `feature_library_training_view`。两者选择一个对应原owner的入口。`prepared_batch` 与 `reuse_raw_from_batch` 互斥。公开的 `ExperimentReader(index_path).result(result_id, roots=roots)` 返回登记产物；从 `StockMLBatchManifest` 条目的 `root_id`、`relative_path` 解析准确batch路径，UI产物列表也显示该条目，无需扫描目录猜测。

策略使用Engine的 `stock_strategy_spec` 与 `stock_portfolio_policy`；具体参数见[策略说明](design/engine-strategy-protocol-v1.md)。私有Data路径、市场绑定和实际保存身份留在本地配置中。
新增列或日期使用[增量特征库公开接口](design/incremental-feature-library-v1.md#公开使用接口)：在同一库目录调用 `CatalogFeatureLibrary.ensure`，显式给出登记选列、输出日期和样本证券。它查询覆盖、保留仍有效的旧分区，并只计算缺口；新增特征必须已有定义与算子，来源也须覆盖所需字段、日期及回看历史。上方 A01 脚本说明保留其原母矩阵读取路径，不能仅改旧 `feature-result.json` 就把它转换为增量库。旧 normalized 母矩阵也不能直接充当池无关的 raw/base。

### 完整产物一次登记

A01各阶段会自动发布进度；它们是独立publish调用，每次各自核验保存件。[PR25](https://github.com/sinnergarden/axiom-research/pull/25)只在同一次publish内复用共同读取和验证，跨独立追加仍重新准入。若实验、信号统计与两个账户均已完整保存，可由公开 `publish_stock_result` 在同一次调用登记；该调用读取owner保存件，不训练或运行账户：

```python
from axiom_research import publish_stock_result

publish_stock_result(
    request_path="/private/research-results/model-a/.result-request.json",
    index_path="/private/research-results/index.json",
    roots={"research": "/private/research-results", "engine": "/private/engine-results"},
    experiment_result="/private/research-results/model-a/<owner-receipt>/experiment-result.json",
    signal_evaluation="/private/research-results/model-a/evaluation-result.json",
    engine_handoff="/private/engine-results/two-accounts-handoff.json",
)
```

路径均替换为真实owner回执，沿用首次运行冻结的request。`two-accounts-handoff.json` 的 `accounts` 数组放两个对象，各对象保存下表字段。Publisher逐一检查原身份与状态，再关联到同一实验。T01原双账户及评价已完成正常登记；新对照也已完成正常索引/UI登记，保留原结果。

| 每个账户对象的字段 | 值来自哪里 |
| --- | --- |
| `run_manifest` | Engine保存run的准确路径 |
| `run_ref` | 原 `{run_id, content_digest, committed_sequence}` 三键，不改名或重算 |
| `evaluations` | 以原evaluation_ref为键，每个值为 `{"path": "<saved evaluation path>"}`；报告input_run_ref须匹配上行 |

`signal_evaluation` 指向公开evaluate阶段生成的 `evaluation-result.json`，保留statistics及可选by_year的原路径/引用。发布成功后刷新UI索引；不复制大结果、不新增registry，也不以某个阶段的COMPLETE状态替代整个研究问题的验收。

### 从固定已登记结果追加新策略账户

[Research PR27](https://github.com/sinnergarden/axiom-research/pull/27)入口适用于训练、原预测及信号评价已有正常登记，本次只保存了新策略账户及账户评价的情况。先从同一索引选择所复用结果的 head，并冻结它的四项 basis 身份，再提交 Engine 保存回执的准确路径：

```python
from axiom_research import ExperimentReader, attach_stock_account_from_basis

head = next(h for h in ExperimentReader(index_path).index()["result_heads"]
            if h["result_id"] == result_id)
basis = {k: head[k] for k in ("result_id", "revision", "manifest_ref")}
basis["content_digest"] = head["manifest_ref"]["content_digest"]
attach_stock_account_from_basis(
    basis, index_path=index_path, roots=roots,
    run_path="<Engine saved run path>",
    evaluation_paths=["<Engine saved evaluation path>"],
)
```

成功后刷新 UI 保存索引即可在同一结果中看到新增账户。入口要求 basis 含一份原 prediction-bindings，只追加此前没有的策略与预测组合，至少提供一份匹配新账户的评价；原训练、信号和评价引用保持固定。它继承这些历史产物在此前登记时的验证身份，本次完整核验新账户、评价与小型配置/预测绑定内容，不即时重读全部历史叶子。原件检查仍使用 UI full 页面或原 owner loader。其他发布更新了 head 时，此请求会拒绝；刚完成的完全相同请求可用原 basis 重试，保持索引及不可变修订不变。已实现并通过保存产物新增登记验证，耗时以环境实测为准；无需训练或账户重跑。

### 准备与后续迭代的成本

首次准备包含来源事实及历史准入、缺口特征计算和保存；延长日期或新增列时，仍须支付新增来源和实际缺口的成本。本次全期准备经历中断恢复及性能修复，没有一段可作为连续首次运行总耗时的测量。

训练兼容投影可以从已保存库生成一次，本次全范围投影测得约11分49秒，Feature 计算为0。每个新进程打开保存的训练视图时仍要核验来源与实际 bytes，并逐日核对数值、有效位、时钟、缺失原因和成员；本次公共冷加载测得约20分钟，Feature 计算同样为0。这是上述样本在执行环境中的测量，其他规模或机器须另测。

完成准入后，同一进程的多个fold和窗口共享全期owner，不为每折重复冷加载。换模型可显式复用兼容prepared batch，省去Data/Raw/Core及proof写入；换subset仅复用兼容Raw，实际cohort的标准化与控制重新准备。新的独立进程需重新准入，投影、训练、预测、评价和账户执行仍各有成本。PR26的小范围验证没有给出七年迭代耗时或性能达标结论。精确测量及其范围见 [versions.json](../versions.json)。
## 人和agent共用的操作约定
执行者先读对应版本的能力清单，再展开配置、检查覆盖、估计资源，随后运行。所有命令必须来自经过实际执行的版本说明。上方入口与研究用例说明提供本轮已执行的命令；尚未列出实测命令的用法按设计说明理解。
实验报告至少回答：跑了什么、实际完成多少、结果在哪里、复用了什么、总共花了多久、还有什么限制。缺必要字段、算子或策略类型时明确停止对应步骤，不能偷偷换股票池、特征或价格口径。
## 用说明书验收
- 首次实验能否从配置得到完整结果？
- 更换特征子集，是否复用兼容Feature/Raw并重准备实际cohort，再重训？
- 换模型或训练标签，是否保留无关准备结果？
- 换评价标签或指标，是否复用预测？
- 换策略，是否复用信号并独立生成账户？
- 配置、实际使用范围与报告描述是否一致？
- 普通执行者能否根据准确命令、结果路径和错误说明完成任务？
每项写入真实验证状态和对应版本。尚未实现的能力保留在缺口清单，不能通过改说明书措辞变成已完成。
