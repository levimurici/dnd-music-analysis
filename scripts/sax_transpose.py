#!/usr/bin/env python3
"""
sax_transpose.py - Lê uma lead sheet em tom de concerto (MusicXML ou ABC) e gera
um arquivo ABC com a melodia transposta para sax alto (Eb) e/ou sax tenor (Bb),
mantendo as cifras no tom de CONCERTO.

Uso:
  python scripts/sax_transpose.py entrada.musicxml -o saida.abc
  python scripts/sax_transpose.py entrada.abc --inst alto tenor --layout voices
  python scripts/sax_transpose.py entrada.mxl --inst alto --octave -1

Layouts:
  tunes  (padrão) -> uma música por instrumento (X:1 Concerto, X:2 Alto, X:3 Tenor).
                     No editor.drawthedots.com cada uma aparece como uma partitura.
  voices          -> uma única partitura com sistemas de duas vozes
                     (melodia de concerto em cima, melodia transposta embaixo).

Transposição escrita (padrão):
  alto  = sexta maior acima  (+9 semitons)  -> Eb
  tenor = nona maior acima   (+14 semitons) -> Bb
"""
import argparse
import re
import sys
from fractions import Fraction
from pathlib import Path

from music21 import converter, harmony, interval, key, meter, note, chord, bar, spanner, stream, tempo

INSTRUMENTS = {
    "concert": {"name": "Concerto (C)", "short": "C", "interval": "P1"},
    "alto": {"name": "Sax Alto (Eb)", "short": "Alto", "interval": "M6"},
    "tenor": {"name": "Sax Tenor (Bb)", "short": "Ten.", "interval": "M9"},
}

UNIT = Fraction(1, 8)  # L:1/8
SHARPS_ORDER = "FCGDAEB"
FLATS_ORDER = "BEADGCF"


# ---------------------------------------------------------------- helpers ---
def key_signature_map(sharps: int) -> dict:
    """step -> alteração implicada pela armadura."""
    m = {s: 0 for s in "CDEFGAB"}
    if sharps > 0:
        for s in SHARPS_ORDER[:sharps]:
            m[s] = 1
    elif sharps < 0:
        for s in FLATS_ORDER[: -sharps]:
            m[s] = -1
    return m


def simplify_key(k: key.KeySignature) -> key.KeySignature:
    """Evita armaduras com mais de 6 acidentes (ex.: C# maior -> Db maior)."""
    s = k.sharps
    if s > 6:
        s -= 12
    elif s < -6:
        s += 12
    if s == k.sharps:
        return k
    new = key.KeySignature(s)
    if isinstance(k, key.Key):
        return new.asKey(k.mode)
    return new


def abc_key_name(k) -> str:
    if isinstance(k, key.Key):
        tonic = k.tonic.name.replace("-", "b")
        return tonic + ("m" if k.mode == "minor" else "")
    # KeySignature sem modo -> assume maior
    tonic = k.asKey("major").tonic.name.replace("-", "b")
    return tonic


def chord_text(cs: harmony.ChordSymbol) -> str:
    """Cifra legível em ABC: troca o '-' de bemol do music21 por 'b'."""
    fig = cs.figure or ""
    fig = re.sub(r"(?<=[A-G])-", "b", fig)
    fig = fig.replace('"', "")
    return fig


def duration_str(q: Fraction) -> str:
    """quarterLength (Fraction) -> sufixo de duração ABC relativo a L:1/8."""
    units = Fraction(q) / (UNIT * 4)  # q em semínimas -> unidades de colcheia
    if units == 1:
        return ""
    if units.denominator == 1:
        return str(units.numerator)
    if units.numerator == 1:
        return "/" * 1 if units.denominator == 2 else f"/{units.denominator}"
    return f"{units.numerator}/{units.denominator}"


def pitch_to_abc(p, bar_state: dict, ks_map: dict) -> str:
    step = p.step
    octv = p.octave if p.octave is not None else 4
    alter = int(p.accidental.alter) if p.accidental else 0
    implied = bar_state.get((step, octv), ks_map[step])
    acc = ""
    if alter != implied:
        acc = {-2: "__", -1: "_", 0: "=", 1: "^", 2: "^^"}[alter]
        bar_state[(step, octv)] = alter
    if octv >= 5:
        s = step.lower() + "'" * (octv - 5)
    else:
        s = step + "," * (4 - octv)
    return acc + s


# --------------------------------------------------------------- extração ---
def load(path: Path):
    """Carrega o arquivo. Para ABC, guarda as cifras exatamente como escritas
    (o parser do music21 descarta cifras como Cmaj9, C7alt, Ab°7, C6/9...)."""
    raw_chords = None
    if path.suffix.lower() == ".abc":
        text, raw_chords = protect_abc_chords(path.read_text(encoding="utf-8"))
        s = converter.parse(text, format="abc")
    else:
        s = converter.parse(str(path))
    if not isinstance(s, stream.Score):
        sc = stream.Score()
        sc.insert(0, s)
        s = sc
    return s, raw_chords


