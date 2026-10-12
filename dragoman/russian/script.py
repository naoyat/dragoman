#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ロシア語の文字: 照合用のキー (強勢記号を除き、ё を е に、小文字)、強勢の表示、ラテン文字への転写
#
#   key('Кни́га') → 'книга'      key('ёлка') → 'елка'
#   translit('кни́га') → 'kníga' (Wiktionary と同じ学術転写。強勢は母音の上の ´)
#
import unicodedata

STRESS = '́'  # 結合アキュート (кни́га の и́)
GRAVE = '̀'   # 第二強勢 (複合語)

TRANSLIT = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'jo', 'ж': 'ž', 'з': 'z', 'и': 'i', 'й': 'j',
    'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'x', 'ц': 'c', 'ч': 'č', 'ш': 'š', 'щ': 'šč', 'ъ': 'ʺ', 'ы': 'y', 'ь': 'ʹ', 'э': 'e', 'ю': 'ju', 'я': 'ja',
}


def strip_stress(text):
    nfd = unicodedata.normalize('NFD', text)
    return unicodedata.normalize('NFC', ''.join(c for c in nfd if c not in (STRESS, GRAVE)))


def key(word):
    """照合用のキー: 強勢記号を除き、小文字にし、ё を е に"""
    return strip_stress(word).lower().replace('ё', 'е')


def stress_index(word):
    """強勢のある母音の位置 (強勢記号の無い文字列での添字)。ё は常に強勢がある。分からなければ None"""
    plain = []
    for c in unicodedata.normalize('NFD', word):
        if c == STRESS:
            return len(plain) - 1
        if c != GRAVE:
            plain.append(c)
    text = unicodedata.normalize('NFC', word)
    for i, c in enumerate(strip_stress(text)):
        if c in 'ёЁ':
            return i
    return None


def translit(word):
    """学術転写 (強勢記号はそのまま母音の上に)"""
    out = []
    for c in unicodedata.normalize('NFD', word):
        if c in (STRESS, GRAVE):
            out.append(c)
            continue
        lower = c.lower()
        t = TRANSLIT.get(lower, TRANSLIT.get(unicodedata.normalize('NFC', lower), c))
        out.append(t.capitalize() if c != lower and t else t)
    return unicodedata.normalize('NFC', ''.join(out))


# ----------------------------------------------------------------------
# ラテン文字の転写 → キリル文字 (学術転写 kníga・žena・ščí、ISO 9 の ŝ・â・û・ë、英語式の zh・kh・ts・shch・ya・yu)。
# 曖昧な所 (語頭・母音の後ろの e → е / э、ts → ц / тс) は辞書 (pymorphy3 の既知の語) で選ぶ。強勢記号は除く

FROM_LATIN = [('shch', ['щ']), ('šč', ['щ']), ('ŝ', ['щ']), ('zh', ['ж']), ('kh', ['х']), ('ts', ['ц', 'тс']),
              ('ch', ['ч']), ('sh', ['ш']), ('ž', ['ж']), ('č', ['ч']), ('š', ['ш']), ('x', ['х']), ('h', ['х']),
              ('c', ['ц']), ('yu', ['ю']), ('ju', ['ю']), ('û', ['ю']), ('ya', ['я']), ('ja', ['я']), ('â', ['я']),
              ('yo', ['ё']), ('jo', ['ё']), ('ë', ['ё']), ('ye', ['е']), ('je', ['е']), ('è', ['э']), ('ė', ['э']),
              ('ʹ', ['ь']), ("'", ['ь', 'ъ']), ('’', ['ь', 'ъ']), ('ʺ', ['ъ']), ('a', ['а']), ('b', ['б']), ('v', ['в']),
              ('w', ['в']), ('g', ['г']), ('d', ['д']), ('z', ['з']), ('i', ['и']), ('k', ['к']), ('l', ['л']),
              ('m', ['м']), ('n', ['н']), ('o', ['о']), ('p', ['п']), ('r', ['р']), ('s', ['с']), ('t', ['т']),
              ('u', ['у']), ('f', ['ф']), ('e', ['е'])]
LATIN_VOWELS = set('aeiouy')
LATIN_WORD = r"[A-Za-zÀ-žʹʺ]+(?:['’][A-Za-zÀ-žʹʺ]*)*"


def _known(word):
    from . import morphology
    try:
        return morphology.morph().word_is_known(word)
    except ImportError:
        return False


def _from_latin_word(word):
    plain = ''.join(c for c in unicodedata.normalize('NFD', word) if c not in (STRESS, GRAVE))
    plain = unicodedata.normalize('NFC', plain)
    lower = plain.lower()
    options, i = [], 0
    while i < len(lower):
        c = lower[i]
        prev = lower[i - 1] if i else ''
        nxt = lower[i + 1] if i + 1 < len(lower) else ''
        if c in 'yj' and (nxt not in 'aueo' or not nxt):   # 母音の前でない y・j: 母音の後ろ・語頭なら й、子音の後ろの y は ы
            options.append(['й'] if c == 'j' or prev in LATIN_VOWELS or not prev else ['ы'])
            i += 1
            continue
        if c == 'e' and (not prev or prev in LATIN_VOWELS):
            options.append(['е', 'э'] if prev else ['э', 'е'])   # это・поэзия / есть・мое
            i += 1
            continue
        for latin, cyrillic in FROM_LATIN:
            if lower.startswith(latin, i):
                options.append(cyrillic)
                i += len(latin)
                break
        else:
            options.append([c])
            i += 1
    out = _pick(options)
    return out[:1].upper() + out[1:] if plain[:1].isupper() else out


def _pick(options):
    from dragoman.core.reverse import pick
    return pick(options, _known)


def has_cyrillic(text):
    return any('Ѐ' <= c <= 'ӿ' for c in text)


def from_latin(text):
    """ラテン文字で書いたロシア語の文 → キリル文字 (キリル文字を含めばそのまま)"""
    if has_cyrillic(text):
        return text
    from dragoman.core.reverse import words
    return words(text, LATIN_WORD, _from_latin_word)
