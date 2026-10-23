#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ヒンディー語 (とウルドゥー語) の語をカタカナで書く: 転写 (hindi/script.translit。語末・語中のあいまい母音を落とした形) →
# 音素 → 共通の規則 (core/kana.py)
#
#   आदमी (ādmī) → アードミー、किताब (kitāb) → キターブ、नमस्ते (namaste) → ナマステー、है (hai) → ヘー、
#   और (aur) → オール、मैं (ma͠i) → メーン、कहाँ (kahā̃) → カハーン、लड़का (laṛkā) → ラルカー
#
#   - 長母音 ā・ī・ū と、いつも長い e・o は「ー」。ai [ɛː] はエ段の長音 (है → ヘー)、au [ɔː] はオ段の長音 (और → オール)
#   - 鼻母音 (ã・ma͠i) は母音の後ろに「ン」
#   - 有気音 (kh・bh …) は無気音と同じ行 (भारत → バーラト)、そり舌音 (ṭ・ḍ・ṇ) は歯音と同じ、ṛ・ṛh [ɽ] はラ行、
#     ś・ṣ [ʃ] はシャ行、c [tʃ] はチャ行、j [dʒ] はジャ行、x・ġ (ख़・ग़) はハ行・ガ行、v [ʋ] はワ行 (母音の前)
#
import re
import unicodedata

from dragoman.core.kana import kana, text_words

VOWELS = {'ā': 'aː', 'ī': 'iː', 'ū': 'uː', 'e': 'eː', 'o': 'oː', 'ai': 'eː', 'au': 'oː', 'a': 'a', 'i': 'i', 'u': 'u',
          'ŕ': 'ri'}
CONSONANTS = {'kh': 'k', 'gh': 'g', 'ch': 'tʃ', 'jh': 'dʒ', 'ṭh': 't', 'ḍh': 'd', 'th': 't', 'dh': 'd', 'ph': 'p',
              'bh': 'b', 'ṛh': 'r', 'k': 'k', 'g': 'g', 'c': 'tʃ', 'j': 'dʒ', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n', 't': 't',
              'd': 'd', 'n': 'n', 'p': 'p', 'b': 'b', 'm': 'm', 'y': 'j', 'r': 'r', 'l': 'l', 'v': 'w', 'w': 'w',
              'ś': 'ʃ', 'ṣ': 'ʃ', 's': 's', 'h': 'h', 'ṛ': 'r', 'x': 'x', 'ġ': 'g', 'q': 'k', 'z': 'z', 'f': 'f',
              'ñ': 'n', 'ṅ': 'ŋ', 'ṃ': 'n', 'ž': 'ʒ'}
NASAL = '~'   # 鼻母音の印 (phonemes の中で結合文字のチルダなどを置き換える)
TOKEN = re.compile('|'.join(sorted((re.escape(k) for k in list(VOWELS) + list(CONSONANTS)), key=len, reverse=True)))


def phonemes(roman):
    """転写 → 音素の列"""
    # 鼻音の記号 (結合文字のチルダ・ma͠i の二重のチルダ・チャンドラビンドゥ) を「~」にして母音の後ろへ
    text = unicodedata.normalize('NFD', roman.lower())
    text = re.sub('[̃̐͠]', NASAL, text).replace('ṁ', NASAL)
    text = unicodedata.normalize('NFC', text)
    text = re.sub('a' + NASAL + '([iu])', r'a\1' + NASAL, text)   # ma͠i の鼻音は二重母音の後ろ (メーン)
    out = []
    k = 0
    while k < len(text):
        if text[k] == NASAL:
            out.append('n')   # 鼻母音 (kahā̃ → カハーン)
            k += 1
            continue
        m = TOKEN.match(text, k)
        if not m:
            k += 1
            continue
        token = m.group(0)
        k = m.end()
        if token == 'v' and (k >= len(text) or text[k] not in 'aāiīuūeo'):
            out.append('v')   # 母音の前でない v は「ヴ」
            continue
        ph = VOWELS.get(token) or CONSONANTS.get(token)
        if token == 'ŕ':
            out += ['r', 'i']
        else:
            if ph == 'j' and out and out[-1] == 'n':
                out[-1] = 'ŋ'   # 子音の前の n は音節の終わり (dhanyavād → ダンヤワード。「ダニャ」でなく)
            out.append(ph)
    return out


def katakana(roman, long='phonemic', **options):
    """転写の語 → カタカナ"""
    return kana(phonemes(roman), long=long, **options)


def word_katakana(word, **options):
    """デーヴァナーガリーの語 → カタカナ"""
    from . import script
    return katakana(script.translit(word), **options)


def sentence(text, **options):
    return [word_katakana(w, **options) for w in text_words(text)]
