#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語の文を語に切り分ける: spaCy の中国語モデル (zh_core_web_sm) の切り分け (pkuseg) を基本に、
#   - 辞書 (CC-CEDICT) に無い2字以上の語 (书放) は、辞書の見出しの最長一致 (前から・後ろから。語の数・1字の語の少ないほう) で
#     分け直す。pkuseg が無ければ文全体を最長一致で
#   - 数詞・指示詞の後ろの「量詞 + 名詞」(一本书 → 一 / 本 / 书) は量詞の前で切る
#   - 繁体字は簡体字に直して切り分け (OpenCC。字の数は変わらない)、元の字に戻す
#
import re

from . import dictionary

PUNCTUATION = set('。，、；：？！…—（）《》「」『』“”‘’·.,;:?!()"\'')
NUMERALS = set('一二三四五六七八九十百千万亿两零〇几')
DEMONSTRATIVES = ('这', '那', '哪', '每', '某', '各', '上', '下', '第')
# よく使う量詞 (数詞・指示詞の後ろで、後ろの名詞と分ける)
CLASSIFIERS = set('个只条张件位口头匹辆台架座栋间家所把支枝根片块杯瓶碗盘双对套份封篇首部场次回遍趟顿种样些点岁年天月分秒层群批本')
HAN = '㐀-鿿豈-﫿'
PIECES = re.compile(r'\s+|[A-Za-z0-9０-９Ａ-Ｚａ-ｚ.%%]+|[%s]+|.' % HAN)


def _forward(text, keys, longest):
    out, i = [], 0
    while i < len(text):
        for n in range(min(longest, len(text) - i), 0, -1):
            if n == 1 or text[i:i + n] in keys:
                out.append(text[i:i + n])
                i += n
                break
    return out


def _backward(text, keys, longest):
    out, j = [], len(text)
    while j > 0:
        for n in range(min(longest, j), 0, -1):
            if n == 1 or text[j - n:j] in keys:
                out.insert(0, text[j - n:j])
                j -= n
                break
    return out


def _chunk(text):
    """漢字の連なりを辞書の見出しで最長一致 (前から・後ろから。語の数・1字の語の少ないほう)"""
    keys, longest = dictionary.keys()
    longest = min(longest, 8)
    fw, bw = _forward(text, keys, longest), _backward(text, keys, longest)
    score = lambda seg: (len(seg), sum(1 for w in seg if len(w) == 1))
    return fw if score(fw) <= score(bw) else bw


def _split_classifiers(words):
    """数詞・指示詞の後ろの量詞 + 名詞の語 (本书「この本」・个人) を量詞と名詞に。数詞 + 量詞の語 (一本・两个) も分ける"""
    keys, _ = dictionary.keys()
    out = []
    for w in words:
        prev = out[-1] if out else ''
        after_number = prev and (all(c in NUMERALS for c in prev) or prev in DEMONSTRATIVES or prev.isdigit())
        if after_number and len(w) >= 2 and w[0] in CLASSIFIERS and w[1:] in keys:
            out += [w[0], w[1:]]
            continue
        if len(w) >= 2 and all(c in NUMERALS for c in w[:-1]) and w[-1] in CLASSIFIERS:
            out += [w[:-1], w[-1]]
            continue
        out.append(w)
    return out


def _split_you(words):
    """節の終わりの有人 (这里有人吗「ここに 人が いるか」) は 有 / 人 に。有人说「ある人が言う」の有人はそのまま"""
    out = []
    for k, w in enumerate(words):
        nxt = words[k + 1] if k + 1 < len(words) else ''
        if w in ('有人', '没有人') and (not nxt or nxt in PUNCTUATION or nxt in ('吗', '嗎', '吧', '呢', '啊')):
            out += [w[:-1], '人']
            continue
        out.append(w)
    return out


_t2s = None


def simplified(text):
    """繁体字 → 簡体字 (OpenCC。字の数が変われば元のまま)"""
    global _t2s
    try:
        if _t2s is None:
            import opencc
            _t2s = opencc.OpenCC('t2s')
    except ImportError:
        return text
    out = _t2s.convert(text)
    return out if len(out) == len(text) else text


def _pkuseg(text):
    from . import morphology
    try:
        return [t.text for t in morphology.nlp().tokenizer(text)]
    except (ImportError, OSError):
        return None


def segment(text):
    """文 → 語の列 (元の字のまま)"""
    simple = simplified(text)
    keys, _ = dictionary.keys()
    words = []
    for piece in _pkuseg(simple) or PIECES.findall(simple):
        if piece.isspace():
            continue
        if len(piece) > 1 and piece not in keys and re.fullmatch('[%s]+' % HAN, piece):
            words += _chunk(piece)   # 辞書に無い語 (书放) は分け直す
        else:
            words.append(piece)
    words = _split_classifiers(words)
    words = _split_you(words)
    out, i = [], 0   # 元の字に戻す
    for w in words:
        k = simple.find(w, i)
        if k < 0:
            out.append(w)
            continue
        out.append(text[k:k + len(w)])
        i = k + len(w)
    return out
