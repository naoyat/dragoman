#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_german_dic.py [FILE.jsonl | -]
#   curl -sL https://kaikki.org/dictionary/German/kaikki.org-dictionary-German.jsonl | python3 tools/build_german_dic.py -
#
# 元のデータは約 1.1GB あるので、標準入力から読んで必要なものだけを残せる (元のファイルを置かなくてよい)。
# 見出し語ごとの品詞・訳語 (英語の語義。日本語には実行時に core/en_ja.py で直す)・名詞の性・動詞の完了の助動詞
# (haben / sein)・分離動詞の前つづり、語形の表 (語形 → 見出し語・品詞・印 (格・数・人称・時制 …))。
# 「plural of 〜」「past participle of 〜」のような語義だけの項目は、語形の表に入れる。
#
# 入力: kaikki.org-dictionary-German.jsonl (https://kaikki.org/dictionary/German/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/de/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
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
       'postp': 'preposition', 'intj': 'intj', 'article': 'article', 'contraction': 'contraction'}
# 語形の印のうち残すもの
FORM_TAGS = {'nominative', 'accusative', 'dative', 'genitive', 'singular', 'plural', 'masculine', 'feminine', 'neuter',
             'first-person', 'second-person', 'third-person', 'present', 'past', 'preterite', 'subjunctive-i',
             'subjunctive-ii', 'subjunctive', 'indicative', 'imperative', 'infinitive', 'participle', 'strong', 'weak',
             'mixed', 'comparative', 'superlative', 'predicative', 'definite', 'indefinite', 'without-article',
             'zu-infinitive', 'dependent', 'positive'}
SKIP_FORM_TAGS = {'table-tags', 'inflection-template', 'class', 'diminutive', 'auxiliary', 'error-unrecognized-form',
                  'romanization', 'obsolete', 'archaic', 'dialectal', 'rare', 'nonstandard', 'misspelling'}
FORM_OF = re.compile(r'^(?:(?:(?:nominative|accusative|dative|genitive|strong|weak|mixed|definite|indefinite|'
                     r'masculine|feminine|neuter|singular|plural|first|second|third|person|present|past|preterite|'
                     r'subjunctive|indicative|imperative|participle|comparative|superlative|inflection|form|degree|'
                     r'and|the|[/,-]|I|II|\s)+)) of ([^\s,;:()]+)', re.I)
ALT_OF = re.compile(r'^(?:alternative (?:form|spelling)|obsolete (?:form|spelling)|archaic (?:form|spelling)|'
                    r'superseded spelling|dated (?:form|spelling)|nonstandard (?:form|spelling)|'
                    r'(?:pre-1996|pre-reform) spelling) of ([^\s,;:()]+)', re.I)
# 派生語の語義で、後ろに定義が付いているもの (agent noun of lehren: one who teaches, teacher。
# agent noun of fahren; driver (person)。gerund of essen; eating。diminutive of …)
DERIVED_OF = re.compile(r'^[^:;]* of [^\s:;]+[:;]\s*(\S.*)$')


def gender_of(entry):
    """名詞の性: 見出しのテンプレートの最初の引数 (n,,^er → n。m,es → m。複数だけの名詞は p)"""
    for head in entry.get('head_templates', []):
        first = (head.get('args') or {}).get('1', '')
        g = re.split('[,:<]', first)[0].strip()
        if g in ('m', 'f', 'n', 'p'):
            return g
    for sense in entry.get('senses', []):
        for t in sense.get('tags') or []:
            if t in ('masculine', 'feminine', 'neuter'):
                return t[0]
    return None


def auxiliary_of(entry):
    """完了の助動詞 (gehen<ging,gegangen.sein> → sein)"""
    auxes = {f['form'] for f in entry.get('forms', []) if 'auxiliary' in (f.get('tags') or [])}
    if auxes == {'sein'}:
        return 'sein'
    if 'haben' in auxes and 'sein' in auxes:
        return 'haben,sein'
    return 'haben' if auxes else None


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('de', 'kaikki.org-dictionary-German.jsonl')
    out = paths.data('de', 'wiktionary.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE lemmas (key TEXT, pos TEXT, en TEXT, gender TEXT, aux TEXT, senses INTEGER, word TEXT);
        CREATE TABLE forms (form TEXT, lemma TEXT, pos TEXT, tags TEXT);
    ''')
    # 語形は見出しの活用表のものを先に、「past participle of loben」のような語義だけの項目のものを後に、取れた順で入れる
    # (loben の過去分詞は活用表の gelobt。語義だけの項目の gelobet を先にしない)
    lemmas, forms, form_of = [], {}, {}
    stream = sys.stdin if source == '-' else open(source, encoding='utf-8')
    n = 0
    for line in stream:
        n += 1
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get('lang_code') != 'de':
            continue
        pos = POS.get(entry.get('pos'))
        word = entry.get('word', '')
        if pos is None or not word or ' ' in word.strip() and pos != 'verb':
            continue
        senses = []
        for sense in entry.get('senses', []):
            gloss = (sense.get('glosses') or [''])[0]
            m = FORM_OF.match(gloss) or ALT_OF.match(gloss)
            definition = DERIVED_OF.match(gloss)
            if not m and definition and 'form-of' in (sense.get('tags') or []):
                # 派生語 (agent noun of lehren: one who teaches, teacher → Lehrer) は語形ではなく、定義を語義にする
                senses.append(dict(sense, glosses=[definition.group(1)]))
                if 'participle' not in gloss.split(' of ')[0]:
                    continue
                # 分詞 (perfect participle of anfixen; hooked) は語形の表にも入れる
            if m or 'form-of' in (sense.get('tags') or []):
                target = m.group(1) if m else ((sense.get('form_of') or [{}])[0].get('word') or '')
                if target:
                    tags = sorted(t for t in (sense.get('tags') or []) if t in FORM_TAGS)
                    form_of[(word, target, pos, ','.join(tags))] = None
                continue
            if gloss:
                senses.append(sense)
        if not senses:
            continue
        en = english_glosses(entry, senses=senses)
        lemmas.append((word.lower(), pos, en, gender_of(entry) if pos in ('noun', 'name') else None,
                       auxiliary_of(entry) if pos == 'verb' else None, len(senses), word))
        for f in entry.get('forms', []):
            tags = set(f.get('tags') or [])
            form = f.get('form', '')
            if not form or tags & SKIP_FORM_TAGS or form.startswith('-') or len(form) > 40:
                continue
            kept = sorted(tags & FORM_TAGS)
            if kept:
                forms[(form, word, pos, ','.join(kept))] = None
        if n % 200000 == 0:
            print('  %d lines, %d entries, %d forms (%.0fs)' % (n, len(lemmas), len(forms), time.time() - t0),
                  file=sys.stderr)
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?, ?, ?)', lemmas)
    rows = [(f.lower(), l, p, t) for f, l, p, t in list(forms) + [x for x in form_of if x not in forms]]
    db.executemany('INSERT INTO forms VALUES (?, ?, ?, ?)', rows)
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX forms_form ON forms (form);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries, %d forms → %s (%.1fs)' % (len(lemmas), len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
