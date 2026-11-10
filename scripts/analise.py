#!/usr/bin/env python3
"""
analise.py - Fatos musicais calculados (sem IA) para as skills de análise.

Lê uma lead sheet em ABC de CONCERTO e produz fatos verificáveis: notas de cada
cifra, relação de cada nota da melodia com a cifra do momento, tempo forte/fraco,
estimativa de tom por trecho, extensão. Também confere as interpretações
escritas pelo Claude (graus, dominantes secundários, escalas de improviso).

Não depende de bibliotecas externas.

Uso:
  python scripts/analise.py fatos   musicas/x_concerto.abc                        -> analises/x_fatos.json
  python scripts/analise.py resumo  musicas/x_concerto.abc                        -> analises/x_resumo.txt (compacto, para ler)
  python scripts/analise.py checar  musicas/x_concerto.abc analises/x_funcional.json
  python scripts/analise.py escalas musicas/x_concerto.abc analises/x_improviso.json  -> musicas/x_escalas.abc

Formato do analise.json (escrito na skill analise-funcional):
  {"acordes": [{"idx": 0, "cifra": "Am7(9)", "tom_local": "G", "grau": "IIm7",
                "funcao": "S", "alvo": null, "confianca": "certo"}, ...]}
  "proximo_idx" (opcional) indica o acorde seguinte quando há repetição/volta.
  grau aceita: IIm7, V7, I7M, bVII7, IIm7(b5), V7/IIm, SubV7/IIm, IIm7/IV, VII°/V ...

Formato do improviso.json (skill improvisacao):
  {"trechos": [{"titulo": "c. 1-3: II-V-I em Sol", "idx": [0, 1, 2],
                "opcoes": [{"idx": 0, "nivel": "segura", "escala": "A dórico"}, ...]}]}
"""
import argparse
import json
import re
import sys
import unicodedata
from fractions import Fraction as F
from pathlib import Path

# ------------------------------------------------------------------ alturas ---
LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
LETTERS = "CDEFGAB"
SHARPS_ORDER = "FCGDAEB"
FLATS_ORDER = "BEADGCF"
NOMES_PT = {"C": "Dó", "D": "Ré", "E": "Mi", "F": "Fá", "G": "Sol", "A": "Lá", "B": "Si"}

INTERVALO_NOME = {0: "1", 1: "b9", 2: "9", 3: "b3/#9", 4: "3", 5: "11", 6: "#11/b5",
                  7: "5", 8: "b13/#5", 9: "13/6", 10: "b7", 11: "7M"}


def norm_acc(s: str) -> str:
    return s.replace("♯", "#").replace("♭", "b").replace("∕", "/")


def parse_note_name(name: str):
    """'F#' -> (letter, alter)."""
    name = norm_acc(name.strip())
    m = re.match(r"^([A-Ga-g])(#{1,2}|b{1,2})?$", name)
    if not m:
        raise ValueError(f"nome de nota inválido: {name!r}")
    acc = m.group(2) or ""
    alter = acc.count("#") - acc.count("b")
    return m.group(1).upper(), alter


def note_pc(letter: str, alter: int) -> int:
    return (LETTER_PC[letter] + alter) % 12


def note_label(letter: str, alter: int) -> str:
    return letter + ("#" * alter if alter > 0 else "b" * (-alter))


