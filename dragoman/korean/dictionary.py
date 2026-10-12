#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語の辞書 ($DRAGOMAN_DATA/ko/wiktionary.sqlite。tools/build_korean_dic.py で作る) を引く
#
import functools
import os
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('ko', 'wiktionary.sqlite')
FIELDS = ('key', 'pos', 'en', 'hanja', 'roman', 'target', 'senses')
_db = None


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=100000)
def _rows(key):
    db = _connect()
    if db is None or not key:
        return ()
    return tuple(dict(zip(FIELDS, row)) for row in
                 db.execute('SELECT %s FROM lemmas WHERE key = ?' % ', '.join(FIELDS), (key,)).fetchall())


def lemmas(key, pos=None):
    """見出し → [{key, pos, en, hanja, roman, target, senses}] (品詞 pos (タプルでもよい) の項目を、語義の多い順に)。
    語義の無い項目 (alternative form of …) は元の語の項目に置き換える"""
    poses = (pos,) if isinstance(pos, str) else pos
    out = []
    for row in _rows(key):
        if poses and row['pos'] not in poses:
            continue
        if not row['en'] and row['target'] and row['target'] != key:
            out += [dict(r, key=key) for r in _rows(row['target']) if r['en'] and (not poses or r['pos'] in poses)]
        elif row['en']:
            out.append(row)
    return sorted(out, key=lambda r: -(r['senses'] or 0))


def lookup(word, langs=None):
    return []


def descendants(lemma):
    return []


def etymology(lemma):
    return []
