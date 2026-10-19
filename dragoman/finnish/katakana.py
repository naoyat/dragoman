#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語の語をカタカナで書く: 綴りがほぼそのまま発音なので、綴り → 音素 → 共通の規則 (core/kana.py)
#
#   Matti → マッティ、Liisa → リーサ、Jyväskylä → ユヴァスキュラ、Ville → ヴィッレ、Lahti → ラハティ、Helsinki → ヘルスィンキ
#
#   - 同じ母音字2つは長母音「ー」、同じ子音字2つは重子音 (l・r も「ッ」: Ville → ヴィッレ。n・m は「ン」: Anna → アンナ)
#   - ä [æ] はア段、ö [ø] はエ段、y [y] は「ユ」(子音の後ろは「キュ」)
#   - 母音の続かない h は前の母音の段 (Lahti → ラハティ、Tohmajärvi → トホマヤルヴィ)
#   - ng は [ŋŋ] (kengät → ケンガト)、nk は [ŋk]
#
from dragoman.core.kana import kana, text_words

VOWELS = {'a': 'ɑ', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'y': 'y', 'ä': 'æ', 'ö': 'ø', 'å': 'o'}
CONSONANTS = {'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'j', 'k': 'k', 'l': 'l', 'm': 'm',
              'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's', 'š': 'ʃ', 't': 't', 'v': 'v', 'w': 'v', 'x': 'ks',
              'z': 'ts', 'ž': 'ʒ'}
H_VOWELS = {'ɑ': 'a', 'æ': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'y': 'u', 'ø': 'e'}


def phonemes(word):
    word = word.lower()
    out = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c in VOWELS:
            if nxt == c:
                out.append(VOWELS[c] + 'ː')
                k += 2
                continue
            out.append(VOWELS[c])
        elif c == 'n' and nxt == 'g':
            out += ['ŋ', 'g']                 # ng [ŋŋ] → 「ング」+ 母音
            k += 2
            continue
        elif c == 'h' and nxt not in VOWELS and out and out[-1][:1] in H_VOWELS:
            out += ['h', H_VOWELS[out[-1][:1]]]   # 母音の続かない h (Lahti → ラハティ)
        elif c in CONSONANTS:
            ph = CONSONANTS[c]
            if ph == 'ks':
                out += ['k', 's']
            else:
                out.append(ph)
        k += 1
    return out


def katakana(word, long='phonemic', **options):
    options.setdefault('liquid_sokuon', True)
    return kana(phonemes(word), long=long, **options)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)"""
    return [katakana(w, **options) for w in text_words(text)]
