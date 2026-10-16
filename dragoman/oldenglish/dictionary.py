#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の辞書 ($DRAGOMAN_DATA/ang/wiktionary.sqlite。tools/build_oldenglish_dic.py で作る) を引く
#
#   forms('cyninges') → [(見出しの情報, 語形の情報)]   (鍵は orthography.key: 長音符・点を除き、ð → þ)
#   lemmas('cyning', 'noun') → [見出しの情報]
#
import functools
import json
import os
import sqlite3

from dragoman.core import paths
from . import orthography

DB_PATH = paths.data('ang', 'wiktionary.sqlite')
_db = None


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=50000)
def _lemma(lemma_id):
    info, = _connect().execute('SELECT info FROM lemmas WHERE id = ?', (lemma_id,)).fetchone()
    return dict(json.loads(info), id=lemma_id)


@functools.lru_cache(maxsize=100000)
def _forms(k):
    db = _connect()
    if db is None or not k:
        return ()
    rows = db.execute('SELECT surface, lemma_id, features FROM forms WHERE key = ?', (k,)).fetchall()
    return tuple((_lemma(lemma_id), dict(json.loads(features), surface=surface)) for surface, lemma_id, features in rows)


def forms(word):
    """語形 → [(見出しの情報, 語形の情報)]。見出しは語義の多い順"""
    found = _forms(orthography.key(word))
    return sorted(found, key=lambda pair: -(pair[0].get('senses') or 0))


@functools.lru_cache(maxsize=20000)
def variant_forms(word):
    """辞書に無い綴りを、綴りの揺れで読み替えて引く (1か所、無ければ2か所) → (読み替えた鍵, [(見出し, 語形)])"""
    for depth in (1, 2):
        for v in orthography.variants(word, depth):
            found = _forms(v)
            if found:
                return v, sorted(found, key=lambda pair: -(pair[0].get('senses') or 0))
    return None, []


@functools.lru_cache(maxsize=50000)
def _lemmas(k):
    db = _connect()
    if db is None or not k:
        return ()
    return tuple(_lemma(lemma_id) for lemma_id, in db.execute('SELECT id FROM lemmas WHERE key = ?', (k,)))


def lemmas(word, pos=None):
    """見出し → [見出しの情報] (品詞 pos (タプルでもよい) のものを、語義の多い順に)"""
    poses = (pos,) if isinstance(pos, str) else pos
    rows = [r for r in _lemmas(orthography.key(word)) if not poses or r['pos'] in poses]
    return sorted(rows, key=lambda r: -(r.get('senses') or 0))


@functools.lru_cache(maxsize=20000)
def lemma_forms(word, pos, english=()):
    """見出し → その語形の表 [(語形 (長音符付き), 語形の情報)] (生成で使う)。同じ綴りの見出しが複数あれば、英語の
    訳語 english と合うもの (sēon「見る」と「漉す」)、無ければ語義の多いもの"""
    rows = lemmas(word, pos)
    db = _connect()
    if not rows or db is None:
        return ()
    if not _has_lemma_index():
        db.execute('CREATE INDEX IF NOT EXISTS forms_lemma ON forms (lemma_id)')
    wanted = {e.lower() for e in english}
    exact = [r for r in rows if r['base'] == word] or rows   # 綴りの同じ見出し (God「神」を gōd より)
    row = next((r for r in exact if wanted & {e.strip().lower() for e in (r.get('en') or '').split(',')}), exact[0])
    return tuple((surface, json.loads(features)) for surface, features in
                 db.execute('SELECT surface, features FROM forms WHERE lemma_id = ?', (row['id'],)))


@functools.lru_cache(maxsize=1)
def _has_lemma_index():
    return bool(_connect().execute("SELECT 1 FROM sqlite_master WHERE name = 'forms_lemma'").fetchone())


def lookup(word, langs=None):
    return []


def descendants(lemma):
    return []


def etymology(lemma):
    return []
