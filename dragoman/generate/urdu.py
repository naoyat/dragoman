#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からウルドゥー語の文を作る: ヒンディー語と文法が同じなので generate/hindi.py で作り、
# ウルドゥー文字 (辞書の見出しのウルドゥー文字の綴り + 規則の語尾) で出す
#
from . import hindi


def available():
    return hindi.available()


def sentence(clauses):
    return hindi.sentence_urdu(clauses)
