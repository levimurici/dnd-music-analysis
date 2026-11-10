---
name: estudo-completo
description: Executa o fluxo inteiro para uma música (ler partitura, transpor para sax, análise tonal/funcional/melódica, improvisação, revisão e PDFs). Use quando o Levi pedir "fluxo completo", "faz tudo" ou só entregar uma partitura.
---

# Fluxo completo de uma música

Responda em português. Rode tudo da raiz do repositório. Seja econômico: cada etapa lê só o que precisa.

## Entrada
Um PDF/foto em `partituras/` (ou um caminho que o Levi indicar) ou um `musicas/<nome>_concerto.abc` já pronto.
Defina `<nome>` em snake_case sem acento a partir do título. Se `musicas/<nome>_*` já existe, retome da
primeira etapa que falta em vez de refazer tudo (veja a tabela de arquivos do `CLAUDE.md`).

## Etapas (em ordem; não pule checagens)
1. **Leitura** — sem `_concerto.abc`: chame o subagente `leitor-partitura` com o arquivo e o `<nome>`.
2. **Transposição** — skill `transpor-sax`, passo 2 (`_sax.abc` + `_sax.pdf`).
3. **Análise** — skill `analise-harmonica` completa: `_resumo.txt`, `_funcional.json` com `checar` N/N, `_estudo.md` seções 1–3 e 5.
4. **Improvisação** — skill `improvisacao-sax`: `_improviso.json`, `escalas` sem falha em opção segura, `_escalas.pdf`, seção 4 do estudo.
5. **Revisão** — chame o subagente `revisor-estudo` com `<nome>`. Corrija o que ele apontar (só os problemas listados) e rode `node scripts/render_estudo.js musicas/<nome>_estudo.md`.
6. **Conferência final** — `python scripts/verificar.py <nome>` precisa sair sem erro.

## Entrega
Em até 6 linhas: a tese da música (2–3 frases), a extensão escrita do alto e do tenor, e os caminhos de
`musicas/<nome>_sax.pdf`, `musicas/<nome>_escalas.pdf` e `musicas/<nome>_estudo.pdf`.
Se alguma leitura ficou *provável* por falta de cifras (harmonia sugerida), diga isso numa frase.
