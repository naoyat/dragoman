#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古典ギリシア語のラテン文字への転写 (学術的な転写を簡略に)
#
#   ἐν ἀρχῇ ἦν ὁ λόγος → en archêi ên ho lógos
#
# η ω は ē ō (曲アクセントなら ê ô)、υ は y (二重母音の中では u)、χ θ φ ψ は ch th ph ps、γγ γκ γξ γχ の γ は n、
# 気息記号 (῾) は h、語頭の ῥ は rh、下書きのイオタは i。鋭アクセント・重アクセントは母音の上にそのまま
#
import re
import unicodedata

LETTERS = {'α': 'a', 'β': 'b', 'γ': 'g', 'δ': 'd', 'ε': 'e', 'ζ': 'z', 'η': 'ē', 'θ': 'th', 'ι': 'i', 'κ': 'k',
           'λ': 'l', 'μ': 'm', 'ν': 'n', 'ξ': 'x', 'ο': 'o', 'π': 'p', 'ρ': 'r', 'σ': 's', 'ς': 's', 'τ': 't',
           'υ': 'y', 'φ': 'ph', 'χ': 'ch', 'ψ': 'ps', 'ω': 'ō', 'ϝ': 'w'}
VOWELS = set('αεηιουω')
SMOOTH, ROUGH, ACUTE, GRAVE, CIRCUMFLEX, IOTA_SUB, DIAERESIS = ('̓', '̔', '́', '̀', '͂',
                                                               'ͅ', '̈')
MACRON, BREVE = '̄', '̆'
VELARS = set('γκξχ')
DIPHTHONG_SECOND = set('ιυ')


def _letters(word):
    """[(小文字の字, 大文字か, 記号の集合)]"""
    out = []
    for c in unicodedata.normalize('NFD', word):
        if unicodedata.combining(c):
            if out:
                out[-1][2].add(c)
        else:
            out.append([c.lower(), c != c.lower(), set()])
    return out


def _accented(latin, marks):
    if CIRCUMFLEX in marks:
        latin = latin.replace('ē', 'ê').replace('ō', 'ô').replace('a', 'â').replace('i', 'î').replace('y', 'ŷ').replace(
            'u', 'û').replace('e', 'ê').replace('o', 'ô')
        return latin
    for mark in (ACUTE, GRAVE):
        if mark in marks:
            return unicodedata.normalize('NFC', latin[0] + mark + latin[1:]) if latin else latin
    return latin


def romanize_word(word):
    letters = _letters(word)
    out = []
    rough_pending = False
    for i, (c, upper, marks) in enumerate(letters):
        if c not in LETTERS:
            out.append(c)
            continue
        nxt = letters[i + 1][0] if i + 1 < len(letters) else ''
        prev = letters[i - 1][0] if i > 0 else ''
        latin = LETTERS[c]
        if c == 'γ' and nxt in VELARS:
            latin = 'n'
        if c == 'υ' and prev in VOWELS and prev not in DIPHTHONG_SECOND and DIAERESIS not in marks:
            latin = 'u'  # αυ ευ ηυ ου
        if c == 'ρ' and (ROUGH in marks or i == 0):
            latin = 'rh'
        # 二重母音の気息記号・アクセントは2つ目の字にある (οἱ, αὐτός)
        diphthong_head = c in VOWELS and nxt in DIPHTHONG_SECOND and i + 1 < len(letters) and \
            DIAERESIS not in letters[i + 1][2] and not (c == 'ι') and not (c == 'υ' and nxt == 'υ')
        second_of_diphthong = c in DIPHTHONG_SECOND and prev in VOWELS and prev not in DIPHTHONG_SECOND - {'υ'} \
            and DIAERESIS not in marks and i > 0
        if ROUGH in marks and c != 'ρ' and not second_of_diphthong:
            latin = 'h' + latin  # 二重母音の2つ目の字の気息記号は1つ目の字の前に (下で)
        if diphthong_head and ROUGH in letters[i + 1][2]:
            latin = 'h' + latin
        latin = _accented(latin, marks)
        if IOTA_SUB in marks:
            latin += 'i'
        if upper:
            latin = latin[:1].upper() + latin[1:]
        out.append(latin)
    return unicodedata.normalize('NFC', ''.join(out))


def romanize(text):
    return ' '.join(romanize_word(w) for w in text.split())


# ----------------------------------------------------------------------
# ラテン文字 → ギリシア文字 (入力用)。学術的な転写 (en archêi ên ho lógos) と Beta Code (e)n a)rxh=| h)=n o( lo/gos)
#
#   学術転写: ē ō (ê ô は曲アクセント付き)・h (気息)・ch th ph ps・y (υ)・rh、長い母音 + i は下書きのイオタ (archêi → ἀρχῇ)。
#   語頭の母音は h が無ければ無気の記号。文に長音の印 (ē ō ê ô) が一つも無ければ e・o の長短 (ε/η・ο/ω) は辞書で選ぶ

LATIN_TO_GREEK = [('rh', 'ρ'), ('ph', 'φ'), ('th', 'θ'), ('ch', 'χ'), ('kh', 'χ'), ('ps', 'ψ'), ('b', 'β'),
                  ('g', 'γ'), ('d', 'δ'), ('z', 'ζ'), ('k', 'κ'), ('c', 'κ'), ('l', 'λ'), ('m', 'μ'), ('n', 'ν'),
                  ('x', 'ξ'), ('p', 'π'), ('r', 'ρ'), ('s', 'σ'), ('t', 'τ'), ('w', 'ϝ')]
