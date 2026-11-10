# dnd-music-analysis

Análise de partituras para estudo de **saxofone alto e tenor**, pronta para rodar dentro de um agente
local (Claude Code ou qualquer agente que leia `CLAUDE.md`/`AGENTS.md`).

Você entrega uma lead sheet em tom de concerto (PDF, foto ou ABC) e o agente devolve:

- a partitura transposta para **sax alto (E♭)** e **sax tenor (B♭)**, com as cifras em concerto (`_sax.pdf`);
- um **estudo explicado** com análise tonal, funcional e melódica (`_estudo.pdf`);
- **alternativas de improvisação** por trecho e a folha de escalas escrita para alto e tenor (`_escalas.pdf`).

Toda afirmação do estudo é conferida por script (sem IA): graus, dominantes secundários, SubV, resolução e
escalas contra as notas da cifra e da melodia.

## Começar

```bash
git clone https://github.com/levimurici/dnd-music-analysis
cd dnd-music-analysis
pip install -r requirements.txt   # music21 (só para a transposição)
npm install                       # abcjs, marked e Playwright + Chromium (PDFs)
python scripts/verificar.py       # confere as músicas de exemplo
claude                            # abre o Claude Code na pasta
```

Depois é só pedir em linguagem natural:

> Faça o fluxo completo da partitura `partituras/garota_de_ipanema.pdf`.

> Transpõe o Canto de Ossanha só para tenor, uma oitava abaixo.

> Faz só a análise funcional do Samba em prelúdio.

> Que escalas eu uso para improvisar no Autumn Leaves?

No Claude Code as skills também podem ser chamadas direto: `/estudo-completo`, `/transpor-sax`,
`/analise-harmonica`, `/improvisacao-sax`.

## Como o fluxo funciona

```
partitura (PDF/foto) ─▶ leitor-partitura (subagente) ─▶ musicas/<nome>_concerto.abc
                                                              │
        ┌─────────────────────────────────────────────────────┼──────────────────────────┐
        ▼                                                     ▼                          ▼
  transpor-sax                                      analise-harmonica            improvisacao-sax
  sax_transpose.py + render_pdf.js                  analise.py resumo/checar     analise.py escalas
  → _sax.abc / _sax.pdf                             → _funcional.json             → _improviso.json
                                                    → _estudo.md (1–3, 5)         → _escalas.pdf, seção 4
                                                              │
                                                              ▼
                                         revisor-estudo (subagente) + verificar.py
                                                              ▼
                                                        _estudo.pdf
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
node   scripts/render_pdf.js    musicas/x_sax.abc                    # ABC → PDF (uma música por página)
python scripts/analise.py resumo  musicas/x_concerto.abc             # fatos compactos (o que o agente lê)
python scripts/analise.py fatos   musicas/x_concerto.abc             # fatos completos (JSON grande)
python scripts/analise.py checar  musicas/x_concerto.abc musicas/x_funcional.json
python scripts/analise.py escalas musicas/x_concerto.abc musicas/x_improviso.json
node   scripts/render_estudo.js musicas/x_estudo.md                  # estudo → PDF A4
python scripts/verificar.py [x]                                      # conferência de tudo
```

- Alto = 6ª maior acima; tenor = 9ª maior acima. Cifras ficam em concerto.
- `analise.py` e `verificar.py` são Python puro; `sax_transpose.py` precisa do `music21`.
- Os PDFs usam Playwright/Chromium. Se o Chromium não puder ser baixado, aponte para um Chrome
  instalado: `export CHROMIUM_PATH="/caminho/do/chrome"`.
- Os `.abc` podem ser abertos em https://editor.drawthedots.com/.

## Pastas

```
CLAUDE.md, AGENTS.md      instruções do agente
.claude/skills/           skills do fluxo
.claude/agents/           subagentes
.claude/settings.json     permissões para os scripts rodarem sem pedir confirmação
scripts/                  transposição, análise, checagem, renderização
musicas/                  arquivos de cada música (<nome>_concerto.abc, _sax.pdf, _estudo.md…)
partituras/               onde você coloca o PDF/foto original (não vai para o git)
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
