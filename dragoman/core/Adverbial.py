#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 副詞節: 従属接続詞 (when・because・if …) で始まる節を、主節の述語の従属節に入れる
#
#   I saw her when she came.          {彼女が 来た}とき / 私が / 彼女を / 見た
#   Because it rained, we stayed home.  {雨が 降った}ので / 私たちが / 家に / とどまった
#
# 接続詞の語の項目の clause_suffix (とき・ので・なら …) で日本語のつなぎ方を決める (解析器が付ける)。clause_tense が
# あれば節の動詞の時制をそれにする (before「来る前に」は現在、after「来た後で」は過去)
#
from .LatinObject import LatinObject


class AdverbialClause(LatinObject):
    adverbial = False   # 主節の訳の頭に置く (Predicate.translate の従属節)

    def __init__(self, predicate, conjunction):
        self.predicate = predicate
        self.conjunction = conjunction
        self.surface = conjunction.surface + ' ' + predicate.surface
        self.surface_len = len(self.surface)

    def translate(self):
        item = self.conjunction.items[0]
        suffix = item.attrib('clause_suffix')
        verb = self.predicate.first_item
        tense = item.attrib('clause_tense')
        saved = verb.item.get('tense')
        if tense:
            verb.item['tense'] = tense
        try:
            inner, _ = self.predicate.translate()
        finally:
            if tense:
                verb.item['tense'] = saved
        inner = ' '.join(part for part in inner.split(' / ') if part.strip())
        if item.attrib('clause_negated'):   # unless「〜しないなら」
            pass
        return ('{' + inner + '}' + suffix, False)
