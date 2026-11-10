---
name: analise-harmonica
description: Gera o estudo explicado de uma música (análise tonal, funcional e/ou melódica) a partir da partitura de concerto, com cada afirmação verificável por script.
---

# Análise harmônica: tonal, funcional e melódica

Responda em português. O Levi estuda sax: o `_estudo.md` é material de ESTUDO. Gabarito de forma e profundidade: `estudos/autumn_leaves_estudo.md`. Termos e convenções ficam só em `glossario.md` (não repita teoria geral no estudo). Rode tudo da raiz do repositório.

Se o Levi pedir só uma análise ("análise tonal", "funcional", "melódica"), gere só essa seção, mas a funcional precisa do tom local da tonal, e a melódica da funcional.

## Passos
1. Garanta `musicas/<nome>_concerto.abc` (senão, faça o passo 1 da skill `transpor-sax`).
2. `python scripts/analise.py resumo musicas/<nome>_concerto.abc` e leia SÓ o `analises/<nome>_resumo.txt` (economia de tokens; não leia nem gere o `_fatos.json`). Ele traz cifras, melodia por compasso, notas de fora, notas sustentadas sobre troca de cifra, tom por janela, extensão e saltos.
3. Sem cifras na partitura: deduza a harmonia da melodia, grave em `musicas/<nome>_sugestao.abc` (cópia do concerto com cifras), use esse arquivo nos comandos, gere `node scripts/render_pdf.js musicas/<nome>_sugestao.abc --separar partituras/` (→ `partituras/<nome>_sugestao_concerto.pdf`) e marque toda leitura harmônica como no máximo *provável*.
4. Escreva `analises/<nome>_funcional.json`:
   `{"acordes": [{"idx": 0, "cifra": "Am7(9)", "tom_local": "G", "grau": "IIm7", "funcao": "S", "alvo": null, "confianca": "certo"}]}`
   - grau com cifra (Chediak), relativo à escala MAIOR da tônica local: em Mi menor, C7M = bVI7M. Aceitos: IIm7, V7, I7M, bVII7, IIm7(b5), VII°7, V7/IIm, SubV7/I, IIm7/IV…
   - `proximo_idx` quando a resolução acontece por repetição/casa.
5. `python scripts/analise.py checar musicas/<nome>_concerto.abc analises/<nome>_funcional.json` até dar N/N. Grau que falhar: corrija ou trate como ambíguo. Nunca entregue com erro.
6. Escreva `estudos/<nome>_estudo.md` (seções 1 a 3 e 5; a 4 é da skill `improvisacao-sax`) e `node scripts/render_estudo.js estudos/<nome>_estudo.md` (gera `estudos/<nome>_estudo.pdf`).

## Estrutura do estudo
Título; 1 linha (compositor, tom, "Termos e convenções: ver `glossario.md`").
1. **Análise tonal**: Tese (1 frase) · Mapa da forma (tabela seção/compassos/o que acontece/região) · Evidências (estatística do script, cadências, nota final, notas fora da armadura explicadas) · tonicalizações/modulações com "o que causa".
2. **Análise funcional**: Tese · tabela de cadências (cada uma UMA vez, com "repete em c. X"), coluna "Por que" · explicações de casos especiais · Pontos ambíguos (as duas leituras e qual foi adotada).
3. **Análise melódica**: Tese · motivos/sequências · notas-guia sustentadas · tabela de notas que pedem explicação (P, B, Ap, An, tensão escrita) · ponto culminante.
4. (improvisação, outra skill)
5. **Um caminho de estudo**: o que o Levi deve ANOTAR À MÃO na parte do sax (`partituras/<nome>_alto.pdf` ou `_tenor.pdf`) (graus/funções, regiões, setas, notas-guia, siglas), terminando com "compare com as tabelas e siga os passos gerais do glossario.md". Não gere PDF anotado.

## Regras
- Toda afirmação cita compasso (e tempo quando importa). Fatos vêm do resumo, não de cálculo de cabeça.
- Toda marcação tem o que é, por que é e o que causa.
- Afirmativo para fato calculado; condicional para interpretação. Confiança: certo / provável / ambíguo.
- Sem redundância: cada cadência, ambiguidade e explicação aparece uma vez; nada de bastidor técnico (nomes de JSON, comandos) no estudo.
- Tamanho alvo: 1.500 a 2.500 palavras para o estudo completo.

## Entrega
Anexe `estudos/<nome>_estudo.pdf` (A4, tablet/impressão) e diga em 2–3 frases a tese da música.
