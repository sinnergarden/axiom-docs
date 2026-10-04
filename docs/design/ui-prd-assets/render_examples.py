"""Render discussion-only PRD illustrations from explicit synthetic inputs."""
from __future__ import annotations

import argparse
import json
import tempfile
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="axiom-prd-mpl-"))
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, patches
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "illustration-data.json").read_text())
FONT_CANDIDATES = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]
for filename in FONT_CANDIDATES:
    if Path(filename).is_file():
        font_manager.fontManager.addfont(filename)
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=filename).get_name()
        break
plt.rcParams.update({"font.size": 10, "axes.unicode_minus": False,
                     "svg.fonttype": "none", "svg.hashsalt": "axiom-ui-prd-draft"})
BG, PANEL, INK, MUTED = "#f5f7fb", "#ffffff", "#25354a", "#63738a"
BLUE, GOLD, PROFIT, LOSS = "#476eaa", "#bb8e34", "#f789ac", "#6bcda8"


def frame(number: str, title: str):
    fig = plt.figure(figsize=(11, 2.9), facecolor=BG)
    fig.text(.028, .92, f"F{number}  {title}", color=INK, fontsize=12, weight="bold")
    fig.text(.975, .92, "合成示意 · 功能及口径待讨论", ha="right", color=MUTED, fontsize=9)
    fig.text(.028, .035, "所有曲线、交易及统计均为设计示例，不是实际回测结果。", color=MUTED, fontsize=8)
    return fig


def axes(fig, rect):
    ax = fig.add_axes(rect, facecolor=PANEL)
    ax.tick_params(labelsize=8, colors=MUTED)
    for spine in ax.spines.values():
        spine.set_color("#dce3ed")
    ax.grid(axis="y", color="#e8edf4", linewidth=.7, zorder=0)
    return ax


def card(ax, x, y, width, height, text, color=BLUE):
    ax.add_patch(patches.FancyBboxPatch((x, y), width, height,
        boxstyle="round,pad=.014,rounding_size=.018", facecolor=PANEL,
        edgecolor="#dce3ed", linewidth=1))
    ax.text(x+.02, y+height*.5, text, va="center", color=color, fontsize=10)


def save(fig, stem, preview):
    svg_path = ROOT / (stem+".svg")
    fig.savefig(svg_path, metadata={"Date": None, "Description":
        "Synthetic PRD discussion illustration; not owner backtest evidence."})
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines())+"\n")
    if preview:
        preview.mkdir(parents=True, exist_ok=True)
        fig.savefig(preview / (stem+".png"), dpi=120)
    plt.close(fig)


