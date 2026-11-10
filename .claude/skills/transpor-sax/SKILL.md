---
name: transpor-sax
description: Transpõe uma partitura (PDF, foto ou ABC) em tom de concerto para sax alto e/ou tenor, mantendo as cifras em concerto, e gera ABC e PDF.
---

# Transpor para sax alto / tenor

Responda em português. Rode tudo da raiz do repositório (ver `CLAUDE.md`).

## Preparar o ambiente (se faltar)
```bash
pip install -r requirements.txt
npm install
```

## 1. Ler a partitura -> `musicas/<nome>_concerto.abc`
Se o ABC de concerto já existe, pule. Se a entrada é PDF/foto (normalmente em `originais/`), **delegue ao subagente `leitor-partitura`**
(passe o caminho do arquivo e o `<nome>`); ele devolve o ABC pronto e conferido.
Regras de escrita do ABC (o subagente segue as mesmas):
- melodia, cifras, fórmula de compasso, armadura, casas 1/2, D.S./Fine/!segno!;
- cifras com ♭/♯ dentro de parênteses e "∕" (U+2215) em extensões tipo 9∕13, senão o abcjs corta a cifra;
- letra como trecho por compasso em anotação "_texto" alinhada à cifra; segunda letra após D.S. com "_1. …" "_2. …";
- mudança de tom no meio: `K:` em linha própria;
- foto torta: gire e desentorte pauta a pauta antes de ler.
Confira: soma dos tempos de cada compasso bate com o M:; renderize o ABC e compare compasso a compasso com o original antes de seguir.

## 2. Transpor
```bash
python scripts/sax_transpose.py musicas/<nome>_concerto.abc -o musicas/<nome>_sax.abc [--inst alto tenor] [--octave-alto N] [--octave-tenor N]
node scripts/render_pdf.js musicas/<nome>_sax.abc --separar partituras/
```
- Alto = 6ª maior acima; tenor = 9ª maior acima. Cifras ficam sempre em concerto.
- Regra de oitava: padrão quando a escrita cabe confortável; baixar 1 oitava (-1) quando a melodia de concerto é aguda. Tenor costuma ficar melhor com `--octave-tenor -1`.
- Extensão escrita do sax: Si♭3 a F♯6. Informe a extensão resultante e avise se sair dela.
- Fine/D.S./segno extras que o script não copiar: acrescente à mão no ABC final.

## Saída
`musicas/<nome>_sax.abc` (cole em https://editor.drawthedots.com/) e, em `partituras/`, um PDF por instrumento: `<nome>_concerto.pdf`, `<nome>_alto.pdf`, `<nome>_tenor.pdf` (só os instrumentos pedidos). Em `musicas/` ficam só os `.abc`. Entregue os PDFs e diga a extensão escrita de cada instrumento.
