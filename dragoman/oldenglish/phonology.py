#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の発音 (ウェストサクソン方言の古典期、およそ 1000年頃の再建音) と、espeak-ng の音素の列
#
#   ipa('ċild') → ['tʃ', 'i', 'l', 'd'] と強勢の位置
#   espeak_phonemes('Hwæt wē Gārdena') → '[[hw'Et w'e: g'A:RdenA]]'
#
# 綴りと音:
#   - 母音は綴りのまま (a [ɑ]、æ [æ]、e [e]、i [i]、o [o]、u [u]、y [y])。長音符は長母音 (ā [ɑː] …)。二重母音 ea [æɑ]・
#     eo [eo]・ie [iy]・io [io] (長音符は最初の字に: ēa・ēo・īe・īo)。強勢の無い母音も音色は保つ
#   - ċ [tʃ]・ġ [j] (点の付いた口蓋音)。点の無い綴り (翻刻) では位置から推す: 語頭の前舌母音 (e・i・æ と ea・eo・ie) の前、
#     前舌母音の後ろの語末 (iċ、dæġ) は口蓋音。ġe- は [je]。cg・ċġ [dʒ]、sc [ʃ]、ng [ŋg]
#   - g は語頭・n の後ろで [g]、母音・l・r の後ろで [ɣ]
#   - h は語頭で [h]、それ以外は後舌母音の後ろで [x]、前舌母音の後ろで [ç] (niht [niçt]、dohtor [doxtor])。hw [hw]
#   - f・s・þ (ð) は有声音に挟まれると [v]・[z]・[ð] (ofer [over]、wesan [wezan])、それ以外は [f]・[s]・[θ]。重子音は長く
#   - r は震え音 [r]
#   - 強勢は最初の音節。ġe-・be-・bi-・for-・ā- の接頭辞の付いた語はその次 (ġesēon [jeˈseːon])
#
import os
import re
import unicodedata

from . import orthography

SHORT = {'a': 'ɑ', 'æ': 'æ', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'y': 'y', 'œ': 'ø'}
LONG = {'ā': 'ɑː', 'ǣ': 'æː', 'ē': 'eː', 'ī': 'iː', 'ō': 'oː', 'ū': 'uː', 'ȳ': 'yː', 'œ̄': 'øː'}
DIPHTHONGS = {'ea': 'æɑ', 'ēa': 'æːɑ', 'eo': 'eo', 'ēo': 'eːo', 'ie': 'iy', 'īe': 'iːy', 'io': 'io', 'īo': 'iːo'}
FRONT = ('e', 'i', 'æ', 'ē', 'ī', 'ǣ')       # 口蓋化を起こす前舌母音 (y は u の変音なので含めない)
BACK_IPA = ('ɑ', 'o', 'u')
VOICED = set('ɑæeiouyø') | {'l', 'r', 'm', 'n', 'w', 'j', 'ŋ', 'b', 'd', 'g', 'ɣ', 'v', 'z', 'ð'}
PREFIXES = ('ġe', 'ge', 'be', 'bi', 'for', 'ā')
VOWEL_LETTERS = set('aæeiouyœāǣēīōūȳ')


def _letters(word):
    """長音符・点の付いた字を1字にまとめ (NFC)、ð → þ、ƿ → w、小文字に"""
    word = unicodedata.normalize('NFC', word.lower())
    return word.replace('ð', 'þ').replace('ƿ', 'w').replace('ꝥ', 'þæt').replace('k', 'c')


def _is_vowel(c):
    return c in VOWEL_LETTERS or unicodedata.normalize('NFD', c)[0] in 'aeiouyæ'


def prefix_length(word, lemma=None):
    """接頭辞 (ġe-・be-・bi-・for-・ā-) の字数。ġe- は子音の前、ほかは残りが4字以上の辞書の語のとき
    (beran「運ぶ」は be- + ran でない)"""
    w = _letters(word)
    base = _letters(lemma) if lemma else None
    for p in PREFIXES:
        rest = w[len(p):]
        if not w.startswith(p) or not any(_is_vowel(c) for c in rest):
            continue
        if base is not None and p not in ('ġe', 'ge'):
            # 見出し語で判定: for- を外した lǣtan が動詞の見出しにあれば forlǣtan は接頭辞付き (beran・biscop は違う)
            if base.startswith(p) and _verb_lemma(base[len(p):]):
                return len(p)
            continue
        if p in ('ġe', 'ge') and len(rest) >= 3 and not _is_vowel(rest[0]):
            return len(p)   # ġe- + 子音 (ġefrūnon・ġesewen。ġeard の ġea は二重母音)
        if p not in ('ġe', 'ge') and len(rest) >= 4 and _known_verb(rest):
            return len(p)
    return 0