def protect_abc_chords(text: str):
    """Troca cada cifra "..." do corpo por "C" e devolve a lista original, em ordem."""
    raw, out, in_body = [], [], False
    bar_acc = {}
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[A-Za-z]:", stripped) or stripped.startswith("%"):
            if stripped.startswith("K:"):
                in_body = True
            out.append(line)
            continue
        if not in_body:
            out.append(line)
            continue

        def repl(mo):
            # cifras, anotações ("_Fim", "^texto") e decorações (!segno!) são
            # guardadas literalmente e devolvidas na mesma posição da saída
            raw.append(mo.group(0))
            return '"C"'

        line = re.sub(r'(?:"[^"]*"|!(?:segno|coda|fine|D\.S\.|D\.C\.|dacoda|dacapo)[^!]*!)+', repl, line)
        out.append(explicit_accidentals(line, bar_acc))
    return "\n".join(out) + "\n", raw


_NOTE_RE = re.compile(r'("[^"]*"|![^!]*!|\[\d|\|+|:+|(\^\^|\^|__|_|=)?([A-Ga-g])([,\']*))')


def explicit_accidentals(line: str, state: dict) -> str:
    """O parser ABC do music21 não aplica um acidente ao resto do compasso
    (ex.: "_e e e" vira Mib, Mi, Mi). Aqui o acidente é repetido em cada nota
    da mesma altura até a barra, como manda o padrão ABC."""
    def sub(mo):
        tok = mo.group(1)
        if tok.startswith('"') or tok.startswith("!") or tok.startswith("["):
            return tok
        if tok[0] in "|:":
            if "|" in tok:
                state.clear()
            return tok
        acc, letter, octv = mo.group(2), mo.group(3), mo.group(4)
        k = (letter, octv)
        if acc:
            state[k] = acc
            return tok
        return state.get(k, "") + letter + octv
    return _NOTE_RE.sub(sub, line)


def melody_part(score: stream.Score) -> stream.Part:
    parts = list(score.parts)
    if not parts:
        raise SystemExit("Nenhuma parte encontrada no arquivo.")
    # lead sheet: a primeira parte que tem notas
    for p in parts:
        if p.recurse().notes:
            return p
    return parts[0]


def collect_chords(part: stream.Part, raw=None) -> dict:
    """(nº do compasso, offset) -> texto da cifra, sempre em concerto."""
    out, i = {}, 0
    for m in part.getElementsByClass(stream.Measure):
        for cs in m.recurse().getElementsByClass(harmony.ChordSymbol):
            txt = raw[i] if raw is not None and i < len(raw) else f'"{chord_text(cs)}"'
            i += 1
            out.setdefault((m.number, Fraction(cs.offset).limit_denominator(64)), []).append(txt)
    if raw is not None and i != len(raw):
        print(f"AVISO: {len(raw)} cifras/anotações no ABC, {i} reconhecidas", file=sys.stderr)
    return out


# ---------------------------------------------------------------- escrita ---
def measure_to_abc(m: stream.Measure, ks_map: dict, chords: dict) -> str:
    bar_state = {}
    tokens = []
    chord_offsets = {off: txt for (num, off), txt in chords.items() if num == m.number}
    used_chords = set()
    # usa a primeira voz se houver várias
    src = m.voices[0] if m.voices else m
    elements = [e for e in src.notesAndRests if not isinstance(e, harmony.ChordSymbol)]
    tup_left = Fraction(0)
    for idx, el in enumerate(elements):
        off = Fraction(el.offset).limit_denominator(64)
        prefix = ""
        # cifras que caem antes ou no início desta nota
        for c_off in sorted(chord_offsets):
            if c_off not in used_chords and c_off <= off:
                prefix += "".join(chord_offsets[c_off])
                used_chords.add(c_off)
        dur = el.duration
        # tercinas e outras quiálteras
        tup = dur.tuplets[0] if dur.tuplets else None
        if tup is not None and tup_left <= 0:
            # novo grupo: soma as notas seguintes até completar a quiáltera
            total = Fraction(tup.totalTupletLength()).limit_denominator(64)
            acc, r = Fraction(0), 0
            for nxt in elements[idx:]:
                if not nxt.duration.tuplets or acc >= total:
                    break
                acc += Fraction(nxt.duration.quarterLength).limit_denominator(64)
                r += 1
            n, q = tup.numberNotesActual, tup.numberNotesNormal
            prefix = prefix + (f"({n}" if r == n else f"({n}:{q}:{r}")
            tup_left = total
        if tup is not None:
            tup_left -= Fraction(dur.quarterLength).limit_denominator(64)
        else:
            tup_left = Fraction(0)
        ql = Fraction(dur.quarterLength).limit_denominator(64)
        if tup is not None:
            ql = ql * Fraction(tup.numberNotesActual, tup.numberNotesNormal)
        d = duration_str(ql)
        if isinstance(el, note.Rest):
            body = ("x" if el.style.hideObjectOnPrint else "z") + d
        elif isinstance(el, chord.Chord):
            body = "[" + "".join(pitch_to_abc(p, bar_state, ks_map) for p in el.pitches) + "]" + d
        else:
            body = pitch_to_abc(el.pitch, bar_state, ks_map) + d
        if getattr(el, "tie", None) is not None and el.tie.type in ("start", "continue"):
            body += "-"
        beam_break = ""
        bt = _beam_types(el)
        if bt and bt[0] in ("start", None):
            beam_break = " "
        tokens.append((beam_break, prefix + body))
    # cifras restantes (ex.: compasso só com pausa de compasso inteiro)
    rest = ["".join(chord_offsets[o]) for o in sorted(chord_offsets) if o not in used_chords]
    text = ""
    for i, (br, tok) in enumerate(tokens):
        if i > 0 and (br or not _beamed(elements[i])):
            text += " "
        text += tok
    if rest:
        text = "".join(rest) + text
    return text


