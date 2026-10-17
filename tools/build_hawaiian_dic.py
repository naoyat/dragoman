#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_hawaiian_dic.py [FILE.jsonl [OUT.sqlite]]
#
# 入力: kaikki.org-dictionary-Hawaiian.jsonl (https://kaikki.org/dictionary/Hawaiian/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/haw/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#   lemmas (key, word, pos, en, senses): 見出し (ʻokina・長音符付き)・品詞・英語の語義 (多くて3つ)・語義の数。
#     鍵は hawaiian/orthography.key (ʻokina と長音符を除いた小文字)
#   forms (key, form, lemma, pos, tags): 複数形 (kānaka ← kanaka)・異綴り (wau ← au)・変化形だけの項目
#
import os
import sys
import json
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.core.wiktionary_import import english_glosses
from dragoman.hawaiian.orthography import key, normalize

POS = {'noun': 'noun', 'name': 'name', 'verb': 'verb', 'adj': 'adj', 'adv': 'adv', 'pron': 'pronoun',
       'det': 'det', 'num': 'num', 'prep': 'preposition', 'conj': 'conj', 'particle': 'particle', 'intj': 'intj',
       'article': 'article', 'phrase': 'phrase'}


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('haw', 'kaikki.org-dictionary-Hawaiian.jsonl')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('haw', 'wiktionary.sqlite')
    lemmas, forms = [], set()
    for line in open(source, encoding='utf-8'):
        entry = json.loads(line)
        if entry.get('lang_code') != 'haw':
            continue
        pos = POS.get(entry.get('pos'))
        word = normalize(entry.get('word', ''))
        if pos is None or not word:
            continue
        senses = []
        for sense in entry.get('senses', []):
            target = (sense.get('form_of') or sense.get('alt_of') or [{}])[0].get('word')
            if target:
                tags = sorted(t for t in sense.get('tags') or [] if t in ('plural', 'passive', 'alternative', 'obsolete'))
                forms.add((key(word), word, normalize(target), pos, ','.join(tags or ['alternative'])))
                continue
            if sense.get('glosses'):
                senses.append(sense)
        if not senses:
            continue
        lemmas.append((key(word), word, pos, english_glosses(entry, senses), len(senses)))
        for f in entry.get('forms', []):
            tags = set(f.get('tags') or [])
            form = normalize(f.get('form', ''))
            if form and form != word and tags & {'plural', 'alternative', 'passive'} and ' ' not in form:
                forms.add((key(form), form, word, pos, ','.join(sorted(tags & {'plural', 'alternative', 'passive'}))))
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE lemmas (key TEXT, word TEXT, pos TEXT, en TEXT, senses INTEGER);
        CREATE TABLE forms (key TEXT, form TEXT, lemma TEXT, pos TEXT, tags TEXT);
    ''')
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?)', lemmas)
    db.executemany('INSERT INTO forms VALUES (?, ?, ?, ?, ?)', sorted(forms))
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX lemmas_word ON lemmas (word); '
                     'CREATE INDEX forms_key ON forms (key);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d lemmas, %d forms → %s (%.1fs)' % (len(lemmas), len(forms), out, time.time() - t0))


if __name__ == '__main__':
    main()
