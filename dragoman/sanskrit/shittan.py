#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 日本の悉曇 (梵字) の伝統の読み: 種字・真言の読み方でカタカナに (--kana-reading=shittan)
#
#   hrīḥ → キリーク、trāḥ → タラーク、vaṃ → バン、hāṃ → カン、oṃ → オン、hūṃ → ウン、svāhā → ソワカ
#
# 規則 (音節ごと):
#   ka・ga・ca・ja・śa・ṣa の a は「キャ・ギャ・シャ・ジャ」(字母の読み)。ほかの母音はふつうの行 (ki → キ、ke → ケイ)
#   e・o は「エイ・オウ」。長母音の「ー」は1音節の語 (種字) だけ (hrīḥ → キリーク、pāragate → ハラギャテイ)。
#   ṃ の前では短く (hāṃ → カン)
#   ṃ (空点) は「ン」、ḥ (涅槃点) は「ク」
#   子音の連なりは、前の子音にも音節の母音を付ける (trā → タラー、hrī → キリー、sarva → サラバ)。
#   鼻音 + 子音は「ン」、同じ子音の重なりは「ッ」、kṣa は「キシャ」、jña は「ジャ」
#   有気音は無気音と同じ (kha → キャ、bha → バ)、v は b と同じ (vajra → バザラ)、h + u は「ウ」(hūṃ → ウン)
# 真言の読みは漢字音写を経た慣用で、規則に合わないものがある。よく出る語は表 (WORDS) で
#
from . import script

def _row(kana):
    """'キャキクケコ' のような行 → [a, i, u, e, o]"""
    out = []
    for ch in kana:
        if ch in 'ャュョ' and out:
            out[-1] += ch
        else:
            out.append(ch)
    return out


# 子音 (SLP1) → 行 (a i u e o の5つ)。有気音は無気音と同じ行
ROWS = {}
for _cs, _kana in (('kK', 'キャキクケコ'), ('gGN', 'ギャギグゲゴ'), ('cCSz', 'シャシシュセソ'), ('jJY', 'ジャジジュゼゾ'),
                   ('wWtT', 'タチツテト'), ('qQdD', 'ダジズデド'), ('Rn', 'ナニヌネノ'), ('pP', 'ハヒフヘホ'),
                   ('bBv', 'バビブベボ'), ('m', 'マミムメモ'), ('y', 'ヤイユエヨ'), ('rl', 'ラリルレロ'),
                   ('s', 'サシスセソ'), ('h', 'カキクケコ')):
    for _c in _cs:
        ROWS[_c] = _row(_kana)
ROWS['kz'] = ['キシャ', 'キシ', 'キシュ', 'キセ', 'キソ']   # kṣa
ROWS['jY'] = ROWS['j']                                      # jña → ジャ
VOWELS = {'a': (0, ''), 'A': (0, 'ー'), 'i': (1, ''), 'I': (1, 'ー'), 'u': (2, ''), 'U': (2, 'ー'),
          'e': (3, 'イ'), 'o': (4, 'ウ'), 'E': (0, 'イ'), 'O': (0, 'ウ'),
          'f': (1, 'リ'), 'F': (1, 'リー'), 'x': (1, 'リョ'), 'X': (1, 'リョー')}   # ṛ → キリ、ḷ → リョ
BARE = ['ア', 'イ', 'ウ', 'エ', 'オ']
NASALS = set('NYRnm')
CONSONANTS = set('kKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzsh')
# 有気音と無気音の組 (dd・ddh・tth …: 同じ子音の重なりとして「ッ」)
PLAIN = {'K': 'k', 'G': 'g', 'C': 'c', 'J': 'j', 'W': 'w', 'Q': 'q', 'T': 't', 'D': 'd', 'P': 'p', 'B': 'b'}

# 規則に合わない慣用の読み (SLP1 → カタカナ)
WORDS = {
    'oM': 'オン', 'AUM': 'オン', 'om': 'オン', 'hUM': 'ウン', 'svAhA': 'ソワカ', 'namaH': 'ノウマク', 'namo': 'ノウモ', 'vajra': 'バザラ',
    'padme': 'ハンドメイ', 'BrUM': 'ボロン', 'Paw': 'ハッタ', 'samanta': 'サマンダ', 'budDAnAm': 'ボダナン',
    'pArasaMgate': 'ハラソウギャテイ',
}

