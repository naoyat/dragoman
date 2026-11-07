# -*- coding: utf-8 -*-
#
# パーリ語のカタカナ読み: 発音から、どの言語にも共通の規則 (core/kana.py) で
#
#   namo tassa bhagavato → ナモー タッサ バガヴァトー、buddhaṃ saraṇaṃ gacchāmi → ブッダン サラナン ガッチャーミ、
#   metta → メッタ、veḷuvana → ヴェールヴァナ、paññā → パンニャー
#
# - 長母音 ā ī ū は「ー」。e・o は長いが、重子音・子音の連なりの前では短い (metta・sotthi・okkamati)
# - ṃ (niggahīta) は「ン」、鼻音 + 子音も「ン」(pañca → パンチャ、saṅgha → サンガ)
# - 有気音 (kh・gh・ch・th・dh・ph・bh) の h は書かない、そり舌音 (ṭ ḍ ṇ ḷ) は t・d・n・l、v は「ヴ」
#
from dragoman.core.kana import kana
from . import script

VOWELS = {'a': 'a', 'ā': 'ɑː', 'i': 'i', 'ī': 'iː', 'u': 'u', 'ū': 'uː', 'e': 'eː', 'o': 'oː'}
CONSONANTS = {'k': 'k', 'g': 'g', 'ṅ': 'ŋ', 'c': 'tʃ', 'j': 'dʒ', 'ñ': 'ɲ', 'ṭ': 't', 'ḍ': 'd', 'ṇ': 'n',
              't': 't', 'd': 'd', 'n': 'n', 'p': 'p', 'b': 'b', 'm': 'm', 'y': 'j', 'r': 'r', 'l': 'l', 'ḷ': 'l',
              'v': 'ʋ', 's': 's', 'h': 'h', 'ṃ': 'ŋ'}
ASPIRATED = set('kgcjṭḍtdpbḷ')
NASALS = set('ṅñṇnm')


def _segments(word):
    """語 → [(音, 母音か)]。有気音は1つの子音に"""
    out = []
    i = 0
    while i < len(word):
        c = word[i]
        if c in VOWELS:
            out.append((c, True))
        elif c in CONSONANTS:
            out.append((c, False))
            if c in ASPIRATED and word[i + 1:i + 2] == 'h':
                i += 1
        i += 1
    return out


def ipa(word):
    segs = _segments(script.normalize(word.lower()))
    phonemes = []
    for k, (c, vowel) in enumerate(segs):
        nxt = segs[k + 1:k + 3]
        if vowel:
            p = VOWELS[c]
            if c in 'eo' and len(nxt) == 2 and not nxt[0][1] and not nxt[1][1]:
                p = c   # 子音の連なりの前の e・o は短い (metta → メッタ)
            phonemes.append(p)
        elif c in NASALS and nxt and not nxt[0][1] and nxt[0][0] != c and c not in 'nm':
            phonemes.append('n')   # ñc・ṅg・ṇḍ … は「ン」(pañca → パンチャ。ññ は ンニャ)
        elif c == 'ñ' and nxt and nxt[0][0] == 'ñ':
            phonemes.append('n')
        else:
            phonemes.append(CONSONANTS[c])
    return phonemes


def katakana(word, **options):
    phonemes = []
    for w in script.to_roman(word).split():
        if phonemes:
            phonemes.append(' ')
        phonemes += ipa(w)
    return kana(phonemes, **options)
