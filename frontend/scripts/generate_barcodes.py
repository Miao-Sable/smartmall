# -*- coding: utf-8 -*-
"""生成可打印的商品条形码清单（供 App 扫码测试用）。

读取 src/data/products.json，生成 frontend/barcodes.html：
- 用 JsBarcode（CDN）在浏览器端渲染 CODE128 条形码（能编码任意 13 位数字串，与后端按条码精确匹配）；
- 每条商品一个标签：商品名 + 品牌/品类 + 条形码图 + 数字；
- 自带打印按钮与打印样式，打开后 Ctrl+P 即可输出，贴到商品上再扫码。

用法： python scripts/generate_barcodes.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src" / "data" / "products.json"
OUT = HERE.parent / "barcodes.html"

JSBARCODE_CDN = "https://cdn.jsdelivr.net/npm/jsbarcode@3.11.6/dist/JsBarcode.all.min.js"

products = json.loads(SRC.read_text(encoding="utf-8"))
products.sort(key=lambda p: (p.get("category", ""), p["id"]))
data_json = json.dumps(products, ensure_ascii=False)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>智慧购物 · 商品条形码打印清单</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 0; color: #222; }
  .toolbar { position: sticky; top: 0; background: #fff; border-bottom: 1px solid #dcdcdc; padding: 12px 16px; display: flex; align-items: center; gap: 16px; z-index: 10; }
  .toolbar h1 { font-size: 16px; margin: 0; }
  .toolbar .hint { font-size: 12px; color: #666; }
  .toolbar button { margin-left: auto; padding: 8px 18px; background: #1989fa; color: #fff; border: 0; border-radius: 6px; font-size: 14px; cursor: pointer; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 16px; }
  .label { border: 1px solid #dcdcdc; border-radius: 8px; padding: 10px 10px 8px; display: flex; flex-direction: column; align-items: center; text-align: center; page-break-inside: avoid; break-inside: avoid; background: #fff; }
  .label .name { font-size: 13px; font-weight: 600; line-height: 1.3; min-height: 2.6em; }
  .label .meta { font-size: 11px; color: #888; margin: 2px 0 8px; }
  .label svg { width: 100%; height: auto; }
  .label .num { font-family: Consolas, monospace; font-size: 11px; letter-spacing: 1px; color: #333; margin-top: 4px; }
  @media print {
    .toolbar { display: none; }
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .grid { grid-template-columns: repeat(2, 1fr); gap: 6mm; padding: 6mm; }
    .label { border-radius: 0; padding: 3mm 2mm; }
  }
  @page { size: A4; margin: 10mm; }
</style>
</head>
<body>
<div class="toolbar">
  <h1>商品条形码打印清单</h1>
  <span class="hint">共 __COUNT__ 条 · CODE128 条形码，贴到商品后即可用 App「扫码」识别</span>
  <button onclick="window.print()">打印</button>
</div>
<div class="grid" id="grid"></div>

<script src="__CDN__"></script>
<script>
const PRODUCTS = __DATA__;
const grid = document.getElementById('grid');
PRODUCTS.forEach(function (p) {
  var label = document.createElement('div');
  label.className = 'label';
  label.innerHTML =
    '<div class="name"></div>' +
    '<div class="meta"></div>' +
    '<svg class="bc"></svg>' +
    '<div class="num"></div>';
  label.querySelector('.name').textContent = p.name;
  label.querySelector('.meta').textContent = (p.brand || '') + (p.category ? ' · ' + p.category : '');
  label.querySelector('.num').textContent = p.barcode;
  grid.appendChild(label);
  try {
    JsBarcode(label.querySelector('.bc'), p.barcode, {
      format: 'CODE128', width: 2, height: 42, margin: 0,
      displayValue: false, lineColor: '#000'
    });
  } catch (e) {
    console.warn('barcode render failed:', p.barcode, e);
  }
});
</script>
</body>
</html>
"""

html = (
    HTML.replace("__CDN__", JSBARCODE_CDN)
    .replace("__DATA__", data_json)
    .replace("__COUNT__", str(len(products)))
)

OUT.write_text(html, encoding="utf-8")
print("Generated: %s (%d products)" % (OUT, len(products)))
