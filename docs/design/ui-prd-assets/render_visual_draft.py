# -*- coding: utf-8 -*-
"""Render a self-contained visual draft from explicit synthetic PRD inputs.

This is a design artifact: no owner loader, backend, account calculation or write API.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT / "illustration-data.json").read_text())

CSS = """
:root{--ink:#24364a;--muted:#7b8997;--line:#e7ecf1;--blue:#547da3;--gold:#b6955d;
--profit:#d48198;--loss:#6fa58f;--bg:#f4f6f8}*{box-sizing:border-box}body{margin:0;
background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,BlinkMacSystemFont,
'PingFang SC','Microsoft YaHei',sans-serif}button,select{font:inherit;color:inherit}
button{cursor:pointer}select{border:1px solid #dce5ec;border-radius:7px;padding:5px 6px;background:white;font-size:11px}
button:focus-visible,summary:focus-visible{outline:2px solid var(--blue)}
.shell{display:grid;grid-template-columns:240px minmax(0,1fr);max-width:1600px;margin:auto;
min-height:100vh}.sidebar{background:#fbfcfd;border-right:1px solid var(--line);padding:30px 20px}
.brand{font-size:21px;font-weight:680;letter-spacing:1px;margin-bottom:34px}.brand span{
font-size:11px;letter-spacing:0;color:var(--muted);display:block;font-weight:400}.small{
color:var(--muted);font-size:12px}.sidebar h2{font-size:12px;color:var(--muted);font-weight:500;
margin:22px 0 10px}.filter-row{display:flex;gap:6px;flex-wrap:wrap}.filter{border:1px solid
var(--line);padding:5px 10px;border-radius:20px;background:white;font-size:12px}.filter.active{
background:#e9eff5;color:var(--blue);border-color:#dce6ef}.group{margin:20px 0}.question{
font-size:13px;font-weight:600;margin-bottom:9px}.run{border-left:1px solid #d9e2ea;margin-left:5px;
padding:8px 8px 8px 14px;font-size:12px}.run.selected{border-left:3px solid var(--blue);
background:#edf2f7;border-radius:0 9px 9px 0;color:var(--blue)}.run span{display:block;color:
var(--muted);font-size:11px}.sidebar-foot{margin-top:45px;padding-top:20px;border-top:1px solid
var(--line)}main{padding:27px 38px 32px;min-width:0}.topline{display:flex;justify-content:space-between;
align-items:center;color:var(--muted);font-size:12px}.prototype{color:#8b6d47;background:#f5efe4;
border-radius:20px;padding:4px 11px}.hero{display:flex;justify-content:space-between;align-items:flex-start;
margin:23px 0 12px;gap:20px}h1{font-size:26px;letter-spacing:-.5px;margin:0 0 5px;font-weight:650}
p{margin:0}.pill{display:inline-block;border:1px solid var(--line);border-radius:20px;padding:3px 9px;
font-size:11px;color:var(--muted);background:white}.hero-actions{display:flex;gap:8px;padding-top:8px}
.btn{padding:7px 13px;border:1px solid #dce5ec;border-radius:8px;background:white;font-size:12px}
.btn.primary{background:var(--blue);border-color:var(--blue);color:white}.subline{font-size:12px;
color:var(--muted);margin-bottom:22px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);
gap:24px;padding:16px 4px 21px;border-bottom:1px solid var(--line)}.metric .label{color:var(--muted);
font-size:12px}.metric .value{font-size:26px;margin:3px 0;font-variant-numeric:tabular-nums;font-weight:570}
.metric .detail{font-size:11px;color:var(--muted)}.positive{color:var(--profit)}.negative{color:var(--loss)}
.tabs{display:flex;gap:24px;margin:20px 0 18px;border-bottom:1px solid var(--line)}.tab{border:0;
border-bottom:2px solid transparent;background:transparent;padding:0 0 11px;font-size:13px;color:var(--muted)}
.tab.active{color:var(--ink);border-bottom-color:var(--blue);font-weight:600}.pane{display:none}.pane.active{
display:block}.card{background:white;border:1px solid var(--line);border-radius:14px;padding:22px 24px;
box-shadow:0 4px 20px #273c5103;margin-bottom:16px}.card-top{display:flex;justify-content:space-between;
align-items:flex-start;gap:18px;margin-bottom:12px}h3{font-size:15px;font-weight:600;margin:0 0 3px}
.legend{display:flex;gap:15px;color:var(--muted);font-size:11px;align-items:center}.key:before{
content:'';display:inline-block;width:15px;height:2px;background:var(--blue);vertical-align:middle;margin-right:5px}
.key.bench:before{background:var(--gold)}svg{display:block;width:100%;height:auto;overflow:visible}
.note{font-size:11px;color:var(--muted);margin-top:12px}.comparison-controls{display:flex;gap:8px;
align-items:center;font-size:11px}.compare-chip{background:#f8f5ee;border:1px solid #ede3d2;border-radius:20px;
padding:4px 9px;font-size:11px;color:#9b7b42}.settings{color:var(--muted);font-size:12px;padding:0 4px;
margin:17px 0 20px}.settings summary{cursor:pointer}.settings p{margin-top:9px}.two-col{display:grid;
grid-template-columns:1.13fr 1fr;gap:16px}.two-col .card{min-width:0}.year-grid{display:grid;
grid-template-columns:43px repeat(12,minmax(0,1fr));gap:4px;margin:28px 0 16px;font-variant-numeric:tabular-nums}
.heat-scroll{overflow-x:auto}.year-grid{min-width:430px}.year-grid .month{color:var(--muted);text-align:center;font-size:10px;margin-bottom:4px}.heat-cell{
height:40px;border-radius:5px;display:flex;align-items:center;justify-content:center;background:#edf0f4;
color:#8b98a4;font-size:10px;white-space:nowrap}.heat-cell.up{background:#f4dce4;color:#a35470}
.heat-cell.down{background:#daece3;color:#468367}.heat-cell.partial{outline:1px dashed #bead8c;outline-offset:2px}
.year{font-size:11px;align-self:center;color:var(--muted)}.stat-pair{display:grid;grid-template-columns:1fr 1fr;
gap:18px;padding-top:15px;border-top:1px solid var(--line);margin-top:16px}.stat-pair strong{font-size:22px;
display:block;font-weight:570}.stat-pair span{font-size:11px;color:var(--muted)}.source-note{border-top:1px solid
var(--line);padding-top:13px;margin-top:14px;font-size:11px;color:var(--muted)}.data-info{background:white;
border:1px solid var(--line);border-radius:11px;padding:15px 20px;font-size:12px;margin-top:17px}
.data-info summary{cursor:pointer;color:var(--muted)}.data-info .facts{display:grid;grid-template-columns:
1fr 1fr;gap:14px;margin-top:17px;font-size:12px}.facts span{display:block;color:var(--muted);font-size:11px}
.trade-grid{display:grid;grid-template-columns:minmax(0,1fr) 230px;gap:22px}.trade-facts h4{font-size:13px;
margin:0 0 14px}.fact{margin-bottom:15px;font-size:13px}.fact span{display:block;font-size:11px;color:var(--muted)}
.trace{display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);margin:12px 0 20px}.trace b{
font-weight:500;background:#edf2f7;padding:4px 8px;border-radius:5px;color:var(--blue)}.signal-note{font-size:12px;
color:var(--muted);padding:18px 22px;border:1px dashed #d9e3eb;border-radius:10px}.run-note{font-size:11px;
color:var(--muted);margin:12px 4px 0}.toast{position:fixed;bottom:28px;right:35px;max-width:380px;color:white;
background:#34495d;padding:12px 18px;border-radius:10px;font-size:12px;display:none}a{color:var(--blue)}
@media(max-width:1000px){.shell{grid-template-columns:200px minmax(0,1fr)}main{padding:24px}.two-col{
grid-template-columns:1fr}.trade-grid{grid-template-columns:1fr}.trade-facts{display:grid;grid-template-columns:
1fr 1fr}.hero{display:block}.hero-actions{margin-top:10px}.year-grid{gap:3px}.metrics{gap:10px}}
@media(max-width:700px){.shell{display:block}.sidebar{display:none}main{padding:20px}.metrics{grid-template-columns:
1fr 1fr}.hero h1{font-size:22px}.card{padding:17px}.card-top{display:block}.comparison-controls{margin-top:10px}}
"""


def path(values, y0, height, low, high, x0=50, width=880):
    return " ".join(f"{'M' if i == 0 else 'L'}{x0+i*width/(len(values)-1):.2f},{y0+height-(v-low)*height/(high-low):.2f}" for i, v in enumerate(values))


def performance():
    lines=[]
    for value in [1.00,1.05,1.10,1.15]:
        y=30+190-(value-1)*190/.15
        lines.append(f'<line x1="50" x2="930" y1="{y}" y2="{y}" stroke="#edf1f5"/><text x="35" y="{y+4}" text-anchor="end" fill="#8b98a4" font-size="11">{value:.2f}</text>')
    for x,t in [(50,'03月'),(343,'04月'),(637,'06月'),(930,'08月')]:
        lines.append(f'<text x="{x}" y="330" text-anchor="middle" fill="#8b98a4" font-size="11">{t}</text>')
    nav=path(D['nav'],30,190,1,.15+1)
    bench=path(D['baseline'],30,190,1,.15+1)
    dd=path(D['drawdown'],263,48,-10,0)
    return f'<svg viewBox="0 0 960 345" role="img" aria-label="合成净值与回撤，同一时间轴"><defs><linearGradient id="dd-fill" x2="0" y2="1"><stop stop-color="#6fa58f" stop-opacity=".24"/><stop offset="1" stop-color="#6fa58f" stop-opacity=".05"/></linearGradient></defs>{"".join(lines)}<text x="50" y="14" font-size="11" fill="#8b98a4">净值指数 · 保存值示意</text><path d="{nav}" fill="none" stroke="#547da3" stroke-width="2.5"/><path id="benchmark-path" d="{bench}" fill="none" stroke="#b6955d" stroke-width="1.8" stroke-dasharray="5 5"/><line x1="50" x2="930" y1="263" y2="263" stroke="#edf1f5"/><path d="{dd} L930,263 L50,263 Z" fill="url(#dd-fill)"/><path d="{dd}" fill="none" stroke="#6fa58f" stroke-width="1.5"/><text x="35" y="266" text-anchor="end" fill="#8b98a4" font-size="10">0%</text><text x="35" y="313" text-anchor="end" fill="#8b98a4" font-size="10">−10%</text><text x="50" y="250" fill="#8b98a4" font-size="11">回撤</text></svg>'


def heatmap():
    result=['<div class="year-grid"><div></div>']
    result.extend(f'<div class="month">{m:02d}</div>' for m in range(1,13))
    result.append(f'<div class="year">{D["month_year"]}</div>')
    monthly=dict(D['months'])
    for m in range(1,13):
        k=f'{m:02d}';value=monthly.get(k)
        cls='' if value is None else ' up' if value>0 else ' down' if value<0 else ''
        if k in D['partial_months']:cls+=' partial'
        label='—' if value is None else f'{value:+.1f}%'
        result.append(f'<div class="heat-cell{cls}" title="{D["month_year"]}-{k} 合成保存值；缺失不补零">{label}</div>')
    return '<div class="heat-scroll">'+''.join(result)+'</div></div>'


def distribution():
    bars=[]
    for i,(value,count) in enumerate(zip(D['segment_distribution']['centers_cny'],D['segment_distribution']['counts'])):
        x=55+i*85;h=count*23;color='#d48198' if value>0 else '#6fa58f'
        bars.append(f'<rect x="{x}" y="{125-h}" width="54" height="{h}" rx="4" fill="{color}" opacity=".76"/><text x="{x+27}" y="{119-h}" text-anchor="middle" fill="#7b8997" font-size="11">{count}</text><text x="{x+27}" y="147" text-anchor="middle" fill="#8b98a4" font-size="10">{value}</text>')
    return f'<svg viewBox="0 0 420 165" role="img" aria-label="合成完整持仓段净盈亏分布"><line x1="45" x2="390" y1="125" y2="125" stroke="#e7ecf1"/>{"".join(bars)}<text x="389" y="162" text-anchor="end" fill="#8b98a4" font-size="10">净盈亏 / 元（区间中心）</text></svg>'


def candles():
    marks=[]
    def to_y(v):return 220-(v-5.5)*160/1.6
    for v in [5.5,6.0,6.5,7.0]:
        y=to_y(v)
        marks.append(f'<line x1="45" x2="700" y1="{y}" y2="{y}" stroke="#edf1f5"/><text x="37" y="{y+3}" text-anchor="end" fill="#8b98a4" font-size="9">{v:.1f}</text>')
    marks.append('<text x="45" y="22" fill="#8b98a4" font-size="10">价格 · 元 / 份</text>')
    for span in D['holding_spans']:
        start=50+span['start_index']*10.7;end=50+span['end_index']*10.7
        marks.append(f'<rect x="{start}" y="35" width="{end-start}" height="190" rx="4" fill="#547da3" opacity=".04"/><text x="{(start+end)/2}" y="43" text-anchor="middle" fill="#8b98a4" font-size="9">{span["label"]} · 合成持有区间</text>')
    for i,row in enumerate(D['candles']):
        x=50+i*10.7
        c='#d48198' if row['close']>=row['open'] else '#6fa58f'
        marks.append(f'<line x1="{x}" x2="{x}" y1="{to_y(row["high"])}" y2="{to_y(row["low"])}" stroke="{c}"/><rect x="{x-2.8}" y="{min(to_y(row["open"]),to_y(row["close"]))}" width="5.6" height="{max(abs(to_y(row["close"])-to_y(row["open"])),1)}" fill="{c}"/>')
        marks.append(f'<rect x="{x-2.5}" y="{315-row["volume"]*.16}" width="5" height="{row["volume"]*.16}" fill="{c}" opacity=".5"/>')
    for i,e in enumerate(D['events']):
        x=50+e['index']*10.7;y=to_y(float(e['price']))
        marks.append(f'<g class="event" data-event="{i}" tabindex="0" role="button" aria-label="选择合成成交 {i+1}" style="cursor:pointer"><circle cx="{x}" cy="{y}" r="11" fill="#f2f6fb" stroke="#547da3"/><text x="{x}" y="{y+4}" text-anchor="middle" font-size="10" fill="#547da3">{e["label"]}</text></g>')
    for i,label in [(0,'03月'),(20,'05月'),(40,'07月'),(59,'08月')]:
        marks.append(f'<text x="{50+i*10.7}" y="340" text-anchor="middle" fill="#8b98a4" font-size="10">{label}</text>')
    marks.append('<text x="45" y="271" fill="#8b98a4" font-size="10">成交量 · 合成单位</text>')
    return f'<svg viewBox="0 0 710 360" role="img" aria-label="合成K线、成交量、持有区间与成交点">{"".join(marks)}</svg>'


def render(output: Path, revision: str):
    e=D['evaluation']
    content=f"""
<aside class="sidebar">
<div class="brand">AXIOM<span>研究工作台 · 视觉设计</span>
</div>
<h2>研究问题</h2>
<div class="filter-row">
<button class="filter active" data-filter="近期">近期</button>
<button class="filter" data-filter="收藏">收藏</button>
<button class="filter" data-filter="搁置">搁置</button>
</div>
<h2>标签 / 状态</h2>
<div class="filter-row">
<select aria-label="标签筛选">
<option>全部标签</option>
<option>ETF · 动量</option>
</select>
<select aria-label="状态筛选">
<option>全部状态</option>
<option>保存结果</option>
<option>失败 / 阻断</option>
</select>
</div>
<div class="group">
<div class="question">01 动量能否更稳？</div>
<div class="run selected">v2 · run 02 <span>近期 · 收藏 · 保存结果</span>
</div>
<div class="run">v1 · run 01 <span>负结果 · 保留</span>
</div>
</div>
<div class="group">
<div class="question">02 模型信号值得保留吗？</div>
<div class="run">v1 · run 03 <span>失败 · 搁置</span>
</div>
<div class="run">v1 · run 04 <span>状态缺证 · 阻断</span>
</div>
</div>
<div class="sidebar-foot small">按问题 → 版本 → 运行<br>记录和标记由 Research 提供</div>
</aside>
<main>
<div class="topline">
<span>研究问题 01 <span aria-hidden="true"> / </span> 实验 v2 <span aria-hidden="true"> / </span> run 02</span>
<span class="prototype">视觉草案 · 全部为合成示例</span>
</div>
<div class="hero">
<div>
<h1>动量轮动，让退出更稳一点</h1>
<p class="small">本轮仅改变退出条件 · 看改善是否伴随更高成本</p>
</div>
<div class="hero-actions">
<button class="btn" id="old-version">＋ 旧版对照</button>
<button class="btn primary" id="summary-copy">复制讨论摘要</button>
</div>
</div>
<div class="subline">2026.03 — 2026.08 <span class="pill">实验 v2 · run 02</span> <span class="pill">日线执行假设 · 示例</span> <span class="pill">数据版本固定</span>
</div>
<p class="small" style="margin-bottom:10px">各面板为独立合成图例；页签只演示界面联动，不是同一账户的验收结果。</p>
<div class="metrics">
<div class="metric">
<div class="label">期间收益</div>
<div class="value positive">{e['total_return']}
</div>
<div class="detail">账户含费用 / 分红口径示意</div>
</div>
<div class="metric">
<div class="label">最大回撤</div>
<div class="value negative">{e['max_drawdown']}
</div>
<div class="detail">Engine 保存原值</div>
</div>
<div class="metric">
<div class="label">总费用</div>
<div class="value">¥ {e['fees']}
</div>
<div class="detail">现金口径 · 元</div>
</div>
<div class="metric">
<div class="label">闭合段胜率</div>
<div class="value">{e['win_rate']}
</div>
<div class="detail">{e['wins']} / {e['closed_segments']} · 开放段另列</div>
</div>
</div>
<nav class="tabs" aria-label="结果视图">
<button class="tab active" data-pane="performance">收益与风险</button>
<button class="tab" data-pane="trade">交易复盘</button>
<button class="tab" data-pane="statistics">月收益与持仓段</button>
</nav>
<section class="pane active" id="performance">
<div class="card">
<div class="card-top">
<div>
<h3>收益与风险 <span class="small"> / 回测结果对比</span>
</h3>
<div class="legend">
<span class="key">当前 v2</span>
<span class="key bench" id="bench-legend">沪深300 · 合成</span>
</div>
</div>
<div class="comparison-controls">
<button class="compare-chip" id="bench-toggle" aria-pressed="true">沪深300 ×</button>
<span class="small">同一图，加入对照即比较</span>
</div>
</div>{performance()}
<div class="note">沪深300为已确认市场基准；本图为合成曲线，具体价格 / 全收益系列待核实，未宣称公平收益对比。</div>
</div>
<details class="settings">
<summary>共用配置 · 当前一致</summary>
<p>区间 / 初始资金 / 费用 / 滑点由 Research 固定；具体配置仅示意，不在此启动回测。遇到差异时只提示不同字段。</p>
</details>
<div class="signal-note">主要限制保持可见：日线执行假设不能代表开盘流动性或实盘保证。曲线与各统计面板为独立合成图例，不是一次已完成回测。</div>
</section>
<section class="pane" id="statistics">
<div class="two-col">
<div class="card">
<h3>年份 × 月份收益率</h3>
<p class="small">账户月收益 · 百分比</p>{heatmap()}
<p class="note">虚线：不完整月示意　—：未提供，不能补零</p>
<div class="source-note">Engine 保存月收益；点击月份可定位同一运行的净值和交易区间。</div>
</div>
<div class="card">
<h3>完整持仓段盈亏分布</h3>
<p class="small">8 个闭合段 · 费用 / 分红归入净盈亏</p>{distribution()}
<div class="stat-pair">
<div>
<strong>{e['win_rate']}
</strong>
<span>盈利 5 / 闭合 8 · 开放 1 单列</span>
</div>
<div>
<strong>−4.13 <span>元</span>
</strong>
<span>平均段净盈亏 · 合成示例</span>
</div>
</div>
<p class="note">平均段收益率：未提供（资金分母尚未冻结）</p>
</div>
</div>
<div class="signal-note">
<strong>信号评价 · 按策略适用性展示</strong>
<br>IC / Rank IC / ICIR 由 Research 提供。当前示例未保存成熟标签评估，因此没有数值；信号评价不替代账户收益。</div>
</section>
<section class="pane" id="trade">
<div class="card">
<div class="card-top">
<div>
<h3>交易复盘 <span class="small"> / 示例 ETF</span>
</h3>
<div class="small">点 B / S 查看当时保存记录</div>
</div>
<span class="pill">交易图例 · 独立合成行情</span>
</div>
<div class="trade-grid">
<div>{candles()}
<div class="trace">
<b>信号</b> → <b>决策</b> → <b>委托</b> → <b>成交</b>
</div>
<p class="note">原始价量与交易日区分。图例不证明真实日历或交易核算；正式点查需 owner 固定投影。</p>
</div>
<div class="trade-facts">
<h4 id="event-title">B · 首次建仓</h4>
<div class="fact">
<span>成交价 / 份额</span>
<b id="event-price">5.9400 / 1000</b>
</div>
<div class="fact">
<span>费用 · 元</span>
<b id="event-fee">5.00</b>
</div>
<div class="fact">
<span>保存的信号</span>
<div id="event-signal">20 日动量排名 1</div>
</div>
<div class="fact">
<span>执行原因</span>
<div id="event-reason">首次建仓 · 设计示例</div>
</div>
</div>
</div>
<details class="settings">
<summary>决策 debug · 低优先级后续增强</summary>
<p>当时特征 / 模型分数与版本 / 排名 / 门槛 / 买卖触发 / 执行依据，仅读取保存链。本示例未保存完整 debug，不生成事后解释。</p>
</details>
</div>
</section>
<details class="data-info">
<summary>数据与运行信息 <span class="small"> · 数据版本 / 运行身份 / 保存来源</span>
</summary>
<div class="facts">
<div>
<span>实验 / 运行</span>synthetic:experiment-v2 / synthetic:run-02</div>
<div>
<span>Data / Feature / Signal</span>synthetic:data-v2 / feature-v2 / signal-v2</div>
<div>
<span>Core / Runtime</span>设计字段示意 · 不是实际版本验收</div>
<div>
<span>质量与缺失</span>账户月收益、平均收益率及 trace 需 owner 投影</div>
</div>
</details>
<p class="run-note">只读视觉草案，未实现正式工作台。<a href="https://github.com/sinnergarden/axiom-docs/blob/{escape(revision)}/docs/design/08_axiom_ui_research_prd_draft.md">统一设计源稿</a> · 无后台调用或数据写入。</p>
</main>
<div class="toast" role="status" id="toast">
</div>
"""
    script="""
const events=EVENTS;const toast=document.getElementById('toast');
function message(s){toast.textContent=s;toast.style.display='block';setTimeout(()=>toast.style.display='none',2800)}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab,.pane').forEach(e=>e.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.pane).classList.add('active')});
document.getElementById('bench-toggle').onclick=function(){const on=this.getAttribute('aria-pressed')==='true';this.setAttribute('aria-pressed',String(!on));this.textContent=on?'＋ 沪深300':'沪深300 ×';document.getElementById('benchmark-path').style.display=on?'none':'';document.getElementById('bench-legend').style.display=on?'none':'';message(on?'单运行表现：仍为同一图与指标区':'回测结果对比：加入合成市场参考，具体系列待核实')};
document.getElementById('old-version').onclick=()=>message('旧版对照需 Research 关联及 Engine 保存结果；本示例未提供曲线。');
document.getElementById('summary-copy').onclick=()=>message('摘要示意：问题 01 / v2 / run 02 / 退出条件变动。正式复制入口尚未实现。');
document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filter').forEach(e=>e.classList.remove('active'));b.classList.add('active');message('展示 Research 已保存的'+b.dataset.filter+'标记；合成列表仅演示视觉状态。')});
document.querySelectorAll('select').forEach(e=>e.onchange=()=>message('筛选设计示意；不修改研究记录或运行。'));
document.querySelectorAll('.event').forEach(g=>{const pick=()=>{const e=events[Number(g.dataset.event)];document.getElementById('event-title').textContent=e.label+' · 保存成交';document.getElementById('event-price').textContent=e.price+' / '+e.quantity;document.getElementById('event-fee').textContent=e.fee;document.getElementById('event-signal').textContent=e.signal;document.getElementById('event-reason').textContent=e.reason;};g.onclick=pick;g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();pick()}}});
""".replace('EVENTS',json.dumps(D['events'],ensure_ascii=False))
    html='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'"><title>Axiom 工作台 · 视觉草案</title><style>'+CSS+'</style></head><body><div class="shell">'+content+'</div><script>'+script+'</script></body></html>'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--revision',required=True)
    args=parser.parse_args()
    render(args.output,args.revision)
