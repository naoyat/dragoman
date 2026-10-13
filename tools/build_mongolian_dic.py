#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語 (ハルハ方言・キリル文字) の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_mongolian_dic.py
#
# 見出し語 (動詞は -х の形: өгөх「与える」) ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)・
# ラテン文字の転写・伝統的なモンゴル文字の綴り (縦書きの表示と、伝統文字の入力の対応表のため)。
# 名詞の変化表の形 (номын「本の」…) は語形の表に。動詞の活用は解析器が規則で分ける (mongolian/morphology.py)
#
# 入力: $DRAGOMAN_DATA/mn/kaikki.org-dictionary-Mongolian.jsonl (https://kaikki.org/dictionary/Mongolian/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/mn/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
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
       'intj': 'intj', 'suffix': 'suffix'}
FORM_OF = re.compile(r'^(?:alternative (?:form|spelling)|(?:[a-z-]+ )*(?:case|plural|form|participle|converb)[a-z ]* of) '
                     r'([^\s,;:()]+)', re.I)
CASE_TAGS = {'nominative': 'Nom', 'genitive': 'Gen', 'accusative': 'Acc', 'dative': 'Dat', 'locative': 'Dat',
             'dative-locative': 'Dat', 'ablative': 'Abl', 'instrumental': 'Ins', 'comitative': 'Com',
             'directive': 'Dir', 'directional': 'Dir'}
CYRILLIC = re.compile('^[а-яёөүА-ЯЁӨҮ-]+$')


def main():
    t0 = time.time()
    path = paths.data('mn', 'kaikki.org-dictionary-Mongolian.jsonl')
    out = paths.data('mn', 'wiktionary.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE lemmas (key TEXT, pos TEXT, en TEXT, roman TEXT, script TEXT, target TEXT, senses INTEGER);
        CREATE TABLE forms (form TEXT, lemma TEXT, pos TEXT, case_ TEXT, number TEXT, tags TEXT);
    ''')
    rows, forms = [], set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            if entry.get('lang_code') != 'mn':
                continue
            pos = POS.get(entry.get('pos'))
            word = entry.get('word', '')
            if pos is None or not CYRILLIC.match(word):
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
            if pos == 'verb':   # 'to give' → 'give' (english_glosses が除く)。形容詞の 'be good' は 'good' に
                pass
            if pos == 'adj':
                en = ','.join(re.sub(r'^be ', '', g) for g in en.split(','))
            roman = next((x['form'] for x in entry.get('forms', []) if 'romanization' in (x.get('tags') or [])), None)
            script = next((x['form'] for x in entry.get('forms', []) if 'Mongolian' in (x.get('tags') or [])), None)
            if not en and not target:
                continue
            rows.append((word.lower(), pos, en, roman, script, target, len(senses)))
            for x in entry.get('forms', []):
                tags = set(x.get('tags') or [])
                form = x.get('form', '')
                if not CYRILLIC.match(form) or tags & {'romanization', 'Mongolian', 'table-tags', 'inflection-template'}:
                    continue
                case = next((CASE_TAGS[t] for t in tags if t in CASE_TAGS), None)
                if case is None and 'attributive' not in tags:
                    continue
                number = 'pl' if 'plural' in tags else 'sg'
                forms.add((form.lower(), word, pos, case or 'Nom', number, ','.join(sorted(tags))))
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?, ?, ?)', rows)
    db.executemany('INSERT INTO forms VALUES (?, ?, ?, ?, ?, ?)', sorted(forms))
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX forms_form ON forms (form);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries, %d forms → %s (%.1fs)' % (len(rows), len(forms), out, time.time() - t0))


if __name__ == '__main__':
    main()