def _verb_lemma(lemma):
    try:
        from . import dictionary
    except ImportError:
        return False
    return dictionary.available() and len(lemma) >= 3 and bool(dictionary.lemmas(lemma, 'verb'))


def _known_verb(word):
    """辞書に動詞の形としてある語か (be-・for- は動詞の接頭辞: behealdan、forlǣtan。biscop は bi- + scop でない)"""
    try:
        from . import dictionary
    except ImportError:
        return False
    return dictionary.available() and any(info['pos'] == 'verb' for info, _ in dictionary.forms(word))


def segments(word, lemma=None):
    """綴り → [(IPA の音, 母音か)]。lemma (見出し語) があれば接頭辞の判定に使う"""
    w = _letters(word)
    out = []
    i = 0
    n = len(w)
    start = prefix_length(word, lemma)   # 接頭辞の後ろは語頭と同じ (ġesēon の s は無声)
    while i < n:
        c = w[i]
        nxt = w[i + 1] if i + 1 < n else ''
        two = w[i:i + 2]
        if _is_vowel(c):
            if two in DIPHTHONGS:
                out.append((DIPHTHONGS[two], True))
                i += 2
                continue
            out.append((LONG.get(c) or SHORT.get(c) or SHORT.get(orthography.key(c), 'e'), True))
            i += 1
            continue
        prev_letter = w[i - 1] if i else ''
        initial = i == 0 or i == start
        if two in ('cg', 'ċġ'):
            out.append(('dʒ', False))
            i += 2
            continue
        if two == 'sc':
            out.append(('ʃ', False))
            i += 2
            continue
        if two == 'hw':
            out += [('h', False), ('w', False)]
            i += 2
            continue
        if c in ('c', 'g', 'ċ', 'ġ') and i > 0 and w[i + 1:i + 2] == 'e' and w[i + 2:i + 3] in ('a', 'o', 'u'):
            out.append(('tʃ' if c in 'cċ' else 'j', False))   # sēċean・seċġean の e は口蓋音の印
            i += 2
            continue
        if c in ('ċ', 'c'):
            if c == 'ċ' or _palatal(w, i):
                out.append(('tʃ', False))
            else:
                out.append(('k', False))
            i += 1
            continue
        if c in ('ġ', 'g'):
            if c == 'ġ' or _palatal(w, i):
                out.append(('j', False))
            elif initial or prev_letter in ('n', 'g') or nxt == 'g':
                out.append(('g', False))
            else:
                out.append(('ɣ', False))
            i += 1
            continue
        if c == 'n' and nxt in ('g', 'c', 'ġ', 'ċ'):
            out.append(('ŋ', False))
            i += 1
            continue
        if c == 'h':
            if initial or prev_letter == 'h':
                out.append(('h', False))
            else:
                back = next((s for s, v in reversed(out) if v), 'ɑ')
                out.append(('x' if back.startswith(BACK_IPA) and not back.startswith('æ') else 'ç', False))
            i += 1
            continue
        if c == 'x':
            out += [('k', False), ('s', False)]
            i += 1
            continue
        if c in ('f', 's', 'þ'):
            double = nxt == c or prev_letter == c
            between = out and (out[-1][1] or out[-1][0] in VOICED) and nxt and \
                (_is_vowel(nxt) or nxt in 'lrmnwġg')
            voiced = between and not double and not initial
            out.append(({'f': 'v', 's': 'z', 'þ': 'ð'}[c] if voiced else {'f': 'f', 's': 's', 'þ': 'θ'}[c], False))
            i += 1
            continue
        if c.isalpha():
            out.append((c, False))
        i += 1
    return _geminates(out)


def _palatal(w, i):
    """点の無い c・g が口蓋音か: 語頭の前舌母音の前 (cild・giefan・ge-)、前舌母音の後ろの語末 (ic・dæg・weg)"""
    nxt = w[i + 1] if i + 1 < len(w) else ''
    prev = w[i - 1] if i else ''
    if i == 0 and nxt in FRONT:
        return True
    if i == len(w) - 1 and prev in FRONT:
        return True
    return False


