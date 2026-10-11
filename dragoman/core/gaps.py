#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 解析の穴の一覧 (--gaps): 辞書に無い語・推測した語形・構造に入らなかった語・述語の見つからない文の数
#
#   本文は出さない。語は理由ごとに重複を除いて並べ替え (文中の順・位置・前後の語は出さない) るので、一覧から
#   元のテキストは組み立て直せない。歌詞など手元だけで読むテキストの穴を、本文を渡さずに伝えるため
#
from collections import Counter

from dragoman.core.Word import Word

REASONS = (('unknown', '辞書に無い'), ('guess', '推測した語形'), ('isolated', '構造の外'))


class Gaps:
    def __init__(self, lang):
        self.lang = lang
        self.found = {key: Counter() for key, _ in REASONS}
        self.details = {}   # (理由, 語) → 補足 (推測した見出し語と文法、構造の外の語の品詞)
        self.sentences = 0
        self.words = 0
        self.no_predicate = 0

    def add(self, analysis):
        from dragoman.core.notebook import marks_context, lemma_of, grammar_of, GUESS_SOURCES, POS_NAMES
        self.sentences += 1
        if not analysis.clauses:
            self.no_predicate += 1
        context = marks_context(analysis)
        for word in analysis.words:
            if word.items is None:   # 句読点
                continue
            self.words += 1
            surface = word.surface
            if not word.items:
                self.found['unknown'][surface] += 1
                continue
            item = word.items[0]
            if item.attrib('source') in GUESS_SOURCES:
                self.found['guess'][surface] += 1
                self.details[('guess', surface)] = '%s %s' % (lemma_of(item), grammar_of(item))
            if word.index in context['isolated']:
                self.found['isolated'][surface] += 1
                self.details[('isolated', surface)] = POS_NAMES.get(item.pos, item.pos)

    def report(self):
        lines = ['# dragoman --gaps (%s): %d 文・%d 語。本文は含まない (語は理由ごとに重複を除き五十音・アルファベット順)'
                 % (self.lang, self.sentences, self.words)]
        if self.no_predicate:
            lines.append('述語が見つからない文: %d' % self.no_predicate)
        for key, name in REASONS:
            counter = self.found[key]
            if not counter:
                continue
            lines.append('%s (%d 語):' % (name, len(counter)))
            for surface in sorted(counter, key=lambda s: s.lower()):
                detail = self.details.get((key, surface))
                lines.append('  %s%s%s' % (surface, '  ×%d' % counter[surface] if counter[surface] > 1 else '',
                                           '  (%s)' % detail if detail else ''))
        if len(lines) == 1:
            lines.append('穴は見つからなかった')
        return '\n'.join(lines)
