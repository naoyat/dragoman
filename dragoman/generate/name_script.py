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
    return None
