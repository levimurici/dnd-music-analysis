# dnd-music-analysis — orquestrador

Responda sempre em **português**. O usuário (Levi) estuda saxofone: tudo o que sai daqui é material de
estudo para sax alto (E♭) e tenor (B♭). **Seja econômico em tokens**: leia resumos, não arquivos grandes,
e não releia o que já está no contexto.

Todos os comandos rodam a partir da **raiz do repositório**.

## Pastas

| Pasta | O que tem |
|---|---|
| `originais/` | PDF/foto original que o Levi coloca (não versionado) |
| `musicas/` | **Só `.abc`**: concerto, sax, escalas, sugestão |
| `partituras/` | PDFs gerados, um por instrumento: `_concerto.pdf`, `_alto.pdf`, `_tenor.pdf` (e `_escalas_*`) |
| `estudos/` | `_estudo.md` (fonte) e `_estudo.pdf` |
| `analises/` | Dados das análises: `_resumo.txt`, `_funcional.json`, `_improviso.json` |
| `scripts/` | Scripts determinísticos (sem IA): transposição, fatos/checagem, renderização |
| `glossario.md` | Teoria e convenções, escritas UMA vez. Os estudos não repetem teoria geral |
| `exemplos/` | Arquivos de teste dos scripts |
| `.claude/skills/` | As skills do fluxo |
| `.claude/agents/` | Subagentes (contexto isolado para tarefas pesadas) |

`<nome>` é snake_case sem acento (ex.: `samba_em_preludio`).

## Fluxo completo

Quando o Levi pedir "fluxo completo", "faz tudo", "estuda essa música" ou só entregar uma partitura,
use a skill **`estudo-completo`**. Ela encadeia as outras na ordem:

```
originais/ (PDF/foto) ─▶ 1. transpor-sax       ─▶ musicas/<nome>_concerto.abc, _sax.abc
                                                   partituras/<nome>_concerto.pdf, _alto.pdf, _tenor.pdf
                         2. analise-harmonica  ─▶ analises/<nome>_funcional.json, estudos/<nome>_estudo.md (1–3, 5)
                         3. improvisacao-sax   ─▶ analises/<nome>_improviso.json, musicas/<nome>_escalas.abc
                                                   partituras/<nome>_escalas_{concerto,alto,tenor}.pdf, seção 4
                         4. revisor-estudo     ─▶ conferência final ─▶ estudos/<nome>_estudo.pdf
```

Pedidos parciais chamam só a skill correspondente:

| Pedido | Skill |
|---|---|
| "transpõe para alto/tenor", "passa para sax" | `transpor-sax` |
| "análise tonal / funcional / melódica", "analisa a harmonia" | `analise-harmonica` (só a seção pedida) |
| "escalas para improvisar", "o que tocar em cima" | `improvisacao-sax` |

Dependências: a funcional precisa da tonal; a melódica precisa da funcional; a improvisação precisa do
`_funcional.json` checado. Se faltar um pré-requisito, rode a skill anterior antes, sem perguntar.

## Subagentes

- **`leitor-partitura`**: lê o PDF/foto de `originais/` e escreve `musicas/<nome>_concerto.abc`. Use-o sempre que a
  entrada for imagem/PDF: a leitura visual gasta muitos tokens e fica fora do contexto principal.
- **`revisor-estudo`**: confere um `_estudo.md` contra as regras (tamanho, citação de compassos,
  redundância, checagens N/N) e devolve só a lista de problemas.

## Arquivos por música

| Arquivo | Quem gera | Ler? |
|---|---|---|
| `musicas/<nome>_concerto.abc` | leitor-partitura / transpor-sax | sim |
| `musicas/<nome>_sax.abc` | `scripts/sax_transpose.py` | não |
| `musicas/<nome>_sugestao.abc` | analise-harmonica, quando a partitura não tem cifras | sim |
| `musicas/<nome>_escalas.abc` | `scripts/analise.py escalas` | não |
| `partituras/<nome>_{concerto,alto,tenor}.pdf` | `render_pdf.js musicas/<nome>_sax.abc --separar partituras/` | não |
| `partituras/<nome>_escalas_{concerto,alto,tenor}.pdf` | `render_pdf.js musicas/<nome>_escalas.abc --separar partituras/` | não |
| `analises/<nome>_resumo.txt` | `scripts/analise.py resumo` | **sim — é a fonte de fatos** |
| `analises/<nome>_fatos.json` | `scripts/analise.py fatos` | **não** (grande; não versionado) |
| `analises/<nome>_funcional.json` | analise-harmonica | sim |
| `analises/<nome>_improviso.json` | improvisacao-sax | sim |
| `estudos/<nome>_estudo.md/.pdf` | analise-harmonica + improvisacao-sax + `render_estudo.js` | sim (o .md) |

Nunca grave PDF, JSON ou TXT em `musicas/`: o `verificar.py` acusa erro.

Gabarito de forma e profundidade: **`estudos/autumn_leaves_estudo.md`**.

## Regras que valem para todas as skills

- Fatos vêm dos scripts, nunca de cálculo de cabeça. Toda afirmação cita compasso.
- Nada sai com checagem falhando: `checar` precisa dar N/N; opção "segura" de escala que falhar é trocada.
- Cifras ficam sempre em **concerto**, inclusive nas partes de sax.
- Sem PDF anotado automático: o Levi anota a partitura à mão (seção "Um caminho de estudo").
- Escalas saem em semínimas.
- Estudo completo: 1.500 a 2.500 palavras, sem bastidor técnico (nomes de JSON, comandos).

## Ambiente

```bash
pip install -r requirements.txt     # music21
npm install                         # abcjs, marked, playwright (+ Chromium)
python scripts/verificar.py         # confere as músicas já prontas
```

Sem internet para baixar o Chromium: `export CHROMIUM_PATH=/caminho/do/chrome`.

## Entrega

Ao terminar, diga ao Levi em 2–3 frases a tese da música e liste os PDFs gerados com o caminho
(`partituras/<nome>_alto.pdf`, `_tenor.pdf`, `_concerto.pdf`, `_escalas_*.pdf` e `estudos/<nome>_estudo.pdf`).
