#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# パーリ語の辞書 ($DRAGOMAN_DATA/pi/pali.sqlite) を Digital Pāḷi Dictionary (DPD) の SQLite から作る
#
#   python3 tools/build_pali_dic.py [dpd.db] [pali.sqlite]
#
# DPD (https://github.com/digitalpalidictionary/dpd-db、CC BY-NC-SA 4.0) の dpd.db.tar.xz を展開した dpd.db
# ($DRAGOMAN_DATA/pi/dpd.db) から、解析に使う列だけを抜き出す:
#   forms     語形 → 見出しの番号・文法 (語幹, 品詞, "masc nom pl")・連声と複合語の分解 ("sammanti + idha")
#   headwords 見出しの番号 → 見出し語 (dhamma 1.01)・品詞・文法・英語の語義・成り立ち・サンスクリットの対応語・語根・頻度、
#             番号を除いた見出し語 (base: dhamma。複合語の要素を引く索引)
#
import os
import sys
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dragoman.core import paths

HEADWORD_COLUMNS = ('id', 'lemma_1', 'pos', 'grammar', 'meaning_1', 'meaning_lit', 'meaning_2', 'construction',
                    'sanskrit', 'root_key', 'plus_case', 'compound_type', 'ebt_count')


def base(lemma):
    """見出し語の番号を除いた形 (dhamma 1.01 → dhamma)"""
    return re.sub(r' [0-9.]+$', '', lemma)


def build(src, dst):
    con = sqlite3.connect('file:%s?mode=ro' % src, uri=True)
    if os.path.exists(dst):
        os.remove(dst)
    out = sqlite3.connect(dst)
    out.execute('CREATE TABLE headwords (id INTEGER PRIMARY KEY, lemma TEXT, pos TEXT, grammar TEXT, meaning TEXT, '
                'meaning_lit TEXT, meaning_2 TEXT, construction TEXT, sanskrit TEXT, root TEXT, plus_case TEXT, '
                'compound_type TEXT, ebt INTEGER, base TEXT)')
    out.execute('CREATE TABLE forms (key TEXT PRIMARY KEY, headwords TEXT, grammar TEXT, deconstructor TEXT)')
    rows = con.execute('SELECT %s FROM dpd_headwords' % ', '.join(HEADWORD_COLUMNS))
    out.executemany('INSERT INTO headwords VALUES (%s)' % ','.join('?' * (len(HEADWORD_COLUMNS) + 1)),
                    (tuple(r) + (base(r[1]),) for r in rows))
    out.execute('CREATE INDEX headwords_base ON headwords (base)')
    n = 0
    batch = []
    for key, headwords, grammar, decon in con.execute(
            'SELECT lookup_key, headwords, grammar, deconstructor FROM lookup '
            "WHERE headwords != '' OR deconstructor != ''"):
        batch.append((key, headwords or '[]', grammar or '[]', decon or '[]'))
        if len(batch) >= 50000:
            out.executemany('INSERT INTO forms VALUES (?,?,?,?)', batch)
            n += len(batch)
            batch = []
    out.executemany('INSERT INTO forms VALUES (?,?,?,?)', batch)
    n += len(batch)
    out.commit()
    heads = out.execute('SELECT count(*) FROM headwords').fetchone()[0]
    out.execute('VACUUM')
    out.close()
    print('%s: 見出し %d、語形 %d' % (dst, heads, n))


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else paths.data('pi', 'dpd.db')
    dst = sys.argv[2] if len(sys.argv) > 2 else paths.data('pi', 'pali.sqlite')
    if not os.path.exists(src):
        sys.exit('%s が無い (DPD の dpd.db.tar.xz を https://github.com/digitalpalidictionary/dpd-db/releases から)' % src)
    build(src, dst)


if __name__ == '__main__':
    main()
