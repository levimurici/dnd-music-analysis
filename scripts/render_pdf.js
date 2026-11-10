#!/usr/bin/env node
// Renderiza um arquivo .abc em PDF usando abcjs + Chromium.
// Cada música (X:) começa numa página nova, e as quebras de página só caem
// entre sistemas, nunca cortando uma pauta ou a letra ao meio.
// Uso: node scripts/render_pdf.js entrada.abc [saida.pdf]
const fs = require('fs');
const { chromium } = require('playwright');

const PAGE_W = 718;   // largura útil de A4 com margem de 10 mm, em px CSS
const PAGE_H = 1040;  // altura útil de A4 com margem de 10 mm (com folga)

(async () => {
  const input = process.argv[2];
  if (!input) { console.error('Uso: node scripts/render_pdf.js entrada.abc [saida.pdf]'); process.exit(1); }
  const out = process.argv[3] || input.replace(/\.abc$/i, '') + '.pdf';
  const abc = fs.readFileSync(input, 'utf8');
  const abcjs = fs.readFileSync(require.resolve('abcjs/dist/abcjs-basic-min.js'), 'utf8');
  const tunes = abc.split(/\n(?=X:)/).filter(t => t.trim());

  // CHROMIUM_PATH: usa um Chromium/Chrome já instalado em vez do baixado pelo Playwright
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  // 1) desenha cada música com um SVG por sistema e fotografa cada sistema
  const page = await browser.newPage({ viewport: { width: PAGE_W, height: 1000 }, deviceScaleFactor: 3 });
  const pages = [];
  for (let i = 0; i < tunes.length; i++) {
    await page.setContent(`<!doctype html><html><head><meta charset="utf-8">
      <style>body{margin:0;background:#fff} svg{display:block}</style>
      <script>${abcjs}</script></head><body><div id="t"></div></body></html>`);
    const warnings = await page.evaluate((t) => {
      const r = ABCJS.renderAbc('t', t, { staffwidth: 680, add_classes: true, oneSvgPerLine: true });
      return (r[0].warnings || []).map(w => w.replace(/<[^>]+>/g, ''));
    }, tunes[i]);
    warnings.forEach(w => console.warn(`AVISO abcjs (música ${i + 1}):`, w));
    const lines = [];
    for (const el of await page.$$('#t svg')) {
      const box = await el.boundingBox();
      if (!box || box.height < 2) continue;
      lines.push({ h: box.height, png: (await el.screenshot()).toString('base64') });
    }
    // 2) distribui os sistemas em páginas sem cortá-los
    let cur = [], used = 0;
    for (const ln of lines) {
      if (used + ln.h > PAGE_H && cur.length) { pages.push(cur); cur = []; used = 0; }
      cur.push(ln); used += ln.h;
    }
    if (cur.length) pages.push(cur);
  }

  // 3) monta o PDF
  const html = `<!doctype html><html><head><meta charset="utf-8"><style>
    @page { size: A4; margin: 10mm; } body { margin: 0; }
    .pg { break-after: page; } .pg:last-child { break-after: auto; }
    img { display: block; width: ${PAGE_W}px; }
  </style></head><body>${pages.map(p => `<div class="pg">${p.map(l =>
    `<img style="height:${l.h}px" src="data:image/png;base64,${l.png}">`).join('')}</div>`).join('')}</body></html>`;
  const pdfPage = await browser.newPage();
  await pdfPage.setContent(html, { waitUntil: 'load' });
  await pdfPage.pdf({ path: out, format: 'A4', printBackground: true });
  await browser.close();
  console.log('PDF gerado:', out);
})();