def midi_name(m: int, prefer_flat=False) -> str:
    names_s = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    names_f = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
    return (names_f if prefer_flat else names_s)[m % 12] + str(m // 12 - 1)


# ------------------------------------------------------------- armaduras ---
MODE_OFFSET = {"": 0, "maj": 0, "ion": 0, "m": -3, "min": -3, "aeo": -3, "dor": -2,
               "phr": -4, "lyd": 1, "mix": -1, "loc": -5}


def parse_key(k: str):
    """'Em' -> (sharps, tonic_letter, tonic_alter, mode)."""
    k = norm_acc(k.strip().split()[0]) if k.strip() else "C"
    if k.lower() in ("none", ""):
        return 0, "C", 0, "maj"
    m = re.match(r"^([A-G])(#|b)?([A-Za-z]*)$", k)
    if not m:
        return 0, "C", 0, "maj"
    letter, acc, mode = m.group(1), m.group(2) or "", m.group(3).lower()[:3]
    if mode == "m" or mode == "min":
        mode = "m"
    alter = 1 if acc == "#" else -1 if acc == "b" else 0
    # sustenidos da tonalidade maior com essa tônica
    major_sharps = {("C", 0): 0, ("G", 0): 1, ("D", 0): 2, ("A", 0): 3, ("E", 0): 4, ("B", 0): 5,
                    ("F", 1): 6, ("C", 1): 7, ("F", 0): -1, ("B", -1): -2, ("E", -1): -3,
                    ("A", -1): -4, ("D", -1): -5, ("G", -1): -6, ("C", -1): -7,
                    ("G", 1): 8, ("D", 1): 9, ("A", 1): 10, ("E", 1): 11, ("B", 1): 12,
                    ("F", -1): -8}
    s = major_sharps.get((letter, alter), 0) + MODE_OFFSET.get(mode, 0)
    return s, letter, alter, ("m" if mode in ("m", "aeo") else "maj" if mode in ("", "maj", "ion") else mode)


def key_sig_map(sharps: int) -> dict:
    m = {s: 0 for s in LETTERS}
    if sharps > 0:
        for s in SHARPS_ORDER[:sharps]:
            m[s] = 1
    elif sharps < 0:
        for s in FLATS_ORDER[:-sharps]:
            m[s] = -1
    return m


# ------------------------------------------------------------------ cifras ---
def parse_chord(sym: str):
    """Cifra (padrão brasileiro ou jazz) -> dict com fundamental, baixo, qualidade
    e classes de altura (em semitons a partir da fundamental)."""
    raw = sym
    s = norm_acc(sym).replace(" ", "")
    m = re.match(r"^([A-G])(#|b)?", s)
    if not m:
        return None
    root_letter, root_alter = m.group(1), (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)
    rest = s[m.end():]
    bass = None
    mb = re.search(r"/([A-G](#|b)?)$", rest)
    if mb:
        bass = parse_note_name(mb.group(1))
        rest = rest[: mb.start()]
    body = rest.replace("(", " ").replace(")", " ").replace(",", " ")

    third, fifth, seventh = 4, 7, None
    tensions = set()
    quality = "maior"
    b = body.strip()

    def take(prefixes):
        nonlocal b
        for p in prefixes:
            if b.startswith(p):
                b = b[len(p):].lstrip()
                return p
        return None

    if take(["ø7", "ø"]):
        third, fifth, seventh, quality = 3, 6, 10, "meio-diminuto"
    elif take(["°7", "º7", "o7", "dim7", "°", "º", "dim"]):
        third, fifth, seventh, quality = 3, 6, 9, "diminuto"
    elif re.match(r"^(m|min|-)(?!aj)", b):
        take(["min", "m", "-"])
        third, quality = 3, "menor"
    elif take(["aug", "+"]):
        fifth, quality = 8, "aumentado"

    if take(["sus4", "sus2", "sus"]):
        third = 5
        quality += " sus4"

    # sétima
    if take(["7M", "maj7", "Maj7", "M7", "Δ7", "Δ", "maj"]):
        seventh = 11
    elif re.match(r"^(13|11|9)", b) and quality in ("maior", "menor", "maior sus4"):
        # C9 / Cm9 / C13 implicam sétima (menor)
        seventh = 10
    elif take(["7"]):
        if seventh is None:
            seventh = 10
    elif re.match(r"^6", b):
        pass  # sexta tratada como tensão abaixo

    if "alt" in b:
        tensions |= {1, 3, 6, 8}
        b = b.replace("alt", "")
    b = b.replace("add", " ")
    for acc, num in re.findall(r"([#b]?)(13|11|9|6|5|4|2)", b):
        n = int(num)
        if n == 5:
            fifth = 6 if acc == "b" else 8 if acc == "#" else fifth
            continue
        if n == 4:
            third = 5
            continue
        base = {2: 2, 9: 2, 11: 5, 13: 9, 6: 9}[n]
        tensions.add((base + (1 if acc == "#" else -1 if acc == "b" else 0)) % 12)
    if re.match(r"^13", rest.lstrip("(")) and seventh == 10:
        tensions.add(2)

    tones = {0, third, fifth} | ({seventh} if seventh is not None else set())
    pcs_rel = sorted(tones | tensions)
    root_pc = note_pc(root_letter, root_alter)
    tipo = classify(third, fifth, seventh, tensions)
    return {
        "cifra": raw,
        "fundamental": note_label(root_letter, root_alter),
        "fundamental_pc": root_pc,
        "baixo": note_label(*bass) if bass else None,
        "tipo": tipo,
        "terca": third, "quinta": fifth, "setima": seventh,
        "notas_base_rel": sorted(tones),
        "tensoes_rel": sorted(tensions),
        "pcs": sorted({(root_pc + r) % 12 for r in pcs_rel}),
        "pcs_base": sorted({(root_pc + r) % 12 for r in tones}),
        "dominante": third == 4 and seventh == 10,
    }


def classify(third, fifth, seventh, tensions):
    if third == 3 and fifth == 6 and seventh == 9:
        return "°7"
    if third == 3 and fifth == 6 and seventh == 10:
        return "m7(b5)"
    if third == 3 and fifth == 6:
        return "°"
    if third == 5:
        return "7sus4" if seventh == 10 else "sus4"
    if third == 3:
        return {None: "m6" if 9 in tensions else "m", 10: "m7", 11: "m7M"}[seventh]
    if fifth == 8 and seventh is None:
        return "+"
    return {None: "6" if 9 in tensions else "maior", 10: "7", 11: "7M"}[seventh]


# ------------------------------------------------------------- leitor ABC ---
NOTE_RE = re.compile(r"(\^\^|\^|__|_|=)?([A-Ga-g])([,']*)(\d*/*\d*)")


def parse_len(s: str) -> F:
    if not s:
        return F(1)
    if re.fullmatch(r"\d+", s):
        return F(int(s))
    m = re.fullmatch(r"(\d*)(/+)(\d*)", s)
    if m:
        num = int(m.group(1)) if m.group(1) else 1
        if m.group(3):
            den = int(m.group(3))
        else:
            den = 2 ** len(m.group(2))
        return F(num, den)
    return F(1)


def parse_meter(m: str) -> F:
    m = m.strip()
    if m == "C":
        return F(1)
    if m == "C|":
        return F(1)
    a, b = m.split("/")
    return F(int(a), int(b))


def meter_beats(m: str):
    m = m.strip()
    if m == "C|":
        return F(1, 2), 2
    if m == "C":
        return F(1, 4), 4
    a, b = (int(x) for x in m.split("/"))
    if b == 8 and a % 3 == 0 and a > 3:
        return F(3, 8), a // 3
    return F(1, b), a


def read_abc(path: Path):
    text = path.read_text(encoding="utf-8")
    # só a primeira música
    tunes = re.split(r"\n(?=X:)", text)
    text = tunes[0]
    hdr = {"T": "", "M": "4/4", "L": None, "K": "C", "C": ""}
    body_lines, in_body = [], False
    for line in text.splitlines():
        st = line.strip()
        if not in_body:
            m = re.match(r"^([A-Za-z]):(.*)$", st)
            if m:
                if m.group(1) in hdr and not hdr[m.group(1)] or m.group(1) in ("M", "L", "K"):
                    hdr[m.group(1)] = m.group(2).strip()
                if m.group(1) == "K":
                    in_body = True
            continue
        body_lines.append(line)
    if hdr["L"] is None:
        hdr["L"] = "1/16" if parse_meter(hdr["M"]) < F(3, 4) else "1/8"
    return hdr, body_lines


def parse_body(hdr, body_lines):
    """Percorre o corpo do ABC e devolve compassos, notas e cifras."""
    unit = parse_len(hdr["L"].split("/")[0] + "/" + hdr["L"].split("/")[1]) if "/" in hdr["L"] else F(1)
    unit = F(int(hdr["L"].split("/")[0]), int(hdr["L"].split("/")[1]))
    meter = hdr["M"]
    sharps, kl, ka, kmode = parse_key(hdr["K"])
    ks = key_sig_map(sharps)
    keys = [{"compasso": None, "K": hdr["K"]}]

    measures = []          # lista de dicts {numero, inicio, dur, volta, tom}
    notes = []             # notas da melodia (ligaduras fundidas)
    chords = []            # cifras na ordem do arquivo
    annotations = []       # outras anotações ("^FIM", "_letra")
    pos = F(0)
    cur = {"idx": 0, "inicio": F(0), "volta": None, "K": hdr["K"], "M": meter}
    bar_acc = {}
    pending_chords = []
    tie_open = None
    tuplet = None  # [restantes, fator]
    broken = None  # fator para a próxima nota
    last_note = None

    def close_measure():
        nonlocal cur, bar_acc
        dur = pos - cur["inicio"]
        if dur > 0:
            measures.append({"idx": cur["idx"], "inicio": cur["inicio"], "dur": dur,
                             "volta": cur["volta"], "K": cur["K"], "M": cur["M"]})
            cur = {"idx": cur["idx"] + 1, "inicio": pos, "volta": None, "K": cur["K"], "M": cur["M"]}
        bar_acc = {}

    def add_event(dur, pitch=None, rest=False, tie_from=False):
        nonlocal pos, pending_chords, last_note, tie_open
        for c in pending_chords:
            c["pos"] = pos
            c["medida_idx"] = cur["idx"]
            chords.append(c)
        pending_chords = []
        if rest:
            pos += dur
            tie_open = None
            return
        if tie_open is not None and tie_open["midi"] == pitch:
            tie_open["dur"] += dur
            tie_open["ligada"] = True
            pos += dur
            last_note = tie_open
            return
        n = {"pos": pos, "dur": dur, "midi": pitch, "medida_idx": cur["idx"]}
        notes.append(n)
        last_note = n
        pos += dur

    for raw_line in body_lines:
        line = raw_line.split("%")[0]
        st = line.strip()
        if not st:
            continue
        mf = re.match(r"^([A-Za-z]):(.*)$", st)
        if mf:
            fld, val = mf.group(1), mf.group(2).strip()
            if fld == "K":
                sharps, kl, ka, kmode = parse_key(val)
                ks = key_sig_map(sharps)
                cur["K"] = val
                keys.append({"compasso_idx": cur["idx"], "K": val})
            elif fld == "M":
                meter = val
                cur["M"] = val
            continue
        i = 0
        L = len(line)
        while i < L:
            ch = line[i]
            if ch == '"':
                j = line.index('"', i + 1)
                content = line[i + 1:j]
                if content and content[0] in "^_<>@":
                    annotations.append({"texto": content, "pos": pos, "medida_idx": cur["idx"]})
                else:
                    pending_chords.append({"cifra": content, "ordem": len(chords) + len(pending_chords)})
                i = j + 1
                continue
            if ch == "!":
                j = line.index("!", i + 1)
                annotations.append({"texto": line[i:j + 1], "pos": pos, "medida_idx": cur["idx"]})
                i = j + 1
                continue
            if ch == "{":
                i = line.index("}", i) + 1
                continue
            if ch == "[" and i + 1 < L and line[i + 1] in "KM" and line[i + 2:i + 3] == ":":
                j = line.index("]", i)
                fld, val = line[i + 1], line[i + 3:j].strip()
                if fld == "K":
                    sharps, kl, ka, kmode = parse_key(val)
                    ks = key_sig_map(sharps)
                    cur["K"] = val
                    keys.append({"compasso_idx": cur["idx"], "K": val})
                else:
                    meter = val
                    cur["M"] = val
                i = j + 1
                continue
            if ch in "|:[" and not (ch == "[" and i + 1 < L and line[i + 1] in "ABCDEFGabcdefg^_=z"):
                m = re.match(r"(:*\|+\]?:*|:+\|*|\[\|)?\s*(\[?\d+(?:[,-]\d+)*)?", line[i:])
                tok, volta = (m.group(1) or ""), m.group(2)
                if tok:
                    close_measure()
                    if ":" in tok and "|" not in tok and False:
                        pass
                if volta and (tok or volta.startswith("[")):
                    cur["volta"] = volta.lstrip("[")
                adv = m.end() if m.end() > 0 else 1
                i += adv
                continue
            if ch == "(" and i + 1 < L and line[i + 1].isdigit():
                p = int(line[i + 1])
                q = {2: 3, 3: 2, 4: 3, 5: 2, 6: 2, 7: 2, 8: 3, 9: 2}.get(p, 2)
                tuplet = [p, F(q, p)]
                i += 2
                continue
            if ch == "[":
                # acorde de notas: pega a nota mais aguda
                j = line.index("]", i)
                inner = line[i + 1:j]
                durm = re.search(r"\](\d*/*\d*)", line[j:j + 6])
                best = None
                for mm in NOTE_RE.finditer(inner):
                    p = pitch_of(mm, ks, bar_acc)
                    d = parse_len(mm.group(4))
                    if best is None or p > best[0]:
                        best = (p, d)
                if best:
                    d = best[1] * (parse_len(durm.group(1)) if durm and durm.group(1) else 1)
                    dur = d * unit
                    if tuplet:
                        dur *= tuplet[1]; tuplet[0] -= 1
                        if tuplet[0] == 0: tuplet = None
                    add_event(dur, best[0])
                i = j + 1 + (len(durm.group(1)) if durm else 0)
                continue
            m = NOTE_RE.match(line, i)
            if m:
                p = pitch_of(m, ks, bar_acc)
                dur = parse_len(m.group(4)) * unit
                if broken:
                    dur *= broken; broken = None
                if tuplet:
                    dur *= tuplet[1]; tuplet[0] -= 1
                    if tuplet[0] == 0: tuplet = None
                i = m.end()
                k = i
                while k < L and line[k] == " ":
                    k += 1
                if k < L and line[k] in "<>":
                    nb = 1
                    while k + nb < L and line[k + nb] == line[k]:
                        nb += 1
                    f = F(2 ** (nb + 1) - 1, 2 ** nb)
                    if line[k] == ">":
                        dur *= f; broken = 2 - f
                    else:
                        dur *= 2 - f; broken = f
                    i = k + nb
                prev_tie = tie_open
                add_event(dur, p)
                if i < L and line[i] == "-":
                    tie_open = last_note
                    i += 1
                elif prev_tie is not None and last_note is prev_tie:
                    tie_open = None
                else:
                    tie_open = None
                continue
            mr = re.match(r"([zxZX])(\d*/*\d*)", line[i:])
            if mr:
                if mr.group(1) in "ZX":
                    n = int(mr.group(2) or 1)
                    for _ in range(n):
                        add_event(parse_meter(meter), rest=True)
                        close_measure()
                else:
                    dur = parse_len(mr.group(2)) * unit
                    if broken:
                        dur *= broken; broken = None
                    if tuplet:
                        dur *= tuplet[1]; tuplet[0] -= 1
                        if tuplet[0] == 0: tuplet = None
                    add_event(dur, rest=True)
                i += mr.end()
                continue
            i += 1
    close_measure()
    for c in pending_chords:
        c["pos"] = pos
        c["medida_idx"] = cur["idx"]
        chords.append(c)
    return measures, notes, chords, annotations, keys


def pitch_of(m, ks, bar_acc):
    acc, letter, octs = m.group(1), m.group(2), m.group(3)
    up = letter.upper()
    octave = 5 if letter.islower() else 4
    octave += octs.count("'") - octs.count(",")
    key = (up, octave)
    if acc:
        alter = {"^": 1, "^^": 2, "_": -1, "__": -2, "=": 0}[acc]
        bar_acc[key] = alter
    else:
        alter = bar_acc.get(key, ks[up])
    return 12 * (octave + 1) + LETTER_PC[up] + alter


# --------------------------------------------------------- tom (Krumhansl) ---
KK_MAJ = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MIN = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
PC_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def corr(a, b):
    ma, mb = sum(a) / 12, sum(b) / 12
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0


def estimate_keys(hist, top=3):
    res = []
    for t in range(12):
        rot = hist[t:] + hist[:t]
        res.append((corr(rot, KK_MAJ), PC_NAMES[t], "maior"))
        res.append((corr(rot, KK_MIN), PC_NAMES[t], "menor"))
    res.sort(reverse=True)
    return [{"tom": f"{n}{'m' if mo == 'menor' else ''}", "modo": mo, "correlacao": round(c, 3)} for c, n, mo in res[:top]]


# ------------------------------------------------------------------ fatos ---
def beat_info(rel_pos: F, meter: str):
    beat_len, nbeats = meter_beats(meter)
    b = rel_pos / beat_len
    beat_no = int(b) + 1
    on_beat = b.denominator == 1
    if on_beat and beat_no == 1:
        forca = "forte"
    elif on_beat and nbeats == 4 and beat_no == 3:
        forca = "meio-forte"
    elif on_beat:
        forca = "fraco"
    else:
        forca = "contratempo"
    frac = b - int(b)
    return beat_no, (str(frac) if frac else ""), forca


def build_facts(path: Path):
    hdr, body = read_abc(path)
    measures, notes, chords, annotations, keys = parse_body(hdr, body)
    # numeração: anacruse = compasso 0
    full = parse_meter(hdr["M"])
    first_num = 0 if measures and measures[0]["dur"] < full else 1
    num_of = {m["idx"]: first_num + k for k, m in enumerate(measures)}
    start_of = {m["idx"]: m["inicio"] for m in measures}
    meter_of = {m["idx"]: m["M"] for m in measures}

    parsed = []
    for k, c in enumerate(chords):
        info = parse_chord(c["cifra"])
        end = chords[k + 1]["pos"] if k + 1 < len(chords) else (measures[-1]["inicio"] + measures[-1]["dur"] if measures else c["pos"])
        rel = c["pos"] - start_of.get(c["medida_idx"], 0)
        beat_no, frac, _ = beat_info(rel, meter_of.get(c["medida_idx"], hdr["M"]))
        parsed.append({"idx": k, "compasso": num_of.get(c["medida_idx"]), "tempo": beat_no,
                       "inicio": c["pos"], "fim": end, **(info or {"cifra": c["cifra"], "erro": "cifra não reconhecida"})})

    def chord_at(p):
        cur = None
        for c in parsed:
            if c["inicio"] <= p:
                cur = c
            else:
                break
        return cur

    nfacts = []
    hist = [0.0] * 12
    for n in notes:
        c = chord_at(n["pos"])
        rel = n["pos"] - start_of.get(n["medida_idx"], 0)
        beat_no, frac, forca = beat_info(rel, meter_of.get(n["medida_idx"], hdr["M"]))
        item = {"compasso": num_of.get(n["medida_idx"]), "tempo": beat_no, "fracao_tempo": frac,
                "forca": forca, "nota": midi_name(n["midi"]), "midi": n["midi"],
                "duracao_semiminimas": str(n["dur"] * 4), "ligada": n.get("ligada", False)}
        hist[n["midi"] % 12] += float(n["dur"])
        if c and "pcs" in c:
            iv = (n["midi"] - c["fundamental_pc"]) % 12
            item["cifra_idx"] = c["idx"]
            item["cifra"] = c["cifra"]
            item["intervalo"] = interval_label(iv, c)
            if iv in c["notas_base_rel"]:
                item["relacao"] = "nota do acorde"
            elif iv in c["tensoes_rel"]:
                item["relacao"] = "tensão escrita na cifra"
            elif iv in available_tensions(c):
                item["relacao"] = "tensão disponível (não escrita)"
            else:
                item["relacao"] = "fora do acorde"
        # nota ligada que atravessa uma troca de cifra: o papel dela muda
        atr = []
        for c2 in parsed:
            if "pcs" in c2 and n["pos"] < c2["inicio"] < n["pos"] + n["dur"]:
                iv2 = (n["midi"] - c2["fundamental_pc"]) % 12
                atr.append({"cifra_idx": c2["idx"], "cifra": c2["cifra"], "compasso": c2["compasso"],
                            "intervalo": interval_label(iv2, c2)})
        if atr:
            item["sustentada_sobre"] = atr
        nfacts.append(item)
    for c in parsed:
        if "pcs" in c:
            for pc in c["pcs_base"]:
                hist[pc] += float(c["fim"] - c["inicio"]) * 0.5

    # janelas de 4 compassos
    janelas = []
    nums = sorted(set(num_of.values()))
    for a in range(0, len(nums), 4):
        grupo = set(nums[a:a + 4])
        h = [0.0] * 12
        for n, f in zip(notes, nfacts):
            if f["compasso"] in grupo:
                h[n["midi"] % 12] += float(n["dur"])
        for c in parsed:
            if c.get("compasso") in grupo and "pcs" in c:
                for pc in c["pcs_base"]:
                    h[pc] += float(c["fim"] - c["inicio"]) * 0.5
        if sum(h):
            janelas.append({"compassos": [min(grupo), max(grupo)], "candidatos": estimate_keys(h, 2)})

    ks_sharps = parse_key(hdr["K"])[0]
    fora_armadura = []
    ksm = key_sig_map(ks_sharps)
    diat = {(LETTER_PC[l] + a) % 12 for l, a in ksm.items()}
    for f in nfacts:
        if f["midi"] % 12 not in diat:
            fora_armadura.append({"compasso": f["compasso"], "tempo": f["tempo"], "nota": f["nota"]})

    mids = [n["midi"] for n in notes]
    ext = {}
    if mids:
        lo, hi = min(mids), max(mids)
        ext = {"concerto": [midi_name(lo), midi_name(hi)], "amplitude_semitons": hi - lo}
        for inst, t in (("alto", 9), ("tenor", 14)):
            for oc in (0, -1):
                a, b = lo + t + 12 * oc, hi + t + 12 * oc
                ok = a >= 58 and b <= 90  # Bb3 .. F#6 escritos
                ext[f"{inst}{'' if oc == 0 else '_8vb'}"] = {"escrito": [midi_name(a), midi_name(b)],
                                                            "dentro_da_extensao": ok}
        ponto = max(range(len(mids)), key=lambda k: mids[k])
        ext["ponto_culminante"] = {"nota": midi_name(hi), "compasso": nfacts[ponto]["compasso"],
                                   "tempo": nfacts[ponto]["tempo"]}

    intervalos = []
    for a, b, fa, fb in zip(notes, notes[1:], nfacts, nfacts[1:]):
        d = b["midi"] - a["midi"]
        if abs(d) >= 9:
            intervalos.append({"de": f"c. {fa['compasso']} {fa['nota']}", "para": f"c. {fb['compasso']} {fb['nota']}",
                               "semitons": d})

    def jsonable(o):
        if isinstance(o, F):
            return str(o)
        if isinstance(o, dict):
            return {k: jsonable(v) for k, v in o.items()}
        if isinstance(o, list):
            return [jsonable(v) for v in o]
        return o

    out = {
        "titulo": hdr["T"], "compositor": hdr["C"], "compasso": hdr["M"], "armadura": hdr["K"],
        "mudancas_de_armadura": [{"compasso": num_of.get(k["compasso_idx"]), "K": k["K"]} for k in keys[1:]],
        "compassos": [{"numero": num_of[m["idx"]], "casa": m["volta"], "duracao": str(m["dur"])} for m in measures],
        "cifras": [{k: v for k, v in c.items() if k not in ("inicio", "fim")} for c in parsed],
        "notas": nfacts,
        "tom_estimado_geral": estimate_keys(hist),
        "tom_por_janela": janelas,
        "notas_fora_da_armadura": fora_armadura,
        "extensao": ext,
        "saltos_de_sexta_ou_mais": intervalos,
        "anotacoes": [{"texto": a["texto"], "compasso": num_of.get(a["medida_idx"])} for a in annotations],
    }
    return jsonable(out), parsed, notes, nfacts


def interval_label(iv, c):
    """Nome do intervalo no contexto da cifra (b3 num menor, #9 num dominante...)."""
    if iv == 3:
        return "b3" if c["terca"] == 3 else "#9"
    if iv == 5:
        return "4" if c["terca"] == 5 else "11"
    if iv == 6:
        return "b5" if c["quinta"] == 6 else "#11"
    if iv == 8:
        return "#5" if c["quinta"] == 8 else "b13"
    if iv == 9:
        if c["setima"] == 9:
            return "7°"
        return "13" if c["setima"] is not None else "6"
    return INTERVALO_NOME[iv]


def available_tensions(c):
    """Tensões disponíveis (regra usual de jazz/Chediak): 9 / 11 / 13 sem choque
    de meio tom acima de nota do acorde."""
    base = set(c["notas_base_rel"])
    av = set()
    for t in (1, 2, 3, 5, 6, 8, 9):
        if t in base:
            continue
        if c["dominante"]:
            if t in (1, 2, 3, 6, 8, 9):
                av.add(t)
            continue
        if (t - 1) % 12 in base:
            continue  # nota a evitar: meio tom acima de nota do acorde
        av.add(t)
    return av


# ------------------------------------------------------- checagem de graus ---
ROMAN = {"I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11}


def parse_degree(s):
    s = norm_acc(s.strip())
    m = re.match(r"^(b|#)?(VII|VI|V|IV|III|II|I)(.*)$", s)
    if not m:
        return None
    off = {"b": -1, "#": 1}.get(m.group(1), 0)
    return (ROMAN[m.group(2)] + off) % 12, m.group(3)


def key_tonic(k):
    s = norm_acc(k.strip())
    m = re.match(r"^([A-G])(#|b)?(m)?", s)
    letter, acc = m.group(1), m.group(2) or ""
    return note_pc(letter, 1 if acc == "#" else -1 if acc == "b" else 0), bool(m.group(3))


def quality_ok(suffix, c):
    """Confere se a qualidade escrita no grau bate com a cifra."""
    suf = suffix.replace(" ", "")
    if not suf:
        return True, ""
    if suf.startswith(("m7(b5)", "m7b5", "ø")):
        return c["tipo"] == "m7(b5)", "esperava m7(b5)"
    if suf.startswith(("°", "º", "dim")):
        return c["tipo"] in ("°7", "°"), "esperava diminuto"
    if suf.startswith("m"):
        return c["terca"] == 3, "esperava acorde menor"
    if suf.startswith("7M") or suf.startswith("Δ"):
        return c["setima"] == 11 and c["terca"] == 4, "esperava 7M (maior com sétima maior)"
    if suf.startswith("7"):
        return c["dominante"] or c["tipo"] == "7sus4", "esperava acorde dominante (3ª maior e 7ª menor)"
    if suf.startswith("6"):
        return c["terca"] == 4, "esperava acorde maior com 6ª"
    return True, ""


def check_analysis(parsed, analysis):
    """Confere cada grau escrito pelo Claude contra a cifra real."""
    by_idx = {c["idx"]: c for c in parsed}
    report = []
    entries = analysis.get("acordes", [])
    for k, e in enumerate(entries):
        c = by_idx.get(e["idx"])
        r = {"idx": e["idx"], "cifra": e.get("cifra"), "grau": e.get("grau"), "problemas": []}
        if c is None or "pcs" not in c:
            r["problemas"].append("cifra não encontrada ou não reconhecida")
            report.append(r); continue
        if e.get("cifra") and norm_acc(e["cifra"]).replace(" ", "") != norm_acc(c["cifra"]).replace(" ", ""):
            r["problemas"].append(f"cifra do índice {e['idx']} é {c['cifra']}, não {e['cifra']}")
        tonic, _ = key_tonic(e["tom_local"])
        g = e["grau"].replace("–", "-")
        root_rel = (c["fundamental_pc"] - tonic) % 12
        mm = re.match(r"^(SubV7|SubV|V7|V|IIm7\(b5\)|IIm7|IIm|VII°|VII°7|°)(?:\([^)]*\))?/(.+)$", norm_acc(g))
        alvo_rel = None
        if mm:
            kind, tgt = mm.group(1), mm.group(2)
            pd = parse_degree(tgt)
            if not pd:
                r["problemas"].append(f"alvo '{tgt}' não reconhecido")
                report.append(r); continue
            alvo_rel = pd[0]
            exp = {"SubV7": 1, "SubV": 1, "V7": 7, "V": 7, "IIm7(b5)": 2, "IIm7": 2, "IIm": 2,
                   "VII°": 11, "VII°7": 11, "°": 11}[kind]
            if (alvo_rel + exp) % 12 != root_rel:
                r["problemas"].append(f"fundamental {c['fundamental']} não fica a {exp} semitons acima do alvo {tgt} em {e['tom_local']}")
            if kind.startswith(("SubV", "V")) and not c["dominante"]:
                r["problemas"].append("um dominante (secundário ou SubV) precisa de 3ª maior e 7ª menor")
            if kind.startswith(("VII°", "°")) and c["tipo"] not in ("°7", "°"):
                r["problemas"].append("esperava acorde diminuto")
        else:
            pd = parse_degree(g)
            if not pd:
                r["problemas"].append(f"grau '{g}' não reconhecido")
                report.append(r); continue
            if pd[0] != root_rel:
                r["problemas"].append(f"em {e['tom_local']}, {c['fundamental']} é o grau de {root_rel} semitons, não {g}")
            ok, why = quality_ok(pd[1], c)
            if not ok:
                r["problemas"].append(f"qualidade: {why}; a cifra é {c['tipo']}")
        # resolução
        nxt_idx = e.get("proximo_idx", entries[k + 1]["idx"] if k + 1 < len(entries) else None)
        if alvo_rel is not None and nxt_idx is not None:
            nxt = by_idx.get(nxt_idx)
            if nxt and "pcs" in nxt:
                nrel = (nxt["fundamental_pc"] - tonic) % 12
                r["resolucao"] = "resolveu no alvo" if nrel == alvo_rel else f"não resolveu no alvo (foi para {nxt['cifra']})"
        r["ok"] = not r["problemas"]
        report.append(r)
    return report


# -------------------------------------------------------------- escalas ---
SCALES = {
    # modos da escala maior
    "jônio": [0, 2, 4, 5, 7, 9, 11], "maior": [0, 2, 4, 5, 7, 9, 11],
    "dórico": [0, 2, 3, 5, 7, 9, 10], "frígio": [0, 1, 3, 5, 7, 8, 10],
    "lídio": [0, 2, 4, 6, 7, 9, 11], "mixolídio": [0, 2, 4, 5, 7, 9, 10],
    "eólio": [0, 2, 3, 5, 7, 8, 10], "menor natural": [0, 2, 3, 5, 7, 8, 10],
    "lócrio": [0, 1, 3, 5, 6, 8, 10],
    # menor harmônica e modos
    "menor harmônica": [0, 2, 3, 5, 7, 8, 11], "lócrio 6": [0, 1, 3, 5, 6, 9, 10],
    "jônio #5": [0, 2, 4, 5, 8, 9, 11], "dórico #4": [0, 2, 3, 6, 7, 9, 10],
    "mixolídio b9 b13": [0, 1, 4, 5, 7, 8, 10], "frígio dominante": [0, 1, 4, 5, 7, 8, 10],
    "lídio #2": [0, 3, 4, 6, 7, 9, 11],
    # menor melódica e modos
    "menor melódica": [0, 2, 3, 5, 7, 9, 11], "dórico b2": [0, 1, 3, 5, 7, 9, 10],
    "lídio aumentado": [0, 2, 4, 6, 8, 9, 11], "lídio b7": [0, 2, 4, 6, 7, 9, 10],
    "mixolídio b13": [0, 2, 4, 5, 7, 8, 10], "lócrio 2": [0, 2, 3, 5, 6, 8, 10],
    "alterada": [0, 1, 3, 4, 6, 8, 10], "superlócrio": [0, 1, 3, 4, 6, 8, 10],
    # simétricas e pentatônicas
    "diminuta semitom-tom": [0, 1, 3, 4, 6, 7, 9, 10], "dominante diminuta": [0, 1, 3, 4, 6, 7, 9, 10],
    "diminuta tom-semitom": [0, 2, 3, 5, 6, 8, 9, 11], "tons inteiros": [0, 2, 4, 6, 8, 10],
    "pentatônica maior": [0, 2, 4, 7, 9], "pentatônica menor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10], "blues maior": [0, 2, 3, 4, 7, 9],
    "bebop dominante": [0, 2, 4, 5, 7, 9, 10, 11],
}


def strip_accents(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s) if unicodedata.category(ch) != "Mn")


SCALES_NORM = {strip_accents(k).lower(): k for k in SCALES}


def parse_scale(s):
    s = norm_acc(s.strip())
    m = re.match(r"^([A-G])(#|b)?\s+(.+)$", s)
    if not m:
        raise ValueError(f"escala inválida: {s!r} (use 'A dórico')")
    name = strip_accents(m.group(3)).lower().replace("♮", "").strip()
    if name not in SCALES_NORM:
        raise ValueError(f"escala desconhecida: {m.group(3)!r}")
    letter, alter = m.group(1), (1 if m.group(2) == "#" else -1 if m.group(2) == "b" else 0)
    key = SCALES_NORM[name]
    return letter, alter, key, SCALES[key]


def check_scales(parsed, notes, nfacts, impro):
    by_idx = {c["idx"]: c for c in parsed}
    out = []
    for t in impro.get("trechos", []):
        for o in t.get("opcoes", []):
            c = by_idx.get(o["idx"])
            letter, alter, nome, steps = parse_scale(o["escala"])
            root = note_pc(letter, alter)
            pcs = {(root + s) % 12 for s in steps}
            choque = [interval_label((pc - c["fundamental_pc"]) % 12, c) for pc in c["pcs"] if pc not in pcs]
            mel = [f for f in nfacts if f.get("cifra_idx") == o["idx"]]
            fora = [f"c. {f['compasso']} {f['nota']}" for f in mel if f["midi"] % 12 not in pcs]
            nivel = o.get("nivel")
            prob = []
            if nivel == "segura" and choque:
                prob.append("opção 'segura' não contém todas as notas da cifra")
            item = {"idx": o["idx"], "cifra": c["cifra"], "escala": o["escala"], "nivel": nivel,
                    "notas_da_cifra_fora_da_escala": choque, "melodia_fora_da_escala": fora,
                    "melodia_total": len(mel), "problemas": prob, "ok": not prob}
            out.append(item)
    return out


def spell_scale(letter, alter, steps):
    """Soletra a escala com uma letra por grau quando possível (7 notas)."""
    root_pc = note_pc(letter, alter)
    res = []
    if len(steps) == 7:
        li = LETTERS.index(letter)
        for k, s in enumerate(steps):
            l2 = LETTERS[(li + k) % 7]
            want = (root_pc + s) % 12
            a = (want - LETTER_PC[l2] + 6) % 12 - 6
            res.append((l2, a))
        return res
    flat = alter < 0 or (letter, alter) in (("F", 0),)
    for s in steps:
        pc = (root_pc + s) % 12
        name = (PC_NAMES if flat else ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])[pc]
        if not flat and name == "Db":
            name = "C#"
        res.append(parse_note_name(name))
    return res


