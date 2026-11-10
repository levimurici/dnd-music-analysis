#!/usr/bin/env node
// Renderiza um arquivo .abc em PDF usando abcjs + Chromium.
// Cada música (X:) começa numa página nova, e as quebras de página só caem
// entre sistemas, nunca cortando uma pauta ou a letra ao meio.
//
// Uso:
//   node scripts/render_pdf.js entrada.abc [saida.pdf]
//       -> um PDF só, uma música (X:) por página
//   node scripts/render_pdf.js musicas/x_sax.abc --separar partituras/
//       -> um PDF por instrumento: partituras/x_concerto.pdf, x_alto.pdf, x_tenor.pdf
//          (o instrumento vem do 2º T: de cada música; sem ele, conta como concerto.
//           O sufixo _sax do nome é retirado; outros sufixos ficam: x_escalas_alto.pdf)
//
// CHROMIUM_PATH: usa um Chromium/Chrome já instalado em vez do baixado pelo Playwright.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const PAGE_W = 718;   // largura útil de A4 com margem de 10 mm, em px CSS
const PAGE_H = 1040;  // altura útil de A4 com margem de 10 mm (com folga)

function instrumento(tune) {
  const titulos = tune.split('\n').filter(l => l.startsWith('T:')).map(l => l.slice(2).toLowerCase());
  const sub = titulos[1] || '';
  if (sub.includes('alto')) return 'alto';
  if (sub.includes('tenor')) return 'tenor';
  return 'concerto';
}

async function renderTunes(browser, abcjs, tunes, out) {
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
    warnings.forEach(w => console.warn(`AVISO abcjs (${path.basename(out)}, música ${i + 1}):`, w));
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
  await page.close();

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
  await pdfPage.close();
  console.log('PDF gerado:', out);
}

(async () => {
  const args = process.argv.slice(2);
  const iSep = args.indexOf('--separar');
  let dirSep = null;
  if (iSep >= 0) { dirSep = args[iSep + 1] || 'partituras'; args.splice(iSep, 2); }
  const input = args[0];
  if (!input) {
    console.error('Uso: node scripts/render_pdf.js entrada.abc [saida.pdf | --separar pasta/]');
    process.exit(1);
  }
  const abc = fs.readFileSync(input, 'utf8');
  const abcjs = fs.readFileSync(require.resolve('abcjs/dist/abcjs-basic-min.js'), 'utf8');
  const tunes = abc.split(/\n(?=X:)/).filter(t => t.trim());

  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  if (dirSep) {
    fs.mkdirSync(dirSep, { recursive: true });
    const base = path.basename(input).replace(/\.abc$/i, '').replace(/_sax$/, '');
    const grupos = {};
    for (const t of tunes) (grupos[instrumento(t)] ||= []).push(t);
    for (const [inst, ts] of Object.entries(grupos)) {
      await renderTunes(browser, abcjs, ts, path.join(dirSep, `${base}_${inst}.pdf`));
    }
  } else {
    await renderTunes(browser, abcjs, tunes, args[1] || input.replace(/\.abc$/i, '') + '.pdf');
  }
  await browser.close();
})();
