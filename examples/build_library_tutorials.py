"""Bundle the two saved HTML tutorials for one offline Library file.

Notebook prose, code and outputs remain canonical. This only wraps generated
HTML, keeps role/chapter navigation in one file and fixes public source links.
"""
import argparse
import hashlib
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit


class PreText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pre = False
        self.current = []
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.in_pre = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_pre = False
            self.blocks.append("".join(self.current))

    def handle_data(self, data):
        if self.in_pre:
            self.current.append(data)


def role_body(document, role, source_ref):
    base = f"https://github.com/sinnergarden/axiom-docs/blob/{source_ref}/"
    body = re.search(r"<body>([\s\S]*)</body>", document).group(1)
    body = re.sub(r'(?<=\s)id="([^"]+)"', lambda m: f'id="{role}-{m[1]}"', body)

    def link(match):
        url = match[1]
        if url.startswith("#"):
            return f'href="#{role}-{url[1:]}"'
        parsed = urlsplit(url)
        if parsed.path in ("researcher_tutorial.html", "developer_tutorial.html"):
            target_role = parsed.path.split("_")[0]
            anchor = parsed.fragment or "section-1"
            return f'href="#{target_role}-{anchor}" data-role-target="{target_role}"'
        if not parsed.scheme and not url.startswith("/"):
            # Generated tutorials live in notebooks/ relative to the repo root.
            path = parsed.path[3:] if parsed.path.startswith("../") else "notebooks/" + parsed.path
            url = base + path + ("#" + parsed.fragment if parsed.fragment else "")
        return f'href="{escape(url, quote=True)}" target="_blank" rel="noopener"'

    body = re.sub(r'(?<=\s)href="([^"]+)"', link, body)
    before = PreText(); before.feed(document)
    after = PreText(); after.feed(body)
    if before.blocks != after.blocks:
        raise ValueError("saved code/output text changed while bundling")
    return body


def build(source_root, source_ref, output):
    commit = subprocess.check_output(["git", "rev-parse", source_ref + "^{commit}"],
                                     cwd=source_root, text=True).strip()
    documents = {}
    for role in ("researcher", "developer"):
        relative = f"notebooks/{role}_tutorial.html"
        local = (source_root / relative).read_bytes()
        committed = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=source_root)
        if local != committed:
            raise ValueError(f"{relative} does not match the declared commit")
        documents[role] = local.decode("utf-8")
    styles = re.findall(r"<style>([\s\S]*?)</style>", documents["researcher"])[0]
    styles += """
.library-banner{padding:16px 24px}.library-banner h1{font-size:22px;margin:0}
.role-tabs{padding:10px 24px;background:white;display:flex;gap:10px;border-bottom:1px solid #dfe6ee}
.role-tabs button{font:inherit;padding:7px 14px;cursor:pointer;border:1px solid #c6d6e4;border-radius:6px;background:white;color:#213e59}
.role-tabs button[aria-selected="true"]{color:white;background:#176c9e}article[hidden]{display:none}
"""
    base = f"https://github.com/sinnergarden/axiom-docs/blob/{commit}/"
    banner = f'''<header class="library-banner"><h1>Axiom · 研究与数据接入教程</h1>
<p>从取表到重复实验，从接入到发布与恢复。两份教程使用保存输出。</p>
<p><a href="{base}docs/current-delivery.md" target="_blank" rel="noopener">当前交付</a> ·
<a href="{base}versions.json" target="_blank" rel="noopener">版本与执行范围</a></p></header>
<div class="role-tabs" role="tablist" aria-label="选择教学角色">
<button data-role="researcher" role="tab" aria-selected="true" aria-controls="researcher">Quant Researcher</button>
<button data-role="developer" role="tab" aria-selected="false" aria-controls="developer">Quant Developer</button></div>'''
    script = '''function chooseRole(role){document.querySelectorAll('article[data-role]').forEach(function(a){a.hidden=a.dataset.role!==role;});document.querySelectorAll('button[data-role]').forEach(function(b){b.setAttribute('aria-selected',String(b.dataset.role===role));});if(typeof markWideTables==='function')markWideTables();}
document.querySelectorAll('button[data-role]').forEach(function(b){b.addEventListener('click',function(){chooseRole(b.dataset.role);location.hash=b.dataset.role;});});
function showAnchor(){var id=decodeURIComponent(location.hash.slice(1));var role=id.split('-')[0];if(role==='researcher'||role==='developer'){chooseRole(role);var target=document.getElementById(id);if(target){for(var p=target;p;p=p.parentElement){if(p.tagName==='DETAILS')p.open=true;}target.scrollIntoView();}}}
document.querySelectorAll('[data-role-target]').forEach(function(a){a.addEventListener('click',function(){chooseRole(a.dataset.roleTarget);});});window.addEventListener('hashchange',showAnchor);showAnchor();'''
    articles = "".join(f'<article id="{role}" data-role="{role}"'+(' hidden' if role=="developer" else '')+">"+
                       role_body(documents[role], role, commit)+"</article>" for role in documents)
    result = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Axiom 教程</title><style>'+styles+'</style></head><body>'+banner+articles+'<script>'+script+'</script></body></html>'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result)
    return {"docs_commit": commit, "size_bytes": output.stat().st_size,
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", required=True, help="Committed source ref matching the saved HTML")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(build(Path(__file__).resolve().parents[1], args.source_ref, args.output))