def transpose_name(letter, alter, letter_steps, semis):
    li = LETTERS.index(letter)
    l2 = LETTERS[(li + letter_steps) % 7]
    want = (note_pc(letter, alter) + semis) % 12
    a = (want - LETTER_PC[l2] + 6) % 12 - 6
    return l2, a


def best_spelling(letter, alter, steps):
    cands = [(letter, alter)]
    pc = note_pc(letter, alter)
    for l in LETTERS:
        for a in (-1, 0, 1):
            if note_pc(l, a) == pc and (l, a) != (letter, alter):
                cands.append((l, a))
    def cost(c):
        sp = spell_scale(c[0], c[1], steps)
        return (sum(abs(a) > 1 for _, a in sp) * 10 + sum(abs(a) for _, a in sp), c != (letter, alter))
    return min(cands, key=cost)


def scale_abc(letter, alter, steps):
    """Escala ascendente de uma oitava em ABC (K:C, acidentes explícitos),
    com a tônica escrita entre C4 e B4."""
    sp = spell_scale(letter, alter, steps) + [spell_scale(letter, alter, steps)[0]]
    out, prev_midi, state = [], None, {}
    base_oct = 4
    root_midi = 12 * (base_oct + 1) + LETTER_PC[letter] + alter
    if root_midi < 60:
        base_oct += 1
    for k, (l, a) in enumerate(sp):
        midi_guess = 12 * (base_oct + 1) + LETTER_PC[l] + a
        while prev_midi is not None and midi_guess <= prev_midi:
            midi_guess += 12
        prev_midi = midi_guess
        octv = (midi_guess - a - LETTER_PC[l]) // 12 - 1
        acc = ""
        if state.get((l, octv), 0) != a:
            acc = {-2: "__", -1: "_", 0: "=", 1: "^", 2: "^^"}[a]
            state[(l, octv)] = a
        name = l.lower() + "'" * (octv - 5) if octv >= 5 else l + "," * (4 - octv)
        out.append(acc + name)
    return " ".join(out)


