#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 名前の表 (names.tsv) に無い固有名詞を、ラテン文字の綴りから各言語の文字に写す (規則による写し。慣用の形とは限らない)
#
#   ラテン語の名前は語尾 -us・-um を除いた形を写す (ロシア語の name() と同じ: Mārcus → Mark-)。長母音 (ā・ō …) は
#   長母音の字に。ギリシア語は男性 -ος・中性 -ον・女性 -α を付ける (Mārcus → Μαρκος)。アクセントは付けない
#
#   写す言語: grc (ギリシア文字)・ar (アラビア文字)・fa・ur (ペルシア文字)・he (ヘブライ文字)・hi (デーヴァナーガリー)
#
import re
import unicodedata

LONG = {'ā': 'A', 'ē': 'E', 'ī': 'I', 'ō': 'O', 'ū': 'U', 'ȳ': 'I'}


def _normalize(latin):
    """ラテン文字の名前 → 写しの元の形 (小文字。長母音は大文字 A E I O U、二字の音は1字に)"""
    word = unicodedata.normalize('NFC', latin.strip())
    word = ''.join(LONG.get(c, c) for c in word.lower())
    word = ''.join(c for c in unicodedata.normalize('NFD', word) if not unicodedata.combining(c))
    for a, b in (('ae', 'E'), ('oe', 'E'), ('ph', 'f'), ('th', 't'), ('ch', 'x'), ('qu', 'kw'), ('x', 'ks'),
                 ('c', 'k'), ('y', 'i')):
        word = word.replace(a, b)
    word = re.sub(r'^[ij](?=[aeiouAEIOU])', 'j', word)   # Iūlia → jUlia
    word = re.sub(r'(?<=[aeiouAEIOU])[ij](?=[aeiouAEIOU])', 'j', word)
    word = re.sub(r'v|(?<![a-zAEIOU])u(?=[aeiouAEIOU])', 'w', word)
    return word


def _stem(word):
    """男性・中性の語尾 -us・-um を除く (語幹が短すぎるときは除かない)"""
    for ending in ('us', 'um'):
        if word.endswith(ending) and len(word) > 4:
            return word[:-2], 'm' if ending == 'us' else 'n'
    return word, ''   # 語尾を除かなかった名前 (Iūnō・Caesar) はそのまま写す


GREEK = {'a': 'α', 'A': 'α', 'b': 'β', 'd': 'δ', 'e': 'ε', 'E': 'η', 'f': 'φ', 'g': 'γ', 'h': '', 'i': 'ι', 'I': 'ι',
         'j': 'ι', 'k': 'κ', 'l': 'λ', 'm': 'μ', 'n': 'ν', 'o': 'ο', 'O': 'ω', 'p': 'π', 'r': 'ρ', 's': 'σ', 't': 'τ',
         'u': 'ου', 'U': 'ου', 'w': 'ου', 'x': 'χ', 'z': 'ζ'}
ARABIC = {'a': 'ا', 'A': 'ا', 'b': 'ب', 'd': 'د', 'e': 'ي', 'E': 'ي', 'f': 'ف', 'g': 'غ', 'h': 'ه', 'i': 'ي', 'I': 'ي',
          'j': 'ي', 'k': 'ك', 'l': 'ل', 'm': 'م', 'n': 'ن', 'o': 'و', 'O': 'و', 'p': 'ب', 'r': 'ر', 's': 'س', 't': 'ت',
          'u': 'و', 'U': 'و', 'w': 'و', 'x': 'خ', 'z': 'ز'}
PERSIAN = dict(ARABIC, p='پ', g='گ', k='ک', w='و', e='ی', E='ی', i='ی', I='ی', j='ی')
HEBREW = {'a': '', 'A': 'א', 'b': 'ב', 'd': 'ד', 'e': '', 'E': 'י', 'f': 'פ', 'g': 'ג', 'h': 'ה', 'i': 'י', 'I': 'י',
          'j': 'י', 'k': 'ק', 'l': 'ל', 'm': 'מ', 'n': 'נ', 'o': 'ו', 'O': 'ו', 'p': 'פ', 'r': 'ר', 's': 'ס', 't': 'ט',
          'u': 'ו', 'U': 'ו', 'w': 'ו', 'x': 'כ', 'z': 'ז'}
