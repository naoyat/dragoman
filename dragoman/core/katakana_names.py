#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 固有名詞をカタカナで書く (トルコ語・モンゴル語・フィンランド語・ドイツ語の名前。ラテン語は latin/katakana.py)
#
#   turkish('Ali') → アリ、turkish('Ayşe') → アイシェ、turkish('Çağlar') → チャーラル、turkish('İstanbul') → イスタンブル
#   mongolian('Бат') → バト、mongolian('Дорж') → ドルジ、mongolian('Улаанбаатар') → ウラーンバータル
#   latin('Matti', 'fi') → マッティ、latin('Hänsel', 'de') → ヘンゼル、latin('Müller', 'de') → ミュラー
#   korean('민수') → ミンス、korean('김철수') → キムチョルス、korean('서울') → ソウル
#
# 綴りを (子音, 母音, 長音) の列に直してから、子音の行と母音の段でカタカナを選ぶ。母音の続かない子音は
# ウ段 (ト・ドは o 段) で書く (n は ン)
#
import re
import unicodedata

ROWS = {
    '': 'アイウエオ', 'k': 'カキクケコ', 'g': 'ガギグゲゴ', 's': 'サシスセソ', 'z': 'ザジズゼゾ', 't': ('タ', 'ティ', 'トゥ', 'テ', 'ト'),
    'd': ('ダ', 'ディ', 'ドゥ', 'デ', 'ド'), 'n': 'ナニヌネノ', 'h': 'ハヒフヘホ', 'f': ('ファ', 'フィ', 'フ', 'フェ', 'フォ'),
    'p': 'パピプペポ', 'b': 'バビブベボ', 'm': 'マミムメモ', 'r': 'ラリルレロ', 'l': 'ラリルレロ', 'y': ('ヤ', 'イ', 'ユ', 'イェ', 'ヨ'),
    'w': ('ワ', 'ウィ', 'ウ', 'ウェ', 'ウォ'), 'v': ('ヴァ', 'ヴィ', 'ヴ', 'ヴェ', 'ヴォ'), 'sh': ('シャ', 'シ', 'シュ', 'シェ', 'ショ'),
    'ch': ('チャ', 'チ', 'チュ', 'チェ', 'チョ'), 'j': ('ジャ', 'ジ', 'ジュ', 'ジェ', 'ジョ'), 'ts': ('ツァ', 'ツィ', 'ツ', 'ツェ', 'ツォ'),
    'kh': 'ハヒフヘホ', 'ç': ('ヒャ', 'ヒ', 'ヒュ', 'ヒェ', 'ヒョ'),
}
# 前舌の円唇母音 (ö・ü) は子音の後ろで拗音 (キュ・ギョ)
FRONT_ROUNDED = {'ü': 'u', 'ö': 'o'}
CODA = {'k': 'ク', 'g': 'グ', 's': 'ス', 'z': 'ズ', 't': 'ト', 'd': 'ド', 'n': 'ン', 'h': 'フ', 'f': 'フ', 'p': 'プ', 'b': 'ブ',
        'm': 'ム', 'r': 'ル', 'l': 'ル', 'y': 'イ', 'w': 'ウ', 'v': 'ヴ', 'sh': 'シュ', 'ch': 'チ', 'j': 'ジ', 'ts': 'ツ', 'kh': 'フ', 'Q': 'ッ', 'ç': 'ヒ'}
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


GERMAN_RULES = (('sch', 'ʃ'), ('tsch', 'tʃ'), ('ck', 'k'), ('tz', 'z'), ('ph', 'f'), ('th', 't'), ('qu', 'kv'),
                ('ei', 'ai'), ('ey', 'ai'), ('ai', 'ai'), ('ie', 'ii'), ('eu', 'oi'), ('äu', 'oi'), ('ä', 'e'),
                ('v', 'f'), ('w', 'v'), ('z', 'ʦ'), ('ß', 's'))


def _german(word):
    if word.startswith('sp') or word.startswith('st'):
        word = 'ʃ' + word[1:]   # Stefan → シュテファン
    for a, b in GERMAN_RULES:
        word = word.replace(a, b)
    word = re.sub(r'([aeiouöü])h(?=[^aeiouöü]|$)', r'\1\1', word)   # 長音の h (Lehmann → レーマン)
    word = re.sub(r'(?<=[^aeiouöü])er$', 'aa', word)                    # 語末の -er (Müller → ミュラー)
    word = re.sub(r'(?<=[aeiouöü])s(?=[aeiouöü])', 'z', word)          # 母音の間の s (Hänsel・Rose)
    word = re.sub(r'(?<=[lnmr])s(?=[aeiouöü])', 'z', word)
    word = re.sub(r'^s(?=[aeiouöü])', 'z', word)
    word = re.sub(r'b$', 'p', re.sub(r'd$', 't', re.sub(r'g$', 'k', word)))   # 語末の無声化 (Jakob → ヤコプ)
    word = re.sub(r'(?<=[eiäöüylr])ch|(?<!n)chen$', lambda m: 'ç' + m.group(0)[2:], word)   # ich-Laut (Heinrich → ハインリヒ、-chen → ヒェン)
    return word.replace('ʦ', 'ts').replace('ch', 'h')


