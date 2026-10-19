#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語の辞書: 訳語は英和の表 (core/en_ja.py) を english/morphology.gloss で引く。子孫語・語源はまだ無い
#
from dragoman.core import en_ja


def available():
    return en_ja.available()


def lookup(word, langs=None):
    return []


def descendants(lemma):
    return []


def etymology(lemma):
    return []
