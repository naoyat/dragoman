#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語の辞書 ($DRAGOMAN_DATA/fr/wiktionary.sqlite。tools/build_french_dic.py で作る) を引く
#
import functools
import os
import re
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('fr', 'wiktionary.sqlite')
FIELDS = ('key', 'pos', 'en', 'gender', 'senses', 'word', 'valency')
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
    columns = [c for c in FIELDS if c in _columns()]   # 古い辞書には valency の列が無い
    return tuple(dict(zip(columns, row)) for row in
                 db.execute('SELECT %s FROM lemmas WHERE key = ?' % ', '.join(columns), (key.lower(),)).fetchall())


@functools.lru_cache(maxsize=1)
def _columns():
    return {row[1] for row in _connect().execute('PRAGMA table_info(lemmas)')}


@functools.lru_cache(maxsize=50000)
def gender(noun):
    """名詞の性: 辞書の最初の項目 (Wiktionary で先に載る主な語義: livre「本」(男性) を livre「ポンド」(女性) より)"""
    db = _connect()
    if db is None:
        return None
    row = db.execute("SELECT gender FROM lemmas WHERE key = ? AND pos = 'noun' AND gender IN ('m', 'f') ORDER BY rowid "
                     "LIMIT 1", (noun.lower(),)).fetchone()
    return row[0] if row else None


REFORM = re.compile(r'post-1990 spelling of ([^\s,;]+)')


@functools.lru_cache(maxsize=1)
def reform_spellings():
    """1990年の綴りの改革: (新しい綴り → 従来の綴り, 従来の綴り → 新しい綴り)。辞書の語義「post-1990 spelling of coût」から"""
    db = _connect()
    new_to_old, old_to_new = {}, {}
    if db is None:
        return new_to_old, old_to_new
    for key, en in db.execute("SELECT key, en FROM lemmas WHERE en LIKE '%post-1990 spelling of%'"):
        m = REFORM.search(en)
        if m:
            new_to_old.setdefault(key, m.group(1).lower())
            old_to_new.setdefault(m.group(1).lower(), key)
    return new_to_old, old_to_new


def valency(lemma):
    """動詞の語義の印 (最初の3つの語義の集まり: transitive・intransitive・reflexive・à・to-someone …)"""
    rows = lemmas(lemma, 'verb')
    tags = set()
    for row in rows[:1]:
        for sense in (row.get('valency') or '').split(';'):
            tags |= {t for t in sense.split(',') if t}
    return tags


def lemmas(word, pos=None):
    """見出し → [{key, pos, en, gender, senses, word}] (品詞 pos (タプルでもよい) の項目を、表記の大文字・小文字の
    合うもの・語義の多い順に)"""
    poses = (pos,) if isinstance(pos, str) else pos
    rows = [r for r in _rows(word) if not poses or r['pos'] in poses]
    return sorted(rows, key=lambda r: (r['word'] != word, -(r['senses'] or 0)))


@functools.lru_cache(maxsize=100000)
def forms(word):
    """語形 → [(見出し語, 品詞, 印のタプル)]"""
    db = _connect()
    if db is None or not word:
        return ()
    return tuple((lemma, pos, tuple(t for t in tags.split(',') if t)) for lemma, pos, tags in
                 db.execute('SELECT lemma, pos, tags FROM forms WHERE form = ?', (word.lower(),)).fetchall())


def lookup(word, langs=None):
    return []


def descendants(lemma):
    return []


def etymology(lemma):
    return []
