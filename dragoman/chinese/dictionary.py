#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語の辞書 ($DRAGOMAN_DATA/zh/cedict.sqlite。tools/build_chinese_dic.py で CC-CEDICT から作る) を引く
#
import functools
import os
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('zh', 'cedict.sqlite')
FIELDS = ('simplified', 'traditional', 'pinyin', 'en', 'classifiers', 'proper', 'senses')
_db = None


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=100000)
def lookup(word):
    """語 (簡体字か繁体字) → [{simplified, traditional, pinyin, en, classifiers, proper, senses}] (普通名詞を固有名詞より、
    語義の多い順に)"""
    db = _connect()
    if db is None or not word:
        return ()
    rows = [dict(zip(FIELDS, r)) for r in db.execute(
        'SELECT %s FROM words WHERE simplified = ? OR traditional = ?' % ', '.join(FIELDS), (word, word)).fetchall()]
    return tuple(sorted(rows, key=lambda r: (r['proper'], -(r['senses'] or 0))))


@functools.lru_cache(maxsize=1)
def keys():
    """見出しの集まり (簡体字・繁体字) と、いちばん長い見出しの字数 (語の切り分けの最長一致に)"""
    db = _connect()
    out = set()
    if db is None:
        return out, 1
    for s, t in db.execute('SELECT simplified, traditional FROM words'):
        out.add(s)
        out.add(t)
    return out, max(len(k) for k in out)


def descendants(lemma):
    return []


def etymology(lemma):
    return []
