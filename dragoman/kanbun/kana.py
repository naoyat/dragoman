#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 歴史的仮名遣い → 現代仮名遣い (読みの突き合わせ用。字の読みの歴史的仮名遣いの表 tools/build_ja_historical.py と ruby.py)
#
#   modern('しやう', on=True) → 'しょう'   modern('ゑん') → 'えん'   modern('をしふ') → 'おしう'   modern('けふ', on=True) → 'きょう'
#
# 語の頭でないハ行はワ行に (かへり → かえり)。字音 (on=True) は拗音を小書きに (しや → しゃ) し、長音を現代の綴りに
# (かう → こう、せう → しょう、きう → きゅう、かふ → こう)
#
A_TO_O = dict(zip('かがさざただなはばぱまやらわあ', 'こごそぞとどのほぼぽもよろおお'))
E_TO_I = dict(zip('けげせぜてでねへべぺめれえ', 'きぎしじちぢにひびぴみりい'))
I_ROW = set('きぎしじちぢにひびぴみり')
SMALL = {'や': 'ゃ', 'ゆ': 'ゅ', 'よ': 'ょ'}
HA_ROW = dict(zip('はひふへほ', 'わいうえお'))


def modern(hist, on=False):
    s = hist.replace('ゐ', 'い').replace('ゑ', 'え').replace('を', 'お').replace('くわ', 'か').replace('ぐわ', 'が')
    s = s.replace('ぢ', 'じ').replace('づ', 'ず')
    s = s[:1] + ''.join(HA_ROW.get(c, c) for c in s[1:])
    if not on:
        return s
    out = []
    k = 0
    while k < len(s):
        c = s[k]
        nxt = s[k + 1] if k + 1 < len(s) else ''
        after = s[k + 2] if k + 2 < len(s) else ''
        if c in I_ROW and nxt in SMALL:          # しや → しゃ、しやう → しょう
            vowel = SMALL[nxt]
            if nxt == 'や' and after == 'う':
                out.append(c + 'ょう')
                k += 3
                continue
            out.append(c + vowel)
            k += 2
            continue
        if nxt == 'う' and c in A_TO_O:          # かう → こう
            out.append(A_TO_O[c] + 'う')
            k += 2
            continue
        if nxt == 'う' and c in E_TO_I:          # せう → しょう、えう → よう
            out.append('よう' if c == 'え' else E_TO_I[c] + 'ょう')
            k += 2
            continue
        if nxt == 'う' and c in I_ROW:           # きう → きゅう
            out.append(c + 'ゅう')
            k += 2
            continue
        if nxt == 'う' and c == 'い' and k == 0:  # いう → ゆう
            out.append('ゆう')
            k += 2
            continue
        out.append(c)
        k += 1
    return ''.join(out)


def same(hist, mod, on=True):
    """歴史的仮名遣いの読みが現代仮名遣いの読みに当たるか (促音の つ・っ は同じに)"""
    m = mod.replace('っ', 'つ')
    return modern(hist, on).replace('っ', 'つ') == m or modern(hist, False).replace('っ', 'つ') == m
