---
name: improvisacao-sax
description: Monta alternativas de improvisação explicáveis (modos gregos, escalas menores, diminutas, pentatônicas) por trecho de uma música e gera a folha de escalas para alto e tenor.
---

# Improvisação explicável para sax

Responda em português. Rode tudo da raiz do repositório. Gabarito: seção 4 de `musicas/autumn_leaves_estudo.md`.

## Pré-requisito
`musicas/<nome>_funcional.json` checado (skill `analise-harmonica`). Se não existir, rode-a antes. Use o `_resumo.txt` para ver as notas da melodia; não leia o `_fatos.json`.

## Passos
1. Divida a música em trechos (cadências ou seções; acorde repetido aparece uma vez).
2. Para cada acorde, até 3 níveis:
   - **segura**: contém todas as notas da cifra (inclusive tensões escritas) e de preferência a melodia;
   - **colorida**: troca uma nota de propósito (ex.: dórico no lugar de eólio, lídio no lugar de jônio);
   - **tensão**: atrito proposital (alterada, dominante diminuta…).
   Regra de ouro: antes de escolher, olhe as notas que a melodia já usa naquele acorde.
3. Escreva `musicas/<nome>_improviso.json`:
   `{"trechos": [{"titulo": "c. 1-3: II-V-I em Sol maior", "opcoes": [{"idx": 0, "nivel": "segura", "escala": "A dórico"}]}]}`
   Escalas aceitas: modos maiores (jônio…lócrio), menor harmônica e modos (mixolídio b9 b13, lócrio 6…), menor melódica e modos (lídio b7, mixolídio b13, lócrio 2, alterada…), diminutas (tom-semitom, dominante diminuta), tons inteiros, pentatônicas, blues, bebop dominante.
4. `python scripts/analise.py escalas musicas/<nome>_concerto.abc musicas/<nome>_improviso.json` (use `_sugestao.abc` se a harmonia foi sugerida). Opção "segura" que falhar deve ser trocada. Nas outras, registre a falha em itálico na tabela (ex.: *Não tem a 5ª.*, *Choca com o C♯ da melodia no c. 6.*).
5. `node scripts/render_pdf.js musicas/<nome>_escalas.abc` (semínimas; concerto, alto e tenor escritos).
6. Escreva/atualize a seção **4. Improvisação explicável** do `<nome>_estudo.md` e rode `node scripts/render_estudo.js musicas/<nome>_estudo.md`.

## Formato da seção 4
Tese (quais coleções de notas servem a música e por quê; notas-alvo remetem às notas-guia da seção 3) · uma tabela por trecho: Acorde | Nível | Escala | Por que encaixa (de onde vem a escala e qual nota a diferencia) · uma "Lição" ou "Ideia" curta quando a checagem ensinar algo. Sem coluna de checagem, sem "Para o sax".

## Entrega
Anexe `<nome>_escalas.pdf` e o estudo atualizado em PDF.
