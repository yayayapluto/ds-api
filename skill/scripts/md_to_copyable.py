#!/usr/bin/env python3
"""md_to_copyable.py - ubah jawaban_LKP_Modul_X.md jadi HTML copyable per-sel.

Pakai: python3 md_to_copyable.py input.md [output.html]
Tiap sel tabel + tiap Q/A analisis + tiap baris list + tiap blok kode
dapat tombol `copy` (salin teks bersih sel itu saja, tanpa tombol).
Pola acuan: references/contoh_copyable.html (hasil Modul 4).
"""
import html
import pathlib
import re
import sys

CSS = """*{box-sizing:border-box}body{font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;max-width:1000px;margin:0 auto;padding:20px;line-height:1.55;color:#111}h1{font-size:1.5rem}h2{margin-top:2em;border-bottom:2px solid #111;padding-bottom:4px;font-size:1.2rem}h3{font-size:1.05rem;color:#333}blockquote{background:#f4f4f4;border-left:4px solid #333;margin:8px 0;padding:8px 12px}table{border-collapse:collapse;width:100%;font-size:.9rem;margin:12px 0}th,td{border:1px solid #999;padding:6px 8px;text-align:left;vertical-align:top}th{background:#eee}.tbl-wrap{overflow-x:auto}code{background:#f0f0f0;padding:1px 5px;border-radius:4px;font-size:.88em}.qa{border:1px solid #ccc;border-radius:8px;margin:10px 0;overflow:hidden}.q{background:#f7f7f7;padding:8px 10px;display:flex;gap:8px;align-items:flex-start;font-weight:600}.a{padding:8px 10px;display:flex;gap:8px;align-items:flex-start}.qn{color:#555;flex:none}.txt{flex:1;user-select:text}.cp,.cp-block{flex:none;font-size:.72rem;border:1px solid #888;background:#fff;border-radius:6px;padding:2px 8px;cursor:pointer}.cp:hover,.cp-block:hover{background:#111;color:#fff;border-color:#111}.codeblock{position:relative;background:#fafafa;border:1px solid #ccc;border-radius:8px;margin:12px 0}.codeblock pre{margin:0;padding:12px;overflow-x:auto}.cp-block{position:absolute;top:8px;right:8px}.li,.li-num,.chk,p.copyable{display:flex;gap:8px;align-items:flex-start;background:#fbfbfb;border:1px solid #e2e2e2;border-radius:6px;padding:6px 10px;margin:6px 0}.toolbar{position:sticky;top:0;background:#fff;border-bottom:2px solid #111;padding:10px 0;display:flex;gap:10px;align-items:center;z-index:10}#toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#111;color:#fff;padding:8px 18px;border-radius:20px;opacity:0;transition:opacity .2s;pointer-events:none}#toast.show{opacity:1}@media print{.cp,.cp-block,.toolbar{display:none}}"""

JS = """function txt(el){return el.innerText;}
function flash(msg){var t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');clearTimeout(t._x);t._x=setTimeout(function(){t.classList.remove('show');},1200);}
async function copyText(s){try{await navigator.clipboard.writeText(s);return true;}catch(e){var ta=document.createElement('textarea');ta.value=s;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');return true;}catch(_){return false;}finally{ta.remove();}}}
document.addEventListener('click',async function(ev){var b=ev.target.closest('.cp,.cp-block');if(!b)return;var wrap=b.closest('th,td,.q,.a,.li,.li-num,.chk,p.copyable,.codeblock');var t=wrap?wrap.querySelector('.txt,pre code'):null;var s=t?txt(t):'';if(!s.trim()){flash('Kosong');return;}var ok=await copyText(s);flash(ok?'Tersalin: '+s.slice(0,60):'Gagal menyalin');});"""


def inline(s):
    parts = re.split(r'(`[^`]+`)', s)
    out = ''
    for p in parts:
        if len(p) >= 2 and p.startswith('`') and p.endswith('`'):
            out += '<code>' + html.escape(p[1:-1]) + '</code>'
        else:
            e = html.escape(p)
            e = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', e)
            out += e
    return out


