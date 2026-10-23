#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# アラビア語 (現代標準アラビア語) の語をカタカナで書く: 解析で選んだ母音付きの語形の転写 (DIN 31635 に近い形。arabic/script.translit)
# → 音素 → 共通の規則 (core/kana.py)。母音を書かない文は解析しないと読めないので、文の解析の後で (command.katakana)
#
#   kitābun → キターブン、al-waladu → アルワラドゥ、ad-darsa → アッダルサ、ḏahaba → ザハバ、šams → シャムス
#
#   - 長母音 ā・ī・ū は「ー」、二重母音 ay・aw は「アイ」「アウ」、同じ子音の重なり (ad-darsa の dd) は「ッ」(l・r も)
#   - ḏ [ð] はザ行、ṯ [θ] はサ行、ǧ [dʒ] はジャ行、š はシャ行、ḥ・ḫ・h はハ行、ġ [ɣ] はガ行、q はカ行、
#     強勢音 (ṣ・ḍ・ṭ・ẓ) は普通の子音と同じ、ハムザ ʾ とアイン ʿ は書かない
#   - 格の語尾 (-u・-i・-a・-un) は書いてあるとおりに読む (休止形にしない)
#
import re

from dragoman.core.kana import kana

LETTERS = {'ā': 'aː', 'ī': 'iː', 'ū': 'uː', 'a': 'a', 'i': 'i', 'u': 'u', 'e': 'e', 'o': 'o',
           'b': 'b', 't': 't', 'ṯ': 'θ', 'ǧ': 'dʒ', 'j': 'dʒ', 'ḥ': 'h', 'ḫ': 'x', 'x': 'x', 'd': 'd', 'ḏ': 'ð', 'r': 'r',
           'z': 'z', 's': 's', 'š': 'ʃ', 'ṣ': 's', 'ḍ': 'd', 'ṭ': 't', 'ẓ': 'z', 'ġ': 'ɣ', 'f': 'f', 'q': 'k', 'k': 'k',
           'l': 'l', 'm': 'm', 'n': 'n', 'h': 'h', 'w': 'w', 'y': 'j', 'p': 'p', 'v': 'v', 'g': 'g'}
SILENT = "ʾʿ'’-"


def phonemes(roman):
    roman = roman.lower().replace('iyy', 'īy').replace('uww', 'ūw')   # ʿarabiyyun → アラビーユン
    out = []
    for c in roman:
        if c in SILENT:
            continue
        ph = LETTERS.get(c)
        if ph:
            out.append(ph)
    return out


def katakana(roman, long='phonemic', **options):
    """転写の語 → カタカナ"""
    options.setdefault('liquid_sokuon', True)
    return kana(phonemes(roman), long=long, **options)
