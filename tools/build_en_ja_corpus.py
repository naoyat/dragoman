#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英日の対訳文 (Tatoeba。ManyThings.org の jpn-eng.zip) から、訳語を文脈で選ぶための表 (SQLite) を作る
#
#   python3 tools/build_en_ja_corpus.py
#
# 入力: $DRAGOMAN_DATA/en/tatoeba/jpn.txt (英語 TAB 日本語 TAB 出典。https://www.manythings.org/anki/jpn-eng.zip、
#       tatoeba.org の文、CC BY 2.0 FR)
# 出力: $DRAGOMAN_DATA/en/tatoeba.sqlite (pairs: 文の対、lemmas: 英語の文の原形 (spaCy) → 文の番号)。
#       core/en_ja.corpus_ranked が、英語の語の訳語の候補を、その語を含む英文の和訳に現れる数 (周りの語も含む英文に
#       絞ったもの) で並べ替えるのに使う
#
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

SOURCE = paths.data('en', 'tatoeba', 'jpn.txt')
OUT = paths.data('en', 'tatoeba.sqlite')


def main():
    import spacy
    t0 = time.time()
    pairs = []
    with open(SOURCE, encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2:
                pairs.append((parts[0], parts[1]))
    tmp = OUT + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE pairs (id INTEGER PRIMARY KEY, en TEXT, ja TEXT)')
    db.execute('CREATE TABLE lemmas (lemma TEXT, id INTEGER)')
    db.executemany('INSERT INTO pairs VALUES (?, ?, ?)', [(k, en, ja) for k, (en, ja) in enumerate(pairs)])
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])
    rows = []
    for k, doc in enumerate(nlp.pipe((en for en, _ in pairs), batch_size=1000)):
        lemmas = {t.lemma_.lower() for t in doc if t.is_alpha}
        rows += [(lemma, k) for lemma in lemmas]
    db.executemany('INSERT INTO lemmas VALUES (?, ?)', rows)
    db.execute('CREATE INDEX lemmas_lemma ON lemmas (lemma)')
    db.commit()
    db.close()
    os.replace(tmp, OUT)
    print('%d pairs, %d lemma rows -> %s (%.1fMB, %.0fs)' % (len(pairs), len(rows), OUT, os.path.getsize(OUT) / 1e6,
                                                             time.time() - t0))


if __name__ == '__main__':
    main()
