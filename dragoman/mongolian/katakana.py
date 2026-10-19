#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語 (キリル文字) の語をカタカナで書く: 綴り → 音素 → 共通の規則 (core/kana.py)
#
#   Бат → バト、Дорж → ドルジ、Улаанбаатар → ウラーンバータル、Дулмаа → ドゥルマー、Сүхбаатар → スフバータル
#
#   - 同じ母音字2つ・ий・ый は長母音「ー」(Улаанбаатар → ウラーンバータル、Батсүхийн → バトスヒーン)
#   - ө はオ段、ү はウ段 (Өлзий → オルズィー)
#   - ж [dʒ] はジャ行 (Дорж → ドルジ)、з [dz] はザ行、х [x] はハ行 (音節末は「フ」: Сүхбаатар → スフバータル)、в は「ヴ」
#   - я・ё・е・ю は語頭・母音の後ろでヤ行 (Ёндон → ヨンドン)、子音の後ろの я・ё・ю は拗音、е は「エ」
#   - 綴りの母音はそのまま書く (語中・語末の短い母音の弱まりは書かない: байна → バイナ)
#
from dragoman.core.kana import kana, text_words

VOWELS = {'а': 'a', 'э': 'e', 'и': 'i', 'о': 'o', 'у': 'u', 'ө': 'o', 'ү': 'u', 'ы': 'i'}
IOTATED = {'я': 'a', 'е': 'e', 'ё': 'o', 'ю': 'u'}
CONSONANTS = {'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ж': 'dʒ', 'з': 'dz', 'й': 'j', 'к': 'k', 'л': 'l', 'м': 'm',
              'н': 'n', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'tʃ', 'ш': 'ʃ',
              'щ': 'ʃ'}


def phonemes(word):
    word = word.lower()
    out = []
    k = 0
    while k < len(word):
        c = word[k]
        nxt = word[k + 1] if k + 1 < len(word) else ''
        prev = word[k - 1] if k else ''
        if c in IOTATED:
            after_consonant = prev in CONSONANTS and prev != 'й'
            if not (c == 'е' and after_consonant):
                out.append('j')
            long_ = nxt == c
            out.append(IOTATED[c] + ('ː' if long_ else ''))
            k += 2 if long_ else 1
            continue
        if c in VOWELS:
            long_ = nxt == c or c in 'иы' and nxt == 'й'
            out.append(VOWELS[c] + ('ː' if long_ else ''))
            k += 2 if long_ else 1
            continue
        if c in CONSONANTS:
            out.append(CONSONANTS[c])
        k += 1
    return out


def katakana(word, long='phonemic', **options):
    return kana(phonemes(word), long=long, **options)


def sentence(text, **options):
    """文のカタカナ読み (語ごとの列)"""
    return [katakana(w, **options) for w in text_words(text)]
