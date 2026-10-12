#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハングル: 字母への分解とローマ字 (改訂ローマ字表記の簡略版。音節末の子音の連音 (읽어 → ilgeo) と ㄹㄹ → ll だけ。
# 鼻音化などの音の変化は写さない)。辞書にある語は Wiktionary のローマ字を使う
#
#   romanize('학교') → 'hakgyo'    romanize('읽어요') → 'ilgeoyo'
#
import re
import unicodedata

INITIALS = ['g', 'kk', 'n', 'd', 'tt', 'r', 'm', 'b', 'pp', 's', 'ss', '', 'j', 'jj', 'ch', 'k', 't', 'p', 'h']
VOWELS = ['a', 'ae', 'ya', 'yae', 'eo', 'e', 'yeo', 'ye', 'o', 'wa', 'wae', 'oe', 'yo', 'u', 'wo', 'we', 'wi', 'yu',
          'eu', 'ui', 'i']
# 音節末の子音: (子音の前・語末の形, 母音の前に移る形 (残る部分, 移る部分))
FINALS = [('', ('', '')), ('k', ('', 'g')), ('k', ('', 'kk')), ('k', ('k', 's')), ('n', ('', 'n')), ('n', ('n', 'j')),
          ('n', ('', 'n')), ('t', ('', 'd')), ('l', ('', 'r')), ('k', ('l', 'g')), ('m', ('l', 'm')), ('l', ('l', 'b')),
          ('l', ('l', 's')), ('l', ('l', 't')), ('p', ('l', 'p')), ('l', ('', 'r')), ('m', ('', 'm')), ('p', ('', 'b')),
          ('p', ('p', 's')), ('t', ('', 's')), ('t', ('', 'ss')), ('ng', ('ng', '')), ('t', ('', 'j')), ('t', ('', 'ch')),
          ('k', ('', 'k')), ('t', ('', 't')), ('p', ('', 'p')), ('t', ('', ''))]
HANGUL = re.compile('[가-힣]')


def is_hangul(text):
    return bool(HANGUL.search(text))


def jamo(syllable):
    """音節 → (初声, 中声, 終声) の番号。ハングルの音節でなければ None"""
    code = ord(syllable) - 0xAC00
    if not 0 <= code < 11172:
        return None
    return code // 588, (code % 588) // 28, code % 28


def has_final(syllable):
    j = jamo(syllable)
    return bool(j and j[2])


def romanize(text):
    out = []
    chars = list(unicodedata.normalize('NFC', text))
    for k, c in enumerate(chars):
        j = jamo(c)
        if j is None:
            out.append(c)
            continue
        initial, vowel, final = j
        out.append(INITIALS[initial] if not (initial == 5 and out and out[-1].endswith('l')) else 'l')
        out.append(VOWELS[vowel])
        if not final:
            continue
        nxt = jamo(chars[k + 1]) if k + 1 < len(chars) else None
        before_consonant, (stay, move) = FINALS[final]
        if nxt is not None and nxt[0] == 11:   # 次が ㅇ で始まる: 連音 (읽어 → il-geo)
            out.append(stay + move)
        else:
            out.append(before_consonant)
    return ''.join(out)
