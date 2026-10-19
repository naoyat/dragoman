#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古典ギリシア語の語 (主に固有名詞) をカタカナで書く: 発音 (greek/phonology.phonemize_word。アッティカ方言の再建音) を
# IPA にして、どの言語にも共通の規則 (core/kana.py) で
#
#   Σωκράτης → ソークラテース、Ἀθῆναι → アテーナイ、Ὅμηρος → ホメーロス
#
# 長母音 (η・ω、長い α ι υ) は「ー」、二重母音 αι・οι は「アイ」「オイ」(音声の近似の記号 aE・OE は実際の音 [ai] [oi] に)、
# 有気音 (φ θ χ) は無気音と同じ (パ・タ・カ行)、υ は「ユ」(子音の後ろは「キュ」)
#
from dragoman.core.kana import kana
from .phonology import Nucleus, phonemize_word

VOWELS = {'a': 'a', 'E': 'ɛ', 'e': 'e', 'I': 'i', 'i': 'i', 'O': 'ɔ', 'o': 'o', 'U': 'u', 'u': 'u', 'y': 'y'}
DIPHTHONGS = {'aE': ('a', 'i'), 'aU': ('a', 'u'), 'OE': ('o', 'i')}
CONSONANTS = {'N': 'ŋ'}


def ipa(word, pron='attic'):
    if pron in ('attic', 'erasmian'):   # 長短どちらもある母音 (α ι υ) の長さを辞書から (φιλοσοφία の最後の α は長い)
        from . import length
        word = length.mark(word)
    out = []
    for seg in phonemize_word(word, pron).segments:
        if isinstance(seg, Nucleus):
            for p in seg.phonemes:
                if p in DIPHTHONGS:
                    out += DIPHTHONGS[p]
                else:
                    out.append(VOWELS.get(p.rstrip(':'), p.rstrip(':')) + ('ː' if p.endswith(':') else ''))
        else:
            base = seg.replace('_h', 'ʰ')
            out.append(CONSONANTS.get(base, base))
    return out


def katakana(word, pron='attic', **options):
    phonemes = []
    for w in word.split():
        if phonemes:
            phonemes.append(' ')
        phonemes += ipa(w, pron)
    return kana(phonemes, **options)
