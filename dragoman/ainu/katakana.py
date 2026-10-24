#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# アイヌ語の語をカタカナで書く: ラテン文字の綴りから、現代のアイヌ語のカタカナ表記 (ainu-utils。音節末の子音は小書き:
# kamuy → カムイ、cep → チェㇷ゚、aynu → アイヌ、pirka → ピㇼカ)。small='off' (--kana-small=off) で小書きを普通のカナに。
# カタカナで書いた語はそのまま (small='off' なら小書きだけ直す)
#
#   small='off' の音節末の子音:
#   - 閉鎖音 k・p・t (ㇰ・ㇷ゚・ㇳ) は破裂させずに止めるので「ッ」(cep → チェッ、pet → ペッ、ahup → アフッ)。母音を書かない
#   - r・h (ㇻ〜ㇿ・ㇵ〜ㇹ) は前の母音を軽く伴うので、その段の普通のカナ (pirka → ピリカ、kor → コロ、ah → アハ)
#   - s・n・m は普通のカナ (ㇱ → シ、ㇴ → ン、ㇺ → ム)
#
from . import phonology, script

STOPS = {'ㇷ\u309a': 'ッ', 'ㇷ゚': 'ッ', 'ㇰ': 'ッ', 'ㇳ': 'ッ'}   # ㇷ゚ (p) を ㇷ (h) より先に


def katakana(word, small='on', **options):
    kana = word if script.has_kana(word) else script.kana(word)
    if small == 'off':
        for small_kana, full in list(STOPS.items()) + list(phonology.SMALL_KANA.items()):
            kana = kana.replace(small_kana, full)
    return kana


def sentence(text, **options):
    from dragoman.core.kana import text_words
    return [katakana(w, **options) for w in text_words(text)]