HEBREW_FINALS = {'כ': 'ך', 'מ': 'ם', 'נ': 'ן', 'פ': 'ף', 'צ': 'ץ'}
DEVANAGARI_CONSONANTS = {'b': 'ब', 'd': 'ड', 'f': 'फ़', 'g': 'ग', 'h': 'ह', 'j': 'य', 'k': 'क', 'l': 'ल', 'm': 'म',
                         'n': 'न', 'p': 'प', 'r': 'र', 's': 'स', 't': 'ट', 'w': 'व', 'x': 'ख़', 'z': 'ज़'}
DEVANAGARI_VOWELS = {'a': ('अ', ''), 'A': ('आ', 'ा'), 'e': ('ए', 'े'), 'E': ('ए', 'े'), 'i': ('इ', 'ि'), 'I': ('ई', 'ी'),
                     'o': ('ओ', 'ो'), 'O': ('ओ', 'ो'), 'u': ('उ', 'ु'), 'U': ('ऊ', 'ू')}
VIRAMA = '्'


def _greek(stem, kind):
    letters = [GREEK.get(c, '') for c in stem]
    ending = {'m': 'ος', 'n': 'ον'}.get(kind, '')
    word = ''.join(letters) + ending
    word = re.sub('σ$', 'ς', word)
    return word[:1].upper() + word[1:] if word else word


def _abjad(stem, table, initial_vowel):
    out = []
    for k, c in enumerate(stem):
        if k == 0 and c in 'aeiouAEIOU':
            out.append(initial_vowel.get(c, 'ا'))   # 語頭の母音 (アラビア語 أ・إ・أو)
            continue
        if c == 'a' and 0 < k < len(stem) - 1:
            continue   # 語中の短い a は書かない (Marcus → مركوس でなく مارك… は長い ā だけ)
        out.append(table.get(c, ''))
    return ''.join(out)


def _hebrew(stem):
    out = []
    for k, c in enumerate(stem):
        if k == 0 and c in 'aeiouAEIOU':
            out.append('א' + HEBREW.get(c, ''))
            continue
        out.append(HEBREW.get(c, ''))
    word = ''.join(out)
    if word and word[-1] in HEBREW_FINALS:
        word = word[:-1] + HEBREW_FINALS[word[-1]]
    if stem.endswith(('a', 'A')):
        word += 'ה'   # 語末の -a は ה (Julia → יוליה)
    return word


def _devanagari(stem):
    stem = re.sub('ia$', 'ijA', stem)   # 語末の -ia は -iyā (Julia → जूलिया)
    stem = re.sub('a$', 'A', stem)      # 語末の -a は長い ā (名前の慣用)
    out = ''
    pending = False   # 直前が子音 (母音記号か virama を待っている)
    for c in stem:
        if c in DEVANAGARI_VOWELS:
            independent, sign = DEVANAGARI_VOWELS[c]
            out += sign if pending else independent
            pending = False
        else:
            if pending:
                out += VIRAMA   # 子音の連続
            out += DEVANAGARI_CONSONANTS.get(c, '')
            pending = True
    return out   # 語末の子音は inherent a を書かない慣用 (मार्क)


# ハングル: 初声・中声の番号 (korean.py の _compose と同じ並び)
HANGUL_INITIALS = {'g': 0, 'k': 15, 'n': 2, 'd': 3, 't': 16, 'r': 5, 'l': 5, 'm': 6, 'b': 7, 'p': 17, 'f': 17, 's': 9,
                   '': 11, 'j': 11, 'w': 11, 'z': 12, 'x': 15, 'h': 18, 'c': 15, 'q': 15, 'v': 7}
