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
        plt.rcParams["font.family"] = [font_manager.FontProperties(fname=filename).get_name(), "DejaVu Sans"]
        break
plt.rcParams.update({"font.size": 10, "axes.unicode_minus": False,
                     "svg.fonttype": "none", "svg.hashsalt": "axiom-ui-prd-draft"})
BG, PANEL, INK, MUTED = "#f5f7fb", "#ffffff", "#25354a", "#63738a"
BLUE, GOLD, PROFIT, LOSS = "#476eaa", "#bb8e34", "#f789ac", "#6bcda8"


def frame(number: str, title: str, height: float = 2.9):
    fig = plt.figure(figsize=(11, height), facecolor=BG)
    fig.text(.028, .92, f"F{number}  {title}", color=INK, fontsize=12, weight="bold")
    fig.text(.975, .92, "合成示意 · 功能已确认 / 视觉待确认", ha="right", color=MUTED, fontsize=8)
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
    fig = frame("01", "研究问题 → 实验版本 → 运行")
    ax = fig.add_axes([.025, .15, .95, .68]); ax.axis("off")
    ax.text(.02,.92,"近期结果     标签 / 状态     收藏 / 搁置",color=MUTED,fontsize=9)
    ax.text(.02,.73,"研究问题 01：动量能否更稳？",color=INK,weight="bold")
    card(ax,.04,.42,.34,.19,"v1 → run 01 · 负结果保留",MUTED)
    card(ax,.04,.16,.34,.19,"v2 → run 02 · 近期 / 收藏",BLUE)
    ax.text(.02,-.04,"研究问题 02 → v1 → run 03 · 失败 / 搁置",color=MUTED,fontsize=9)
    card(ax,.49,.43,.46,.35,"当前 v2：假设 / 本轮变动\n关联运行与输入输出版本",INK)
    ax.annotate("",xy=(.49,.58),xytext=(.40,.26),arrowprops={"arrowstyle":"->","color":BLUE})
    ax.text(.50,.19,"看结果 → 加对照 → 下一轮讨论",color=MUTED)
    save(fig,"figure01_experiment_versions",preview)

    fig = frame("02", "回测结果对比 · 添加市场基准")
    ax=axes(fig,[.07,.23,.57,.58])
    ax.plot(DATA["nav"],color=BLUE,lw=2,label="策略示例")
    ax.plot(DATA["baseline"],color=GOLD,lw=1.7,ls="--",label="沪深300 · 合成示意 / 系列待核实")
    ax.set_ylabel("净值指数",color=MUTED)
    ax.set_xticks([0,8,16,24],["03月","04月","06月","08月"])
    ax.legend(loc="upper left",frameon=False,fontsize=8)
    fig.text(.70,.68,"与 F03 共用图和指标",color=INK,weight="bold")
    fig.text(.70,.49,"加旧版 / 基准即比较\n共用区间 · 资金 · 费用 · 滑点",color=MUTED,linespacing=1.7)
    fig.text(.70,.24,"配置详情折叠，只提示差异\n缺基准：明确不可用",color=INK,linespacing=1.7)
    save(fig,"figure02_comparison",preview)

    fig = frame("03", "同一收益风险区 · 单运行状态")
    ax=axes(fig,[.07,.52,.70,.29]);ax.plot(DATA["nav"],color=BLUE,lw=2)
    ax.set_ylabel("净值指数",color=MUTED);ax.set_xticklabels([])
    dd=axes(fig,[.07,.20,.70,.24]);dd.plot(DATA["drawdown"],color=LOSS,lw=1.6)
    dd.fill_between(range(len(DATA["drawdown"])),DATA["drawdown"],0,color=LOSS,alpha=.25)
    dd.yaxis.set_major_formatter(PercentFormatter(100));dd.set_ylabel("回撤",color=MUTED)
    dd.set_ylim(-10,1);dd.set_yticks([-10,-5,0])
    dd.set_xticks([0,8,16,24],["03月","04月","06月","08月"])
    fig.text(.81,.67,"期间收益 12.4%\n最大回撤 −9.3%",color=INK,linespacing=1.8)
    fig.text(.81,.29,"加对照进入 F02\n不会新画另一套",color=MUTED,linespacing=1.8)
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
    fig.text(.71,.24,"决策 debug · 低优先级增强\n特征 / 分数 / 排名 / 门槛\n未保存的依据明确不可用",color=INK,linespacing=1.5)
    save(fig,"figure04_trade_replay",preview)

    fig = frame("05", "月收益热力图与完整持仓段分布",3.3)
    ax=fig.add_axes([.035,.28,.49,.53]);ax.axis("off")
    ax.text(0,1.00,"账户月收益率（%）",color=INK,weight="bold")
    ax.text(0,.48,str(DATA["month_year"]),color=MUTED,fontsize=8)
    monthly=dict(DATA["months"])
    for month in range(1,13):
        key=f"{month:02d}";v=monthly.get(key);x=.10+(month-1)*.074
        ax.text(x+.028,.75,key,ha="center",fontsize=8,color=MUTED)
        c="#e8edf4" if v is None else (PROFIT if v>0 else LOSS if v<0 else PANEL)
        ax.add_patch(patches.FancyBboxPatch((x,.37),.055,.26,boxstyle="round,pad=.003,rounding_size=.009",facecolor=c,edgecolor="none",alpha=.65))
        label="—" if v is None else f"{v:+.1f}"
        ax.text(x+.028,.49,label,ha="center",va="center",fontsize=7.5,color=INK)
        if key in DATA["partial_months"]:ax.text(x+.052,.62,"*",fontsize=9,color=INK)
    ax.text(.10,.14,"— 未提供    * 不完整月示意；缺失不补零",color=MUTED,fontsize=8)
    ax2=axes(fig,[.61,.34,.35,.44])
    distribution=DATA["segment_distribution"]
    ax2.bar(distribution["centers_cny"],distribution["counts"],width=80,
            color=[PROFIT if x>0 else LOSS for x in distribution["centers_cny"]])
    ax2.set_xlabel("完整段净盈亏 / 元",color=MUTED,fontsize=8)
    ax2.set_ylabel("段数",color=MUTED);ax2.set_yticks([0,2,4]);ax2.set_ylim(0,5)
    for x,n in zip(distribution["centers_cny"],distribution["counts"]):ax2.text(x,n+.18,str(n),ha="center",fontsize=8,color=INK)
    fig.text(.61,.17,"胜率 62.5%（5 / 8） · 开放段 1 单列",color=INK,fontsize=8)
    fig.text(.61,.10,"平均净盈亏 −4.13 元 · 平均收益率未提供",color=MUTED,fontsize=8)
    save(fig,"figure05_monthly_segments",preview)

    fig = frame("06", "数据与运行信息 · 默认折叠")
    ax=fig.add_axes([.025,.17,.95,.63]);ax.axis("off")
    card(ax,.03,.40,.35,.37,"▸ 数据与运行信息\n同一 run · 默认折叠",INK)
    ax.annotate("展开",xy=(.49,.59),xytext=(.41,.59),color=MUTED,fontsize=9,arrowprops={"arrowstyle":"->","color":BLUE})
    card(ax,.53,.33,.43,.48,"Data 版本 / Feature / Signal 引用\nCore 与 Runtime 版本 / 账户水位\n质量与缺失说明",INK)
    ax.text(.015,.06,"主要限制保留短句；完整来源按需展开，不占满结果页面。",color=MUTED,fontsize=10)
    save(fig,"figure06_provenance",preview)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--preview-dir",type=Path)
    render(parser.parse_args().preview_dir)
