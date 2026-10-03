# 真实教程入口

唯一编辑源是 [Researcher notebook](researcher_tutorial.ipynb) 和 [Developer notebook](developer_tutorial.ipynb)。生成的 [Researcher HTML](researcher_tutorial.html) 与 [Developer HTML](developer_tutorial.html) 可直接阅读真实表格。HTML 不独立修改，原工作区 `design/notebooks` 与 Data 旧入口仅保留导航。

Researcher 从事实链路、固定版本和第一次读取开始，解释时间、缺失、复权、财务与成员，再讲查询重放和完整实验。Developer 从 Raw、字段映射和 manifest 开始，解释批量作业、daily/refresh、恢复、迁移与部署。跨仓接口和较长验收放在附录；Qlib 是显式消费格式。

## 离线重新运行

基础 Data 运行不需要教学工具或 Qlib。复跑完整两教程需要本地真实样本和已保存的验收报告，并安装教学及 Qlib 消费依赖。另提供同级 Engine、Research、UI 的薄 adapter 源码；Data 包本身不依赖它们。已测锁定环境为 Python 3.12/macOS，其他平台需解析适用环境。

```sh
python -m pip install -r ../axiom-data/requirements-local.lock
python -m pip wheel ../axiom-data --no-deps --no-build-isolation --wheel-dir /absolute/retained-wheels
python -m pip install /absolute/retained-wheels/axiom_data-0.3.4-py3-none-any.whl
python -m pip install -r ../axiom-data/requirements-notebooks.txt -r ../axiom-data/requirements-qlib.lock
python -m pip install ../axiom-engine "../axiom-research[build]"
python -m ipykernel install --user --name axiom-data --display-name 'Axiom Data'
AXIOM_TUTORIAL_DATA_PACKAGE="$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')" python examples/real_tutorials.py
```

本命令执行已有 notebook、更新输出并生成 HTML，不生成另一份正文。只读正式样本，写入演示使用临时数据根，不加载 token 或联网采集。`--no-execute` 只渲染已有输出，不记作新执行。运行报告在本地 `docs/real-tutorial-validation.json`，未推送生产数据或运行日志。

初始化路径和变量集中在 [tutorial_support.py](../examples/tutorial_support.py)，可用 `AXIOM_WORKSPACE`、`AXIOM_TUTORIAL_DATA_ROOT`、`AXIOM_UNIFIED_DATA_ROOT`、`AXIOM_UNIFIED_SNAPSHOT` 等环境变量适配搬移后的实际样本。静态 HTML 不要求安装环境，也无需先拉十二年数据。

## 教学与验收范围

表格来自一年固定1800行情样本、两证券完整来源样本和七ETF日线样本，三者各有固定版本。两证券原教学样本含留存原供应商响应的离线回放，receipt 属于回放时间；新鲜生产入口验证另见 [bulk preflight](../docs/bulk-preflight.md)。合成测试只证明相应语义边界，不当作供应商数据。

[权威设计](../docs/design/README.md)规定目标，[当前交付](https://github.com/sinnergarden/axiom-data/blob/main/DELIVERY.md)记录已测范围。研究策略、模型、账户回测和 UI 产品仍由其 owner 实现和验收。

Research 0.1.1（`eb6ae3a`）已发布 Data/Qlib/ViewRef adapter 和具名、多字段、多报告期联合输入的最小持久 FeatureBuild。每个 cutoff 由 Data 选修订，各财务流再选最新可见报告期，由 Core identity/pct_change/asof 执行，支持保存、重读和复用。Engine Core `c8a506b` 已发布；本地 Runtime 仍未提交。任意 FeaturePlan、TTM 联合投影、标签、训练、模型/OOS/策略回测及多年规模性能仍不是这次交付。 主线 Data 查询重放不依赖 Research。完整跨仓附录需要本地未发布的 Runtime/UI；新联合输入示例只需要已发布的三仓实现。

上面的 wheel 必须留存原文件，kernel 与运行命令使用同一安装环境。`AXIOM_TUTORIAL_DATA_PACKAGE` 指向该 wheel 的 site-packages；否则 helper 默认读源码树，离线构建需要干净且可恢复的 commit。执行更新 notebook 会使源码树变脏，留存安装包可以独立固定实际 builder；不允许只写一个旧 HEAD 代替真实代码来源。

本轮新增 Researcher 联合输入与 Developer 离线扩标单元，分别连同初始化单元执行：4 个 fresh code cells、0 errors；其余 93 个代码单元保留此前输出，没有声称本轮全量重跑。当前合计 Researcher 43、Developer 54 个代码单元。

[本轮实现与限制](../docs/current-delivery.md)记录字段/时间/证券三类增量和实际小样本测量。
