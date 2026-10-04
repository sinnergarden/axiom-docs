"""Generate a self-contained review HTML from the authoritative docs draft.

Uses the already available Mistune renderer; never reads business artifacts.
"""
from __future__ import annotations

import argparse
import base64
from html import escape
from pathlib import Path
import re

import mistune

CSS = """
:root{color-scheme:light}body{max-width:1080px;margin:24px auto;padding:0 26px;
font:14px/1.65 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;
color:#25354a;background:#f5f7fb}h1{font-size:27px;margin:18px 0 10px}h2{font-size:19px;
margin:25px 0 10px}h3{font-size:17px;margin:22px 0 8px}p{margin:9px 0}li{margin:7px 0}
ul{padding-left:22px}strong{font-weight:650}a{color:#365f98}table{border-collapse:collapse;
width:100%;background:white;font-size:12px;margin:12px 0}th,td{text-align:left;
vertical-align:top;padding:10px;border:1px solid #dce3ed}th{background:#edf2f8}
figure{margin:14px 0 19px;background:white;border:1px solid #dce3ed;border-radius:6px;
overflow:hidden}figure img{display:block;width:100%;height:auto}figcaption{padding:5px 12px;
font-size:11px;color:#63738a}footer,.note{font-size:12px;color:#63738a}.layout-grid{display:grid;
grid-template-columns:1fr 1fr;gap:12px}details{margin:24px 0}summary{cursor:pointer;font-weight:600}
code{font-size:12px;word-break:break-all}footer{margin:24px 0}h2,h3{scroll-margin-top:15px}
@media(max-width:700px){body{padding:0 14px;font-size:13px}.layout-grid{grid-template-columns:1fr}
table{font-size:11px}td,th{padding:6px}}
@page{size:A4;margin:12mm}
@media print{body{max-width:none;margin:0;padding:0;background:white;font-size:10px;line-height:1.45}
h1{font-size:18px;margin:0 0 7px}h2{font-size:13px;margin:12px 0 6px}h3{font-size:11px;margin:9px 0 5px}
p{margin:5px 0}li{margin:5px 0}ul{padding-left:16px}table{font-size:9px;margin:6px 0}
th,td{padding:5px}figure{margin:6px 0;break-inside:avoid;border:0}figure img{max-height:30mm;
object-fit:contain}figcaption{font-size:8px;padding:2px 0}#F02,#F05,#section-5{break-before:page}
h2,h3{break-after:avoid}.layout-appendix{display:none}footer{font-size:8px;margin:8px 0}}
"""


def image_uri(path: Path) -> str:
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return "data:"+mime+";base64,"+base64.b64encode(path.read_bytes()).decode("ascii")


def render(source: Path, output: Path, revision: str, layouts: Path | None):
    repo = source.parents[2]
    text = source.read_text()
    body = mistune.create_markdown(plugins=["table"])(text)

    def figure(match):
        path, alt = match.groups()
        resolved = (source.parent/path).resolve()
        resolved.relative_to(repo)
        assert resolved.suffix == ".svg"
        return (f'<figure data-function="{alt[:3]}"><img src="{image_uri(resolved)}" '
                f'alt="{alt}"><figcaption>{alt}</figcaption></figure>')

    body = re.sub(r'<img src="([^"]+)" alt="([^"]*)"\s*/>', figure, body)
    assert body.count('data-function="F') == 6

    def link(match):
        ref = match.group(1)
        if ref.startswith(("https://", "http://", "#")):
            return match.group(0)
        parts = ref.split("#", 1)
        relative = (source.parent/parts[0]).resolve().relative_to(repo).as_posix()
        url = f"https://github.com/sinnergarden/axiom-docs/blob/{revision}/{relative}"
        if len(parts)>1:
            url += "#"+parts[1]
        return 'href="'+escape(url, quote=True)+'"'

    body = re.sub(r'href="([^"]+)"', link, body)
    body = re.sub(r'<h3>(F0[1-6]) (.*?)</h3>', r'<h3 id="\1">\1 \2</h3>', body)
    body = re.sub(r'<h2>([1-8]) (.*?)</h2>', r'<h2 id="section-\1">\1 \2</h2>', body)
    appendix = ""
    if layouts:
        images=[]
        for name, label in [("A-research-first.png", "A 研究总览草稿"),
                            ("B-chart-first.png", "B 交易下钻草稿")]:
            images.append(f'<figure><img src="{image_uri(layouts/name)}" alt="{label}">'
                          f'<figcaption>{label} · 合成布局示意，未批准</figcaption></figure>')
        appendix=('<details class="layout-appendix"><summary>附录 A/B 布局草稿</summary>'
                  '<p class="note">这些草稿辅助布局讨论，不是 PRD 正文或真实回测结果。'
                  '交互原型在随附 ZIP 的 layout-drafts 目录内；解压后打开 HTML。</p>'
                  '<div class="layout-grid">'+"".join(images)+'</div></details>')
    relative = source.relative_to(repo).as_posix()
    source_url = f"https://github.com/sinnergarden/axiom-docs/blob/{revision}/{relative}"
    footer=(f'<footer>生成自 <a href="{escape(source_url, quote=True)}">axiom-docs PRD 草案源稿</a>'
            f' · 源版本 {escape(revision[:12])}。图均为合成示意；正式 UI 未实现本提案。</footer>')
    html=('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
          'img-src data:; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
          '<title>Axiom 研究工作台 PRD 草案</title><style>'+CSS+'</style></head><body>'
          +body+appendix+footer+'</body></html>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--revision",required=True)
    parser.add_argument("--layout-dir",type=Path)
    args=parser.parse_args()
    render(args.source.resolve(),args.output,args.revision,args.layout_dir)
