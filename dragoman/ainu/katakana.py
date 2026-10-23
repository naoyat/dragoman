#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# アイヌ語の語をカタカナで書く: ラテン文字の綴りから、現代のアイヌ語のカタカナ表記 (ainu-utils。音節末の子音は小書き:
# kamuy → カムイ、cep → チェㇷ゚、aynu → アイヌ、pirka → ピㇼカ)。small='off' (--kana-small=off) で小書きを普通のカナに
# (チェプ・ピリカ)。カタカナで書いた語はそのまま (small='off' なら小書きだけ直す)
#
from . import phonology, script


def katakana(word, small='on', **options):
    kana = word if script.has_kana(word) else script.kana(word)
    if small == 'off':
        kana = kana.replace('ㇷ\u309a', 'プ').replace('ㇷ゚', 'プ')   # ㇷ゚ (p) を ㇷ (h) より先に
        for small_kana, full in phonology.SMALL_KANA.items():
            kana = kana.replace(small_kana, full)
    return kana


def sentence(text, **options):
    from dragoman.core.kana import text_words
    return [katakana(w, **options) for w in text_words(text)]
