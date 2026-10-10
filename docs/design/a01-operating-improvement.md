# A01：经营改善的中期选股（讨论稿）

状态：研究方案初稿，未训练、未回测。2026-10-10。

## Proposal

选择经营正在改善、价格开始响应且尚未明显过热的公司，争取信息逐步被市场吸收的后续收益。QSYS 提供特征定义和实现参考；旧非 PIT 结果不作为有效性证据。

研究池暂定历史 CSI800 非金融股票，按当时成员和交易资格选样。预测目标暂定信号日之后第1个交易日开盘至第40个交易日收盘的总回报；信号用于排序。40日是待讨论的主目标，不能因为旧配置用了60日便自动替换。

输入采用 Alpha158 全组，加精选财务、估值、中期走势、流动性和行业特征，计划205列。模型先用 LightGBM；使用504个交易日的成熟训练样本，每20个交易日重训，期间每周用新特征更新预测。模型参数继承值另列，作为起点而非最优值。

账户起始50万元，周频检查，次交易日执行，最多5只等权。首轮候选规则为原持仓保留在前10时继续持有，空位按排名补足；它是待检验的换仓缓冲，不代表已证明经济最优。缺少合格股票时持现金，卖不出的持仓继续计入仓位，不能假定释放了资金。费用和成交规则使用同一份已核成本配置。

每周预测都会把40日判断窗口向前移动，允许持有数周以上。预测期、重训期和检查频率分别配置。最终调仓规则须结合信号持续性和成本确认。评估统一引用[研究评估 SOP](m2-evaluation-sop.md)。

## 特征清单

以下是选型，不代表当前 Axiom 已有对应数据。来源名用于对照 QSYS；修正公式时在 Axiom 登记新语义版本，不能静默沿用旧定义。

### 价量基础：Alpha158（158列）

采用标准 Alpha158：9个K线形态、当日 OPEN/HIGH/LOW/VWAP 相对收盘价4列，以及29类滚动算子在5、10、20、30、60交易日窗口上的145列。使用实际锁定的 Qlib 版本展开为有序列表，数量与表达式须核对。保留短期窗口供模型识别过热或回调，中期窗口描述趋势。

### 财务改善与质量（15列）

- `$roe`
- `roa`
- `$grossprofit_margin`
- `net_margin`
- `$debt_to_assets`
- `$current_ratio`
- `operating_cf_to_profit`
- `ocf_margin`
- `ttm_revenue_yoy`
- `single_q_revenue_yoy`
- `is_profitable_ttm`
- `gross_margin_delta_yoy`
- `profit_yoy`
- `revenue_yoy_accel`
- `profit_yoy_accel`

### 估值与规模（8列）

- `$pe`
- `$pb`
- `ps_ttm`
- `pe_rank_252d`
- `pb_rank_252d`
- `earnings_yield_proxy`
- `log_mktcap`
- `float_mktcap`

### 中期走势（12列）

- `ret_120d`
- `up_day_ratio_120d`
- `trend_smoothness_60d`
- `trend_smoothness_120d`
- `volatility_adjusted_return_120d`
- `rps_20d`
- `rps_60d`
- `rps_120d`
- `rps_20d_minus_rps_60d`
- `price_percentile_252d`
- `distance_to_120d_high`
- `distance_to_250d_high`

### 流动性与热度（7列）

- `amount_log`
- `amount_zscore_20`
- `turnover_rate`
- `turnover_acceleration`
- `illiquidity`
- `amount_ratio_60d`
- `volume_spike_20d`

### 行业背景（5列）

- `rps_industry_60d`
- `rps_industry_120d`
- `stock_minus_industry_ret_60d`
- `industry_breadth_20d`
- `industry_breadth_60d`

## 迁移时必须统一的含义

- 财务单季/TTM、分母和单位一致；同比及加速度按报告期对齐，并取当时可见的修订。QSYS 的252行财务滞后近似不作为严格同比继承。
- `profit_yoy`采用TTM利润同比，去年为亏损或接近零时保留缺失和原因；不把符号颠倒的比率当增长。
- 营收、利润加速度采用相邻报告季度的同比增速差。ROA、利润率和现金流比率采用一致TTM流量；资产类分母采用明确的期初期末平均或期末口径并固定，不能混用。
- 盈利收益率使用同单位TTM利润与当前市值。PE/PB历史位置只使用各历史日当时可见值；亏损PE、非正净资产的PB不作为普通低估值。
- 所有证券按共同市场交易日历对齐，再逐证券计算历史窗口；停牌日保留在时间轴上，缺值规则显式配置，不能删除停牌日来压缩窗口；截面排名使用当日有效研究池。行业排名和宽度需要历史行业身份及有效样本覆盖。
- Alpha158和自定义走势列在展开后检查完全相同公式与别名，去重结果写入配置。205是选型上限，不以凑足列数为目标。

## 暂不进入本轮

- 人工综合打分：上涨候选、估值修复、过热、价值陷阱和多重手工交互；保留底层输入，由模型学习组合。
- 财务绝对金额和口径含混的PEG；规模用明确的市值特征表达。
- 两融、股东和业绩预告：保留候选资格，先确认历史覆盖和实际发布时间。缺乏可信输入时不把它们补零混入首版，也不据旧结果判无效。
- 重复的趋势一致性/上涨日占比和波动调整收益别名；不建设两套同义特征。

## 模型起点

| 参数 | 初值 |
|---|---:|
| objective | regression（原始40日总回报） |
| num_boost_round | 最多300 |
| learning_rate | 0.0421 |
| num_leaves / max_depth | 210 / 8 |
| colsample_bytree | 0.8879 |
| lambda_l1 / lambda_l2 | 205.6999 / 580.9768 |
| seed | 42 |
| early_stopping_rounds | 20 |
| 验证段 | 训练时点以前最后40个成熟样本日期，训练段与之按标签区间隔离 |

这些是QSYS源码中的参考值，尚未作为可执行参数冻结。尤其L1/L2与标签尺度、样本量有关：迁移到原始40日回报前，先用训练/验证样本检查分裂数、预测方差和损失，排除正则过强导致恒定预测；如调整，单列配置及理由。旧源码的subsample=0.8789未显式启用bagging_freq，不能声称行采样已经生效；首版显式关闭行采样。线程数按运行机器配置。标准化只在训练段拟合；以验证段确定轮数后，最终训练可用截至当时的成熟样本重训。

## 开跑前剩余确认

1. 核实入选字段在Axiom的历史覆盖、修订可见时间、复权/分红与标签端点；不把有公式等同于有可信数据。
2. 展开特征列表并记录精确公式版本；财务语义修正须有小样本独立预期检查。
3. 确认40日主目标和周频保留规则，固定日期区间及统一费用配置。它们仍是本稿提案。

## 来源

- [QSYS特征库入口](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/feature/library.py)
- [QSYS全部注册家族](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/feature/registry.py)
- [96项Financial RC配置](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/configs/features/v3a_plus_liquidity_financial_rc.yaml)
- [财务计算实现](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/feature/groups/fundamental_context.py)
- [历史模型默认参数](https://github.com/sinnergarden/SysQ/blob/852bcb73125f8781b7a80618b8188928ef4d38f2/qsys/signal/alpha_v1/training.py)
- [Qlib Alpha158表达式](https://github.com/microsoft/qlib/blob/main/qlib/contrib/data/loader.py)；执行前固定实际依赖版本。

