# dnd-music-analysis

Análise de partituras para estudo de **saxofone alto e tenor**, pronta para rodar dentro de um agente
local (Claude Code ou qualquer agente que leia `CLAUDE.md`/`AGENTS.md`).

Você entrega uma lead sheet em tom de concerto (PDF, foto ou ABC) e o agente devolve:

- a partitura transposta para **sax alto (E♭)** e **sax tenor (B♭)**, com as cifras em concerto, um PDF por instrumento em `partituras/` (`_concerto.pdf`, `_alto.pdf`, `_tenor.pdf`);
- um **estudo explicado** com análise tonal, funcional e melódica (`estudos/<nome>_estudo.pdf`);
- **alternativas de improvisação** por trecho e a folha de escalas escrita para alto e tenor (`partituras/<nome>_escalas_alto.pdf`, `_tenor.pdf`, `_concerto.pdf`).

Toda afirmação do estudo é conferida por script (sem IA): graus, dominantes secundários, SubV, resolução e
escalas contra as notas da cifra e da melodia.

## Começar

```bash
git clone https://github.com/levimurici/dnd-music-analysis
cd dnd-music-analysis
bash scripts/setup.sh             # music21 + abcjs, marked e Playwright (em paralelo; pula o que já existe)
python scripts/verificar.py       # confere as músicas de exemplo
claude                            # abre o Claude Code na pasta
```

Depois é só pedir em linguagem natural:

> Faça o fluxo completo da partitura `originais/garota_de_ipanema.pdf`.

> Transpõe o Canto de Ossanha só para tenor, uma oitava abaixo.

> Faz só a análise funcional do Samba em prelúdio.

> Que escalas eu uso para improvisar no Autumn Leaves?

No Claude Code as skills também podem ser chamadas direto: `/estudo-completo`, `/transpor-sax`,
`/analise-harmonica`, `/improvisacao-sax`.

## Como o fluxo funciona

```
originais/ (PDF/foto) ─▶ leitor-partitura (subagente) ─▶ musicas/<nome>_concerto.abc
                                                              │
        ┌─────────────────────────────────────────────────────┼──────────────────────────┐
        ▼                                                     ▼                          ▼
  transpor-sax                                      analise-harmonica            improvisacao-sax
  sax_transpose.py + render_pdf.js                  analise.py resumo/checar     analise.py escalas
  → musicas/_sax.abc                                → analises/_funcional.json    → analises/_improviso.json
  → partituras/_concerto|_alto|_tenor.pdf          → estudos/_estudo.md (1–3, 5) → partituras/_escalas_*.pdf
                                                              │
                                                              ▼
                                         revisor-estudo (subagente) + verificar.py
                                                              ▼
                                                 estudos/_estudo.pdf
```

| Peça | Onde | Papel |
|---|---|---|
| Orquestrador | `CLAUDE.md` | Regras gerais, roteamento dos pedidos, ordem das etapas |
| Skill `estudo-completo` | `.claude/skills/estudo-completo/` | Encadeia todas as etapas e retoma de onde parou |
| Skill `transpor-sax` | `.claude/skills/transpor-sax/` | Partitura → ABC de concerto → alto/tenor (ABC + PDF) |
| Skill `analise-harmonica` | `.claude/skills/analise-harmonica/` | Análise tonal, funcional e melódica |
| Skill `improvisacao-sax` | `.claude/skills/improvisacao-sax/` | Escalas por trecho (segura / colorida / tensão) |
| Subagente `leitor-partitura` | `.claude/agents/` | Leitura visual do PDF/foto, fora do contexto principal |
| Subagente `revisor-estudo` | `.claude/agents/` | Confere o estudo contra as regras e lista problemas |
| Scripts | `scripts/` | Determinísticos: transposição, fatos, checagens, PDFs |

Outros agentes (Codex, Cursor, Gemini CLI…) leem `AGENTS.md`, que aponta para os mesmos arquivos.

## Scripts

```bash
python scripts/sax_transpose.py musicas/x_concerto.abc -o musicas/x_sax.abc [--inst alto tenor] [--octave-tenor -1]
node   scripts/render_pdf.js    musicas/x_sax.abc --separar partituras/   # → x_concerto.pdf, x_alto.pdf, x_tenor.pdf
node   scripts/render_pdf.js    musicas/x.abc [saida.pdf]                 # um PDF só, uma música (X:) por página
python scripts/analise.py resumo  musicas/x_concerto.abc             # → analises/x_resumo.txt (o que o agente lê)
python scripts/analise.py fatos   musicas/x_concerto.abc             # → analises/x_fatos.json (grande)
python scripts/analise.py checar  musicas/x_concerto.abc analises/x_funcional.json
python scripts/analise.py escalas musicas/x_concerto.abc analises/x_improviso.json   # → musicas/x_escalas.abc
node   scripts/render_estudo.js estudos/x_estudo.md                  # → estudos/x_estudo.pdf (A4)
python scripts/verificar.py [x]                                      # conferência de tudo
```

- Alto = 6ª maior acima; tenor = 9ª maior acima. Cifras ficam em concerto.
- `analise.py` e `verificar.py` são Python puro; `sax_transpose.py` precisa do `music21`.
- Os PDFs usam Playwright/Chromium, detectado sozinho (`scripts/chromium.js`): se já houver um Chromium/Chrome
  no sistema, nenhum é baixado. Para forçar um caminho: `export CHROMIUM_PATH="/caminho/do/chrome"`.
- Os `.abc` podem ser abertos em https://editor.drawthedots.com/.

## Pastas

```
CLAUDE.md, AGENTS.md      instruções do agente
.claude/skills/           skills do fluxo
.claude/agents/           subagentes
.claude/settings.json     permissões para os scripts rodarem sem pedir confirmação
scripts/                  transposição, análise, checagem, renderização
originais/                onde você coloca o PDF/foto original (não vai para o git)
musicas/                  só os .abc (<nome>_concerto, _sax, _escalas, _sugestao)
partituras/               PDFs gerados, um por instrumento (<nome>_concerto/_alto/_tenor.pdf, _escalas_*.pdf)
estudos/                  <nome>_estudo.md e <nome>_estudo.pdf
analises/                 dados das análises (_resumo.txt, _funcional.json, _improviso.json)
glossario.md / .pdf       teoria e convenções, escritas uma vez só
exemplos/                 arquivos de teste dos scripts
```

## Músicas prontas

| Música | Tom | Observação |
|---|---|---|
| Autumn Leaves | Mi menor | **Gabarito** de forma e profundidade dos estudos |
| Samba em prelúdio | Lá menor | Alto e tenor uma oitava abaixo |
| Canto de Ossanha | Dó menor / Dó maior | Lido de foto de songbook, com letra |
| Assum Preto | Lá menor | Sem cifras: harmonia sugerida (`_sugestao`), confiança no máximo "provável" |

## Convenções

Graus com cifra no estilo Chediak (sempre relativos à escala maior da tônica local), funções T/S/D,
confiança *certo / provável / ambíguo*. Detalhes em [`glossario.md`](glossario.md).
O estudo não traz PDF anotado: a seção "Um caminho de estudo" diz o que anotar à mão na partitura.
