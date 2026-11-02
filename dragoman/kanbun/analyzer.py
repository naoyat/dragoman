#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文の解析: UD-Kanbun の係り受け (parse.py) → 書き下し (kundoku.py) → 現代語訳 (modern.py)
#
import re
from dataclasses import dataclass, field

from . import kundoku, modern, parse, readings

SENTENCE_END = re.compile('(?<=[。！？!?])')


@dataclass
class KanbunAnalysis:
    text: str
    phrases: list = field(default_factory=list)     # 句ごとの [parse.Token]
    elems: list = field(default_factory=list)       # 句ごとの書き下しの要素 (kundoku.Elem)
    kaeriten: str = ''
    kakikudashi: str = ''
    modern: str = ''

    @property
    def tokens(self):
        return [t for phrase in self.phrases for t in phrase]

    @property
    def reading(self):
        """音読に渡す書き下し文 (新字体)"""
        return readings.shinjitai(self.kakikudashi)

    @property
    def yomi(self):
        """書き下し文の読み (ひらがな。ruby.py。JMdict の読みの表が無ければ '')"""
        from . import ruby
        return ruby.yomi(self) if ruby.available() else ''

    def reading_of(self, token):
        """語の書き下しでの形 (送り仮名・助詞を付けたもの。置き字は '')"""
        for elems in self.elems:
            shown = kundoku._rendered(elems)
            places = [n for n, e in enumerate(shown) if e.token is token and e.kind != 'punct']
            if places:
                out = ''
                for k, n in enumerate(places):   # 続いている要素はつなげ、離れた読み (再読文字) は … で
                    out += ('' if k == 0 or n == places[k - 1] + 1 else '…') + shown[n].out
                return out
        return ''


def sentences(text):
    for line in text.splitlines():
        for s in SENTENCE_END.split(line.strip()):
            if s.strip():
                yield s.strip()


def analyze_sentence(text):
    phrases = parse.phrases(text)
    elems = kundoku.read(phrases)
    kakikudashi = ''.join(''.join(e.out for e in kundoku._rendered(x)) for x in elems)
    translation = ''.join(modern.translate(x) for x in elems)
    return KanbunAnalysis(text, phrases, elems, parse.kaeriten(text), kakikudashi, translation)


def analyze_text(text):
    for s in sentences(text):
        yield analyze_sentence(s)
