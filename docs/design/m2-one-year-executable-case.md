# M2：一年可执行研究用例与复用边界（候选）

状态：2026-10-11，父任务已亲审93d99ce并批准有界实现；本文按审定意见收紧时钟与接口。绝对截止14:55 UTC。本文补充既有05 Research、04 Engine合同，不建设新的执行框架。Research源码基线730c211，Docs基线4105a97；Engine策略遵循已审45fd4aa5的[策略协议](engine-strategy-protocol-v1.md)。

首轮研究问题是价量趋势/过热输入能否产生可比较的中期排序信号。用已覆盖的2023-01-03至2023-12-29作为一年OOS，保留已有历史CSI300的完整成员截面与退出成员执行并集；首版不是CSI800非金融，也不称A01经营改善205列方案已兑现。成员来源沿固定Snapshot的best_effort_vendor_v1限制，不以当前成员回填历史。训练、特征回看及标签成熟尾部属于preparation，不计作OOS。现金50万元，费用/执行规则沿冻结现有配置。

## 配置与责任

每项使用独立可读JSON/YAML，通过入口配置引用；展开后的配置、来源及实现ref进入各层保存身份。

| 文件 | 显式参数 | owner与保存输出 |
|---|---|---|
| `time.yaml` | OOS区间、冻结交易日历、504个成熟日期、每20交易日重训、每日严格前session的新预测、fit/model/inference时钟、事后评价cutoff | Research编译已有fold-v3；H40时声明543个前置Feature日期，按日历预计其中504个成熟日期。真实Label依赖仍必须严格早于fit；预计数量不能替代实际准入检查。不新增窗口ABI或训练器。 |
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
2. 固定参数完成一年OOS；保存预测、最小信号报告，交同一预测给三策略生成各自账户/报告。Engine工厂优先集成已完成项，未完成例明确登记，不扩大真实运行数量。
3. 从同母矩阵选择一个中期subset，再做最多一个固定模型参数变体；这两项需要相应重训，但不再准备Feature母矩阵。单个重进程顺序运行。2026-10-11 用户允许先缩短时间验证功能；本轮工程case为2023-01-03—2023-02-07共21个交易日、完整569股票和88列，训练为60个名义成熟日、99个名义训练Feature日，H40及原PIT不变；实际成熟仍由Label时钟验证，按20交易日触发两次拟合。一年OOS和504日成熟训练尚未验收。

换Feature定义/时钟、Snapshot或成员输入：相关母件失效；只换入模subset：复用母矩阵，训练/预测重算；换训练Label/参数：仅必要Label与训练/预测重算；只换评价Label/指标：复用预测；只换策略/成本：复用预测，重新运行唯一账户路径。每次保存新身份与路径，不覆盖旧结果。

当前缓存仍以完整plan和scope为定义单元，已有母矩阵的subset投影不代表增量扩展已实现。88列一年扩至100列两年时，按日期及独立特征列只补缺口尚未实现。后续目标为预备历史CSI1800成员并集和选定特征库，读取窗口所需历史后按列/日期依赖补齐；截面rank、标准化、行业中性化须按目标股票池另算并缓存，不能直接跨池复用。Raw修订、公式或参数改变应只失效相关依赖。这是后续缓存设计方向，不属于本轮现场实现。

本轮新增显式`matrix_v3`路径：`build_stock_feature_inputs(...,storage_options={layout:'matrix_v3',...},column_source=<saved source.json>)`，一次准备共享Data列；每个输出日只保留必要的独立复权锚点数组视图，复用同一编译Core图。保存件版本为`stock_feature_inputs_v4`，由现公共loader验证，保留来源证据和真实Core packed结果身份。新输入遵循统一[Core列式合同](core-feature-columns-v1.md)，不会冒称旧FactBatch/FeatureFrame字节身份。首次来源读取/准入、Feature数值计算、保存及后续模型/subset/标签/策略迭代分别计时，必要逐日锚点计算成本明确披露。

先选关键定向检查：未来revision与成员、Label成熟、键/时钟对齐、subset与配置失效、收盘触发次日执行；再做一次小输入正确性/性能检查，最后留时间给真实一年及少量复用。公开Draft PR只含代码、测试与通用配置，私人结果保持本地；不自动merge或接实盘。
