# 21日股票研究功能用例与复用边界

本文补充既有05 Research、04 Engine合同，说明一个可以从配置运行、保存和复用的短样本功能用例。Engine策略遵循[策略协议](engine-strategy-protocol-v1.md)，不建设新的执行框架。

首轮研究问题是价量趋势/过热输入能否产生可比较的中期排序信号。当前用例为2023-01-03至2023-02-07共21个交易日，保留历史CSI300完整成员截面与569只股票的执行并集，使用88列Feature及两个60名义成熟日训练fold。其目的为功能和复用验收，不据此宣称策略有效。成员来源沿固定Snapshot的best_effort_vendor_v1限制，不以当前成员回填历史。训练、特征回看及标签成熟尾部属于preparation，不计作OOS。现金50万元，费用/执行规则沿冻结配置。

## 配置与责任

每项使用独立可读JSON/YAML，通过入口配置引用；展开后的配置、来源及实现ref进入各层保存身份。

| 文件 | 显式参数 | owner与保存输出 |
|---|---|---|
| `time.yaml` | OOS区间、冻结交易日历、60个名义成熟日期、每20交易日重训、每日严格前session的新预测、fit/model/inference时钟、事后评价cutoff | 将此片段填入dataset.periodic_schedule，Research编译已有fold-v3；H40时声明99个名义训练Feature日期。真实Label依赖仍必须严格早于fit；预计数量不能替代实际准入检查。不新增窗口ABI或训练器。 |
| `universe.json` | Snapshot、PIT policy、历史成员池、证券并集、资格/覆盖、Native/Reader来源ref | Data选事实与revision；现公共scope/native合同。首例`csi300`；CSI800/行业过滤作为独立输入变体，未有冻结证据不自动开启。 |
| `features.json` | catalog_ref、有序ID/version、lookback、缺值/归一化、存储与驻留预算 | Research只登记/选配既有Core计划。保存一个不可变母矩阵；Core为唯一Feature数值执行器，Data提供每个输出cutoff的真实选择。 |
| `label.yaml` | H=40、open(f+1)至close(f+40)、共同anchor复权、因子价格比、成熟/缺失政策 | 复用公共Label执行与保存Raw。准确称40日复权开收收益；不擅称现金权益总回报。首例训练沿现支持的截面z-score，评价使用原始复权收益；原始回归作为另一个显式训练变体，不静默替换。 |
| `model.yaml` | 固定LightGBM现支持参数、seed、threads、Feature subset、训练Label与目标变换 | 复用Research已有训练适配及持久模型owner；不新增算法，不早停、不自动搜索。输出saved model和原预测，保留完整输入身份。 |
| `strategy-*.json` | strategy id、parameters、目标仓位上限、检查/触发频率、费用/可交易配置 | Engine纯策略接口产生目标权重/持仓方案，由唯一Runtime账本生成订单/成交/NAV；Research仅传配置和保存预测。策略没有训练或Data调用。 |
| `evaluation.json` | 显式daily/weekly观察频率、固定评价Label、共同mask、rank ties、最小样本、十组/头部10%边界、账户统计口径 | IC/RankIC复用现Core统计；分组数值归Core。账户指标复用保存账本。Research组合保存结果引用，不另建通用统计框架。 |

## 首轮特征集：88列

实际可用环境为Python3.12.12、Qlib0.9.8.dev18、LightGBM4.6.0；固定实际backend版本进入训练身份，不把环境写成依赖建议版本。77列公式及原编号已对照该环境Alpha158定义：9个K线、OPEN0/HIGH0/LOW0，以及ROC/MA/STD/MAX/MIN/RANK/RSV/CNTP/CNTN/CNTD/SUMP/SUMN/SUMD各5/10/20/30/60窗口。另11列为RET120、UP120、SMOOTH120、VOLADJRET120、PRICEPOS252、LOG_AMOUNT、AMOUNT_REL20/60、AMOUNT_Z20、ILLIQ20、AMOUNT_CV20。展开catalog含88列、219个共享节点，ref为`sha256:d45348375b02da2bc05213b7dcd6f634ecd0bd9afc22b860a7cec2ad5cd84c5c`；全部交现Core执行。

完整窗口且缺值传播是本例的显式保守政策，与Qlib早期min_periods=1边界有区别；STD固定ddof=1，CS归一化沿已有完整当日可见成员规则、不补零。OHLC同可见复权anchor，amount为未复权CNY。排除当前缺输入/算子的VWAP、volume、Beta/R2/Residual、quantile、极值位置、corr；量额列不冒充volume。财务、估值和行业PIT未核实列本轮排除。不称完整Alpha158或全部47自定义已迁移。

## 信号、策略与评价input/output

信号输入沿现保存PredictionFrame及来源闭包；每日重新取严格前session Feature并预测，日期/证券键唯一、完整，记录Feature/model可用时钟；模型每20交易日重训。Engine仅每周第一交易日决策，账户逐交易日估值。评价可显式选daily全部观察或weekly实际首交易日对应的预测，不能前向填充成新观察。

