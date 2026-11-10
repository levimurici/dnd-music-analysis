#!/usr/bin/env node
// Converte um estudo .md em PDF A4 legível em tablet e bom para imprimir.
// Uso: node scripts/render_estudo.js estudos/x_estudo.md [saida.pdf]   (padrão: mesmo nome, .pdf)
// Requer: npm install (na raiz do repositório)
const fs = require('fs');
const { marked } = require('marked');
const { chromium } = require('playwright');

(async () => {
  const input = process.argv[2];
  if (!input) { console.error('Uso: node render_estudo.js entrada.md [saida.pdf]'); process.exit(1); }
  const out = process.argv[3] || input.replace(/\.md$/i, '') + '.pdf';
  const body = marked.parse(fs.readFileSync(input, 'utf8'));
  const html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
    @page { size: A4; margin: 16mm 15mm 18mm; }
    body { font-family: "Noto Serif", Georgia, serif; font-size: 11.5pt; line-height: 1.5; color: #1d1d1f; }
    h1 { font-size: 21pt; line-height: 1.2; margin: 0 0 10pt; }
    h2 { font-size: 15.5pt; margin: 22pt 0 6pt; padding-bottom: 3pt; border-bottom: 1.5pt solid #2f5d8a; color: #2f5d8a; break-after: avoid; }
    h3 { font-size: 12.5pt; margin: 14pt 0 4pt; break-after: avoid; }
    h2 + *, h3 + * { break-before: avoid; }
    p, li { orphans: 3; widows: 3; }
    hr { border: 0; break-after: page; margin: 0; }
    code { font-family: "Noto Sans Mono", monospace; font-size: 9.5pt; background: #f1f3f6; padding: 0 2pt; border-radius: 2pt; }
    table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; font-family: "Noto Sans", Arial, sans-serif; font-size: 9.5pt; line-height: 1.35; }
    thead { display: table-header-group; }
    th { background: #e8eef5; text-align: left; font-weight: 600; }
    th, td { border: 0.6pt solid #b9c3cf; padding: 3pt 5pt; vertical-align: top; }
    tr { break-inside: avoid; }
    tbody tr:nth-child(even) td { background: #f8fafc; }
    strong { color: #111; }
  </style></head><body>${body}</body></html>`;
  // CHROMIUM_PATH: usa um Chromium/Chrome já instalado em vez do baixado pelo Playwright
  const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: 'load' });
  await page.pdf({ path: out, format: 'A4', printBackground: true,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8pt;width:100%;text-align:center;color:#777"><span class="pageNumber"></span> / <span class="totalPages"></span></div>' });
  await browser.close();
  console.log('PDF gerado:', out);
})();
