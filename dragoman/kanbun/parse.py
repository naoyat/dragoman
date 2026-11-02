#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文の語の切り分け・品詞・係り受け: UD-Kanbun (安岡孝一、MIT。pip install udkanbun)。
# 句点・読点で区切った句ごとに Token の列を返す
#
#   學而時習之 → [Token(i=1, form='學', lemma='學', simplified='学', upos='VERB', xpos='v,動詞,行為,動作', head=1,
#                        deprel='root', gloss='study'), Token(i=2, form='而', … deprel='cc'), …]
#
import functools
from dataclasses import dataclass, field


@dataclass
class Token:
    i: int
    form: str
    lemma: str
    simplified: str     # 見出しの簡体字 (學 → 学。新字体を探す手掛かり)
    upos: str
    xpos: str           # 品詞の細分類 (v,動詞,行為,動作 / v,副詞,否定,無界 / p,助詞,句末 …)
    feats: str
    head: int           # 句の中の係り先の番号 (句の根は自分自身)
    deprel: str
    gloss: str          # 英語の語義 (UD-Kanbun の辞書の Gloss)
    children: list = field(default_factory=list, repr=False)

    @property
    def x(self):
        """品詞の細分類の欄 (['v', '動詞', '行為', '動作'])"""
        return self.xpos.split(',')

    @property
    def rel(self):
        """依存関係の主な部分 (obl:tmod → obl)"""
        return self.deprel.split(':')[0]


def available():
    try:
        import udkanbun   # noqa: F401
        return True
    except ImportError:
        return False


@functools.lru_cache(maxsize=1)
def _pipeline():
    import udkanbun
    return udkanbun.load()


def _misc(misc, key):
    for part in misc.split('|'):
        if part.startswith(key + '='):
            return part[len(key) + 1:]
    return ''


def phrases(text):
    """文 (白文。句読点があればそこで区切る) → [[Token]] (句ごと。句読点の Token も含む)"""
    entry = _pipeline()(text)
    out, current = [], []
    for t in entry[1:]:
        if t.id == 1 and current:
            out.append(current)
            current = []
        lemma, _, simplified = t.lemma.partition('/')
        current.append(Token(i=t.id, form=t.form, lemma=lemma, simplified=simplified or lemma, upos=t.upos,
                             xpos=t.xpos, feats=t.feats, head=t.head.id if t.head is not t else t.id,
                             deprel=t.deprel, gloss=_misc(t.misc, 'Gloss')))
    if current:
        out.append(current)
    for phrase in out:
        by_i = {t.i: t for t in phrase}
        for t in phrase:
            if t.head != t.i and t.head in by_i:
                by_i[t.head].children.append(t)
    return out


def kaeriten(text):
    """UD-Kanbun の返り点付きの白文 (學而時習㆑之、不㆓亦說㆒乎。)"""
    return ''.join(_pipeline()(text).kaeriten().split())
