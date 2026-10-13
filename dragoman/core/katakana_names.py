#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 固有名詞をカタカナで書く (トルコ語・モンゴル語・フィンランド語・ドイツ語の名前。ラテン語は latin/katakana.py)
#
#   turkish('Ali') → アリ、turkish('Ayşe') → アイシェ、turkish('Çağlar') → チャーラル、turkish('İstanbul') → イスタンブル
#   mongolian('Бат') → バト、mongolian('Дорж') → ドルジ、mongolian('Улаанбаатар') → ウラーンバータル
#
# 綴りを (子音, 母音, 長音) の列に直してから、子音の行と母音の段でカタカナを選ぶ。母音の続かない子音は
# ウ段 (ト・ドは o 段) で書く (n は ン)
#
import unicodedata

ROWS = {
    '': 'アイウエオ', 'k': 'カキクケコ', 'g': 'ガギグゲゴ', 's': 'サシスセソ', 'z': 'ザジズゼゾ', 't': ('タ', 'ティ', 'トゥ', 'テ', 'ト'),
    'd': ('ダ', 'ディ', 'ドゥ', 'デ', 'ド'), 'n': 'ナニヌネノ', 'h': 'ハヒフヘホ', 'f': ('ファ', 'フィ', 'フ', 'フェ', 'フォ'),
    'p': 'パピプペポ', 'b': 'バビブベボ', 'm': 'マミムメモ', 'r': 'ラリルレロ', 'l': 'ラリルレロ', 'y': ('ヤ', 'イ', 'ユ', 'イェ', 'ヨ'),
    'w': ('ワ', 'ウィ', 'ウ', 'ウェ', 'ウォ'), 'v': ('ヴァ', 'ヴィ', 'ヴ', 'ヴェ', 'ヴォ'), 'sh': ('シャ', 'シ', 'シュ', 'シェ', 'ショ'),
    'ch': ('チャ', 'チ', 'チュ', 'チェ', 'チョ'), 'j': ('ジャ', 'ジ', 'ジュ', 'ジェ', 'ジョ'), 'ts': ('ツァ', 'ツィ', 'ツ', 'ツェ', 'ツォ'),
    'kh': 'ハヒフヘホ',
}
# 前舌の円唇母音 (ö・ü) は子音の後ろで拗音 (キュ・ギョ)
FRONT_ROUNDED = {'ü': 'u', 'ö': 'o'}
CODA = {'k': 'ク', 'g': 'グ', 's': 'ス', 'z': 'ズ', 't': 'ト', 'd': 'ド', 'n': 'ン', 'h': 'フ', 'f': 'フ', 'p': 'プ', 'b': 'ブ',
        'm': 'ム', 'r': 'ル', 'l': 'ル', 'y': 'イ', 'w': 'ウ', 'v': 'ヴ', 'sh': 'シュ', 'ch': 'チ', 'j': 'ジ', 'ts': 'ツ', 'kh': 'フ'}
DAN = 'aiueo'
SMALL = {'u': 'ュ', 'o': 'ョ', 'a': 'ャ'}


def _kana(segments):
    out = []
    for cons, vowel, long_ in segments:
        if vowel is None:
            out.append(CODA.get(cons, ''))
            continue
        if vowel in FRONT_ROUNDED:
            base = FRONT_ROUNDED[vowel]
            if cons in ('', 'y'):
                out.append({'u': 'ユ', 'o': 'ヨ'}[base])
            elif cons in ('t', 'd'):
                out.append({'t': 'テ', 'd': 'デ'}[cons] + SMALL[base])   # Türkiye → テュルキイェ
            else:
                row = ROWS.get(cons, ROWS[''])
                out.append(row[1][:1] + SMALL[base] if len(row[1]) == 1 else row[1] + SMALL[base])
        else:
            row = ROWS.get(cons, ROWS[''])
            out.append(row[DAN.index(vowel)])
        if long_:
            out.append('ー')
    return ''.join(out)


def _segments(phonemes):
    """[(子音, 母音)] の素の列 → (子音, 母音 / None, 長音)"""
    out = []
    k = 0
    while k < len(phonemes):
        kind, value = phonemes[k]
        if kind == 'C':
            if k + 1 < len(phonemes) and phonemes[k + 1][0] == 'V':
                vowel, long_ = phonemes[k + 1][1]
                out.append((value, vowel, long_))
                k += 2
                continue
            out.append((value, None, False))
        else:
            vowel, long_ = value
            out.append(('', vowel, long_))
        k += 1
    return out


