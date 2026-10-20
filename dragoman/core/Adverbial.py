#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 副詞節: 従属接続詞 (when・because・if …) で始まる節を、主節の述語の従属節に入れる
#
#   I saw her when she came.          {彼女が 来た}とき / 私が / 彼女を / 見た
#   Because it rained, we stayed home.  {雨が 降った}ので / 私たちが / 家に / とどまった
#
# 接続詞の語の項目の clause_suffix (とき・ので・なら …) で日本語のつなぎ方を決める (解析器が付ける)。clause_tense が
# あれば節の動詞の時制をそれにする (before「来る前に」は現在、after「来た後で」は過去)、clause_negate なら節を否定に
# (sans que「〜しないまま」)
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
        saved = dict(verb.item)
        if tense:
            verb.item['tense'] = tense
        if item.attrib('clause_negate') and not self.predicate._negative():
            verb.item['negative'] = True   # sans que「〜しないまま」(否定の無い節を否定に。ne の付いた節はそのまま)
        try:
            inner, _ = self.predicate.translate()
        finally:
            verb.item.clear()
            verb.item.update(saved)
        inner = ' '.join(part for part in inner.split(' / ') if part.strip())
        return ('{' + inner + '}' + suffix, False)


def mark_subordinators(words, table):
    """解析器の語の列の従属接続詞 (項目の base が table にあるもの) に、副詞節のつなぎ方の印を付ける。
    table は 接続詞 → (節の後ろに付ける形, 節の動詞の時制 / None)"""
    for word in words:
        items = getattr(word, 'items', None)
        if not items or items[0].pos != 'conj':
            continue
        base = (items[0].attrib('base') or word.surface).lower()
        if base in table:
            suffix, tense = table[base][:2]
            items[0].item['clause_suffix'] = suffix
            items[0].item['clause_tense'] = tense
            items[0].item['clause_negate'] = len(table[base]) > 2 and table[base][2]