def _beam_types(el):
    b = getattr(el, "beams", None)
    return b.getTypes() if b else []


def _beamed(el) -> bool:
    return bool(_beam_types(el))


def barlines(m: stream.Measure):
    left, right = "", "|"
    lb, rb = m.leftBarline, m.rightBarline
    if isinstance(lb, bar.Repeat):
        left = "|:"
    if isinstance(rb, bar.Repeat):
        right = ":|"
    elif rb is not None:
        right = {"final": "|]", "light-heavy": "|]", "double": "||", "light-light": "||"}.get(rb.type, "|")
    return left, right


def volta_map(part: stream.Part) -> dict:
    out = {}
    for sp in part.recurse().getElementsByClass(spanner.RepeatBracket):
        ms = sp.getSpannedElements()
        if ms:
            out[ms[0].number] = sp.number
    return out


def part_to_abc_body(part: stream.Part, ks: key.KeySignature, chords: dict, bars_per_line: int) -> str:
    ks_map = key_signature_map(ks.sharps)
    voltas = volta_map(part)
    lines, cur = [], ""
    count = 0
    for i, m in enumerate(part.getElementsByClass(stream.Measure)):
        left, right = barlines(m)
        if m.number in voltas:
            left = (left or "") + f"[{voltas[m.number]} "
        mk = m.keySignature
        if i > 0 and mk is not None:  # mudança de tom no meio da música
            mk = simplify_key(mk)
            ks_map = key_signature_map(mk.sharps)
            left += f"[K:{abc_key_name(mk)}] "
        cur += left + measure_to_abc(m, ks_map, chords) + " " + right + " "
        count += 1
        if count % bars_per_line == 0:
            lines.append(cur.strip())
            cur = ""
    if cur.strip():
        lines.append(cur.strip())
    # repete ':|' + '|:' adjacentes como '::'
    return "\n".join(l.replace(":| |:", "::").replace("| |:", "|:") for l in lines)


def header_fields(score, part):
    md = score.metadata
    title = (md.title or md.movementName if md else None) or "Sem título"
    composer = md.composer if md and md.composer else None
    ts = part.recurse().getElementsByClass(meter.TimeSignature).first()
    tm = part.recurse().getElementsByClass(tempo.MetronomeMark).first()
    ks = part.recurse().getElementsByClass(key.KeySignature).first() or key.KeySignature(0)
    return title, composer, ts, tm, ks


def key_for(ks, inst, octave_shift):
    if inst == "concert":
        return ks
    k = ks if isinstance(ks, key.Key) else ks.asKey("major")
    return simplify_key(k.transpose(INSTRUMENTS[inst]["interval"]))


