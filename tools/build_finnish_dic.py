#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_finnish_dic.py [FILE.jsonl | -]
#   curl -sL https://kaikki.org/dictionary/Finnish/kaikki.org-dictionary-Finnish.jsonl | python3 tools/build_finnish_dic.py -
#
# 元のデータは約 4.6GB (変化形の項目が多い) あるので、標準入力から読んで必要なものだけを残せる。見出し語 (動詞は第1不定詞 -a / -ä の形。spaCy の
# 原形と同じ) ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)。
# 語形変化は解析器が見出しに戻すので、語形の表は作らない。「alternative form of 〜」などの項目は元の語を引けるように
#
# 入力: kaikki.org-dictionary-Finnish.jsonl (https://kaikki.org/dictionary/Finnish/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/fi/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#
import os
import re
import sys
import json
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.core.wiktionary_import import english_glosses

POS = {'noun': 'noun', 'name': 'name', 'adj': 'adj', 'num': 'num', 'pron': 'pronoun', 'det': 'det',
       'verb': 'verb', 'adv': 'adv', 'conj': 'conj', 'particle': 'particle', 'postp': 'postposition',
       'prep': 'postposition', 'intj': 'intj', 'suffix': 'suffix'}
FORM_OF = re.compile(r'^(?:alternative (?:form|spelling)|obsolete (?:form|spelling)|archaic (?:form|spelling)|'
                     r'nonstandard (?:form|spelling)|misspelling|dated (?:form|spelling)|'
                     r'(?:[a-z-]+ )*(?:case|plural|singular|form|possessive|participle|tense)[a-z ]* of) ([^\s,;:()]+)', re.I)


def key_of(word):
    return word.lower()


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('fi', 'kaikki.org-dictionary-Finnish.jsonl')
    out = paths.data('fi', 'wiktionary.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('CREATE TABLE lemmas (key TEXT, pos TEXT, en TEXT, target TEXT, senses INTEGER, word TEXT);')
    rows = []
    stream = sys.stdin if source == '-' else open(source, encoding='utf-8')
    for line in stream:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get('lang_code') != 'fi':
            continue
        pos = POS.get(entry.get('pos'))
        word = entry.get('word', '')
        if pos is None or not word:
            continue
        senses, target = [], None
        for sense in entry.get('senses', []):
            gloss = (sense.get('glosses') or [''])[0]
            m = FORM_OF.match(gloss)
            if m or 'form-of' in (sense.get('tags') or []):
                target = target or (m.group(1) if m else ((sense.get('form_of') or [{}])[0].get('word')))
                continue
            if gloss:
                senses.append(sense)
        en = english_glosses(entry, senses=senses) if senses else ''
        if not en and not target:
            continue
        rows.append((key_of(word), pos, en, target, len(senses), word))
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?, ?)', rows)
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries → %s (%.1fs)' % (len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
