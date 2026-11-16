# -*- coding: utf-8 -*-
"""生成少量可打印的测试条形码（供扫码验证用），离线版：条码以 SVG 内嵌，不依赖 CDN。

从 products.json 中挑 8 个代表商品（覆盖主要过敏原 + 1 个安全商品），
用 python-barcode 渲染 CODE128 并内嵌为 SVG，生成 frontend/barcodes-test.html。
打印（Ctrl+P）后贴到商品上，即可用 App「扫码」验证识别 + 过敏提醒。

依赖： pip install python-barcode
用法： python scripts/generate_test_barcodes.py
"""
import json
import re
from pathlib import Path

import barcode
from barcode.writer import SVGWriter

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src" / "data" / "products.json"
OUT = HERE.parent / "barcodes-test.html"

TEST_ITEMS = [
    ("6901234567890", "花生过敏提醒"),
    ("6901234567892", "含大豆（卵磷脂）"),
    ("6901234567896", "含坚果（花生/腰果/杏仁）"),
    ("6901234567900", "含虾（甲壳类）"),
    ("6901234567924", "含芝麻"),
    ("6901234567925", "含海鲜（蚝油）"),
    ("6901234567938", "含蟹（甲壳类）"),
    ("6901234567897", "安全 · 无过敏原"),
]


def code128_svg(value: str) -> str:
    """渲染 CODE128 条码为可内联的 SVG 字符串（去掉 xml 头/DOCTYPE，注入 viewBox）。"""
    code = barcode.get("code128", value, writer=SVGWriter())
    opts = {"module_width": 0.3, "module_height": 15.0, "quiet_zone": 1.0, "write_text": False}
    svg = code.render(opts).decode("utf-8")
    start = svg.index("<svg")
    end = svg.rindex("</svg>") + len("</svg>")
    svg = svg[start:end]
    m = re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', svg)
    w, h = m.group(1), m.group(2)
    svg = re.sub(
        r"<svg[^>]*>",
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="none">',
        svg,
        count=1,
    )
    return svg


products = json.loads(SRC.read_text(encoding="utf-8"))
by_bc = {str(p["barcode"]): p for p in products}

labels = []
for bc, hint in TEST_ITEMS:
    p = by_bc.get(bc)
    if not p:
        print("WARN: barcode not found:", bc)
        continue
    meta = (p.get("brand", "") or "") + (" · " + p.get("category", "") if p.get("category") else "")
    hint_cls = "hint safe" if hint.startswith("安全") else "hint"
    labels.append(
        '<div class="label">'
        f'<div class="name">{p["name"]}</div>'
        f'<div class="meta">{meta}</div>'
        f'<div class="{hint_cls}">{hint}</div>'
        f"{code128_svg(bc)}"
        f'<div class="num">{bc}</div>'
        "</div>"
    )

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>智慧购物 · 扫码测试条码单</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; color: #222; }
  .toolbar { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #dcdcdc; padding: 14px 18px; display: flex; align-items: center; gap: 16px; z-index: 10; }
  .toolbar h1 { font-size: 16px; margin: 0; }
  .toolbar .hint { font-size: 12px; color: #666; }
  .toolbar button { margin-left: auto; padding: 9px 20px; background: #1989fa; color: #fff; border: 0; border-radius: 6px; font-size: 14px; cursor: pointer; }
  .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; padding: 18px; }
  .label { border: 1.5px solid #d0d0d0; border-radius: 10px; padding: 14px 14px 12px; display: flex; flex-direction: column; align-items: center; text-align: center; page-break-inside: avoid; break-inside: avoid; background: #fff; }
  .label .name { font-size: 15px; font-weight: 600; line-height: 1.3; min-height: 1.3em; }
  .label .meta { font-size: 12px; color: #888; margin: 2px 0 6px; }
  .label .hint { font-size: 12px; font-weight: 600; color: #c0392b; margin-bottom: 8px; }
  .label .hint.safe { color: #27ae60; }
  .label svg { width: 100%; height: 48px; }
  .label .num { font-family: Consolas, monospace; font-size: 12px; letter-spacing: 1px; color: #333; margin-top: 5px; }
  @media print {
    .toolbar { display: none; }
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .grid { grid-template-columns: repeat(2, 1fr); gap: 8mm; padding: 8mm; }
    .label { border-radius: 0; padding: 6mm 4mm; }
  }
  @page { size: A4; margin: 10mm; }
</style>
</head>
<body>
<div class="toolbar">
  <h1>扫码测试条码单</h1>
  <span class="hint">共 __COUNT__ 条 · 红色为预期过敏提醒 · 打印后贴到商品上，用 App「扫码」验证</span>
  <button onclick="window.print()">打印</button>
</div>
<div class="grid">
__LABELS__
</div>
</body>
</html>
"""

html = (
    HTML.replace("__COUNT__", str(len(labels)))
    .replace("__LABELS__", "\n".join(labels))
)

OUT.write_text(html, encoding="utf-8")
print("Generated: %s (%d items, offline SVG)" % (OUT, len(labels)))
