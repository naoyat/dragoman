#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# インドネシア語・マレー語の語をカタカナで書く: 綴りがほぼそのまま発音なので、綴り → 音素 → 共通の規則 (core/kana.py)
#
#   saya → サヤ、bapak → バパッ、rumah → ルマ、nyanyi → ニャニ、bunga → ブンガ、syukur → シュクル、Indonesia → インドネスィア
#
#   - e は [ə] も [e] もエ段 (綴りでは分けない: besar → ベサル、enak → エナッ)
#   - ng [ŋ] は母音の前で「ンガ」(bunga [buŋa] → ブンガ。日本語の鼻濁音のガに近い)、ny [ɲ] はニャ行、
#     sy [ʃ] はシャ行、kh [x] はハ行、c [tʃ] はチャ行、j [dʒ] はジャ行
#   - 語末の k は声門閉鎖音 [ʔ] で「ッ」(bapak → バパッ。kh・ng・nk は除く)、語末の h は弱いので書かない (rumah → ルマ)
#   - ai・au・oi は2つの母音 (pantai → パンタイ、pulau → プラウ)
#
from dragoman.core.kana import kana, text_words

VOWELS = {'a': 'a', 'e': 'e', 'é': 'e', 'i': 'i', 'o': 'o', 'u': 'u'}
DIGRAPHS = {'ng': 'ŋ', 'ny': 'ɲ', 'sy': 'ʃ', 'kh': 'x'}
CONSONANTS = {'b': 'b', 'c': 'tʃ', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'dʒ', 'k': 'k', 'l': 'l', 'm': 'm',
              'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's', 't': 't', 'v': 'f', 'w': 'w', 'x': 'ks', 'y': 'j',
              'z': 'z'}
GLOTTAL = 't̚'   # 語末の k の声門閉鎖音を「ッ」で (core/kana.py の内破音の印を借りる)


def phonemes(word):
    word = word.lower()
    if '-' in word:   # 重ねた語 (anak-anak) は部分ごとに (語末の k の「ッ」も部分ごとに)
        return [ph for k, part in enumerate(word.split('-')) for ph in ([' '] if k else []) + phonemes(part)]
    out = []
    k = 0
    while k < len(word):
        two = word[k:k + 2]
        if two in DIGRAPHS:
            out.append(DIGRAPHS[two])
            k += 2
            continue
        c = word[k]
        if c in VOWELS:
            out.append(VOWELS[c])
        elif c in CONSONANTS:
            ph = CONSONANTS[c]
            if c == 'k' and k == len(word) - 1 and out and out[-1] in VOWELS.values():
                ph = GLOTTAL           # 語末の k は [ʔ] (bapak → バパッ)
            elif c == 'h' and k == len(word) - 1 and out and out[-1] in VOWELS.values():
                ph = None              # 語末の h は書かない (rumah → ルマ)
            if ph:
                out += ['k', 's'] if ph == 'ks' else [ph]
        k += 1
    return out


def katakana(word, long='phonemic', **options):
    return kana(phonemes(word), long=long, **options)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列。重ねた語の - は続けて: anak-anak → アナッアナッ)"""
    return [katakana(w, **options) for w in text_words(text)]
