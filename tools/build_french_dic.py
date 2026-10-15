#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_french_dic.py [FILE.jsonl | -] [OUT.sqlite]   (OUT を省くと $DRAGOMAN_DATA/fr/wiktionary.sqlite)
#   curl -sL https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl | python3 tools/build_french_dic.py -
#
# 元のデータは約 580MB あるので、標準入力から読んで必要なものだけを残せる (元のファイルを置かなくてよい)。
# 見出し語ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)・名詞の性・動詞の語義の印 (他動・自動・
# 再帰と à を取るか。人を表す接語の格を決めるのに使う)、
# 語形の表 (見出し語・品詞 → 語形・印 (数・性・人称・法・時制))。動詞は単純時制の形だけ (複合時制は avoir / être + 過去分詞で作る)。
# 「plural of 〜」「feminine of 〜」のような語義だけの項目は、語形の表に入れる。
# 語形の表は見出し順に並べて持つ (WITHOUT ROWID。tools/shrink_dic.py と同じ形) + 語形の索引
#
# 入力: kaikki.org-dictionary-French.jsonl (https://kaikki.org/dictionary/French/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/fr/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
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
# 語形の印のうち残すもの
FORM_TAGS = {'singular', 'plural', 'masculine', 'feminine', 'first-person', 'second-person', 'third-person',
             'present', 'imperfect', 'past', 'historic', 'future', 'conditional', 'subjunctive', 'indicative',
             'imperative', 'infinitive', 'participle', 'gerund', 'comparative', 'superlative'}
SKIP_FORM_TAGS = {'table-tags', 'inflection-template', 'class', 'auxiliary', 'error-unrecognized-form', 'romanization',
                  'obsolete', 'archaic', 'dialectal', 'rare', 'nonstandard', 'misspelling', 'multiword-construction',
                  'perfect', 'pluperfect', 'anterior', 'error-misspelling'}
FORM_OF = re.compile(r'^(?:(?:(?:masculine|feminine|singular|plural|first|second|third|person|present|imperfect|'
                     r'past|historic|future|conditional|subjunctive|indicative|imperative|participle|inflection|'
                     r'form|and|the|[/,-]|\s)+)) of ([^\s,;:()]+)', re.I)
ALT_OF = re.compile(r'^(?:alternative (?:form|spelling)|obsolete (?:form|spelling)|archaic (?:form|spelling)|'
                    r'dated (?:form|spelling)|nonstandard (?:form|spelling)|pre-1990 spelling) of ([^\s,;:()]+)',
                    re.I)


def gender_of(entry):
    """名詞の性: 見出しのテンプレートの引数 (fr-noun|m → m、f → f、mf → mf) か語義の印"""
    for head in entry.get('head_templates', []):
        args = head.get('args') or {}
        g = re.split('[,<-]', (args.get('1') or args.get('g') or '').strip())[0]
        if g in ('m', 'f', 'mf', 'mfbysense'):
            return 'mf' if g.startswith('mf') else g
    for t in entry.get('tags') or []:
        if t in ('masculine', 'feminine'):
            return t[0]
    for sense in entry.get('senses', []):
        for t in sense.get('tags') or []:
            if t in ('masculine', 'feminine'):
                return t[0]
    return None


VALENCY_TAGS = ('transitive', 'intransitive', 'ambitransitive', 'reflexive', 'pronominal', 'impersonal', 'ditransitive')
TO_SOMEONE = re.compile(r"\b(?:something|sth\.?|it|them|one's \w+) to (?:someone|somebody|sb\b|another)|\bto someone else", re.I)
WITH_A = re.compile(r"\[with à|\(\+ à|with à\b|à qqn|à quelqu'un|indirect object", re.I)


def valency_of(senses):
    """動詞の語義の印 (最初の3つの語義): transitive・intransitive・reflexive … と、à を取るか ('à'。「[with à ‘to’]」)。
    語義ごとに ';' で区切る (例: 'transitive,à;intransitive')"""
    out = []
    for sense in senses[:3]:
        tags = [t for t in (sense.get('tags') or []) if t in VALENCY_TAGS]
        raw = ' '.join(sense.get('raw_glosses') or sense.get('glosses') or [])
        if WITH_A.search(raw):
            tags.append('à')
        if TO_SOMEONE.search(raw):
            tags.append('to-someone')   # to grant (something to someone)、to give … to someone else
        out.append(','.join(tags))
    return ';'.join(out)


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('fr', 'kaikki.org-dictionary-French.jsonl')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('fr', 'wiktionary.sqlite')   # 試すときは別の出力先に
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
        if entry.get('lang_code') != 'fr':
            continue
        pos = POS.get(entry.get('pos'))
        word = entry.get('word', '')
        if pos is None or not word or ' ' in word.strip() and pos not in ('verb', 'preposition', 'conj', 'adv'):
            continue
        senses = []
        for sense in entry.get('senses', []):
            gloss = (sense.get('glosses') or [''])[0]
            m = FORM_OF.match(gloss) or ALT_OF.match(gloss)
            if m or 'form-of' in (sense.get('tags') or []):
                target = m.group(1) if m else ((sense.get('form_of') or [{}])[0].get('word') or '')
                if target:
                    tags = sorted(t for t in (sense.get('tags') or []) if t in FORM_TAGS)
                    forms.add((target, pos, word.lower(), ','.join(tags)))
                continue
            if gloss:
                senses.append(sense)
        if not senses:
            continue
        en = english_glosses(entry, senses=senses)
        key = word.lower()
        if pos == 'verb' and key.startswith(("s'", 'se ')):
            key = 'se ' + key[2:].lstrip()   # 代名動詞の見出し (s'appeler → se appeler)
        lemmas.append((key, pos, en, gender_of(entry) if pos in ('noun', 'name') else None, len(senses), word,
                       valency_of(senses) if pos == 'verb' else None))
        if pos == 'verb' and not key.startswith('se '):
            # 再帰・代名動詞の語義 ((reflexive) to get up) は「se + 動詞」の見出しにも (se lever「起きる」)
            reflexive = [sense for sense in senses if {'reflexive', 'pronominal'} & set(sense.get('tags') or [])]
            if reflexive:
                lemmas.append(('se ' + key, pos, english_glosses(entry, senses=reflexive), None, len(reflexive),
                               'se ' + word, valency_of(reflexive)))
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
