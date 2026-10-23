#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 聖書ヘブライ語 (と聖書アラム語) の語をカタカナで書く: 母音記号付きの綴りの転写 (hebrew/script.translit。begadkefat の
# 摩擦音も書き分けた形) → 音素 → 共通の規則 (core/kana.py)。読みは聖書時代の再建音 (現代イスラエルの読みでなく)
#
#   בְּרֵאשִׁית (bərēʾšîṯ) → ベレーシーサ、דָּבָר (dāḇār) → ダーヴァール、מֶלֶךְ (meleḵ) → メレフ、שָׁלוֹם → シャーローム、
#   אֱלֹהִים → エローヒーム、רוּחַ → ルーアハ
#
#   - 長母音 (ā ē ō î û ê ô â) は「ー」、有声のシェヴァ ə と短いハテフ (ă ĕ ŏ) は短い母音 (ə はエ段)
#   - 弱いダゲシュの無い begadkefat は摩擦音: ḇ [v] はヴ行、ḡ [ɣ] はガ行、ḏ [ð] はザ行、ḵ [x] はハ行、f はファ行、
#     ṯ [θ] はサ行。強いダゲシュの重子音 (haššāmayim) は「ッ」
#   - ʾ (א) と ʿ (ע) は書かない、ḥ (ח) はハ行、ṭ (ט) は t、ṣ (צ) は s、q (ק) は k、š はシャ行、ś・s はサ行、w はワ行
#   - 神の名 יהוה は朗読の読み (qere) で (既定 アドーナーイ。音読の --divine-name と同じ)
#
from dragoman.core.kana import kana, text_words

LETTERS = {'ā': 'aː', 'ē': 'eː', 'ō': 'oː', 'î': 'iː', 'û': 'uː', 'ê': 'eː', 'ô': 'oː', 'â': 'aː', 'ī': 'iː', 'ū': 'uː',
           'a': 'a', 'e': 'e', 'i': 'i', 'o': 'o', 'u': 'u', 'ə': 'e', 'ă': 'a', 'ĕ': 'e', 'ŏ': 'o',
           'b': 'b', 'v': 'v', 'ḇ': 'v', 'g': 'g', 'ḡ': 'ɣ', 'd': 'd', 'ḏ': 'ð', 'h': 'h', 'w': 'w', 'z': 'z', 'ḥ': 'h',
           'ṭ': 't', 'y': 'j', 'k': 'k', 'ḵ': 'x', 'l': 'l', 'm': 'm', 'n': 'n', 's': 's', 'p': 'p', 'f': 'f', 'ṣ': 's',
           'q': 'k', 'r': 'r', 'š': 'ʃ', 'ś': 's', 't': 't', 'ṯ': 'θ'}
SILENT = "ʾʿ'-"


def phonemes(roman):
    out = []
    for c in roman.lower():
        if c in SILENT:
            continue
        ph = LETTERS.get(c)
        if ph:
            out.append(ph)
    return out


def katakana(roman, long='phonemic', **options):
    """転写の語 → カタカナ"""
    return kana(phonemes(roman), long=long, **options)


def word_katakana(word, divine_name='adonai', **options):
    """母音記号付きのヘブライ文字の語 → カタカナ"""
    from . import script
    return katakana(script.translit(script.qere(word, divine_name), all_spirants=True), **options)


def sentence(text, divine_name='adonai', **options):
    return [word_katakana(w, divine_name, **options) for w in text_words(text)]