# ----------------------------------------------------------------------
# トルコ語

TR_CONSONANTS = {'b': 'b', 'c': 'j', 'ç': 'ch', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'j', 'k': 'k', 'l': 'l',
                 'm': 'm', 'n': 'n', 'p': 'p', 'r': 'r', 's': 's', 'ş': 'sh', 't': 't', 'v': 'v', 'y': 'y', 'z': 'z'}
TR_VOWELS = {'a': 'a', 'e': 'e', 'ı': 'u', 'i': 'i', 'o': 'o', 'ö': 'ö', 'u': 'u', 'ü': 'ü', 'â': 'a', 'î': 'i', 'û': 'u'}


def turkish(name):
    word = name.replace('I', 'ı').replace('İ', 'i').lower()
    phonemes = []
    for k, c in enumerate(word):
        if c in TR_VOWELS:
            phonemes.append(('V', (TR_VOWELS[c], False)))
        elif c == 'ğ':   # 長音 (Çağlar → チャーラル)。母音の間は無音
            if phonemes and phonemes[-1][0] == 'V' and not (k + 1 < len(word) and word[k + 1] in TR_VOWELS):
                vowel, _ = phonemes[-1][1]
                phonemes[-1] = ('V', (vowel, True))
        elif c in TR_CONSONANTS:
            if c == 'y' and phonemes and phonemes[-1][0] == 'V' and not (k + 1 < len(word) and word[k + 1] in TR_VOWELS):
                phonemes.append(('V', ('i', False)))   # 母音の後ろの y (Ayşe → アイシェ)
                continue
            phonemes.append(('C', TR_CONSONANTS[c]))
    return _kana(_segments(phonemes))


# ----------------------------------------------------------------------
# モンゴル語 (キリル文字)

MN_CONSONANTS = {'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ж': 'j', 'з': 'z', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
                 'н': 'n', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh',
                 'щ': 'sh'}
MN_VOWELS = {'а': 'a', 'э': 'e', 'и': 'i', 'о': 'o', 'у': 'u', 'ө': 'o', 'ү': 'u', 'ы': 'i', 'е': 'e'}
MN_IOTATED = {'я': 'a', 'е': 'e', 'ё': 'o', 'ю': 'u'}


def mongolian(name):
    word = name.lower()
    phonemes = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in MN_IOTATED and (k == 0 or word[k - 1] in MN_VOWELS or word[k - 1] in 'ьъ') or c in 'яёю':
            phonemes.append(('C', 'y'))
            phonemes.append(('V', (MN_IOTATED[c], nxt == c)))
            k += 2 if nxt == c else 1
            continue
        if c in MN_VOWELS:
            vowel = MN_VOWELS[c]
            long_ = nxt == c or c == 'ы' and nxt == 'й'
            if c == 'и' and nxt == 'й':
                long_ = True
            phonemes.append(('V', (vowel, long_)))
            k += 2 if long_ else 1
            continue
        if c in MN_CONSONANTS:
            phonemes.append(('C', MN_CONSONANTS[c]))
        k += 1
    return _kana(_segments(phonemes))


# ----------------------------------------------------------------------
# ラテン文字の名前 (フィンランド語・ドイツ語など: 綴りどおりに)

LATIN_CONSONANTS = {'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'y', 'k': 'k', 'l': 'l', 'm': 'm',
                    'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's', 't': 't', 'v': 'v', 'w': 'v', 'x': 'k', 'z': 'ts'}
LATIN_VOWELS = {'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'y': 'ü', 'ä': 'a', 'ö': 'ö', 'ü': 'ü'}


def latin(name):
    word = ''.join(c for c in unicodedata.normalize('NFD', name.lower()) if not unicodedata.combining(c) or c in '̈')
    word = unicodedata.normalize('NFC', word).replace('sch', 'ʃ').replace('ch', 'h').replace('sh', 'ʃ')
    phonemes = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in LATIN_VOWELS:
            long_ = nxt == c
            phonemes.append(('V', (LATIN_VOWELS[c], long_)))
            k += 2 if long_ else 1
            continue
        if c == 'ʃ':
            phonemes.append(('C', 'sh'))
        elif c in LATIN_CONSONANTS:
            if nxt == c and c in 'kptsfg':
                k += 1   # 重子音 (Pekka → ペッカ は ッ を省いてペカ)
            phonemes.append(('C', LATIN_CONSONANTS[c]))
        k += 1
    return _kana(_segments(phonemes))
