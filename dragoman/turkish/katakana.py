#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語の語をカタカナで書く: 綴りがほぼそのまま発音なので、綴り → 音素 → 共通の規則 (core/kana.py)
#
#   Ali → アリ、Ayşe → アイシェ、Çağlar → チャーラル、İstanbul → イスタンブル、Türkiye → テュルキイェ
#
#   - ı [ɯ] はウ段 (Kılıç → クルチ)、ö [ø] はエ段、ü [y] は「ユ」(子音の後ろは「テュ」「キュ」)
#   - ğ は母音の後ろで前の母音を長く (Çağlar → チャーラル、dağ → ダー)、母音の間では読まない (değil → デイル)
#   - c [dʒ] はジャ行、ç [tʃ] はチャ行、ş [ʃ] はシャ行、j [ʒ] はジャ行
#   - 同じ子音字2つは重子音 (l・r も「ッ」: Allah → アッラー。n・m は「ン」: Muhammed → ムハンメド)
#   - â・î・û は長母音 (Kâzım → キャーズム。k・g・l の後ろの â は拗音)
#
from dragoman.core.kana import kana, text_words

VOWELS = {'a': 'a', 'e': 'e', 'ı': 'ɯ', 'i': 'i', 'o': 'o', 'ö': 'ø', 'u': 'u', 'ü': 'y', 'â': 'aː', 'î': 'iː',
          'û': 'uː'}
CONSONANTS = {'b': 'b', 'c': 'dʒ', 'ç': 'tʃ', 'd': 'd', 'f': 'f', 'g': 'g', 'h': 'h', 'j': 'ʒ', 'k': 'k', 'l': 'l',
              'm': 'm', 'n': 'n', 'p': 'p', 'r': 'r', 's': 's', 'ş': 'ʃ', 't': 't', 'v': 'v', 'y': 'j', 'z': 'z',
              'x': 'ks', 'w': 'v', 'q': 'k'}


def lower(word):
    return word.replace('I', 'ı').replace('İ', 'i').lower()


def phonemes(word):
    word = lower(word)
    out = []
    for k, c in enumerate(word):
        nxt = word[k + 1] if k + 1 < len(word) else ''
        if c == 'ğ':
            if out and out[-1][:1] in 'aeɯioøuy' and nxt not in VOWELS and 'ː' not in out[-1]:
                out[-1] += 'ː'                # 母音の後ろの ğ は長音 (Çağlar → チャーラル)
            continue                          # 母音の間の ğ は読まない (değil → デイル)
        if c in VOWELS:
            if c == 'â' and out and out[-1] in ('k', 'g', 'l'):
                out.append('j')               # kâ・gâ・lâ は拗音 (Kâzım → キャーズム)
            out.append(VOWELS[c])
        elif c in CONSONANTS:
            ph = CONSONANTS[c]
            out += ['k', 's'] if ph == 'ks' else [ph]
    return out


def katakana(word, long='phonemic', **options):
    options.setdefault('liquid_sokuon', True)
    return kana(phonemes(word), long=long, **options)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列。アポストロフィの後ろの接尾辞も続けて: İstanbul'a → イスタンブラ)"""
    return [katakana(w.replace("'", '').replace('’', ''), **options) for w in text_words(text)]