Engine策略统一职责为`frozen prediction + as-of account + previous completed observations + strategy config -> target weights/position intent + reason trace`。公共工厂为`stock_strategy_spec(selection='top_k'|'rank_buffer', top_k=5, rank_buffer=None, exit_overlay=None)`，由`stock_portfolio_policy(strategy_spec=..., universe_id='csi300', execution_universe=..., execution_rules=...)`交现Runtime。首例三种：TopK等权；rank-buffer的`keep_rank=10`，卖不出及待到账权益占位、缺候选留现金；TopK加周频收盘检查止盈止损，默认显式阈值0.20/0.10、一次检查冷却期，严格前session完成收盘与fee-inclusive成本触发，次session执行。目标方案不是成交；资金、lot、费用、T+1、权益及未成交理由均由现Engine执行。Research不实现策略数值逻辑。

首版只保存三类评价：①整体/分年IC与RankIC；②十组及头部10%相对有效股票池复权收益；③账户收益、回撤与既有费用/成交指标。信号输入是同日期/证券键的prediction、成熟Raw Label、共同/原生有效mask及scope/时钟证据；输出保存metrics、series、coverage与计算口径。分组并列规则、组数不足、空组/不足样本明确null，不把组收益叫账户收益。账户输入是保存NAV/trades/fees，输出沿现EvaluationReport。评价保存输入引用，一次固定读取后复用，不为每个指标重读训练祖先。

分组入口为`axiom_engine.core.signal_groups.evaluate_signal_groups(input, spec=...)`，input精确复用`signal_statistics_input_v1`的sessions/signal_keys/pairs。首例spec固定group_count=10、minimum_pairs=20、rank_ties=average、group_assignment=average_rank_fraction、time_weighting=equal_valid_sessions、return_semantics=raw_label_return、annualization=none。升序平均rank按`floor((rank-1)/n*10)`入组，并列不按证券ID拆开；第10组为头部组。输出`signal_groups_v1`含input_ref/spec_ref/groups_ref、每日期组count/mean_return、有效池均值及top_group_excess_return、等日期权重summary与覆盖。不足20或constant截面收益为null，空头部组excess为null并保存原因；不生成年化或账户曲线。

## 一个完整case与失效规则

1. 选固定Snapshot/Native、日历及成员，估算内存；一次准备88列母矩阵和训练Label。24GiB机器，目标单进程≤16GiB；约1000×569×88的纯float64值约0.37GiB，实际预算另外包含Core窗口、证据、转换和模型内部内存，不以纯值代替RSS。
2. 固定参数完成21日OOS；保存预测、最小信号报告，交同一预测给三策略生成各自账户/报告。未完成步骤明确登记，不扩大真实运行数量。
3. 从同母矩阵选择一个中期subset，再做最多一个固定模型参数变体；这两项需要相应重训，但不再准备Feature母矩阵。单个重进程顺序运行。H40及原PIT不变，实际成熟仍由Label时钟验证，按20交易日触发两次拟合。

后续扩展示例可把OOS改为2023-01-03—2023-12-29、名义成熟日期改为504；H40对应543个名义前置训练Feature日期。扩展须另冻完整轴、保存身份并实际运行，当前一年OOS和504日成熟训练尚未验收。CSI800非金融及A01经营改善205列也不属于已交付范围。

换Feature定义/时钟、Snapshot或成员输入：相关母件失效；只换入模subset：复用母矩阵，训练/预测重算；换训练Label/参数：仅必要Label与训练/预测重算；只换评价Label/指标：复用预测；只换策略/成本：复用预测，重新运行唯一账户路径。每次保存新身份与路径，不覆盖旧结果。

当前缓存仍以完整plan和scope为定义单元，已有母矩阵的subset投影不代表增量扩展已实现。88列一年扩至100列两年时，按日期及独立特征列只补缺口尚未实现。后续目标为预备历史CSI1800成员并集和选定特征库，读取窗口所需历史后按列/日期依赖补齐；截面rank、标准化、行业中性化须按目标股票池另算并缓存，不能直接跨池复用。Raw修订、公式或参数改变应只失效相关依赖。这是后续缓存设计方向，不属于本轮现场实现。

本轮新增显式`matrix_v3`路径：`build_stock_feature_inputs(...,storage_options={layout:'matrix_v3',...},column_source=<saved source.json>)`，一次准备共享Data列；每个输出日只保留必要的独立复权锚点数组视图，复用同一编译Core图。保存件版本为`stock_feature_inputs_v4`，由现公共loader验证，保留来源证据和真实Core packed结果身份。新输入遵循统一[Core列式合同](core-feature-columns-v1.md)，不会冒称旧FactBatch/FeatureFrame字节身份。首次来源读取/准入、Feature数值计算、保存及后续模型/subset/标签/策略迭代分别计时，必要逐日锚点计算成本明确披露。

## 可运行入口

Research公开入口为`examples/a01_one_year.py`，参数文件由`options.json`引用独立的experiment/dataset/model/label YAML及冻结Feature轴JSON。安装已审定的Research/Core/Data源码后，在Research目录运行：

