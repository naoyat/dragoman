#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語の文の解析: 語に切り分け (cantonese/segment.py)、普通話の語に置き換えて並べ替え (cantonese/morphology.py の rewrite:
# 佢 → 他、我高過佢 → 我比他高 …)、普通話の解析器 (chinese/analyzer.py。spaCy の依存関係・量詞・的・アスペクト・把・被 …) で
# 訳す。表示の語は広東語のまま。CC-CEDICT に無い語の訳語は CC-Canto の英語の語義から
#
import dataclasses

from dragoman.chinese import analyzer as zh
from dragoman.chinese import dictionary as cedict
from . import dictionary, morphology, segment

PUNCTUATION = zh.PUNCTUATION
# 共通の解析器は表示の語 (広東語の字) で並列・否定・繋辞を見分けるので、広東語の語も足す
CANTONESE = dataclasses.replace(
    zh.CHINESE, name='yue',
    and_words=zh.CHINESE.and_words + ('同', '同埋'),
    or_words=zh.CHINESE.or_words + ('定', '定係'),
    copulas=zh.CHINESE.copulas | {'係'},
    negations=zh.CHINESE.negations | {'唔', '冇', '未', '唔好', '咪', '唔使', '唔係'},
)


def sentences(text):
    current = []
    for token in segment.segment(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _pairs(surfaces):
    pairs = morphology.rewrite(list(surfaces))
    return [p[0] for p in pairs], [p[1] for p in pairs]


def lookup_all(surfaces):
    shown, simple = _pairs(surfaces)
    with cedict.extra(dictionary.lookup):
        return zh.lookup_all(shown, simple)


def analyze_sentence(surfaces):
    surfaces = list(surfaces)
    shown, simple = _pairs(surfaces)
    with cedict.extra(dictionary.lookup):
        return zh.analyze_sentence(shown, simple, original=surfaces, lang=CANTONESE)


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
