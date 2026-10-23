#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ペルシア語 (現代のテヘランの発音) の語をカタカナで書く: 解析で選んだ語形の転写 (persian の roman。â・e・o・ey …) → 音素 →
# 共通の規則 (core/kana.py)。短母音を書かない文字なので、文の解析の後で (command.katakana)
#
#   ketâb → ケターブ、xarid → ハリード、šahr → シャフル、dust-e man → ドゥーステ マン、pedaram → ペダラム、xeyli → ヘイリー
#
#   - â [ɒː]・i・u は長い母音で「ー」(ketâb → ケターブ、dust → ドゥースト)、a [æ]・e・o は短く
#   - ey・ow は「エイ」「オウ」、エザーフェの -e は前の語に続けて (dust-e → ドゥーステ)
#   - x はハ行、q・ğ [ɢ~ɣ] はガ行、č はチャ行、j はジャ行、ž はジャ行、š はシャ行、v はヴ行、ハムザ・アイン (ʾ・ʿ) は書かない
#
from dragoman.core.kana import kana

LETTERS = {'â': 'aː', 'i': 'iː', 'u': 'uː', 'a': 'a', 'e': 'e', 'o': 'o',
           'b': 'b', 'p': 'p', 't': 't', 's': 's', 'j': 'dʒ', 'č': 'tʃ', 'h': 'h', 'x': 'x', 'd': 'd', 'z': 'z', 'r': 'r',
           'ž': 'ʒ', 'š': 'ʃ', 'f': 'f', 'q': 'g', 'ğ': 'g', 'k': 'k', 'g': 'g', 'l': 'l', 'm': 'm', 'n': 'n', 'v': 'v',
           'w': 'v', 'y': 'j'}
SILENT = "ʾʿ'’-"


def phonemes(roman):
    roman = roman.lower()
    out = []
    for k, c in enumerate(roman):
        if c in SILENT:
            continue
        ph = LETTERS.get(c)
        if ph is None:
            continue
        nxt = roman[k + 1] if k + 1 < len(roman) else ''
        if c == 'i' and out and out[-1] == 'e' and nxt not in LETTERS or c == 'y' and out and out[-1] == 'e':
            ph = 'j'   # ey「エイ」(xeyli → ヘイリー)
        if c == 'w' and out and out[-1] == 'o':
            ph = 'w'   # ow「オウ」
        out.append(ph)
    return out


def katakana(roman, long='phonemic', **options):
    """転写の語 → カタカナ"""
    return kana(phonemes(roman), long=long, **options)
