#!/usr/bin/env python3
"""
verificar.py - Conferência automática das músicas (sem IA).

Para cada música em musicas/ (ou só as passadas como argumento):
  - compassos: duração de cada compasso bate com o M: (anacruse e último compasso podem ser menores);
  - checar: todos os graus do _funcional.json conferem (N/N);
  - escalas: nenhuma opção "segura" do _improviso.json falha
             (falha em "colorida"/"tensão" é só aviso: deve estar comentada no estudo);
  - estudo: tem as cinco seções (tonal, funcional, melódica, improvisação, caminho de estudo) e fica entre 1.500 e 2.500 palavras (fora disso é aviso);
  - existem os PDFs em partituras/ (_concerto/_alto/_tenor e _escalas_*) e estudos/;
  - musicas/ só tem .abc.

Uso:
  python scripts/verificar.py                 # todas as músicas
  python scripts/verificar.py autumn_leaves   # só uma
Sai com código 1 se houver erro.
"""
import json
import re
from fractions import Fraction
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MUSICAS = RAIZ / "musicas"          # só .abc
ANALISES = RAIZ / "analises"        # _funcional.json, _improviso.json (e _resumo.txt local)
ESTUDOS = RAIZ / "estudos"          # _estudo.md e _estudo.pdf
PARTITURAS = RAIZ / "partituras"    # PDFs por instrumento
ANALISE = RAIZ / "scripts" / "analise.py"
SECOES = ["Análise tonal", "Análise funcional", "Análise melódica",
          "Improvisação", "Um caminho de estudo"]


def rodar(*args):
    r = subprocess.run([sys.executable, str(ANALISE), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def verificar(nome):
    erros, avisos = [], []
    concerto = MUSICAS / f"{nome}_concerto.abc"
    sugestao = MUSICAS / f"{nome}_sugestao.abc"
    base = sugestao if sugestao.exists() else concerto
    funcional = ANALISES / f"{nome}_funcional.json"
    improviso = ANALISES / f"{nome}_improviso.json"
    estudo = ESTUDOS / f"{nome}_estudo.md"

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = rodar("fatos", concerto, "-o", Path(tmp) / "f.json")
        if rc != 0:
            erros.append("ABC não pôde ser lido: " + out.strip().splitlines()[-1])
            return erros, avisos
        fatos = json.loads((Path(tmp) / "f.json").read_text(encoding="utf-8"))
    if "CIFRAS NÃO RECONHECIDAS" in out:
        erros.append(out.split("CIFRAS NÃO RECONHECIDAS:")[1].strip().join(["cifras não reconhecidas: ", ""]))
    M = fatos["compasso"].strip()
    cheio = Fraction(1) if M.startswith("C") else Fraction(M)
    comp = fatos["compassos"]
    for i, c in enumerate(comp):
        d = Fraction(c["duracao"])
        if d == cheio or (d < cheio and i in (0, len(comp) - 1)):
            continue
        erros.append(f"compasso {c['numero']}{' (casa ' + str(c['casa']) + ')' if c.get('casa') else ''}: "
                     f"dura {d * 4} semínimas, o M:{M} pede {cheio * 4}")

    if funcional.exists():
        rc, out = rodar("checar", base, funcional)
        m = re.search(r"(\d+)/(\d+) graus conferem", out)
        if rc != 0:
            erros.append(f"checar: {m.group(0) if m else 'falhou'}")
    else:
        avisos.append("sem _funcional.json (análise funcional não feita)")

    if improviso.exists():
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = rodar("escalas", base, improviso, "-o", Path(tmp) / "x.abc")
        for linha in out.splitlines():
            if linha.startswith("ERRO"):
                (erros if " segura " in linha else avisos).append("escalas: " + " ".join(linha.split()[:5]))
    else:
        avisos.append("sem _improviso.json (improvisação não feita)")

    if estudo.exists():
        txt = estudo.read_text(encoding="utf-8")
        for s in SECOES:
            if not re.search(r"^##\s*(\d\.\s*)?" + re.escape(s), txt, re.M):
                avisos.append(f"estudo sem a seção '{s}'")
        palavras = len(re.findall(r"\w+", re.sub(r"[|#*_`-]", " ", txt)))
        if not 1500 <= palavras <= 2500:
            avisos.append(f"estudo com {palavras} palavras (alvo 1.500–2.500)")
    else:
        avisos.append("sem _estudo.md")

    pdfs = [PARTITURAS / f"{nome}_{p}{i}.pdf" for p in ("", "escalas_") for i in ("concerto", "alto", "tenor")]
    pdfs.append(ESTUDOS / f"{nome}_estudo.pdf")
    for pdf in pdfs:
        if not pdf.exists():
            avisos.append(f"falta {pdf.relative_to(RAIZ)}")
    extras = [p.name for p in MUSICAS.glob(f"{nome}_*") if p.suffix != ".abc"]
    if extras:
        erros.append(f"musicas/ deve ter só .abc; mova: {', '.join(sorted(extras))}")
    return erros, avisos


def main():
    nomes = sys.argv[1:] or sorted(p.name[:-len("_concerto.abc")] for p in MUSICAS.glob("*_concerto.abc"))
    total_erros = 0
    for nome in nomes:
        if not (MUSICAS / f"{nome}_concerto.abc").exists():
            print(f"ERRO {nome}: musicas/{nome}_concerto.abc não existe")
            total_erros += 1
            continue
        erros, avisos = verificar(nome)
        total_erros += len(erros)
        print(f"{'ERRO' if erros else 'OK  '} {nome}")
        for e in erros:
            print("   ✗", e)
        for a in avisos:
            print("   ·", a)
    sys.exit(1 if total_erros else 0)


if __name__ == "__main__":
    main()
