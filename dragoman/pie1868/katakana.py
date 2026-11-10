#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 印欧祖語 (シュライヒャーの表記) の語をカタカナで書く: 綴り → 音素 → 共通の規則 (core/kana.py)
#
#   avis → アヴィス、akvāsas → アクヴァーサス、bhāram → バーラム、jasmin → ヤスミン、kard → カルド
#
#   - 長母音 ā・ī・ū は「ー」、v は「ヴ」(今の再建の *w)、j は「ヤ行」(*y)
#   - 有気音 bh・dh・gh は b・d・g と同じ (カタカナでは区別しない)
#
from dragoman.core.kana import kana

VOWELS = {'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o', 'ā': 'aː', 'ī': 'iː', 'ū': 'uː'}
DIGRAPHS = {'bh': 'b', 'dh': 'd', 'gh': 'g', 'kh': 'k', 'th': 't', 'ph': 'p'}
CONSONANTS = {'b': 'b', 'd': 'd', 'g': 'g', 'k': 'k', 't': 't', 'p': 'p', 'm': 'm', 'n': 'n', 'r': 'r', 'l': 'l',
              's': 's', 'v': 'v', 'j': 'j', 'h': 'h'}


def phonemes(word):
    word = word.lower()
    out = []
    k = 0
    while k < len(word):
        two = word[k:k + 2]
        if two in DIGRAPHS:
            out.append(DIGRAPHS[two])
            k += 2
            continue
        c = word[k]
        if c in VOWELS:
            out.append(VOWELS[c])
        elif c in CONSONANTS:
            out.append(CONSONANTS[c])
        k += 1
    return out


def katakana(word, long='phonemic', style=None, **options):
    return kana(phonemes(word), long=long, **options)
