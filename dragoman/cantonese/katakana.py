#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語のカタカナ読み: 粤拼 (Jyutping。PyCantonese の parse_jyutping で 頭子音・主母音・末子音に分ける) から音節ごとに。
# 声調と母音の長さ (aa / a) は書かない。
#   你好 nei5 hou2 → ネイ ホウ、唔該 m4 goi1 → ム ゴイ、香港 hoeng1 gong2 → ヒョン ゴン、廣東話 → グォン ドン ワ
#   - 無気音 b・d・g・z はバ・ダ・ガ・ジャ行、有気音 p・t・k・c はパ・タ・カ・チャ行 (普通話のカタカナと同じ)
#   - gw・kw はグァ・クァ行、ng はガ行、j はヤ行、yu はユ (書 syu → シュ)、oe・eo はオ (oe は拗音: 香 → ヒョ)
#   - 末子音 -m ム、-n・-ng ン、-p ップ、-t ット、-k ック。u・o + ng・k はオン・オック (東 dung → ドン、六 luk → ロック)
#   - 音節だけの m (唔) はム、ng (五) はン
#
from . import morphology

# 頭子音 → (ア, イ, ウ, エ, オ) の段
ROWS = {
    '': 'アイウエオ', 'b': 'バビブベボ', 'p': 'パピプペポ', 'm': 'マミムメモ', 'f': ('ファ', 'フィ', 'フ', 'フェ', 'フォ'),
    'd': ('ダ', 'ディ', 'ドゥ', 'デ', 'ド'), 't': ('タ', 'ティ', 'トゥ', 'テ', 'ト'), 'n': 'ナニヌネノ', 'l': 'ラリルレロ',
    'g': 'ガギグゲゴ', 'k': 'カキクケコ', 'ng': 'ガギグゲゴ', 'h': 'ハヒフヘホ',
    'gw': ('グァ', 'グィ', 'グ', 'グェ', 'グォ'), 'kw': ('クァ', 'クィ', 'ク', 'クェ', 'クォ'),
    'w': ('ワ', 'ウィ', 'ウ', 'ウェ', 'ウォ'), 'z': ('ジャ', 'ジ', 'ジュ', 'ジェ', 'ジョ'), 'c': ('チャ', 'チ', 'チュ', 'チェ', 'チョ'),
    's': ('サ', 'シ', 'ス', 'セ', 'ソ'), 'j': ('ヤ', 'イ', 'ユ', 'イェ', 'ヨ'),
}
VOWELS = {'aa': 0, 'a': 0, 'i': 1, 'u': 2, 'e': 3, 'o': 4, 'eo': 4, 'oe': 4, 'yu': 2}
CODAS = {'': '', 'i': 'イ', 'u': 'ウ', 'm': 'ム', 'n': 'ン', 'ng': 'ン', 'p': 'ップ', 't': 'ット', 'k': 'ック'}


def _youon(onset, small):
    """イ段 + 小さいュ・ョ (書 syu → シュ、香 hoeng → ヒョン)。ヤ行・ア行は ユ・ヨ、フィ・ディ … は フュ・デュ …"""
    if onset in ('', 'j'):
        return {'ュ': 'ユ', 'ョ': 'ヨ'}[small]
    i = ROWS[onset][1]
    return (i[:-1] if i.endswith('ィ') else i) + small


def syllable(onset, nucleus, coda):
    if nucleus == 'm' and not onset:
        return 'ム'
    if nucleus == 'ng' and not onset:
        return 'ン'
    if onset == 'w' and nucleus == 'u':
        head = 'ウ'
    elif nucleus == 'yu':
        head = _youon(onset, 'ュ')
    elif nucleus == 'oe':
        head = _youon(onset, 'ョ')
    else:
        row = ROWS.get(onset, ROWS[''])
        vowel = VOWELS.get(nucleus, 0)
        if nucleus == 'u' and coda in ('ng', 'k'):
            vowel = 4   # 東 dung → ドン、六 luk → ロック
        head = row[vowel]
    return head + CODAS.get(coda, '')


def from_jyutping(jyutping):
    import pycantonese
    out = []
    for syl in jyutping.split():
        try:
            parts = pycantonese.parse_jyutping(syl)
        except ValueError:
            continue
        out += [syllable(p.onset, p.nucleus, p.coda) for p in parts]
    return ' '.join(out)


def katakana(word):
    """語 (漢字) → カタカナ (音節ごとに空白で)"""
    jp = morphology.jyutping(word)
    return from_jyutping(jp) if jp else ''
