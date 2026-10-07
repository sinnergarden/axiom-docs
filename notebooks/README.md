# 两种阅读路线

[ML 工程 Notebook](ml_engineering_tutorial.ipynb)及[生成 HTML](ml_engineering_tutorial.html)：
先看整体 owner 图、固定真实短样本、registry、成熟 label/Dataset/model、保存 Signal、
Engine 唯一账户、UI 与缓存边界。真实65-session滑动两折已通过；旧固定配置/成熟控制保留历史；Notebook 第 1–13 节只读本地保存回执，
第3/6节展示公共catalog及真实滑动builder用法，Markdown代码默认不执行；全年/多年 ML 暂停。
[`weekly_ml_pilot.py`](../examples/weekly_ml_pilot.py)仅为原Nov1—Jan31固定窗历史控制，新入口是
`axiom_research.build_stock_ml_fold_from_saved_inputs`。详细合同仍链接统一设计正文，HTML 从 Notebook 生成，不独立编辑。

第 14 节是 CaseC/A/B 的逐单元验收稿。CaseC 直接调用正式的 matrix_v2/stock_feature_inputs_v3、prepare、batch/fold、OOS frozen-input、Runtime v7及保存账户评价入口；一个 batch内完成四折、同配置 HIT和冻结。使用 Python 3.11 及以上的 kernel，设置 `AXIOM_M1_ROOT` 并按该节 `case-inputs.json` 交接真实输入后，从第 14 节单独开始。新增单元未执行且没有保存输出，既有 HTML 保留此前内容；本轮只核对语法、公共签名与标准库小单元。

CaseA 的窄 TrainSpec、CaseB 的保存组合与组合准入、按年和分组统计仍待原 owner 接口。先用固定 5D/LightGBM 做 CaseC 的四个周度 fold和 50 万元 Top5；每阶段耗时及正式 metrics保存到外部根目录 `runs/<本次运行>/timings.jsonl`，准备和 fold缓存留在 `cache/`。随后沿同一实现做 M1 多年正确性与性能验收。完整用例通过与正常 API返回分别记录，中断重用限于 Research 已完成 fold。

Data两种路线的唯一编辑源是 [Researcher notebook](researcher_tutorial.ipynb) 和 [Developer notebook](developer_tutorial.ipynb)。生成的 [Researcher HTML](researcher_tutorial.html) 与 [Developer HTML](developer_tutorial.html) 可直接阅读代码与表格。HTML 不独立修改，原工作区 `design/notebooks` 与 Data 旧入口仅保留导航。

Researcher 沿一次研究准备工作展开：先看一只证券六天的价格，扩成矩阵，处理缺失与价格尺度，再加入当时可见的财报，保存并复用特征，最后交给下游。Developer 沿一次接入工作展开：保存响应、转换字段、检查并发布，再加入财报与基金，继续日更，处理范围变化、失败恢复和交接。

第一次查询先显示代码和小表；完整初始化、长来源引用和工程核对按需展开。Qlib 是可选的显式导出路线。Researcher 的联合特征复用和 Developer 的合成离线扩标都在第 7 节。