LATIN_VOWELS = {'a': 'α', 'e': 'ε', 'i': 'ι', 'o': 'ο', 'u': 'υ', 'y': 'υ'}
LONG = {'e': 'η', 'o': 'ω', 'a': 'α', 'i': 'ι', 'u': 'υ', 'y': 'υ'}
BETA = re.compile(r"[)(/\\=|*]")
LATIN_WORD = r"[A-Za-zÀ-ɏḀ-ỿ̀-ͯ]+"


def _latin_letters(word):
    """[(小文字の字, 大文字か, 記号の集合)] (記号: 長音 MACRON・曲アクセント・鋭・重・分音)"""
    out = []
    for c in unicodedata.normalize('NFD', word):
        if unicodedata.combining(c):
            if out:
                out[-1][2].add(c)
        else:
            out.append([c.lower(), c != c.lower(), set()])
    return out


def _vowel(c, marks, ambiguous):
    """ラテン文字の母音 → [ギリシア文字の候補] (記号付き。気息は後で)"""
    long_ = MACRON in marks or '̂' in marks
    accent = ''.join(m for m in (ACUTE, GRAVE) if m in marks) + (CIRCUMFLEX if '̂' in marks else '')
    diaeresis = DIAERESIS if DIAERESIS in marks else ''
    if long_:
        return [LONG[c] + diaeresis + accent]
    if ambiguous and c in 'eo':
        return [LATIN_VOWELS[c] + diaeresis + accent, LONG[c] + diaeresis + accent]
    return [LATIN_VOWELS[c] + diaeresis + accent]


def _greek_word(word, ambiguous):
    letters = _latin_letters(word)
    upper = letters[0][1] if letters else False
    rough = False
    if len(letters) > 1 and letters[0][0] == 'h' and letters[1][0] in LATIN_VOWELS:
        rough = True
        upper = upper or letters[1][1]
        letters = letters[1:]
    options, i = [], 0
    vowel_slots = []   # 母音の候補の位置 (語頭の気息を付ける所を探す)
    while i < len(letters):
        c, _, marks = letters[i]
        nxt = letters[i + 1][0] if i + 1 < len(letters) else ''
        if c in LATIN_VOWELS:
            long_ = MACRON in marks or '̂' in marks
            if long_ and c in 'aeo' and nxt == 'i' and not letters[i + 1][2] and \
                    (i + 2 == len(letters) or letters[i + 2][0] not in LATIN_VOWELS):
                options.append([v + IOTA_SUB for v in _vowel(c, marks, ambiguous)])   # ēi → ῃ
                vowel_slots.append(len(options) - 1)
                i += 2
                continue
            options.append(_vowel(c, marks, ambiguous))
            vowel_slots.append(len(options) - 1)
            i += 1
            continue
        if c == 'n' and nxt in ('g', 'k', 'x', 'c'):
            options.append(['γ'])   # ng nk nx nch → γγ γκ γξ γχ
            i += 1
            continue
        for latin, greek in LATIN_TO_GREEK:
            if ''.join(x[0] for x in letters[i:i + len(latin)]) == latin:
                options.append([greek])
                i += len(latin)
                break
        else:
            options.append([c])
            i += 1
    if options and options[-1] == ['σ']:
        options[-1] = ['ς']
    # 気息の記号: 語頭の母音 (二重母音なら2つ目の字) に。語頭の ρ は有気
    breathing = ROUGH if rough else SMOOTH
    if vowel_slots and vowel_slots[0] == 0:
        k = 0
        first = letters[0][0]
        if len(vowel_slots) > 1 and vowel_slots[1] == 1 and first in 'aeouy' and letters[1][0] in 'iuy' and \
                DIAERESIS not in letters[1][2]:   # οἱ・αὐτός・υἱός
            k = 1
        options[k] = [v[0] + breathing + v[1:] for v in options[k]]
    elif options and options[0] == ['ρ']:
        options[0] = ['ρ' + ROUGH]

    def known(w):
        from . import dictionary
        return bool(dictionary.lookup(w))

    from dragoman.core.reverse import pick
    out = unicodedata.normalize('NFC', pick(options, known))
    return out[:1].upper() + out[1:] if upper else out


def _beta_word(word):
    from .morpheus import from_betacode
    return from_betacode(word.lower())


def has_greek(text):
    return any('Ͱ' <= c <= 'Ͽ' or 'ἀ' <= c <= '῿' for c in text)


def from_latin(text):
    """ラテン文字で書いた古典ギリシア語 (学術転写か Beta Code) → ギリシア文字。ギリシア文字を含めばそのまま"""
    if has_greek(text) or not re.search('[A-Za-z]', text):
        return text
    from dragoman.core.reverse import words
    if BETA.search(text):
        text = words(text, r"[A-Za-z*)(/\\=|+]+", _beta_word)
        return text.replace(':', '·')   # Beta Code の : は高い点
    nfd = unicodedata.normalize('NFD', text)
    ambiguous = MACRON not in nfd and '̂' not in nfd
    return words(text, LATIN_WORD, lambda w: _greek_word(w, ambiguous))
