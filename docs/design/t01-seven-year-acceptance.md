# T01 七年 M1 通用使用验收计划

T01 用一个固定研究例子检查 M1 是否足够通用。验收范围为 2019-01-02 至 2025-12-31，使用历史 CSI300 当时成员、固定 88 个已有价量特征和一份 LightGBM 配置。执行者通过现有配置和公开入口准备输入、训练、评价、生成两份账户并在 UI 打开结果。发现一般实验也会遇到的能力缺口时，由对应平台 owner 修复；不为 T01 另写训练流程、数据通道或临时账户执行器。

当前状态是分离配置、正式 Data scope 和一次全期保存来源准备完成。Feature、模型、信号评价、两账户和 UI 验收尚未完成。[Research Draft PR20](https://github.com/sinnergarden/axiom-research/pull/20)提供独立通用配置、明确的 88 列定义和经现 Engine 工厂校验的费用表；它尚未合并，也不包含私人数据或结果。原[21 日功能用例](m2-one-year-executable-case.md)保持原来的已执行范围。

## 配置与时间语义

使用现有 `stock_dataset_schedule_v2`，把时间对象放入 `weekly_schedule`。`load_stock_sequential_configuration` 调用 `compile_stock_weekly_folds`，按冻结日历的 ISO 年与周分组，保留节假日短周和跨年边界。每周首交易日前一完整交易日进行 fit，组内每个交易日分别使用严格前一 session 的新特征推理。Engine 按完整日历的周首交易日消费当时已完成的最新模型预测，严格 T+1 执行。

```yaml
trade_start: '2019-01-02'
trade_end_exclusive: '2026-01-01'
training_window:
  unit: feature_sessions
  length: 543
  end: previous_fit_session
timezone: Asia/Shanghai
fit_time: '20:30'
model_time: '20:45'
inference_time: '21:00'
evaluation_cutoff: '2026-03-09T20:30:00+08:00'
```

543 个声明训练 Feature 日期来自 504+40−1。504 是名义成熟日期计划，实际训练只接纳 fit 当时已经成熟的标签。每日 H40 统一从信号日后第一个交易日 open 到第 40 个交易日 close，使用共同 anchor 复权价格收益；训练沿现支持的截面 z-score，评价读取原始收益。H40 观察重叠，汇总不能把每日观察当作独立样本。

原始 LabelSpec 的 `normalization_policy: none` 只描述原始收益；dataset 的 `preparation_options.normalization_backend: core_cs_batch_v1` 接入既有 `forward_label_cs_zscore_v1`。sequential owner 对每个成熟日期截面进行 z-score，并将归一化 target 传入 fit，评价保存原始收益。历史成员和数据可见性沿实际 `best_effort_vendor_v1` 与 `declared_vendor_assumption`，未证实历史真实收件时间。

对保存交易日历的轻量核查得到 1,699 个 OOS 交易日和 359 个真实交易周。首周交易日为 2019-01-02/03/04，fit 在 2018-12-28。母 Feature 需要覆盖 2016-10-13 至 2025-12-30，物理价量回看从 2015-09-28 开始；最后预测 Feature 日期的 H40 终点为 2026-03-06。上述日期是计划证据，正式 Data scope 与逐行标签准入仍需验证。

## 从配置到保存结果

先由 Data 冻结完整真实日历、历史成员及所需事实范围，再把实际 Feature 轴路径和文件摘要填入 dataset。manifest 中已有分区与保存 source 覆盖不足是不同的问题：先检查事实与观察范围，只为真实缺口请求供应商数据。旧保存 source 或旧结果仍保持其原范围和身份。

本次冻结物理来源与库为 638 只证券，其中 32 只仅用于预热。库 owner 的原始 `sample_universe` 和正式训练 projection 为完整 606 只，dataset、保存预测及 StockMarketSpec 统一使用该轴。638 只物理来源保留，逐日历史成员 mask 保留；仅 OOS 的成员并集不替代完整训练轴。

Research 的正式入口仍是 `examples/a01_one_year.py`。名称不限制配置区间；完整 options 引用 experiment、dataset、model、label 和真实保存来源。

```sh
python examples/a01_one_year.py --options /absolute/path/options.json --stage validate
python examples/a01_one_year.py --options /absolute/path/options.json --stage train
python examples/a01_one_year.py --options /absolute/path/options.json --stage evaluate
```

这些是原入口的命令形式，不表示七年训练和评价已经运行。公开模板的 `<...>` 必须替换成正式 Data 保存件、Feature 库 projection 引用和真实本地路径。`dataset.yaml` 的 `weekly_schedule` 是唯一可执行时间配置，`options.json` 的 `evaluation` 是唯一可执行评价配置；直接修改这些对象，无需人手同步另一份片段。评价固定 `frequency: daily`，保留每天原生预测与成熟标签配对，不用周采样或前向填充增加观察。

全期 Feature 只准备一次。使用已合并 Feature 库保存件时，训练 projection 只导出一次、对应 genuine `StockFeatureView` 只打开一次，再传入 `build_configured_stock_sequential_experiment`。原 sequential owner 在 359 折中借用同一句柄，保留重叠 Feature 日期并投影当前训练和预测窗口，逐折释放工作数组；Data ColumnSource 也由调用方一次打开并共享。Research PR20 为原 CLI 添加显式 `feature_library_training_view` 配置，调用正式库适配器，仍待审查合并；该配置只使用 validate/train/evaluate，projection 由自己的公开 owner 准备。

库适配器的冷准入会逐日比对全部 projection 与库中的原始值、时钟、成员和来源，然后释放日 payload；训练滑窗随后读取这些保存件。这是一次冷校验和一次递进工作窗读取，不能声称全部 Feature 字节只读一次。RawLabel 也按每个 fit 的实际共同 anchor 和 cutoff 准备；数值缓存要求端点、anchor 和依赖一致，周训练的 anchor 变化会阻止对应 Raw 数值命中。逐折成熟度、截面 cohort、归一化绑定及矩阵生成仍需计入预算，现 owner 不是只重复 fit/predict。

RawLabel 共用同一 Data Reader/Snapshot 与分区 LRU，每个价格域的批量数组只取得一次，再按 8 日块生成 H40。Data 的 `previous` 只提示差异轴，各 cutoff 仍重新选择版本与计算共同 anchor 复权数组；Research 经公开 API 取得有明确寿命的只读副本。没有逐折重新打开全源，但被 LRU 淘汰的分区仍可能再次解码，不能把共享 owner 宣称为全链零拷贝。

LightGBM 固定 100 树、31 叶、深度 5、学习率 0.05、seed 42，不加消融或参数搜索。50 万元主账户使用 rank-buffer Top5、keep_rank=10；对照使用同一保存预测的 Top5 等权。两账户沿 `stock_request_with_saved_predictions`、`run_saved_stock_strategy` 和 `evaluate_saved_stock_strategy`，共用冻结市场准入，独立保存账本与评价，并关联同一结果登记。359 折所需的读取限额须显式配置；短示例中的 64 折上限和三策略列表不自动代表新范围。

已检查的旧 profile 声明佣金 0.0003、每笔最低 5 元、滑点 0 bps、每日成交量参与率 10%。保存费用表的卖出印花税在 2023-08-28 前为 0.001、之后为 0.0005；双边过户费在 2022-04-29 前为 0.00002、之后为 0.00001。旧 profile 的规则日历仅覆盖短案例，费用证实窗口为 2019-06-28 至 2024-06-28；七年账户须由 Engine 准备匹配完整范围的正式 profile。两份本地结果和用户说明均展示实际准入 profile 身份、佣金、税费、滑点及毛股息未计个人红利税的约定。

## 成本、缺口与完成判据

成本分别记录原始来源读取与准备、Feature 一次生产与保存、训练视图一次准入、359 折训练和预测、市场准备、两账户、只读信号与账户评价。旧短例的时间只能作为对应实现和维度的参考。新库的共享 DAG、分块写入及保存来源与旧 producer 不同，不能把四列小样本时间按列数直接相乘。没有充分实测支持的阶段保留为未知，不用宽区间冒充可靠总预算或最大上界。

已合并库接口的元数据修复和小真实闭环由 Feature owner 提供证据，全期生产仍待完成。359 折的静态审查确认共享 owner 的生命周期，同时指出 fit anchor 不同的 RawLabel 不能当作一张全期可复用表。模板把累计来源准入限额设为 32 GiB；该限额包含保存文件和元数据，12 GiB Research 驻留限额及 Data 自己的预算是另外的约束。多个 owner 与原生 LightGBM 的内存之和须通过进程 RSS 实测，不能把局部限额说成整进程上界。新范围未取得全链实测前，不能保证凌晨 6 点前完成。

完成后保存每日 H40 IC/RankIC、十组与头部表现、两账户净值、收益、回撤、费用和 CSI300 对照。现账户 analysis 的换手是双边 gross traded/mean NAV；持有期是符合统计资格的已平仓 episode 日历天数。需要其他口径时明确缺失，不能改名替代。供应商历史成员、缺值、复权价格收益与现金权益总回报的边界继续说明。

训练和信号评价沿现有自动登记。账户适配器传入同一 registration，最终通过正式 UI 的只读根配置发现完整结果及未完成状态。只有七年指定范围完成、保存件能重新打开、覆盖与排除原因可见、两账户与所属模块值一致，才认定本项 M1 真实使用验收完成。
