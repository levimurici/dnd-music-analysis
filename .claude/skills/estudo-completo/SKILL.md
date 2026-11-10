---
name: estudo-completo
description: Executa o fluxo inteiro para uma música (ler partitura, transpor para sax, análise tonal/funcional/melódica, improvisação, revisão e PDFs). Use quando o Levi pedir "fluxo completo", "faz tudo" ou só entregar uma partitura.
---

# Fluxo completo de uma música

Responda em português. Rode tudo da raiz do repositório. Seja econômico: cada etapa lê só o que precisa.

## Entrada
Um PDF/foto em `originais/` (ou um caminho que o Levi indicar) ou um `musicas/<nome>_concerto.abc` já pronto.
Defina `<nome>` em snake_case sem acento a partir do título. Se já existem arquivos `<nome>_*`, retome da
primeira etapa que falta em vez de refazer tudo (veja a tabela de arquivos do `CLAUDE.md`).

## Etapas (em ordem; não pule checagens)
0. **Ambiente** — `bash scripts/setup.sh` (instala em paralelo enquanto você lê a partitura: rode em segundo plano).
1. **Leitura** — sem `_concerto.abc`: chame o subagente `leitor-partitura` com o arquivo e o `<nome>`.
2. **Transposição** — skill `transpor-sax`, passo 2 (`musicas/<nome>_sax.abc` + `partituras/<nome>_{concerto,alto,tenor}.pdf`).
3. **Análise** — skill `analise-harmonica` completa: `analises/<nome>_resumo.txt`, `analises/<nome>_funcional.json` com `checar` N/N, `estudos/<nome>_estudo.md` seções 1–3 e 5.
4. **Improvisação** — skill `improvisacao-sax`: `analises/<nome>_improviso.json`, `escalas` sem falha em opção segura, `partituras/<nome>_escalas_*.pdf`, seção 4 do estudo.
5. **Revisão** — chame o subagente `revisor-estudo` com `<nome>`. Corrija o que ele apontar (só os problemas listados) e rode `node scripts/render_estudo.js estudos/<nome>_estudo.md`.
6. **Conferência final** — `python scripts/verificar.py <nome>` precisa sair sem erro.

## Entrega
Em até 6 linhas: a tese da música (2–3 frases), a extensão escrita do alto e do tenor, e os caminhos de
`partituras/<nome>_alto.pdf`, `_tenor.pdf`, `_concerto.pdf`, `partituras/<nome>_escalas_*.pdf` e `estudos/<nome>_estudo.pdf`.
Se alguma leitura ficou *provável* por falta de cifras (harmonia sugerida), diga isso numa frase.
