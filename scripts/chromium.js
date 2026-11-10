// Acha um Chromium para o Playwright sem precisar configurar nada.
// Ordem: CHROMIUM_PATH > browser baixado pelo próprio Playwright > Chromium/Chrome já instalado no sistema.
const fs = require('fs');
const { execSync } = require('child_process');

function launchOptions(chromium) {
  if (process.env.CHROMIUM_PATH) return { executablePath: process.env.CHROMIUM_PATH };
  try { if (fs.existsSync(chromium.executablePath())) return {}; } catch (e) { /* sem browser do Playwright */ }
  const candidatos = ['/opt/pw-browsers/chromium', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  for (const c of candidatos) if (fs.existsSync(c) && fs.statSync(c).isFile()) return { executablePath: c };
  for (const cmd of ['chromium', 'chromium-browser', 'google-chrome']) {
    try { const p = execSync(`command -v ${cmd}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim(); if (p) return { executablePath: p }; } catch (e) { /* não achou */ }
  }
  return {}; // deixa o Playwright dar a mensagem de erro dele
}

module.exports = { launchOptions };
