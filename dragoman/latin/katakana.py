#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ラテン語の語 (主に固有名詞) をカタカナで書く
#
#   Caesar → カエサル, Mārcus → マールクス, Iūlia → ユーリア, Cicerō → キケロー,
#   Polyphēmus → ポリュペームス, Hannibal → ハンニバル, Iuppiter → ユッピテル
#
# 音素列 (latin_phonology.phonemize_word) を IPA にして、どの言語にも共通の規則 (core/kana.py) で書く。
# 長母音は「ー」、閉鎖音・s・f の重子音は「ッ」、n・m の重子音は「ン」、l・r の重子音は1つにする (Gallia → ガリア)。
# 有気音は無気音と同じに書く。
#
from dragoman.core.kana import kana
from .latin_phonology import phonemize_word

# latin_phonology の音素の記号 → IPA (core/kana.py に渡す): 短い母音 E I O U は緩んだ母音、N は軟口蓋鼻音、
# 長さの : は ː、有気音の _h は ʰ。二重母音 aE・aU・OE は母音2つ
LATIN_IPA = {'E': 'ɛ', 'I': 'ɪ', 'O': 'ɔ', 'U': 'ʊ', 'N': 'ŋ'}
DIPHTHONGS = {'aE': ('a', 'e'), 'aU': ('a', 'u'), 'OE': ('o', 'e')}


def ipa(phonemes):
    out = []
    for p in phonemes:
        if p in DIPHTHONGS:
            out += DIPHTHONGS[p]
            continue
        base = p.rstrip(':').replace('_h', 'ʰ')
        out.append(LATIN_IPA.get(base, base) + ('ː' if p.endswith(':') else ''))
    return out


def katakana(word, **options):
    """ラテン語の語 → カタカナ (語ごとに音素の列にして、共通の規則 core/kana.py で。options は long・wa)"""
    phonemes = []
    for w in word.split():
        if phonemes:
            phonemes.append(' ')
        phonemes += ipa(phonemize_word(w))
    return kana(phonemes, **options)
