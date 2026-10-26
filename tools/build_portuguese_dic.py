#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_portuguese_dic.py [FILE.jsonl | -] [OUT.sqlite]   (OUT を省くと $DRAGOMAN_DATA/pt/wiktionary.sqlite)
#   curl -sL https://kaikki.org/dictionary/Portuguese/kaikki.org-dictionary-Portuguese.jsonl | python3 tools/build_portuguese_dic.py -
#
# 見出し語ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)・名詞の性・動詞の語義の印 (他動・自動・
# 再帰)、語形の表 (見出し語・品詞 → 語形・印 (数・性・人称・法・時制))。動詞は単純時制の形 (単純過去完了 fizera・
# 接続法未来 fizer・人称不定詞も)。「plural of 〜」「feminine of 〜」のような語義だけの項目は語形の表に入れる。
# ブラジルとポルトガルの綴りの違い (fato / facto)・綴りの改革の前の形 (Janeiro) は、それぞれの見出しの語義
# (「Brazilian spelling of …」「pre-reform spelling (…) of …」) を語形の表に。いくつかの語の固有名詞 (Rio de Janeiro) も見出しに
#
# 入力: kaikki.org-dictionary-Portuguese.jsonl (https://kaikki.org/dictionary/Portuguese/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/pt/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
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
       'verb': 'verb', 'adv': 'adv', 'conj': 'conj', 'particle': 'particle', 'prep': 'preposition',
       'intj': 'intj', 'article': 'article', 'contraction': 'contraction'}
FORM_TAGS = {'singular', 'plural', 'masculine', 'feminine', 'first-person', 'second-person', 'third-person',
             'present', 'imperfect', 'preterite', 'pluperfect', 'future', 'conditional', 'subjunctive', 'indicative',
             'imperative', 'infinitive', 'personal', 'participle', 'gerund', 'comparative', 'superlative',
             'negative', 'affirmative'}
SKIP_FORM_TAGS = {'table-tags', 'inflection-template', 'class', 'auxiliary', 'error-unrecognized-form', 'romanization',
                  'obsolete', 'archaic', 'dialectal', 'rare', 'nonstandard', 'misspelling', 'multiword-construction',
                  'error-misspelling'}
FORM_OF = re.compile(r'^(?:(?:(?:masculine|feminine|singular|plural|first|second|third|person|present|imperfect|'
                     r'preterite|pluperfect|future|conditional|subjunctive|indicative|imperative|affirmative|negative|'
                     r'personal|impersonal|infinitive|participle|gerund|inflection|form|and|the|[/,-]|\s)+)) of '
                     r'([^\s,;:()]+)', re.I)
ALT_OF = re.compile(r'^(?:alternative (?:form|spelling)|obsolete (?:form|spelling)|archaic (?:form|spelling)|'
                    r'dated (?:form|spelling)|nonstandard (?:form|spelling)|(?:Brazilian|European|Portugal|Brazil) '
                    r'(?:Portuguese )?(?:standard )?(?:form|spelling)|pre-(?:1911|1943|1990|2009) spelling|'
                    r'superseded spelling|pre-reform spelling)(?: \([^)]*\))? of ([^\s,;:()]+)', re.I)


def gender_of(entry):
    """名詞の性: 見出しのテンプレートの引数 (pt-noun|m → m、f → f、mf → mf) か語義の印"""
    for head in entry.get('head_templates', []):
        args = head.get('args') or {}
        g = re.split('[,<-]', (args.get('1') or args.get('g') or '').strip())[0]
        if g in ('m', 'f', 'mf', 'mfbysense', 'm-p', 'f-p'):
            return 'mf' if g.startswith('mf') else g[0]
    for t in entry.get('tags') or []:
        if t in ('masculine', 'feminine'):
            return t[0]
    for sense in entry.get('senses', []):
        for t in sense.get('tags') or []:
            if t in ('masculine', 'feminine'):
                return t[0]
    return None


