#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dragoman.core.LatinObject import LatinObject

# 前置詞支配された名詞節
class PrepClause (LatinObject):
    def __init__(self, prep_word, dominated_case, words):
        # self.prep_surface = prep_word.surface
        self.prep = prep_word.surface
        self.dominated_case = dominated_case
        self.words = words

        for item in prep_word.items:
            if item.dominates == dominated_case:
                self.item = item
                break

        self.surface = self.item.surface + ' ' + ' '.join([word.surface for word in words])
        self.surface_len = len(self.surface)

    def translate(self, existential=False):
        """名詞句の訳 + 前置詞の訳 (学校に。訳が複数なら 学校[に,で]。名詞句が複数の語なら {…} で括る)。
        existential なら存在の文の場所: 最初の訳だけを「に」に (庭[で,の中で] → 庭に)"""
        s = ' '.join(t for t in (word.translate()[0] for word in self.words) if t)  # 句読点は訳が空
        glosses = [g.strip() for g in (self.item.ja or '').split(',') if g.strip()]
        if existential and glosses:
            glosses = [existential_gloss(glosses[0])]
        return (prep_text(s, glosses), False)


def existential_gloss(gloss):
    """存在の文の場所の前置詞の訳: 「〜に」に (〜で → 〜に、〜の中で → 〜の中に)。所有の「〜には」はそのまま"""
    if gloss.endswith('には') or gloss[-1:].isascii():
        return gloss   # ロシア語の у + 生格「〜には」、英語の訳語 (πρός「towards」) には助詞を付けない
    if gloss.endswith(('で', 'に')):
        return gloss[:-1] + 'に'
    return gloss + 'に'


def prep_text(noun, glosses):
    """名詞句の訳と前置詞の訳を並べる: 学校 + [〜に] → 学校に、学校 + [〜に, 〜で] → 学校[に,で]"""
    noun = noun.strip()
    if (' ' in noun or ',' in noun) and not (noun.startswith('{') and noun.endswith('}') and _balanced(noun[1:-1])):
        noun = '{' + noun + '}'   # 複数の語の名詞句・訳語の候補 (邸宅,別荘) はまとめる (助詞が最後の語だけに掛からないように)
    parts = [g[1:] if g.startswith(('〜', '～')) else g for g in glosses]
    if not parts:
        return noun
    if len(parts) == 1:
        return noun + parts[0]
    return noun + '[' + ','.join(parts) + ']'


def _balanced(text):
    """中括弧の対応が取れているか ({a} {b} の外側を1組の括弧と取り違えない)"""
    depth = 0
    for c in text:
        depth += (c == '{') - (c == '}')
        if depth < 0:
            return False
    return depth == 0