def convert(md):
    lines = md.splitlines()
    h = []
    i, n = 0, len(lines)
    in_code = False
    code_buf = []

    def emit_table(rows):
        hdr = [c.strip() for c in rows[0].strip().strip('|').split('|')]
        h.append('<div class="tbl-wrap"><table>')
        h.append('<thead><tr>')
        for c in hdr:
            h.append(f'<th><span class="txt">{inline(c)}</span>'
                     '<button class="cp" title="Salin sel">copy</button></th>')
        h.append('</tr></thead><tbody>')
        for r in rows[2:]:
            cells = [c.strip() for c in r.strip().strip('|').split('|')]
            h.append('<tr>')
            for c in cells:
                h.append(f'<td><span class="txt">{inline(c)}</span>'
                         '<button class="cp" title="Salin sel">copy</button></td>')
            h.append('</tr>')
        h.append('</tbody></table></div>')

    while i < n:
        ln = lines[i]
        if ln.strip().startswith('```'):
            if not in_code:
                in_code = True
                code_buf = []
            else:
                in_code = False
                h.append('<div class="codeblock"><button class="cp-block">'
                         'Salin kode</button><pre><code>'
                         + html.escape('\n'.join(code_buf)) + '</code></pre></div>')
            i += 1
            continue
        if in_code:
            code_buf.append(ln)
            i += 1
            continue
        if (re.match(r'^\|.*\|\s*$', ln) and i + 1 < n
                and re.match(r'^\|?[\s\-\:\|]+\|?\s*$', lines[i + 1])):
            j = i
            rows = []
            while j < n and re.match(r'^\|.*\|\s*$', lines[j]):
                rows.append(lines[j])
                j += 1
            emit_table(rows)
            i = j
            continue
        m = re.match(r'^(#{1,3})\s+(.*)', ln)
        if m:
            lv = len(m.group(1))
            h.append(f'<h{lv}>{inline(m.group(2))}</h{lv}>')
            i += 1
            continue
        if ln.startswith('>'):
            h.append(f'<blockquote>{inline(ln.lstrip("> "))}</blockquote>')
            i += 1
            continue
        if ln.strip() == '---':
            h.append('<hr>')
            i += 1
            continue
        m = re.match(r'^(\d+)\.\s+(.*)', ln)
        if m and '**' in ln:
            num, rest = m.group(1), m.group(2)
            ans = []
            j = i + 1
            while j < n:
                nxt = lines[j]
                if re.match(r'^\d+\.\s+', nxt) and '**' in nxt:
                    break
                if (re.match(r'^#{1,3}\s', nxt) or nxt.strip() == '---'
                        or nxt.startswith('>') or re.match(r'^\|.*\|\s*$', nxt)
                        or nxt.strip().startswith('```')):
                    break
                if nxt.strip() == '':
                    k = j + 1
                    while k < n and lines[k].strip() == '':
                        k += 1
                    if (k >= n or re.match(r'^(\d+\.\s+.*|#{1,3}\s|\|.*\||>.*|---)', lines[k])
                            or lines[k].strip().startswith('-')):
                        j = k
                        break
                    j += 1
                    continue
                if re.match(r'^[\-\*]\s+', nxt.strip()) or nxt.strip().startswith('- ['):
                    break
                ans.append(nxt.strip())
                j += 1
            a_text = ' '.join(ans).strip()
            h.append(f'<div class="qa"><div class="q"><span class="qn">{num}.</span> '
                     f'<span class="txt">{inline(rest)}</span><button class="cp">copy</button></div>')
            if a_text:
                h.append(f'<div class="a"><span class="txt">{inline(a_text)}</span>'
                         '<button class="cp">copy</button></div></div>')
            else:
                h.append('</div>')
            i = j
            continue
        if re.match(r'^\- \[x?\]', ln.strip()):
            h.append(f'<div class="chk"><span class="txt">{inline(ln.strip()[5:].strip())}</span>'
                     '<button class="cp">copy</button></div>')
            i += 1
            continue
        m3 = re.match(r'^[\-\*]\s+(.*)', ln.strip())
        if m3:
            h.append(f'<div class="li"><span class="txt">'
                     f'{inline(m3.group(1))}</span>'
                     '<button class="cp">copy</button></div>')
            i += 1
            continue
        if ln.strip() == '':
            i += 1
            continue
        m2 = re.match(r'^(\d+)\.\s+(.*)', ln)
        if m2:
            h.append(f'<div class="li-num"><span class="qn">{m2.group(1)}.</span> '
                     f'<span class="txt">{inline(m2.group(2))}</span>'
                     '<button class="cp">copy</button></div>')
            i += 1
            continue
        if (ln.strip().startswith('**') or ln.strip().startswith('Kompilasi')
                or ln.strip().startswith('Aturan') or ln.strip().startswith('Early')
                or ln.strip().startswith('Menggunakan')):
            h.append(f'<p class="copyable"><span class="txt">{inline(ln.strip())}</span>'
                     '<button class="cp">copy</button></p>')
            i += 1
            continue
        h.append(f'<p>{inline(ln.strip())}</p>')
        i += 1
    return '\n'.join(h)


def main():
    if len(sys.argv) < 2:
        print('Pakai: python3 md_to_copyable.py input.md [output.html]')
        sys.exit(2)
    src = pathlib.Path(sys.argv[1])
    md = src.read_text(encoding='utf-8')
    body = convert(md)
    title = html.escape(src.stem.replace('_', ' '))
    doc = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Copyable</title>
<style>{CSS}</style>
</head>
<body>
<div class="toolbar"><strong>{title} - versi copyable</strong><span style="font-size:.85rem;color:#555">Klik tombol copy di tiap sel / jawaban untuk salin teks bersih (tanpa tombol).</span></div>
{body}
<hr>
<p style="font-size:.85rem;color:#555">Sumber konten: <code>{html.escape(src.name)}</code> (1:1, hanya dibungkus tombol salin).</p>
<div id="toast"></div>
<script>{JS}</script>
</body>
</html>"""
    out = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + '_copyable.html')
    out.write_text(doc, encoding='utf-8')
    print(f'wrote {out} ({out.stat().st_size / 1024:.1f}KB, '
          f'{doc.count("copy</button>")} tombol)')


if __name__ == '__main__':
    main()
