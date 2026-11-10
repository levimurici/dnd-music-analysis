#!/usr/bin/env bash
# Prepara o ambiente em uma chamada só. Idempotente: pula o que já está instalado.
# Uso (da raiz do repo): bash scripts/setup.sh
set -e
cd "$(dirname "$0")/.."

py() {
  python3 -c "import music21" 2>/dev/null && return 0
  pip install -q -r requirements.txt
}

js() {
  if [ -d node_modules/abcjs ] && [ -d node_modules/marked ] && [ -d node_modules/playwright ]; then return 0; fi
  # Se já existe um Chromium no sistema, não baixa outro (scripts/chromium.js o encontra).
  if node -e "const o=require('./scripts/chromium').launchOptions({executablePath(){return ''}});process.exit(o.executablePath?0:1)" 2>/dev/null; then
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --no-bin-links --ignore-scripts --no-audit --no-fund --silent
  else
    npm install --no-bin-links --no-audit --no-fund --silent
  fi
}

py & P=$!
js & J=$!
wait $P && wait $J
echo "ambiente pronto"
