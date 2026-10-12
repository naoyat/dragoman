#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_korean_dic.py
#
# 見出し語 (ハングル。用言は -다 の形) ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)・
# 漢字 (漢字語の 學校 など)・ローマ字 (Wiktionary の改訂ローマ字)。形容詞の語義の「to be pretty」は「pretty」に。
# 語形変化は解析器 (kiwipiepy) が原形に戻すので、語形の表は作らない。
# 「alternative form of 〜」などの語義だけの項目は、元の語 (target) を引けるようにする。
#
# 入力: $DRAGOMAN_DATA/ko/kaikki.org-dictionary-Korean.jsonl (https://kaikki.org/dictionary/Korean/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/ko/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
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
       'verb': 'verb', 'adv': 'adv', 'conj': 'conj', 'particle': 'particle', 'intj': 'intj', 'counter': 'counter',
       'suffix': 'suffix', 'prefix': 'prefix', 'phrase': 'phrase'}
FORM_OF = re.compile(r'^(?:alternative (?:form|spelling)|abbreviation|contraction|clipping|honorific|humble|'
                     r'short form|nonstandard spelling|misspelling|dialectal form|eye dialect spelling) of ([^\s,;:()]+)',
                     re.I)
HANGUL = re.compile('^[가-힣]+(?: [가-힣]+)*$')


def main():
    t0 = time.time()
    path = paths.data('ko', 'kaikki.org-dictionary-Korean.jsonl')
    out = paths.data('ko', 'wiktionary.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('CREATE TABLE lemmas (key TEXT, pos TEXT, en TEXT, hanja TEXT, roman TEXT, target TEXT, '
                     'senses INTEGER);')
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            pos = POS.get(entry.get('pos'))
            word = entry.get('word', '')
            if pos is None or not HANGUL.match(word) or entry.get('lang_code', 'ko') != 'ko':
                continue
            senses, target = [], None
            for sense in entry.get('senses', []):
                gloss = (sense.get('glosses') or [''])[0]
                m = FORM_OF.match(gloss)
                if m:
                    target = target or m.group(1)
                    continue
                if 'form-of' in (sense.get('tags') or []) or not gloss:
                    continue
                senses.append(sense)
            en = english_glosses(entry, senses=senses) if senses else ''
            if pos == 'adj':   # 'be pretty,be lovely' → 'pretty,lovely'
                en = ','.join(re.sub(r'^be ', '', g) for g in en.split(','))
            hanja = next((f['form'] for f in entry.get('forms', []) if 'hanja' in (f.get('tags') or [])), None)
            roman = next((f['form'] for f in entry.get('forms', []) if 'romanization' in (f.get('tags') or [])), None)
            if not en and not target:
                continue
            rows.append((word, pos, en, hanja, roman, target, len(senses)))
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries → %s (%.1fs)' % (len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