| 阅读定位 | 章节 |
|---|---|
| Researcher | [2：取表](researcher_tutorial.html#section-2) → [5：历史财报可见性](researcher_tutorial.html#section-5) → [7：特征复用](researcher_tutorial.html#section-7) |
| Developer | [2：Raw 响应](developer_tutorial.html#section-2) → [3：字段映射](developer_tutorial.html#section-3) → [8：恢复](developer_tutorial.html#section-8) |

## 离线重新运行

基础 Data 运行不需要教学工具或 Qlib。复跑完整两教程需要本地真实样本和已保存的验收报告，并安装教学及 Qlib 消费依赖。另提供同级 Engine、Research、UI 的薄 adapter 源码；Data 包本身不依赖它们。已测锁定环境为 Python 3.12/macOS，其他平台需解析适用环境。

```sh
python -m pip install -r ../axiom-data/requirements-local.lock
python -m pip wheel ../axiom-data --no-deps --no-build-isolation --wheel-dir /absolute/retained-wheels
python -m pip install /absolute/retained-wheels/axiom_data-0.3.5-py3-none-any.whl
python -m pip install -r ../axiom-data/requirements-notebooks.txt -r ../axiom-data/requirements-qlib.lock
python -m pip install ../axiom-engine "../axiom-research[build]"
python -m ipykernel install --user --name axiom-data --display-name 'Axiom Data'
AXIOM_TUTORIAL_DATA_PACKAGE="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" python examples/real_tutorials.py
```

本命令执行已有 notebook、更新输出并生成 HTML，不生成另一份正文。只读正式样本，写入演示使用临时数据根，不加载 token 或联网采集。`--no-execute` 只渲染已有输出，不记作新执行。运行报告在本地 `docs/real-tutorial-validation.json`，未推送生产数据或运行日志。

初始化路径和变量集中在 [tutorial_support.py](../examples/tutorial_support.py)，可用 `AXIOM_WORKSPACE`、`AXIOM_TUTORIAL_DATA_ROOT`、`AXIOM_UNIFIED_DATA_ROOT`、`AXIOM_UNIFIED_SNAPSHOT` 等环境变量适配搬移后的实际样本。静态 HTML 不要求安装环境，也无需先拉十二年数据。

## 教学与验收范围

表格来自一年固定1800行情样本、两证券完整来源样本和七ETF日线样本，三者各有固定版本。两证券原教学样本含留存原供应商响应的离线回放，receipt 属于回放时间；新鲜生产入口验证另见 [bulk preflight](../docs/bulk-preflight.md)。合成测试只证明相应语义边界，不当作供应商数据。

[权威设计](../docs/design/README.md)规定目标，[当前交付](../docs/current-delivery.md)记录已测范围与固定 owner 报告。ETF 信号、离线账户与静态 HTML 已完成短样本消费链；完整模型/OOS、Runtime/Broker 与 UI 产品仍按 owner 范围验收。

本教程保存的联合输入示例来自 Research 0.1.1；本轮 ETF 另使用 Research 0.1.2、Engine 0.2.1 与 UI 0.1.0 的固定已推源码，见[版本表](../versions.json)与[当前交付](../docs/current-delivery.md)。本页安装命令沿用此前教程的已验 Data wheel；没有新的 Research/Engine/UI wheel 验收。主线 Data 查询重放不依赖 Research，跨仓附录的旧输出只证明当时调用；不以新源码身份追认旧输出为新回测。

上面的 wheel 必须留存原文件，kernel 与运行命令使用同一安装环境。`AXIOM_TUTORIAL_DATA_PACKAGE` 指向该 wheel 的 site-packages；否则 helper 默认读源码树，离线构建需要干净且可恢复的 commit。执行更新 notebook 会使源码树变脏，留存安装包可以独立固定实际 builder；不允许只写一个旧 HEAD 代替真实代码来源。

此前新增 Researcher 联合输入与 Developer 离线扩标单元，分别连同初始化单元执行：4 个 fresh code cells、0 errors；其余 93 个代码单元保留此前输出，没有声称本轮全量重跑。当前合计 Researcher 43、Developer 54 个代码单元。

[本轮实现与限制](../docs/current-delivery.md)记录字段/时间/证券三类增量和实际小样本测量。

2026-10-04 ETF 入口：先读[数据与策略交接](../docs/etf-rotation-data.md)，再从[公开加载与复用](../docs/current-delivery.md#公开加载与持久复用)进入 Research 保存实验、Engine 中立回测/只读结果和 UI CLI。使用 owner 指定的固定产物位置，静态报告无需执行研究或访问 Data。

本次叙述重编排保留 97 个代码单元及其执行计数与输出；单元顺序和展示元数据随教学路线调整。它只生成 HTML，没有执行教学代码或采集。逐单元与导航核对见[本轮检查](../reports/tutorial-narrative-check.json)。

## 从保存输出生成 HTML

在本仓根目录运行：

```sh
python examples/render_notebook.py --notebook ../notebooks/researcher_tutorial.ipynb
python examples/render_notebook.py --notebook ../notebooks/developer_tutorial.ipynb
```

渲染器默认只读 notebook。HTML 提交后，可将两种角色与章节导航合为一个离线文件：

```sh
python examples/build_library_tutorials.py --source-ref <已提交的教程版本> --output /absolute/axiom-tutorials.html
```

合并器核对本地 HTML 与声明的 commit 一致，保留全部代码和输出文本，将文档链接固定到该版本。它不执行 notebook，也不访问数据源。

上述关键章节已用现有 Mac Chrome 实际查看折叠前后展示，记录见 [Chrome 抽查](../reports/tutorial-chrome-review.json)。宽表会提示横向滚动，也可聚焦后用方向键浏览完整列。


ML工程页第 1–13 节的原四代码单元只读取冻结教学回执与新fold交付回执；第 14 节的独立验收单元按上文真实输入配置执行。
以下回执设置用于第 1–13 节的历史阅读路线。设置 `AXIOM_ML_TEACHING_RECEIPT` / `AXIOM_ML_TEACHING_RECEIPT_REF`，以及
`AXIOM_ML_FOLD_DELIVERY` / `AXIOM_ML_FOLD_DELIVERY_REF` 为owner指定路径和完整字节sha256。
显式函数仅定义，默认不调用业务，也不为展示重复解析大proof；已保存结果由owner和独立reader核验。
新两fold是65session真实滑动；旧January v1 Top3/Top5账户另列，新v2仅中立验证、账户拒绝。
执行输出只在本地副本保存。256周warm约42.72min要求父件全准备且proof规模相近；
每cutoffLabel/norm、冷准备、证明扩张、账户与展示另计，总上界未知。历史固定窗66min不当最终滑窗估计。
详见 [ML工程§12](ml_engineering_tutorial.html#section-12)，无全年/五年实跑。
