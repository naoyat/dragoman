#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古文のカタカナ読み: MeCab (中古和文 UniDic) の語ごとの読みから。kobun='modern' (既定。今の発音: 思ふ → オモウ、
# さぶらひ → サブライ、女御 → ニョーゴ) か kobun='historical' (歴史的仮名遣い: オモフ・サブラヒ・ニョウゴ)
#
#   UniDic の欄: 9 は発音形 (今の発音、長音は「ー」)、20 は仮名形 (歴史的仮名遣い)
#
from . import mecab

STYLES = ('modern', 'historical')


def tokens(text, kobun='modern', **options):
    """文 → [(表層形, 文の中の始め, 終わり, カナ)]。句読点はカナを空に"""
    if kobun not in STYLES:
        raise ValueError('--kana-kobun は %s のどれか' % '|'.join(STYLES))
    out, pos = [], 0
    for line in mecab._tagger().parse(text).splitlines():
        if line == 'EOS' or '\t' not in line:
            continue
        surface, feature = line.split('\t', 1)
        f = next(__import__('csv').reader([feature]))
        f += ['*'] * (24 - len(f))
        start = text.find(surface, pos)
        if start < 0:
            continue
        pos = start + len(surface)
        kana = f[9] if kobun == 'modern' else f[20]
        if f[0] == '補助記号' or kana in ('*', ''):
            kana = ''
        out.append((surface, start, pos, kana))
    return out


def sentence(text, **options):
    return [kana for _, _, _, kana in tokens(text, **options) if kana]
