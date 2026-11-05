#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# サンスクリットの文字: デーヴァナーガリー / IAST / 悉曇文字 (梵字) の入力を受け付け、中では SLP1 (ASCII の転写) で扱う。
# 表示は IAST とデーヴァナーガリーを併記する (vidyut.lipi で変換)。悉曇文字の入力か --siddham なら悉曇文字も
#
import re
import unicodedata

from vidyut import lipi

VEDIC_ACCENTS = re.compile('[॒॑᳐-᳿]')  # ॑ ॒ などのヴェーダのアクセント記号
DANDA = '।॥'
SIDDHAM_RANGE = '\U00011580-\U000115ff'
SIDDHAM = re.compile('[%s]' % SIDDHAM_RANGE)
SIDDHAM_DANDA = '\U000115c2\U000115c3'   # 悉曇文字のダンダ (। ॥ にあたる)
_siddham_forced = False


def set_siddham(flag):
    """--siddham: 悉曇文字も表示する"""
    global _siddham_forced
    _siddham_forced = flag


def siddham_wanted(text=''):
    """悉曇文字も表示するか (--siddham か、入力が悉曇文字)"""
    return _siddham_forced or is_siddham(text)


def is_siddham(text):
    return bool(SIDDHAM.search(text))


def is_devanagari(text):
    return any('ऀ' <= c <= 'ॿ' and c not in DANDA for c in text)


IAST_VOWELS = set('aeiouAEIOU')


def _strip_accents(text):
    """IAST の母音の上の á à (ヴェーダのアクセント) を除く。ś の ´ は子音の一部なので残す"""
    out, base, marks = [], '', ''
    for c in unicodedata.normalize('NFD', text):
        if unicodedata.combining(c):
            vowel = base in IAST_VOWELS or (base in 'rlRL' and '\u0323' in marks)
            if c in '\u0301\u0300' and vowel:
                continue
            marks += c
        else:
            base, marks = c, ''
        out.append(c)
    return unicodedata.normalize('NFC', ''.join(out))


def to_slp1(text):
    """デーヴァナーガリーか IAST の語を SLP1 に (ヴェーダのアクセント記号は除く。IAST なら á à の記号)"""
    text = VEDIC_ACCENTS.sub('', text)
    if is_siddham(text):
        return lipi.transliterate(text, lipi.Scheme.Siddham, lipi.Scheme.Slp1)
    if not is_devanagari(text):
        text = _strip_accents(text)
    scheme = lipi.Scheme.Devanagari if is_devanagari(text) else lipi.Scheme.Iast
    return lipi.transliterate(text, scheme, lipi.Scheme.Slp1)


def iast(slp1):
    return lipi.transliterate(slp1, lipi.Scheme.Slp1, lipi.Scheme.Iast)


def devanagari(slp1):
    return lipi.transliterate(slp1, lipi.Scheme.Slp1, lipi.Scheme.Devanagari)


def siddham(slp1):
    return lipi.transliterate(slp1, lipi.Scheme.Slp1, lipi.Scheme.Siddham)


def display(slp1):
    """IAST (デーヴァナーガリー)"""
    return '%s (%s)' % (iast(slp1), devanagari(slp1))