def build_scales_abc(title, impro):
    """Folha de escalas: concerto, alto e tenor (escrito)."""
    insts = [("Concerto (C)", 0, 0), ("Sax Alto (Eb) escrito", 5, 9), ("Sax Tenor (Bb) escrito", 1, 2)]
    tunes = []
    for x, (iname, lsteps, semis) in enumerate(insts, 1):
        lines = [f"X:{x}", f"T:{title} - escalas de improviso", f"T:{iname}", "M:none", "L:1/4", "K:C"]
        for t in impro.get("trechos", []):
            first = True
            for o in t.get("opcoes", []):
                letter, alter, nome, steps = parse_scale(o["escala"])
                l2, a2 = transpose_name(letter, alter, lsteps, semis)
                l2, a2 = best_spelling(l2, a2, steps)
                nota = NOMES_PT[l2] + ("♯" * a2 if a2 > 0 else "♭" * -a2)
                label = f"{o.get('cifra_rotulo', '')} · {o.get('nivel', '')}: {nota} {nome}".replace('"', "'")
                pre = ""
                if first:
                    pre = '"^' + t.get("titulo", "").replace('"', "'") + '"'
                    lines.append("%")
                    first = False
                lines.append(f'"_{label}"' + pre + scale_abc(l2, a2, steps) + " |]")
        tunes.append("\n".join(lines))
    return "\n\n".join(tunes) + "\n"