def _geminates(segs):
    """重子音 (tt・ll・nn …) は長い子音1つに"""
    out = []
    for s, v in segs:
        if out and not v and not out[-1][1] and out[-1][0] == s:
            out[-1] = (s + 'ː', False)
            continue
        out.append((s, v))
    return out


def stress_index(word, segs, lemma=None):
    """強勢のある母音の位置 (segs の添字)"""
    vowels = [k for k, (s, v) in enumerate(segs) if v]
    if not vowels:
        return None
    if len(vowels) > 1 and prefix_length(word, lemma):
        return vowels[1]
    return vowels[0]


def ipa(word, lemma=None):
    segs = segments(word, lemma)
    k = stress_index(word, segs, lemma)
    return ''.join(('ˈ' if j == k else '') + s for j, (s, v) in enumerate(segs))


# IPA → espeak-ng のドイツ語の音声の音素名 (ドイツ語の音素表は基本の表の θ・ð・w・ɣ も持つ。æ は無いので ɛ で代える)
ESPEAK_DE = {
    'ɑ': 'a', 'ɑː': 'A:', 'æ': 'E', 'æː': 'E:', 'e': 'e', 'eː': 'e:', 'i': 'I', 'iː': 'i:', 'o': 'O', 'oː': 'o:',
    'u': 'U', 'uː': 'u:', 'y': 'y', 'yː': 'y:', 'ø': 'W', 'øː': 'Y:',
    'æɑ': 'Ea', 'æːɑ': 'E:a', 'eo': 'eO', 'eːo': 'e:O', 'iy': 'Iy', 'iːy': 'i:y', 'io': 'IO', 'iːo': 'i:O',
    'tʃ': 'tS', 'dʒ': 'dZ', 'ʃ': 'S', 'θ': 'T', 'ð': 'D', 'ɣ': 'Q', 'x': 'x', 'ç': 'C', 'ŋ': 'N', 'r': 'R', 'j': 'j',
    'w': 'w', 'h': 'h',
}


# 古英語の音声 (tools/build_oldenglish_espeak.py で作る ang。ドイツ語の表 + [æ]、語末の無声化なし) の音素名
ESPEAK_ANG = dict(ESPEAK_DE, **{'æ': '&', 'æː': '&:', 'æɑ': '&a', 'æːɑ': '&:a'})


def ang_voice():
    """古英語の音声 ang のデータの置き場所 (作ってなければ None)"""
    from dragoman.core import paths
    root = paths.data('ang')
    return root if os.path.exists(os.path.join(root, 'espeak-ng-data', 'lang', 'gmw', 'ang')) else None


def default_table():
    return ESPEAK_ANG if ang_voice() else ESPEAK_DE


def espeak_word(word, table=ESPEAK_DE, lemma=None):
    segs = segments(word, lemma)
    k = stress_index(word, segs, lemma)
    out = ''
    for j, (s, v) in enumerate(segs):
        length = s.endswith('ː') and not v
        base = s[:-1] if length else s
        name = table.get(base, base)
        out += ("'" if j == k else '') + name + (name if length else '')   # 長い子音は2つ重ねる
    return out


WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def espeak_words(pairs, table=None):
    """[(綴り, 見出し語)] (analyzer.spelled) → espeak-ng に渡す音素の列 ([[…]])。table を省くと、古英語の音声 ang が
    あればその音素名、無ければドイツ語の音声の音素名"""
    table = table or default_table()
    parts = []
    for spelling, lemma in pairs:
        if spelling in '.,;:!?·':
            parts.append('_:' if spelling in '.!?' else '_')
        elif spelling in orthography.TIRONIAN:
            parts.append(espeak_word('and', table))
        elif WORD.fullmatch(spelling):
            parts.append(espeak_word(spelling, table, lemma))
    return '[[%s]]' % ' '.join(parts)


def espeak_phonemes(text, table=None):
    """文 → espeak-ng に渡す音素の列 ([[…]])。句読点は区切り (_:)"""
    table = table or default_table()
    parts = []
    for token in re.findall(r"[^\W\d_]+|[.,;:!?·]", unicodedata.normalize('NFC', text)):
        if token in '.,;:!?·':
            parts.append('_:' if token in '.!?' else '_')
        elif orthography.key(token) == 'and' and token in orthography.TIRONIAN:
            parts.append(espeak_word('and', table))
        else:
            parts.append(espeak_word(token, table))
    return '[[%s]]' % ' '.join(parts)