HANGUL_VOWELS = {'a': 0, 'A': 0, 'e': 5, 'E': 5, 'i': 20, 'I': 20, 'o': 8, 'O': 8, 'u': 13, 'U': 13}
HANGUL_JVOWELS = {'a': 2, 'e': 7, 'o': 12, 'u': 17, 'i': 20}            # y + 母音 (야・예・요・유)
HANGUL_WVOWELS = {'a': 9, 'e': 15, 'i': 16, 'o': 14, 'u': 13}           # w + 母音 (와・웨・위・워)
HANGUL_FINALS = {'n': 4, 'm': 16, 'l': 8, 'k': 1, 'p': 17, 'g': 0}      # 音節末に残す子音 (ほかは 으 を付けて独立の音節)


def _hangul_syllable(initial, vowel, final=0):
    return chr(0xAC00 + initial * 588 + vowel * 28 + final)


def hangul(latin):
    """ラテン文字の名前 → ハングル (外来語の表記の簡略版。語尾は残す: Mārcus → 마르쿠스、Iūlia → 율리아、Rōma → 로마)"""
    word = _normalize(latin)
    out = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in HANGUL_VOWELS:
            out.append(_hangul_syllable(11, HANGUL_VOWELS[c]))
            k += 1
            continue
        if c == 'j' and nxt.lower() in HANGUL_JVOWELS:
            out.append(_hangul_syllable(11, HANGUL_JVOWELS[nxt.lower()]))
            k += 2
            continue
        if c == 'w' and nxt.lower() in HANGUL_WVOWELS:
            out.append(_hangul_syllable(11, HANGUL_WVOWELS[nxt.lower()]))
            k += 2
            continue
        if c == 'k' and nxt == 's':   # x = ks → 크스
            c = 'k'
        if c == 'l' and nxt in HANGUL_VOWELS and out and (ord(out[-1]) - 0xAC00) % 28 == 0:
            code = ord(out[-1]) - 0xAC00   # 母音の間の l は ㄹㄹ (Iūlia → 율리아)
            out[-1] = chr(0xAC00 + code + 8)
        if nxt in HANGUL_VOWELS:   # 子音 + 母音
            out.append(_hangul_syllable(HANGUL_INITIALS.get(c, 11), HANGUL_VOWELS[nxt]))
            k += 2
            continue
        # 母音の続かない子音: n・m・l は前の音節の終声、ほかは 으 (s は 스、r は 르)
        if out and c in ('n', 'm', 'l') and (ord(out[-1]) - 0xAC00) % 28 == 0 and nxt not in ('l',):
            code = ord(out[-1]) - 0xAC00
            out[-1] = chr(0xAC00 + code - code % 28 + HANGUL_FINALS[c])
            k += 1
            continue
        if c == 'l' and nxt == 'l' and out:   # ll → ㄹㄹ (Gallia → 갈리아)
            code = ord(out[-1]) - 0xAC00
            out[-1] = chr(0xAC00 + code - code % 28 + 8)
            k += 1
            continue
        out.append(_hangul_syllable(HANGUL_INITIALS.get(c, 11), 18))   # 으
        k += 1
    return ''.join(out)


def to_script(lang, latin):
    """ラテン文字の名前 → 言語 lang の文字。写せない言語・空なら None"""
    if not latin or not re.search('[A-Za-zĀ-ž]', latin):
        return None
    word = _normalize(latin)
    stem, kind = _stem(word)
    if lang == 'grc':
        return _greek(stem, kind)
    if lang == 'ar':
        return _abjad(stem, ARABIC, {'a': 'أ', 'A': 'آ', 'e': 'إي', 'i': 'إي', 'I': 'إي', 'o': 'أو', 'O': 'أو',
                                     'u': 'أو', 'U': 'أو'})
    if lang in ('fa', 'ur'):
        return _abjad(stem, PERSIAN, {'a': 'ا', 'A': 'آ', 'e': 'ای', 'i': 'ای', 'I': 'ای', 'o': 'او', 'O': 'او',
                                      'u': 'او', 'U': 'او'})
    if lang == 'he':
        return _hebrew(stem)
    if lang == 'hi':
        return _devanagari(stem)
    if lang == 'ko':
        return hangul(latin)
    return None
