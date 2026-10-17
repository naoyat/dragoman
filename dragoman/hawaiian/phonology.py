#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の発音と、espeak-ng のハワイ語の音声 (haw) に渡す音素の列
#
#   espeak_word('ʻāina') → "?'a:ina"、espeak_phonemes('Aloha ʻoe') → "[[al'oha ?'oe]]"
#
# 音素は子音8つ (p k ʔ h m n l w) と母音5つ (a e i o u) の長短。espeak-ng の haw の音声は文字のまま渡すと ʻokina を
# 読まない (ʻoe → [oe]) ので、音素で渡す:
#   - ʻokina は声門閉鎖音 ?、長音符 (kahakō) は長母音 a: …
#   - w は i・e の後ろで [v]、u・o の後ろと語頭で [w] (ハワイ語の話者の多くの読み: ʻawa [ʔava]・iwi [ivi])
#   - 二重母音 ai・ae・ao・au・ei・eu・oi・ou・iu は1音節 (最初の母音が強い)
#   - 強勢: 最後の音節が長母音・二重母音ならそこ、それ以外は終わりから2番目の音節。ほかの長母音には副強勢
#
import re
import unicodedata

from . import orthography

LONG = {'ā': 'a', 'ē': 'e', 'ī': 'i', 'ō': 'o', 'ū': 'u'}
DIPHTHONGS = ('ai', 'ae', 'ao', 'au', 'ei', 'eu', 'oi', 'ou', 'iu')
VOWELS = 'aeiou'


def syllables(word):
    """語 → [(頭子音, 核, 長いか)] (核は母音1つ・長母音・二重母音)"""
    w = unicodedata.normalize('NFC', orthography.normalize(word).lower())
    out = []
    onset = ''
    i = 0
    while i < len(w):
        c = w[i]
        if c == orthography.OKINA:
            onset = '?'
            i += 1
            continue
        if c in LONG or c in VOWELS:
            v = LONG.get(c, c)
            long_ = c in LONG
            nxt = w[i + 1] if i + 1 < len(w) else ''
            if not long_ and nxt in VOWELS and v + nxt in DIPHTHONGS and \
                    not (i + 2 < len(w) and w[i + 2] in VOWELS + ''.join(LONG)):   # ai・au … (後ろに母音が続かなければ)
                out.append((onset, v + nxt, True))
                i += 2
            else:
                out.append((onset, v, long_))
                i += 1
            onset = ''
            continue
        if c.isalpha():
            onset = c
        i += 1
    return out


def stress(syls):
    """強勢の音節の位置: 最後が長いならそこ、それ以外は終わりから2番目。その前の長母音に頭子音の無い音節が続くとき
    (ʻā-i-na) は長母音の方"""
    if not syls:
        return None
    if syls[-1][2] or len(syls) == 1:
        return len(syls) - 1
    k = len(syls) - 2
    if k > 0 and not syls[k][0] and syls[k - 1][2] and len(syls[k - 1][1]) == 1:
        return k - 1
    return k


def _consonant(c, prev_vowel):
    if c == 'w':
        return 'v' if prev_vowel in ('i', 'e') else 'w'
    return c


def espeak_word(word):
    syls = syllables(word)
    k = stress(syls)
    out = ''
    prev = ''
    for j, (onset, nucleus, long_) in enumerate(syls):
        mark = "'" if j == k else (',' if long_ and len(nucleus) == 1 else '')
        out += _consonant(onset, prev[-1:] if prev else '') + mark + nucleus + (':' if long_ and len(nucleus) == 1 else '')
        prev = nucleus
    return out


def espeak_words(spellings):
    """綴りの列 (analyzer.spelled) → espeak-ng に渡す音素の列 ([[…]])。句読点は区切り"""
    parts = []
    for s in spellings:
        if s in '.!?':
            parts.append('_:')
        elif s in ',;:':
            parts.append('_')
        elif re.search('[A-Za-zĀĒĪŌŪāēīōū]', s):
            parts += [espeak_word(w) for w in s.split()]
    return '[[%s]]' % ' '.join(parts)


def espeak_phonemes(text):
    return espeak_words(re.findall(r"[A-Za-zĀĒĪŌŪāēīōūʻ'‘`’]+|[.!?,;:]", orthography.normalize(text)))