# ---------------------------------------------------------------- resumo ---
def resumo(f):
    """Versão compacta dos fatos, só com o que a análise usa (economiza tokens)."""
    L = [f"{f['titulo']} | M:{f['compasso']} K:{f['armadura']} | {len(f['compassos'])} compassos"]
    if f["mudancas_de_armadura"]:
        L.append("mudanças de armadura: " + ", ".join(f"c.{m['compasso']} K:{m['K']}" for m in f["mudancas_de_armadura"]))
    casas = [f"c.{c['numero']}=casa {c['casa']}" for c in f["compassos"] if c["casa"]]
    if casas:
        L.append("casas: " + ", ".join(casas))
    L.append("tom geral: " + ", ".join(f"{k['tom']} {k['correlacao']}" for k in f["tom_estimado_geral"]))
    L.append("tom por janela: " + " | ".join(
        f"c.{j['compassos'][0]}-{j['compassos'][1]} {j['candidatos'][0]['tom']} {j['candidatos'][0]['correlacao']}"
        for j in f["tom_por_janela"]))
    L.append("cifras (idx c.tempo cifra = tipo +tensões /baixo):")
    row = []
    for c in f["cifras"]:
        if "erro" in c:
            row.append(f"#{c['idx']} c.{c['compasso']}.{c['tempo']} {c['cifra']} = ??")
            continue
        t = "+" + ",".join(str(x) for x in c["tensoes_rel"]) if c["tensoes_rel"] else ""
        b = "/" + c["baixo"] if c["baixo"] else ""
        row.append(f"#{c['idx']} c.{c['compasso']}.{c['tempo']} {c['cifra']}={c['tipo']}{t}{b}")
    L += ["  " + " ; ".join(row[i:i + 4]) for i in range(0, len(row), 4)]
    mel, cur = [], None
    for n in f["notas"]:
        if n["compasso"] != cur:
            cur = n["compasso"]
            mel.append(f"|{cur}:")
        mel.append(n["nota"])
    L.append("melodia por compasso: " + " ".join(mel))
    L.append("notas que não são nota do acorde, ou sustentadas sobre troca de cifra (c.tempo nota intervalo/cifra força):")
    for n in f["notas"]:
        rel = n.get("relacao")
        sus = n.get("sustentada_sobre")
        if rel in (None, "nota do acorde") and not sus:
            continue
        tag = {"tensão escrita na cifra": "T", "tensão disponível (não escrita)": "td", "fora do acorde": "FORA"}.get(rel, "")
        x = f"  c.{n['compasso']}.{n['tempo']}{('+' + n['fracao_tempo']) if n['fracao_tempo'] else ''} {n['nota']} {n.get('intervalo', '')}/{n.get('cifra', '')} {tag} {n['forca']}"
        if sus:
            x += " -> " + ", ".join(f"vira {a['intervalo']} de {a['cifra']} (c.{a['compasso']})" for a in sus)
        L.append(x)
    if f["notas_fora_da_armadura"]:
        L.append("fora da armadura: " + ", ".join(f"c.{n['compasso']}.{n['tempo']} {n['nota']}" for n in f["notas_fora_da_armadura"]))
    e = f["extensao"]
    if e:
        L.append(f"extensão: {e['concerto'][0]}-{e['concerto'][1]} ({e['amplitude_semitons']} st); culminante {e['ponto_culminante']['nota']} c.{e['ponto_culminante']['compasso']}.{e['ponto_culminante']['tempo']}")
    if f["saltos_de_sexta_ou_mais"]:
        L.append("saltos >= 6ª: " + ", ".join(f"{s['de']}->{s['para'].split()[-1]} ({s['semitons']:+d})" for s in f["saltos_de_sexta_ou_mais"]))
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------- main ---
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fatos"); p.add_argument("abc", type=Path); p.add_argument("-o", type=Path)
    p = sub.add_parser("resumo"); p.add_argument("abc", type=Path); p.add_argument("-o", type=Path)
    p = sub.add_parser("checar"); p.add_argument("abc", type=Path); p.add_argument("analise", type=Path)
    p = sub.add_parser("escalas"); p.add_argument("abc", type=Path); p.add_argument("improviso", type=Path); p.add_argument("-o", type=Path)
    a = ap.parse_args()

    stem = a.abc.stem.replace("_concerto", "")
    # musicas/ guarda só .abc: fatos e resumo vão para analises/ (pasta irmã)
    dir_an = a.abc.parent.parent / "analises" if a.abc.parent.name == "musicas" else a.abc.parent
    facts, parsed, notes, nfacts = build_facts(a.abc)
    if a.cmd == "fatos":
        out = a.o or dir_an / (stem + "_fatos.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
        bad = [c["cifra"] for c in facts["cifras"] if "erro" in c]
        print(f"{len(facts['compassos'])} compassos, {len(facts['cifras'])} cifras, {len(facts['notas'])} notas -> {out}")
        print("tom estimado:", ", ".join(f"{k['tom']} ({k['correlacao']})" for k in facts["tom_estimado_geral"]))
        if bad:
            print("CIFRAS NÃO RECONHECIDAS:", bad)
    elif a.cmd == "resumo":
        txt = resumo(facts)
        out = a.o or dir_an / (stem + "_resumo.txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(txt, encoding="utf-8")
        print(txt)
    elif a.cmd == "checar":
        an = json.loads(a.analise.read_text(encoding="utf-8"))
        rep = check_analysis(parsed, an)
        falhas = [r for r in rep if not r.get("ok")]
        for r in rep:
            flag = "OK " if r.get("ok") else "ERRO"
            res = f" [{r['resolucao']}]" if r.get("resolucao") else ""
            print(f"{flag} #{r['idx']:>2} {r['cifra']:<14} {r['grau']:<14}{res}")
            for pb in r["problemas"]:
                print("       -", pb)
        print(f"\n{len(rep) - len(falhas)}/{len(rep)} graus conferem.")
        if "trechos" in an:
            pass
        sys.exit(1 if falhas else 0)
    elif a.cmd == "escalas":
        im = json.loads(a.improviso.read_text(encoding="utf-8"))
        rep = check_scales(parsed, notes, nfacts, im)
        falhas = [r for r in rep if not r["ok"]]
        for r in rep:
            flag = "OK " if r["ok"] else "ERRO"
            print(f"{flag} #{r['idx']:>2} {r['cifra']:<14} {r['nivel'] or '':<8} {r['escala']:<26} "
                  f"cifra fora: {r['notas_da_cifra_fora_da_escala'] or '-'}  melodia fora: {len(r['melodia_fora_da_escala'])}/{r['melodia_total']}")
            for pb in r["problemas"]:
                print("       -", pb)
        out = a.o or a.abc.with_name(stem + "_escalas.abc")
        by_idx = {c["idx"]: c for c in parsed}
        for t in im.get("trechos", []):
            for o in t.get("opcoes", []):
                o.setdefault("cifra_rotulo", by_idx[o["idx"]]["cifra"])
        out.write_text(build_scales_abc(facts["titulo"], im), encoding="utf-8")
        print(f"\nfolha de escalas -> {out}")
        sys.exit(1 if falhas else 0)

if __name__ == "__main__":
    main()
