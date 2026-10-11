# M2：一年可执行研究用例与复用边界（候选）

状态：2026-10-11，待父任务亲审；审后实现。绝对截止14:55 UTC。本文补充既有05 Research、04 Engine合同，不建设新的执行框架。Research源码基线730c211，Docs基线4105a97；Engine策略准确工厂/API由Engine owner在同一合同下冻结。

首轮研究问题是价量趋势/过热输入能否产生可比较的中期排序信号。用已覆盖的2023-01-03至2023-12-29作为一年OOS，保留已有历史CSI300的完整成员截面与退出成员执行并集；首版不是CSI800非金融，也不称A01经营改善205列方案已兑现。成员来源沿固定Snapshot的best_effort_vendor_v1限制，不以当前成员回填历史。训练、特征回看及标签成熟尾部属于preparation，不计作OOS。现金50万元，费用/执行规则沿冻结现有配置。

## 配置与责任

每项使用独立可读JSON/YAML，通过入口配置引用；展开后的配置、来源及实现ref进入各层保存身份。

| 文件 | 显式参数 | owner与保存输出 |
|---|---|---|
| `time.yaml` | OOS区间、冻结交易日历、504个成熟日期、每20交易日重训、每周第一交易日的严格前session预测、fit/model/inference时钟、事后评价cutoff | Research编译已有fold；输出原fold/model/prediction文件；成熟必须检查真实Label依赖可用时间严格早于fit，不只按日期减40。成熟日期选择扩展现窗口语义，不改变数值训练器。 |
| `universe.json` | Snapshot、PIT policy、历史成员池、证券并集、资格/覆盖、Native/Reader来源ref | Data选事实与revision；现公共scope/native合同。首例`csi300`；CSI800/行业过滤作为独立输入变体，未有冻结证据不自动开启。 |
| `features.json` | catalog_ref、有序ID/version、lookback、缺值/归一化、存储与驻留预算 | Research只登记/选配既有Core计划。保存一个不可变母矩阵；Core为唯一Feature数值执行器，Data提供每个输出cutoff的真实选择。 |
| `label.yaml` | H=40、open(f+1)至close(f+40)、共同anchor复权、因子价格比、成熟/缺失政策 | 复用公共Label执行与保存Raw。准确称40日复权开收收益；不擅称现金权益总回报。首例训练沿现支持的截面z-score，评价使用原始复权收益；原始回归作为另一个显式训练变体，不静默替换。 |
| `model.yaml` | 固定LightGBM现支持参数、seed、threads、Feature subset、训练Label与目标变换 | 复用Research已有训练适配及持久模型owner；不新增算法，不早停、不自动搜索。输出saved model和原预测，保留完整输入身份。 |
| `strategy-*.json` | strategy id、parameters、目标仓位上限、检查/触发频率、费用/可交易配置 | Engine纯策略接口产生目标权重/持仓方案，由唯一Runtime账本生成订单/成交/NAV；Research仅传配置和保存预测。策略没有训练或Data调用。 |
| `evaluation.json` | 固定评价Label、共同mask、rank ties、最小样本、十组/头部10%边界、账户统计口径 | IC/RankIC复用现Core统计；分组收益为Core/Engine轻量输出适配。账户指标复用保存账本。Research组合保存结果引用，不另建通用统计框架。 |

## 首轮特征集：88列

锁定已安装Qlib0.9.7 Alpha158原定义与原编号；其中77列可由现Core表示：9个K线、OPEN0/HIGH0/LOW0，以及ROC/MA/STD/MAX/MIN/RANK/RSV/CNTP/CNTN/CNTD/SUMP/SUMN/SUMD各5/10/20/30/60窗口。另11列为RET120、UP120、SMOOTH120、VOLADJRET120、PRICEPOS252、LOG_AMOUNT、AMOUNT_REL20/60、AMOUNT_Z20、ILLIQ20、AMOUNT_CV20。生成展开清单后固定去重、单位与语义版本；不凑列数。

完整窗口且缺值传播是本例的显式保守政策，与Qlib早期min_periods=1边界有区别；STD固定ddof=1，CS归一化沿已有完整当日可见成员规则、不补零。OHLC同可见复权anchor，amount为未复权CNY。排除当前缺输入/算子的VWAP、volume、Beta/R2/Residual、quantile、极值位置、corr；量额列不冒充volume。财务、估值和行业PIT未核实列本轮排除。不称完整Alpha158或全部47自定义已迁移。

## 信号、策略与评价input/output

信号输入沿现保存PredictionFrame及来源闭包；实际周预测日期/证券必须唯一、完整，记录Feature/model可用时钟。日账户仍逐交易日估值。非换仓日不要求生成新预测，不前向填充成信号评价观察；Engine需明确此周频准入边界。

Engine策略候选统一职责为`frozen prediction + as-of account + current observable market + strategy config -> target weights/position intent + reason trace`。首例三种id：TopK等权、rank-buffer（旧仓rank≤10保留，空位补至最多5，卖不出占位、缺候选留现金）、TopK加收盘止盈止损（只能次session执行，阈值显式）。目标方案不是成交；资金、lot、费用、T+1、可交易与未成交理由均由现Engine执行。准确字段/API待Engine owner冻结；不在Research硬编码这三个策略。

首版只保存三类评价：①整体/分年IC与RankIC；②十组及头部10%相对有效股票池复权收益；③账户收益、回撤与既有费用/成交指标。信号输入是同日期/证券键的prediction、成熟Raw Label、共同/原生有效mask及scope/时钟证据；输出保存metrics、series、coverage与计算口径。分组并列规则、组数不足、空组/不足样本明确null，不把组收益叫账户收益。账户输入是保存NAV/trades/fees，输出沿现EvaluationReport。评价保存输入引用，一次固定读取后复用，不为每个指标重读训练祖先。

## 一个完整case与失效规则

1. 选固定Snapshot/Native、日历及成员，估算内存；一次准备88列母矩阵和训练Label。24GiB机器，目标单进程≤16GiB；约1000×569×88的纯float64值约0.37GiB，实际预算另外包含Core窗口、证据、转换和模型内部内存，不以纯值代替RSS。
2. 固定参数完成一年OOS；保存预测、最小信号报告，交同一预测给三策略生成各自账户/报告。Engine工厂优先集成已完成项，未完成例明确登记，不扩大真实运行数量。
3. 从同母矩阵选择一个中期subset，再做最多一个固定模型参数变体；这两项需要相应重训，但不再准备Feature母矩阵。单个重进程顺序运行。时间不足先减变体和附加评价，不缩证券截面、OOS年份或伪造结果。

换Feature定义/时钟、Snapshot或成员输入：相关母件失效；只换入模subset：复用母矩阵，训练/预测重算；换训练Label/参数：仅必要Label与训练/预测重算；只换评价Label/指标：复用预测；只换策略/成本：复用预测，重新运行唯一账户路径。每次保存新身份与路径，不覆盖旧结果。

先选关键定向检查：未来revision与成员、Label成熟、键/时钟对齐、subset与配置失效、收盘触发次日执行；再做一次小输入正确性/性能检查，最后留时间给真实一年及少量复用。公开Draft PR只含代码、测试与通用配置，私人结果保持本地；不自动merge或接实盘。