RARE_SENSE_TAGS = {'obsolete', 'archaic', 'dated', 'rare', 'historical', 'literary', 'nonstandard', 'slang'}
VALENCY_TAGS = ('transitive', 'intransitive', 'ambitransitive', 'reflexive', 'pronominal', 'impersonal', 'ditransitive')


def valency_of(senses):
    """動詞の語義の印 (最初の3つの語義): transitive・intransitive・reflexive …。語義ごとに ';' で区切る"""
    return ';'.join(','.join(t for t in (sense.get('tags') or []) if t in VALENCY_TAGS) for sense in senses[:3])


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('pt', 'kaikki.org-dictionary-Portuguese.jsonl')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('pt', 'wiktionary.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE lemmas (key TEXT, pos TEXT, en TEXT, gender TEXT, senses INTEGER, word TEXT, valency TEXT);
        CREATE TABLE forms (lemma TEXT, pos TEXT, form TEXT, tags TEXT, PRIMARY KEY (lemma, pos, form, tags)) WITHOUT ROWID;
    ''')
    lemmas, forms = [], set()
    stream = sys.stdin if source == '-' else open(source, encoding='utf-8')
    n = 0
    for line in stream:
        n += 1
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get('lang_code') != 'pt':
            continue
        pos = POS.get(entry.get('pos'))
        word = entry.get('word', '')
        if pos is None or not word or ' ' in word.strip() and pos not in ('verb', 'preposition', 'conj', 'adv', 'name'):
            continue
        senses = []
        for sense in entry.get('senses', []):
            gloss = (sense.get('glosses') or [''])[0]
            m = FORM_OF.match(gloss) or ALT_OF.match(gloss)
            if m or 'form-of' in (sense.get('tags') or []) or 'alt-of' in (sense.get('tags') or []):
                target = m.group(1) if m else ((sense.get('form_of') or sense.get('alt_of') or [{}])[0].get('word') or '')
                if target:
                    tags = sorted(t for t in (sense.get('tags') or []) if t in FORM_TAGS)
                    forms.add((target, pos, word.lower(), ','.join(tags)))
                continue
            if gloss:
                senses.append(sense)
        if not senses:
            continue
        senses = sorted(senses, key=lambda sense: bool(set(sense.get('tags') or []) & RARE_SENSE_TAGS))
        en = english_glosses(entry, senses=senses, limit=6)
        key = word.lower()
        lemmas.append((key, pos, en, gender_of(entry) if pos in ('noun', 'name') else None, len(senses), word,
                       valency_of(senses) if pos == 'verb' else None))
        if pos == 'verb' and not key.endswith('-se'):
            # 再帰の語義 ((reflexive) to get up) は「動詞-se」の見出しにも (levantar-se「起きる」)
            reflexive = [sense for sense in senses if {'reflexive', 'pronominal'} & set(sense.get('tags') or [])]
            if reflexive:
                lemmas.append((key + '-se', pos, english_glosses(entry, senses=reflexive), None, len(reflexive),
                               word + '-se', valency_of(reflexive)))
        for f in entry.get('forms', []):
            tags = set(f.get('tags') or [])
            form = f.get('form', '')
            if not form or tags & SKIP_FORM_TAGS or form.startswith(('-', '/', '[')) or '/' in form or len(form) > 40 or ' ' in form:
                continue
            kept = sorted(tags & FORM_TAGS)
            if kept:
                forms.add((word, pos, form.lower(), ','.join(kept)))
        if n % 200000 == 0:
            print('  %d lines, %d entries, %d forms (%.0fs)' % (n, len(lemmas), len(forms), time.time() - t0),
                  file=sys.stderr)
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?, ?, ?)', lemmas)
    db.executemany('INSERT OR IGNORE INTO forms VALUES (?, ?, ?, ?)', sorted(forms))
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX forms_form ON forms (form);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries, %d forms → %s (%.1fs)' % (len(lemmas), len(forms), out, time.time() - t0))


if __name__ == '__main__':
    main()