def build_abc(path: Path, insts, layout, bars_per_line, octave_shift, title_override=None):
    score, raw_chords = load(path)
    part = melody_part(score)
    title, composer, ts, tm, ks = header_fields(score, part)
    if title_override:
        title = title_override
    elif title == "Sem título":
        title = path.stem.replace("_", " ")
    chords = collect_chords(part, raw_chords)

    meter_txt = ts.ratioString if ts else "4/4"
    if ts is not None and ts.symbol == "cut":
        meter_txt = "C|"
    elif ts is not None and ts.symbol == "common":
        meter_txt = "C"
    if path.suffix.lower() == ".abc":  # music21 perde o símbolo C| / C no ABC
        mo = re.search(r"^M:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
        if mo:
            meter_txt = mo.group(1)
    common = [f"M:{meter_txt}", "L:1/8"]
    if tm and tm.number:
        common.append(f"Q:1/4={int(tm.number)}")

    rendered = {}
    for inst in ["concert"] + [i for i in insts if i != "concert"]:
        if inst == "concert":
            p, k = part, ks
        else:
            k = key_for(ks, inst, octave_shift)
            ivl = interval.Interval(INSTRUMENTS[inst]["interval"])
            if k.sharps != (ks if isinstance(ks, key.Key) else ks.asKey("major")).transpose(ivl).sharps:
                # armadura simplificada: usa intervalo enharmônico equivalente
                ivl = _enharmonic_interval(ivl, k, ks)
            p = part.transpose(ivl, inPlace=False)
            shift = octave_shift.get(inst, 0) if isinstance(octave_shift, dict) else octave_shift
            if shift:
                p = p.transpose(interval.Interval(("P8" if shift > 0 else "P-8")), inPlace=False)
                for _ in range(abs(shift) - 1):
                    p = p.transpose(interval.Interval(("P8" if shift > 0 else "P-8")), inPlace=False)
        rendered[inst] = (k, part_to_abc_body(p, k, chords, bars_per_line))

    out = []
    if layout == "tunes":
        for n, inst in enumerate(rendered, start=1):
            k, body = rendered[inst]
            out.append(f"X:{n}")
            out.append(f"T:{title}")
            out.append(f"T:{INSTRUMENTS[inst]['name']}")
            if composer:
                out.append(f"C:{composer}")
            out += common
            out.append(f"K:{abc_key_name(k)}")
            out.append(body)
            out.append("")
    else:
        out.append("X:1")
        out.append(f"T:{title}")
        if composer:
            out.append(f"C:{composer}")
        out += common
        names = list(rendered)
        out.append("%%score " + " ".join(f"({i}" if False else i for i in names))
        out.append(f"K:{abc_key_name(rendered['concert'][0])}")
        for inst in names:
            k, body = rendered[inst]
            out.append(f'V:{inst} name="{INSTRUMENTS[inst]["name"]}" snm="{INSTRUMENTS[inst]["short"]}"')
            out.append(f"K:{abc_key_name(k)}")
            out.append(body)
        out.append("")
    return "\n".join(out)


def _enharmonic_interval(ivl, target_key, concert_ks):
    """Ex.: concerto em E maior -> alto ficaria C# maior (7#); usamos Db (5b)."""
    ck = concert_ks if isinstance(concert_ks, key.Key) else concert_ks.asKey("major")
    target_tonic = target_key.tonic
    from music21 import pitch as m21pitch
    src = m21pitch.Pitch(ck.tonic.name + "4")
    dst = m21pitch.Pitch(target_tonic.name + "4")
    base = interval.Interval(src, dst)
    # ajusta a oitava para bater com o número de semitons do intervalo original
    diff = ivl.semitones - base.semitones
    while diff >= 12:
        dst.octave += 1
        diff -= 12
    while diff <= -12:
        dst.octave -= 1
        diff += 12
    return interval.Interval(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("entrada", type=Path, help="MusicXML (.musicxml/.xml/.mxl) ou ABC (.abc) em tom de concerto")
    ap.add_argument("-o", "--saida", type=Path, help="arquivo .abc de saída (padrão: <entrada>_sax.abc)")
    ap.add_argument("--inst", nargs="+", choices=["alto", "tenor"], default=["alto", "tenor"])
    ap.add_argument("--layout", choices=["tunes", "voices"], default="tunes")
    ap.add_argument("--compassos-por-linha", type=int, default=4, dest="bpl")
    ap.add_argument("--octave", type=int, default=0, help="desloca a melodia transposta em oitavas (ex.: -1)")
    ap.add_argument("--octave-alto", type=int, default=None, help="oitava só do alto (sobrepõe --octave)")
    ap.add_argument("--octave-tenor", type=int, default=None, help="oitava só do tenor (sobrepõe --octave)")
    ap.add_argument("--titulo", help="sobrescreve o título")
    a = ap.parse_args()

    octs = {
        "alto": a.octave if a.octave_alto is None else a.octave_alto,
        "tenor": a.octave if a.octave_tenor is None else a.octave_tenor,
    }
    abc = build_abc(a.entrada, a.inst, a.layout, a.bpl, octs, a.titulo)
    out = a.saida or a.entrada.with_name(a.entrada.stem + "_sax.abc")
    out.write_text(abc, encoding="utf-8")
    print(f"ABC gerado: {out}")


if __name__ == "__main__":
    main()
