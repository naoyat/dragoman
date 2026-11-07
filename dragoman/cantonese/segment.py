#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語の文を語に切り分ける: PyCantonese の切り分け (HKCanCor などで学習したもの) を基本に、
#   - 辞書 (広東語の表・CC-Canto・CC-CEDICT) に無い2字以上の語 (畀本書・高過) は、見出しの最長一致 (前から・後ろから。
#     語の数・1字の語の少ないほう) で分け直す
#   - 指示詞・数詞の後ろの「量詞 + 名詞」(呢本書 → 呢 / 本 / 書) は量詞の前で切る
#   - 否定・存在の語 + 語 (冇錢・唔去) は見出しに無ければ分ける
#
import re

from dragoman.chinese import segment as zh_segment
from . import morphology

HAN = zh_segment.HAN
DEMONSTRATIVES = set('呢嗰邊每第') | set('一二三四五六七八九十百千萬万两兩幾几')
CLASSIFIERS = zh_segment.CLASSIFIERS | set('隻個條張間架部對粒啲樽碗杯份封首套件位')


# PyCantonese が1語にする 動詞 + 目的語 (睇戲「映画を見る」)、反復疑問 (係咪) は分ける
SPLIT = {'睇戲': ['睇', '戲'], '係咪': ['係', '咪'], '有冇': ['有', '冇'], '食飯': ['食', '飯'], '飲茶': ['飲', '茶'],
         '睇書': ['睇', '書'], '冇錢': ['冇', '錢']}


class _Keys:
    """見出しの集まり (in で引く): 広東語の表・CC-Canto・CC-CEDICT"""
    def __contains__(self, word):
        return morphology.known(word)


def _pycantonese(text):
    try:
        import pycantonese
        return pycantonese.segment(text)
    except ImportError:
        return None


def _rechunk(piece):
    keys = _Keys()
    fw, bw = zh_segment._forward(piece, keys, 6), zh_segment._backward(piece, keys, 6)
    score = lambda seg: (len(seg), sum(1 for w in seg if len(w) == 1))
    return fw if score(fw) <= score(bw) else bw


def _split_classifiers(words):
    out = []
    for w in words:
        prev = out[-1] if out else ''
        if prev and (prev in DEMONSTRATIVES or prev.isdigit()) and len(w) >= 2 and w[0] in CLASSIFIERS and \
                morphology.known(w[1:]):
            out += [w[0], w[1:]]
        elif len(w) >= 2 and w[0] in '呢嗰邊' and w[1] in CLASSIFIERS and w not in morphology.MANDARIN:
            out += [w[0], w[1]] + ([w[2:]] if w[2:] else [])   # 呢本書 → 呢 / 本 / 書 (呢個 は表の語のまま)
        else:
            out.append(w)
    return out


def segment(text):
    """文 → 語の列"""
    words = []
    for piece in _pycantonese(text) or zh_segment.PIECES.findall(text):
        if piece.isspace():
            continue
        if len(piece) > 1 and re.fullmatch('[%s]+' % HAN, piece) and \
                (not morphology.known(piece) or piece[0] in '冇唔畀俾' and piece not in morphology.MANDARIN and
                 morphology.known(piece[1:]) and piece[1:] not in ('該', '緊要', '住', '使', '好')):
            words += [piece[0]] + _rechunk(piece[1:]) if morphology.known(piece) else _rechunk(piece)
        else:
            words.append(piece)
    words = _split_classifiers(words)
    out = []
    for k, w in enumerate(words):   # 有啲 + 名詞「いくらかの〜がある」は 有 / 啲
        if w == '有啲' and k + 1 < len(words) and re.match('[%s]' % HAN, words[k + 1]):
            out += ['有', '啲']
        elif w in SPLIT:
            out += SPLIT[w]
        else:
            out.append(w)
    return out