def latin(name, lang=''):
    """ラテン文字の名前。lang='fi' は重子音を ッ (Matti → マッティ)、'de' はドイツ語の読み (Hänsel → ヘンゼル)"""
    word = ''.join(c for c in unicodedata.normalize('NFD', name.lower()) if not unicodedata.combining(c) or c in '̈')
    word = unicodedata.normalize('NFC', word)
    if lang == 'de':
        word = _german(word)
    word = word.replace('sch', 'ʃ').replace('ch', 'h').replace('sh', 'ʃ')
    vowels = dict(LATIN_VOWELS, ä='e') if lang == 'de' else LATIN_VOWELS
    consonants = dict(LATIN_CONSONANTS, z='ts' if lang != 'de' else 'z', j='y', s='s')
    phonemes = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in vowels:
            long_ = nxt == c
            phonemes.append(('V', (vowels[c], long_)))
            k += 2 if long_ else 1
            continue
        if c == 'ʃ':
            phonemes.append(('C', 'sh'))
        elif c == 'ç':
            phonemes.append(('C', 'ç'))
        elif c in consonants:
            if nxt == c:
                k += 1
                if lang == 'fi' and c in 'kptslr':
                    phonemes.append(('C', 'Q'))    # 重子音 (Pekka → ペッカ、Ville → ヴィッレ)
                elif lang == 'fi' and c in 'nm':
                    phonemes.append(('C', 'n'))    # Anna → アンナ、Emma → エンマ
                elif lang == 'de' and c in 'kptf' and phonemes and phonemes[-1][0] == 'V':
                    phonemes.append(('C', 'Q'))    # Otto → オット
            phonemes.append(('C', consonants[c]))
        k += 1
    return _kana(_segments(phonemes))


# ----------------------------------------------------------------------
# 韓国語 (ハングルの音節を 初声・中声・終声 に分けて)

KO_INITIALS = ('k', 'kk', 'n', 't', 'tt', 'r', 'm', 'p', 'pp', 's', 'ss', '', 'ch', 'jj', 'ch', 'k', 't', 'p', 'h')
KO_INITIALS_VOICED = {'k': 'g', 't': 'd', 'p': 'b', 'ch': 'j'}   # 語中の平音は濁る (민기 → ミンギ)
KO_VOWELS = ('a', 'e', 'ya', 'ye', 'o', 'e', 'yo', 'ye', 'o', 'wa', 'we', 'we', 'yo', 'u', 'wo', 'we', 'wi', 'yu', 'u', 'ui', 'i')
KO_FINALS = ('', 'ク', 'ク', 'ク', 'ン', 'ン', 'ン', 'ッ', 'ル', 'ク', 'ム', 'ル', 'ル', 'ル', 'プ', 'ル', 'ム', 'プ', 'プ',
             'ッ', 'ッ', 'ン', 'ッ', 'ッ', 'ク', 'ッ', 'プ', 'ッ')
KO_PLAIN = {0, 3, 7, 12}   # ㄱ ㄷ ㅂ ㅈ (平音)


def _korean_syllable(cons, vowel):
    if cons == 'jj':
        cons = 'ch'
    cons = {'kk': 'k', 'tt': 't', 'pp': 'p', 'ss': 's'}.get(cons, cons)
    glide = vowel[0] if len(vowel) == 2 and vowel[0] in 'yw' else ''
    base = vowel[-1] if glide else vowel
    if vowel == 'ui':
        return _korean_syllable(cons, 'i') if cons else 'ウイ'   # 희 → ヒ、의 → ウイ
    if glide == 'w' and base == 'e' and cons in ('ch', 'j', 's'):
        glide, vowel = '', 'e'   # 최 → チェ
    if glide == 'y':
        if cons == '':
            return {'a': 'ヤ', 'e': 'イェ', 'o': 'ヨ', 'u': 'ユ'}[base]
        if cons in ('ch', 'j', 's'):   # 자・주 などは拗音にしない
            return ROWS['sh' if cons == 's' else cons][DAN.index(base)] if base in 'aou' else ROWS[cons][3]
        row = ROWS.get(cons, ROWS[''])
        head = row[1] if isinstance(row, tuple) else row[1]
        return head + ({'a': 'ャ', 'o': 'ョ', 'u': 'ュ'}.get(base) or 'ェ')
    if glide == 'w':
        if cons == '':
            return {'a': 'ワ', 'e': 'ウェ', 'i': 'ウィ', 'o': 'ウォ'}[base]
        row = ROWS.get(cons, ROWS[''])
        return (row[2] if isinstance(row, tuple) else row[2]) + {'a': 'ァ', 'e': 'ェ', 'i': 'ィ', 'o': 'ォ'}[base]
    if cons == 's' and base == 'i':
        return 'シ'
    if cons in ('ch', 'j'):
        return ROWS[cons][DAN.index(base)]
    if cons == 't' and base == 'u':
        return 'トゥ'
    if cons == 'd' and base == 'u':
        return 'ドゥ'
    return ROWS.get(cons, ROWS[''])[DAN.index(base)]


def korean(name):
    out = []
    previous_final = None
    for ix, ch in enumerate(name):
        code = ord(ch) - 0xAC00
        if not 0 <= code < 11172:
            out.append(ch)
            previous_final = None
            continue
        initial, vowel, final = code // 588, code % 588 // 28, code % 28
        cons = KO_INITIALS[initial]
        if ix and initial in KO_PLAIN and previous_final in (0, 4, 8, 16, 21):   # 母音・ㄴㄹㅁㅇ の後ろで濁る
            cons = KO_INITIALS_VOICED[cons]
        if initial == 5 and ix == 0:
            cons = 'n' if KO_VOWELS[vowel] not in ('i', 'ya', 'yo', 'yu', 'ye') else ''   # 頭音法則風 (리 → イ)
        out.append(_korean_syllable(cons, KO_VOWELS[vowel]))
        out.append(KO_FINALS[final])
        previous_final = final
    return ''.join(out)
