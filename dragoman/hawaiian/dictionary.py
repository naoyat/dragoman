#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の辞書 ($DRAGOMAN_DATA/haw/wiktionary.sqlite。tools/build_hawaiian_dic.py で作る) を引く
#
#   lookup('kanaka') → [{word, pos, en, senses}]   (鍵は ʻokina と長音符を除いた形。綴りの合うものを先に)
#   forms('kānaka') → [(見出し, 品詞, 印)]          (複数形・異綴り)
#
import functools
import os
import sqlite3

from dragoman.core import paths
from . import orthography

DB_PATH = paths.data('haw', 'wiktionary.sqlite')
ANDREWS_PATH = paths.data('haw', 'andrews.sqlite')   # Andrews (Parker の改訂版、1922年) の補い (tools/build_hawaiian_andrews.py)
_db = None
_andrews = None


def _connect_andrews():
    global _andrews
    if _andrews is None and os.path.exists(ANDREWS_PATH):
        _andrews = sqlite3.connect(ANDREWS_PATH, check_same_thread=False)
    return _andrews


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=50000)
def _lemmas(k):
    """鍵 → 見出し。Wiktionary の見出し (ʻokina・長音符付き) を先に、Wiktionary にその品詞の見出しが無いときだけ
    Andrews の見出し (source: andrews。19世紀の綴りなので印は無い)"""
    db = _connect()
    if db is None or not k:
        return ()
    rows = [dict(zip(('word', 'pos', 'en', 'senses'), row)) for row in
            db.execute('SELECT word, pos, en, senses FROM lemmas WHERE key = ?', (k,))]
    andrews = _connect_andrews()
    if andrews is not None:
        poses = {r['pos'] for r in rows}
        for row in andrews.execute('SELECT word, pos, en, senses FROM lemmas WHERE key = ?', (k,)):
            entry = dict(zip(('word', 'pos', 'en', 'senses'), row), source='andrews')
            if entry['pos'] not in poses:
                rows.append(entry)
    return tuple(rows)


def lemmas(word, pos=None):
    """見出し → [{word, pos, en, senses}]。綴り (ʻokina・長音符) の合うもの、語義の多いものを先に。
    長音符の無い綴り (翻刻) なら、同じ鍵のすべての見出し (pau・paʻu)"""
    word = orthography.normalize(word)
    poses = (pos,) if isinstance(pos, str) else pos
    rows = [r for r in _lemmas(orthography.key(word)) if not poses or r['pos'] in poses]
    exact = orthography.marked(word)
    return sorted(rows, key=lambda r: (exact and r['word'].lower() != word.lower(), -(r['senses'] or 0)))


@functools.lru_cache(maxsize=50000)
def forms(word):
    db = _connect()
    if db is None or not word:
        return ()
    return tuple(db.execute('SELECT form, lemma, pos, tags FROM forms WHERE key = ?', (orthography.key(word),)))


def lookup(word, langs=None):
    return []


def descendants(lemma):
    return []


def etymology(lemma):
    return []
