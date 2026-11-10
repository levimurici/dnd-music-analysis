# dnd-music-analysis — orquestrador

Responda sempre em **português**. O usuário (Levi) estuda saxofone: tudo o que sai daqui é material de
estudo para sax alto (E♭) e tenor (B♭). **Seja econômico em tokens**: leia resumos, não arquivos grandes,
e não releia o que já está no contexto.

Todos os comandos rodam a partir da **raiz do repositório**.

## Pastas

| Pasta | O que tem |
|---|---|
| `partituras/` | PDF/foto original que o Levi coloca (não versionado) |
| `musicas/` | Tudo de cada música, com prefixo `<nome>_` (ver tabela de arquivos abaixo) |
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
partitura (PDF/foto)  ──▶  1. transpor-sax        ──▶ <nome>_concerto.abc, <nome>_sax.abc/.pdf
                           2. analise-harmonica   ──▶ <nome>_funcional.json, <nome>_estudo.md (seções 1–3, 5)
                           3. improvisacao-sax    ──▶ <nome>_improviso.json, <nome>_escalas.abc/.pdf, seção 4
                           4. revisor-estudo      ──▶ conferência final  ──▶ <nome>_estudo.pdf
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

- **`leitor-partitura`**: lê o PDF/foto e escreve `musicas/<nome>_concerto.abc`. Use-o sempre que a
  entrada for imagem/PDF: a leitura visual gasta muitos tokens e fica fora do contexto principal.
- **`revisor-estudo`**: confere um `_estudo.md` contra as regras (tamanho, citação de compassos,
  redundância, checagens N/N) e devolve só a lista de problemas.

## Arquivos por música

| Arquivo | Quem gera | Ler? |
|---|---|---|
| `_concerto.abc` | leitor-partitura / transpor-sax | sim |
| `_sax.abc`, `_sax.pdf` | `scripts/sax_transpose.py` + `scripts/render_pdf.js` | não |
| `_resumo.txt` | `scripts/analise.py resumo` | **sim — é a fonte de fatos** |
| `_fatos.json` | `scripts/analise.py fatos` | **não** (grande; não versionado) |
| `_sugestao.abc` | analise-harmonica, quando a partitura não tem cifras | sim |
| `_funcional.json` | analise-harmonica | sim |
| `_improviso.json` | improvisacao-sax | sim |
| `_escalas.abc/.pdf` | `scripts/analise.py escalas` + `render_pdf.js` | não |
| `_estudo.md/.pdf` | analise-harmonica + improvisacao-sax + `render_estudo.js` | sim (o .md) |

Gabarito de forma e profundidade: **`musicas/autumn_leaves_estudo.md`**.

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

Ao terminar, diga ao Levi em 2–3 frases a tese da música e liste os PDFs gerados
(`_sax.pdf`, `_escalas.pdf`, `_estudo.pdf`) com o caminho.
