#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語の辞書 ($DRAGOMAN_DATA/yue/cantonese.sqlite。tools/build_cantonese_dic.py で CC-Canto から作る) を引く。
# 普通話の辞書 (CC-CEDICT。chinese/dictionary.py) に無い語の英語の語義と、粤拼の読み
#
import functools
import os
import sqlite3

from dragoman.core import paths

DB_PATH = paths.data('yue', 'cantonese.sqlite')
_db = None


def _connect():
    global _db
    if _db is None and os.path.exists(DB_PATH):
        _db = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _db


def available():
    return _connect() is not None


@functools.lru_cache(maxsize=100000)
def rows(word):
    """語 (繁体字か簡体字) → [{traditional, simplified, pinyin, jyutping, en, mandarin, senses, source}] (CC-Canto の語を
    読みの表より、語義の多い順に)"""
    db = _connect()
    if db is None or not word:
        return ()
    fields = ('traditional', 'simplified', 'pinyin', 'jyutping', 'en', 'mandarin', 'senses', 'source')
    out = [dict(zip(fields, r)) for r in db.execute(
        'SELECT %s FROM words WHERE traditional = ? OR simplified = ?' % ', '.join(fields), (word, word))]
    return tuple(sorted(out, key=lambda r: (r['source'] != 'canto', -(r['senses'] or 0))))


def lookup(word):
    """普通話の辞書と同じ形の項目 (chinese/dictionary.py の extra に渡す): 英語の語義のある CC-Canto の語"""
    return [{'simplified': r['simplified'], 'traditional': r['traditional'], 'pinyin': r['pinyin'], 'en': r['en'],
             'classifiers': '', 'proper': 0, 'senses': r['senses']} for r in rows(word) if r['en']]


@functools.lru_cache(maxsize=1)
def keys():
    """見出しの集まり (繁体字・簡体字)"""
    db = _connect()
    out = set()
    if db is not None:
        for t, s in db.execute('SELECT traditional, simplified FROM words'):
            out.add(t)
            out.add(s)
    return out


def jyutping(word):
    """辞書の語の粤拼 (無ければ '')"""
    found = rows(word)
    return found[0]['jyutping'] if found else ''


def descendants(lemma):
    return []


def etymology(lemma):
    return []