公开可复制模板位于Research的`examples/a01_short_case/`。`<...>`必须填写为本地路径、实际冻结Data日历/成员/时钟或真实摘要；占位值不构成可运行数据。模板没有私人Snapshot、保存结果ref或用户路径。各文件消费关系如下：

| 编辑入口 | 实际消费位置 |
|---|---|
| time.yaml | 内容复制到dataset.yaml的periodic_schedule；CLI不自动读取time.yaml |
| universe.json、features.json | 两个对象合并为一个完整axes.json；冻结Data选择与完整lookback均不可省略 |
| dataset.yaml | axes_input填该axes.json绝对路径与实际文件摘要；experiment.yaml引用dataset_file |
| label.yaml、model.yaml | experiment.yaml的specification_files；训练目标与Label成熟口径由现owner核实 |
| evaluation.json | 内容复制到options.json的evaluation；evaluate消费该对象 |
| strategies.json | variants各对象作为stock_strategy_spec的参数；由Engine另绑定原执行规则、费用、市场与保存预测，Research CLI不运行账户 |
| options.json | 本地Data/output/config路径，4GiB读取缓存、16GiB工作预算、母矩阵保存路径及显式matrix_v3 |
| subset-dataset/experiment/options | 显式11列subset，feature_result仍指母件，reuse_raw_from_batch指主batch.json |

例如在填好universe/features片段后，按原对象拼合并登记实际文件摘要；这只是配置准备，不是新的执行器：

```python
import json
from pathlib import Path
import yaml
from axiom_research.stock_artifacts import write_json, file_digest

# 在复制、填好占位值的模板目录中运行。
axes = {**json.loads(Path("universe.json").read_text()),
        **json.loads(Path("features.json").read_text())}
write_json("axes.json", axes)
for name in ("dataset.yaml", "subset-dataset.yaml"):
    dataset = yaml.safe_load(Path(name).read_text())
    dataset["axes_input"] = {"path": str(Path("axes.json").resolve()),
                             "file_digest": file_digest("axes.json")}
    dataset["periodic_schedule"] = yaml.safe_load(Path("time.yaml").read_text())
    Path(name).write_text(yaml.safe_dump(dataset, sort_keys=False))
for name in ("options.json", "subset-options.json"):
    options = json.loads(Path(name).read_text())
    options["feature_spec"] = str(Path("axes.json").resolve())
    options["evaluation"] = json.loads(Path("evaluation.json").read_text())
    write_json(name, options)
```

将更新后的dataset/options保存后再validate；相应subset-dataset须登记同一轴摘要和时间对象。不能用工作日猜交易日，不能拿旧范围摘要代替新文件摘要。

```sh
python examples/a01_one_year.py --options /absolute/path/options.json --stage validate
python examples/a01_one_year.py --options /absolute/path/options.json --stage features
python examples/a01_one_year.py --options /absolute/path/options.json --stage train
python examples/a01_one_year.py --options /absolute/path/options.json --stage evaluate
```

首次Feature准备保存`feature-result.json`；后续train从该文件读取同一母矩阵，不重复运行features。train保存`experiment-result.json`、`batch.json`及原始`prediction-bindings.json`，最后一项直接交Engine。evaluate只读保存的配对样本，调用现Core统计及分组入口。subset用另一个dataset YAML显式列出`model_feature_selection`的精确id/semantic_version，options仍引用原`feature_result`，并以`reuse_raw_from_batch`引用原`batch.json`；变更模型参数也保留这些原输入。重型阶段按同一进程窗口顺序执行。私有目录、Data路径和实际保存身份不写入公开范例。

## 增量缓存后续设计边界（未实现）

物理行情输入应按冻结Data选择、revision、价格基准和可用时钟登记，与Feature库选择分开。时间序列列或共享节点按算子版本、公式参数、依赖窗口和独立anchor登记；截面列另绑定当日目标成员、行业输入及rank/标准化政策。历史CSI1800并集可以作为Raw准备范围，但CSI300和其他目标池的截面结果必须各自计算。

88列一年扩到100列两年的验收应证明旧日期/旧列保存摘要不变，只补12列的原区间和全部列的新增日期，以及它们实际需要的暖机依赖。公式/参数变化只失效对应节点及下游；Raw revision变化按实际滚动依赖传播。共同复权anchor仍是价格列的真实依赖，含固定epsilon的公式不能靠假定anchor抵消来复用。成员或行业变更使相关当日截面下游失效，不能只投影另一池的已归一化结果。

未来保存件须保留values、validity、reason、availability和来源闭包；公开owner读取和模型subset投影继续复用这些原值。新增列/日期的缺口、实际Data/Core调用数、原件摘要/mtime不变及目标池区别须用有界扩展用例证明。当前producer仍要求物理源与目标catalog/selection一致，按完整plan/scope缓存；本轮只验收母矩阵、模型subset和Raw复用，不声称上述增量生产已经具备。

先选关键定向检查：未来revision与成员、Label成熟、键/时钟对齐、subset与配置失效、收盘触发次日执行；再做一次小输入正确性/性能检查，最后留时间给真实一年及少量复用。公开Draft PR只含代码、测试与通用配置，私人结果保持本地；不自动merge或接实盘。
