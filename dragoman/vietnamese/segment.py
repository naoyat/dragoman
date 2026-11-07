#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語の文を語に切り分ける。ベトナム語は音節ごとに空白で書くので、何音節で1語か (sinh viên「学生」、
# Việt Nam) を決める:
#   - Stanza の切り分け (UD Vietnamese-VTB で学習したもの) を基本に、
#   - 辞書 (Wiktionary) に無い2音節以上の区切り (mô A) は使わず、辞書の見出しで分け直す (音節の数の少ない切り方)。
#     大文字で始まる音節の続き (人名・地名: Nguyễn Văn An) は辞書に無くても Stanza の区切りのまま
#
import re

from . import dictionary

SYLLABLE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*|\d+(?:[.,]\d+)*|[^\w\s]", re.UNICODE)
MAX_WORD = 6
STANZA_BONUS = 0.6   # Stanza の区切りと同じ語は少し安く (辞書の見出しが重なるときは Stanza の区切りを選ぶ)
HAND_BONUS = 0.5     # 訳語の表 (morphology.GLOSSES) の語は Stanza の区切りより先に (trường đại học「大学」)


def syllables(text):
    return SYLLABLE.findall(text)


def _is_word(syl):
    return bool(syl) and (syl[0].isalpha() or syl[0].isdigit())


def _stanza_spans(sylls):
    """Stanza の切り分け → 音節の区間 {(i, j)}。Stanza が無ければ空"""
    from . import morphology
    tokens = morphology.tokenize(sylls)
    if not tokens:
        return set()
    spans, i = set(), 0
    for token in tokens:
        n = len(syllables(token))
        if n and ' '.join(sylls[i:i + n]).lower() == ' '.join(syllables(token)).lower():
            spans.add((i, i + n))
            i += n
        else:
            return spans   # 区切りがずれたら残りは辞書だけで
    return spans


def _extra_keys():
    """訳語の表の2音節以上の語 (trường đại học「大学」) も見出しに"""
    from . import morphology
    return frozenset(k.lower() for k in morphology.GLOSSES if ' ' in k)


def segment(text):
    """文 → 語 (音節を空白でつないだもの) の列"""
    sylls = syllables(text)
    keys, longest = dictionary.keys()
    extra = _extra_keys()
    keys = keys | extra
    longest = min(longest, MAX_WORD)
    spans = _stanza_spans(sylls)
    n = len(sylls)
    best = [(0.0, 0)] + [(float('inf'), 0)] * n   # best[j] = (cost, 前の切れ目)
    for j in range(1, n + 1):
        for i in range(max(0, j - longest), j):
            piece = sylls[i:j]
            if not all(_is_word(s) for s in piece) and j - i > 1:
                continue
            joined = ' '.join(piece)
            stanza = (i, j) in spans
            names = all(s[:1].isupper() for s in piece) and (i > 0 or j - i > 1)
            if j - i > 1 and joined.lower() not in keys and not (stanza and names):
                continue
            cost = best[i][0] + 1 - (STANZA_BONUS if stanza else HAND_BONUS if joined.lower() in extra else 0)
            if cost < best[j][0]:
                best[j] = (cost, i)
    out, j = [], n
    while j > 0:
        i = best[j][1]
        out.insert(0, ' '.join(sylls[i:j]))
        j = i
    return out
