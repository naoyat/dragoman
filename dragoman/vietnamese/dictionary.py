#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語の辞書 ($DRAGOMAN_DATA/vi/vietnamese.sqlite。tools/build_vietnamese_dic.py で Wiktionary と Unihan から作る) を引く
#
import functools
import os
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('vi', 'vietnamese.sqlite')
FIELDS = ('key', 'word', 'pos', 'en', 'han', 'nom', 'classifiers', 'link', 'target', 'senses', 'ipa')
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
                 db.execute('SELECT %s FROM words WHERE key = ?' % ', '.join(FIELDS), (key,)).fetchall())


@functools.lru_cache(maxsize=100000)
def lookup(word):
    """語 (小文字にして引く) → [{key, word, pos, en, han, nom, classifiers, link, target, senses, ipa}]。
    別の綴り (声調記号の位置の違い khỏe → khoẻ、古い綴り …) は綴りの先の項目の語義で。普通名詞を固有名詞より、語義の多い順"""
    key = word.lower()
    out = []
    for row in _rows(key):
        if row['link'] and not row['en'] and row['target'] and row['target'] != key:
            for target in _rows(row['target']):
                if target['pos'] == row['pos'] and target['en']:
                    out.append(dict(target, key=key, word=row['word'], link=row['link'], target=row['target']))
            continue
        out.append(row)
    return tuple(sorted(out, key=lambda r: (r['pos'] == 'name' and word[:1].islower(), -(r['senses'] or 0))))


@functools.lru_cache(maxsize=1)
def keys():
    """見出しの集まり (小文字。語の切り分けに。ことわざ・成句の見出し uống nước nhớ nguồn は語に分けて訳すので除く) と、
    いちばん長い見出しの音節の数"""
    db = _connect()
    if db is None:
        return frozenset(), 1
    out = frozenset(k for (k,) in db.execute("SELECT DISTINCT key FROM words WHERE pos != 'phrase'"))   # ことわざ・成句は除く
    return out, max(len(k.split()) for k in out)


def han(word):
    """漢越語の漢字 (sinh viên → 生員)。無ければ None"""
    for row in lookup(word):
        if row['han']:
            return row['han']
    return None


@functools.lru_cache(maxsize=10000)
def hanviet(char):
    """漢字 → 漢越音のリスト (學 → [học])"""
    db = _connect()
    if db is None:
        return []
    return sorted({r for (r,) in db.execute('SELECT reading FROM hanviet WHERE char = ?', (char,))})


def descendants(lemma):
    return []


def etymology(lemma):
    """語源 (core/etymology の形): 漢越語の漢字と字ごとの漢越音 (sinh viên: 生員 (生 sinh・員 viên))"""
    h = han(lemma)
    if not h:
        return []
    syllables = lemma.lower().split()
    text = '漢越語: %s (%s)' % (h, '・'.join('%s %s' % (c, s) for c, s in zip(h, syllables)))
    return [{'ancestors': [], 'cognates': [], 'text': text}]
