#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ラテン文字の転写から元の文字の綴りを推す時の共通の部品: 転写が一意に戻らない所 (ロシア語 e → е / э、
# ts → ц / тс、ヒンディー語の子音の連続 → 結合文字 / 内在の a の脱落) を候補の列にし、辞書にある綴りを選ぶ
#
#   pick([['ц', 'тс'], ['е', 'э']] ...) のように、位置ごとの候補 (先頭が既定) の列から綴りを組み立てる
#
import itertools
import re


def pick(options, known, limit=64):
    """options: 位置ごとの候補のリスト (先頭が既定)。既定から外す所の少ない順に組み立て、known(綴り) が真の最初の
    綴りを返す。どれも辞書に無ければ既定の綴り。組み合わせが limit を超えれば、後ろの曖昧な所は既定に固定する"""
    choices = [list(o) for o in options]
    total = 1
    for o in choices:
        if total * len(o) > limit:
            o[1:] = []
        total *= len(o)
    default = ''.join(o[0] for o in choices)
    if total == 1:
        return default
    combos = sorted(itertools.product(*[range(len(o)) for o in choices]), key=lambda c: sum(1 for i in c if i))
    for combo in combos:
        word = ''.join(o[i] for o, i in zip(choices, combo))
        if known(word):
            return word
    return default


def words(text, pattern, convert):
    """text の中の pattern に合う部分 (語) を convert で置き換える (句読点・空白はそのまま)"""
    return re.sub(pattern, lambda m: convert(m.group(0)), text)