def render(preview):
    fig = frame("01", "实验列表与版本关系")
    ax = fig.add_axes([.025, .15, .95, .68]); ax.axis("off")
    rows = [("实验 01 · v1", "已保存 · 示例负结果"),
            ("实验 01 · v2", "已保存 · 修改一个因素"),
            ("实验 02 · v1", "状态阻断 · 仍保留")]
    for i, (name, state) in enumerate(rows):
        y=.66-i*.28
        card(ax,.01,y,.37,.22,f"{name}     {state}",INK)
    card(ax,.47,.52,.49,.35,"选中版本：假设 / 本轮改动 / 关联运行\n版本关系与对照对象明确",INK)
    ax.annotate("",xy=(.47,.66),xytext=(.40,.48),arrowprops={"arrowstyle":"->","color":BLUE})
    ax.text(.49,.25,"查看结果 → 比较 → 复制下一轮讨论摘要",color=MUTED)
    save(fig,"figure01_experiment_versions",preview)

    fig = frame("02", "策略与候选基准的同口径比较")
    ax=axes(fig,[.07,.23,.57,.58])
    ax.plot(DATA["nav"],color=BLUE,lw=2,label="策略示例")
    ax.plot(DATA["baseline"],color=GOLD,lw=1.7,ls="--",label="七 ETF 等权持有 · 候选示意")
    ax.set_ylabel("净值指数",color=MUTED)
    ax.set_xticks([0,8,16,24],["03月","04月","06月","08月"])
    ax.legend(loc="upper left",frameon=False,fontsize=8)
    fig.text(.70,.68,"比较前核对",color=INK,weight="bold")
    fig.text(.70,.53,"期间 · 初始账户 · 收益口径\n费用 · 分红 · 执行差异",color=MUTED,linespacing=1.7)
    fig.text(.70,.28,"缺基准：不画线\n口径不兼容：列出差异",color=INK,linespacing=1.7)
    save(fig,"figure02_comparison",preview)

    fig = frame("03", "净值与风险在同一时间轴")
    ax=axes(fig,[.07,.52,.70,.29]);ax.plot(DATA["nav"],color=BLUE,lw=2)
    ax.set_ylabel("净值指数",color=MUTED);ax.set_xticklabels([])
    dd=axes(fig,[.07,.20,.70,.24]);dd.plot(DATA["drawdown"],color=LOSS,lw=1.6)
    dd.fill_between(range(len(DATA["drawdown"])),DATA["drawdown"],0,color=LOSS,alpha=.25)
    dd.yaxis.set_major_formatter(PercentFormatter(100));dd.set_ylabel("回撤",color=MUTED)
    dd.set_ylim(-10,1);dd.set_yticks([-10,-5,0])
    dd.set_xticks([0,8,16,24],["03月","04月","06月","08月"])
    fig.text(.81,.67,"悬停：保存原值\n选区间：去复盘",color=INK,linespacing=1.8)
    fig.text(.81,.29,"缺回撤序列\n明确不可用",color=MUTED,linespacing=1.8)
    save(fig,"figure03_return_risk",preview)

    fig = frame("04", "K 线 成交点与选点复盘")
    ax=axes(fig,[.055,.24,.61,.57])
    for i,row in enumerate(DATA["candles"]):
        c=PROFIT if row["close"]>=row["open"] else LOSS
        ax.vlines(i,row["low"],row["high"],color=c,lw=.8)
        ax.add_patch(patches.Rectangle((i-.32,min(row["open"],row["close"])),.64,
            max(abs(row["open"]-row["close"]),.006),facecolor=c,edgecolor=c))
    for event in DATA["events"]:
        i=event["index"];price=float(event["price"])
        ax.annotate(event["label"],xy=(i,price),xytext=(i,price+(.28 if event["side"]=="BUY" else -.28)),
            color=BLUE,fontsize=9,ha="center",arrowprops={"arrowstyle":"->","color":BLUE,"lw":.8})
    ticks=[0,20,40,59]
    ax.set_ylabel("元 / 份",color=MUTED);ax.set_xticks(ticks,[DATA['candles'][i]['session'][5:] for i in ticks])
    fig.text(.71,.71,"选中的 B 点 · 合成示例",color=INK,weight="bold")
    fig.text(.71,.51,"信号 → 决策 → 委托 → 成交\n保存价量 / 费用 / 执行原因",color=MUTED,linespacing=1.7)
    fig.text(.71,.23,"未成交记录单列原因\n缺 high / low 不伪造 K 线",color=INK,linespacing=1.7)
    save(fig,"figure04_trade_replay",preview)

    fig = frame("05", "月度收益与闭合持仓段盈亏")
    ax=axes(fig,[.06,.24,.40,.56])
    months,returns=zip(*DATA["months"])
    ax.bar(months,returns,color=[PROFIT if v>0 else LOSS for v in returns],width=.6)
    ax.axhline(0,color=MUTED,lw=.8);ax.set_ylabel("月收益 %",color=MUTED)
    ax.set_ylim(-3.4,7.4)
    for i,v in enumerate(returns):ax.annotate(f"{v:+.1f}",(i,v),xytext=(0,4 if v>0 else -12),textcoords="offset points",ha="center",fontsize=8)
    ax2=axes(fig,[.56,.24,.40,.56]);vals=DATA["closed_segments_net_pnl"]
    ax2.bar(range(1,9),vals,color=[PROFIT if v>0 else LOSS for v in vals],width=.6)
    ax2.axhline(0,color=MUTED,lw=.8);ax2.set_ylabel("段净盈亏 / 元",color=MUTED)
    ax2.set_xticks(range(1,9));ax2.set_ylim(-245,200)
    for i,v in enumerate(vals,1):ax2.annotate(f"{v:+d}",(i,v),xytext=(0,4 if v>0 else -12),textcoords="offset points",ha="center",fontsize=8)
    fig.text(.56,.14,"示例：5 / 8 盈利闭合段；开放段 1 单列。口径待讨论。",color=MUTED,fontsize=8)
    save(fig,"figure05_monthly_segments",preview)

    fig = frame("06", "展开来源后查看同一运行的证据链")
    ax=fig.add_axes([.025,.17,.95,.63]);ax.axis("off")
    items=[("Data\n固定行情与事实",.01), ("Research\n实验 / 信号",.265),
           ("Engine\n账户 / 标准评估",.52), ("UI\n只读展示",.775)]
    for label,x in items:card(ax,x,.43,.20,.40,label,INK)
    for x in [.22,.475,.73]:ax.annotate("",xy=(x+.04,.63),xytext=(x,.63),arrowprops={"arrowstyle":"->","color":BLUE})
    ax.text(.015,.15,"主视图：短限制说明        折叠区：来源版本 / 保存证据 / 账户水位 / 缺失原因",color=MUTED,fontsize=10)
    save(fig,"figure06_provenance",preview)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--preview-dir",type=Path)
    render(parser.parse_args().preview_dir)
