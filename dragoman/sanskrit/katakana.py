#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# サンスクリットの語 (主に固有名詞) をカタカナで書く: 発音 (sanskrit/phonology.segments の IPA) を、どの言語にも共通の規則
# (core/kana.py) で
#
#   rāma → ラーマ、kṛṣṇa → クリシュナ、śiva → シヴァ、buddha → ブッダ、gaṅgā → ガンガー
#
# 入力は IAST (デーヴァナーガリーも可。sanskrit/script で SLP1 に)。長母音 (ā ī ū ṝ と e o) は「ー」、音節の ṛ・ḷ は「リ」、
# そり舌音 (ṭ ḍ ṇ ṣ) は t・d・n・ʃ に、有気音・つぶやきの ʰ・ʱ・ɦ (bh・dh …) は書かない、v は「ヴ」
#
from dragoman.core.kana import kana
from . import phonology, script

RETROFLEX = {'ʈ': 't', 'ɖ': 'd', 'ɳ': 'n', 'ʂ': 'ʃ', 'ɭ': 'l', 'ɽ': 'r'}


def ipa(slp1):
    out = []
    prev_consonant = False
    for seg in phonology.segments(slp1):
        p = seg.ipa.replace('̪', '').replace('ʱ', '').replace('ʰ', '')   # 歯音の印 ̪・有気音
        if p in ('r̩', 'r̩ː', 'l̩', 'l̩ː'):
            out += ['r', 'i' + ('ː' if p.endswith('ː') else '')]   # 音節の ṛ (kṛṣṇa → クリシュナ)
            prev_consonant = False
            continue
        if p == 'ɦ' and prev_consonant:
            continue   # 有声の有気音 (bh・dh) の ɦ
        if seg.vowel:
            out.append(p.replace('ɐ', 'a'))
            prev_consonant = False
        else:
            out.append(RETROFLEX.get(p, p))
            prev_consonant = True
    return out


def katakana(word, **options):
    phonemes = []
    for w in word.split():
        if phonemes:
            phonemes.append(' ')
        phonemes += ipa(script.to_slp1(w.lower()))
    return kana(phonemes, **options)
