# 当前教程与历史归档

[ML 工程当前操作页](ml_engineering_tutorial.ipynb)及[生成 HTML](ml_engineering_tutorial.html)按 8 节组织：当前可用范围、六份配置、共享会话、模型与选列迭代、独立评价与组合、Engine 保存预测消费、冷开与复用实测、固定长周期入口与预算。默认阅读模式只展示说明和已有工程摘要；执行模式由本地路径配置与显式动作开启。模型参数迭代在同一 Data/Feature/Batch 会话内进行，使用已有 typed 配置和公共入口，不手工生成 receipt 或结果身份。

[历史 Notebook](ml_engineering_history_20261011.ipynb)及[历史 HTML](ml_engineering_history_20261011.html)完整保存此前 28 个单元、输出和执行次数，包括两折教学、旧接口限制及失败成本。当前页按现行流程组织操作。255 折预测和 7 份信号评价已有保存证据，五年账户结果待 Engine owner 回填。薄编排已实际执行现有极小合成 fixture，原真实业务没有重跑。

接口定义继续以[Research 主章](../docs/design/05_axiom_research.md)和[Trade 主章](../docs/design/04_axiom_trade.md)为准。当前页沿既有配置解析、准备、训练、保存评价和 Runtime owner；HTML 由 Notebook 生成。旧 [`weekly_ml_pilot.py`](../examples/weekly_ml_pilot.py)保留固定窗历史控制。

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


## ML 工程已有实测

固定保存模型的共享会话实测为：冷打开 25.03 秒、首次核验与冻结 20.67 秒、同 owner 第二次调用 1.59 秒；整进程 47.84 秒、RSS 5.08 GiB、新增 7.74 MiB。两次 fit/predict 均为 0，完整输出身份相同。这条 HIT 证据固定于原实现，不能代替新模型训练、换选列准备或五年账户成本。

[有界工程摘要](../reports/research-shared-owner-acceptance-20261011.json)保留原测量，[当前页检查记录](../reports/ml-engineering-operational-page-20261011.json)记录默认阅读、接线与归档检查；[动作执行记录](../reports/ml-engineering-notebook-actions-20261011.json)另列四个实际合成动作与未覆盖范围。合成评价每日 3 个有效配对未达到原门槛 20，这个极小合成 case 没有覆盖非空 IC、RankIC 和 IR。83.79 秒重开 owner HIT、605 秒失败观察器及旧五年估计仍在历史归档，私人模型与数据留在本地。

[追加保存组合集成](../reports/ml-engineering-saved-combination-integration-20261011.json)：追加的保存模型小集成复用同一周两份真实模型，5 日各有 296 个有效配对，门槛保留 20，原信号与组合的 IC、RankIC、IR 均有限。首个请求沿用五年控制件被 scope 校验拒绝；随后沿公开 Data.export_native_view、stock_execution_rules、stock_daily_open_profile_v2 生成匹配六日的 Query/profile/rules，组合绑定新 membership 引用，原模型、分数、有效性和可用时钟不变。实际 Notebook strategy 读取同一份新交接，Runtime 保存 COMPLETE 账户（5 NAV、5 orders、5 fills），公共 projection 读回通过，训练与预测为 0。本地六类导航、短策略路径和保存账户已接好，默认阅读；完整五年账户与评价仍待 Engine owner。本次固定 c890，最终 Engine 实现身份改变后只复用保存预测重生成组合，记录新耗时与身份，不重训。私人结果留在本地。