def _syllables(slp1):
    """SLP1 の語 → 音節 (子音の列, 母音, 末尾の ṃ・ḥ) の列。語末の子音は母音 '' の音節に"""
    out, cons, i = [], [], 0
    while i < len(slp1):
        c = slp1[i]
        if c in VOWELS:
            coda = ''
            if i + 1 < len(slp1) and slp1[i + 1] in 'MH~':
                coda = 'M' if slp1[i + 1] in 'M~' else 'H'
                i += 1
            out.append((cons, c, coda))
            cons = []
        elif c in CONSONANTS:
            cons.append(c)
        i += 1
    if cons:
        out.append((cons, '', ''))
    return out


def _onset(cons, vowel):
    """音節の頭の子音の連なりのうち最後の子音 (と kṣ・jñ) の鍵と、その前の子音の列"""
    if len(cons) >= 2 and ''.join(cons[-2:]) in ('kz', 'jY'):
        return ''.join(cons[-2:]), cons[:-2]
    return (cons[-1] if cons else ''), cons[:-1]


def _mora(key, vowel):
    """子音の鍵 + 母音 (SLP1) → カタカナ。ka の a は字母の読み (キャ)、ほかの母音はふつうの行"""
    index, tail = VOWELS[vowel]
    if not key:
        return BARE[index] + tail
    if key == 'h' and vowel in 'uU':   # hūṃ → ウン
        return 'ウ' + tail
    row = ROWS[key]
    kana = row[index]
    if index == 0 and vowel in 'EO' and key not in ('kz',):   # kai → カイ (キャイにしない)
        kana = {'キャ': 'カ', 'ギャ': 'ガ', 'シャ': 'サ', 'ジャ': 'ザ'}.get(kana, kana)
    return kana + tail


def _word(slp1):
    if slp1 in WORDS:
        return WORDS[slp1]
    out = []
    sylls = _syllables(slp1)
    for n, (cons, vowel, coda) in enumerate(sylls):
        if not vowel:   # 語末の子音 (phaṭ・vāk): ウ段 (t・ṭ は「ト」)
            for c in cons:
                out.append('ト' if c in 'tTwW' else ('ン' if c in NASALS else ROWS[c][2]))
            continue
        key, before = _onset(cons, vowel)
        short = {'A': 'a', 'I': 'i', 'U': 'u', 'F': 'i', 'X': 'i', 'f': 'i', 'x': 'i', 'e': 'e', 'o': 'o', 'E': 'a',
                 'O': 'a'}.get(vowel, vowel)
        for k, c in enumerate(before):   # 前の子音にも音節の母音 (短く、e・o の「イ・ウ」無しで)
            nxt = before[k + 1] if k + 1 < len(before) else key[:1]
            if c in NASALS:
                out.append('ン')
            elif PLAIN.get(nxt, nxt) == PLAIN.get(c, c):
                out.append('ッ')
            else:
                out.append(ROWS[c][VOWELS[short][0]])
        if coda == 'M':   # ṃ の前の長母音は短く (hāṃ → カン、oṃ → オン)
            vowel = {'A': 'a', 'I': 'i', 'U': 'u', 'e': 'e', 'o': 'o'}.get(vowel, vowel)
            kana = _mora(key, vowel)
            if vowel in 'eo':
                kana = kana[:-1]
            out.append(kana + 'ン')
        else:
            if len(sylls) > 1:   # 真言の語の長母音は書かない (種字の hrīḥ・trāḥ は「キリーク・タラーク」)
                vowel = {'A': 'a', 'I': 'i', 'U': 'u', 'F': 'f', 'X': 'x'}.get(vowel, vowel)
            out.append(_mora(key, vowel) + ('ク' if coda == 'H' else ''))
    return ''.join(out)


def reading(text):
    """語 (デーヴァナーガリー・IAST・悉曇文字) → 悉曇の読みのカタカナ (語の間は空白)"""
    return ' '.join(_word(script.to_slp1(w)) for w in text.split())

