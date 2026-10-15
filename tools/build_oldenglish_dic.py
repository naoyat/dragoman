#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_oldenglish_dic.py [FILE.jsonl [OUT.sqlite]]
#
# 入力: kaikki.org-dictionary-OldEnglish.jsonl (https://kaikki.org/dictionary/Old%20English/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/ang/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#   lemmas (id, key, pos, info): 見出し語ごとの品詞・見出し (長音符付き)・英語の語義・名詞の性・動詞の強弱と類
#   forms (key, lemma_id, features): 語形 (oldenglish/orthography.key の鍵) → 見出し・格・数・性 / 法・時制・人称・数
#
# 語形は見出しの変化表と、「inflection of ābīdan」のような変化形だけの項目の語義の印から集める。変化表の動詞の
# 段は直説法と接続法の印が無いので並びで分ける (人称の付いた形は直説法、人称の無い単数の形の後は接続法)。
# 異綴り (alternative form of 〜、変化表の alternative) は元の語の同じ形の読みを写す
#
import os
import re
import sys
import json
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.core.wiktionary_import import english_glosses, canonical
from dragoman.oldenglish.orthography import key

POS = {'noun': 'noun', 'name': 'noun', 'adj': 'adj', 'det': 'adj', 'num': 'adj', 'pron': 'pronoun',
       'article': 'article', 'verb': 'verb', 'adv': 'adv', 'conj': 'conj', 'prep': 'preposition',
       'intj': 'indecl', 'particle': 'conj'}
NOMINAL = ('noun', 'adj', 'pronoun', 'article')
CASES = {'nominative': 'Nom', 'accusative': 'Acc', 'genitive': 'Gen', 'dative': 'Dat', 'instrumental': 'Ins'}
NUMBERS = {'singular': 'sg', 'plural': 'pl', 'dual': 'du'}
GENDERS = {'masculine': 'm', 'feminine': 'f', 'neuter': 'n'}
PERSONS = {'first-person': 1, 'second-person': 2, 'third-person': 3}
SKIP_FORM_TAGS = {'canonical', 'table-tags', 'inflection-template', 'class', 'romanization', 'personal'}
RARE = {'rare', 'misspelling', 'nonstandard'}


def _genders(entry):
    for head in entry.get('head_templates', []):
        m = re.match(r'\S+ ((?:[mfn](?: or |, | ))*[mfn])\b', head.get('expansion', ''))
        if m:
            return re.findall(r'[mfn]', m.group(1))
    tags = {t for s in entry.get('senses', []) for t in s.get('tags') or []}
    return [g for t, g in GENDERS.items() if t in tags]


def _verb_class(entry):
    """強変化・弱変化と類 (strong III、weak 2)"""
    kind = cls = None
    for f in entry.get('forms', []):
        tags = f.get('tags') or []
        if 'table-tags' in tags and f['form'] in ('strong', 'weak', 'irregular', 'preterite-present', 'anomalous'):
            kind = kind or f['form']
        if 'class' in tags:
            cls = cls or f['form']
    return ' '.join(x for x in (kind, cls) if x) or None


def nominal_features(tags, default_genders, default_numbers=('sg',)):
    cases = [c for t, c in CASES.items() if t in tags]
    if not cases:
        return []
    numbers = [n for t, n in NUMBERS.items() if t in tags] or list(default_numbers)
    genders = [g for t, g in GENDERS.items() if t in tags] or list(default_genders) or [None]
    return [{'_': [(c, n, g) for c in cases for n in numbers for g in genders]}]


def verb_features(tags, mood=None):
    """語義・変化表の印 → [{mood, tense, person, number}]"""
    tense = 'perfect' if tags & {'past', 'preterite'} else 'present'
    if 'participle' in tags:
        return [{'mood': 'participle', 'tense': 'past' if tense == 'perfect' else 'present'}]
    if 'infinitive' in tags:
        return [{'mood': 'infinitive', 'tense': 'present', 'inflected': True} if 'inflected' in tags
                else {'mood': 'infinitive', 'tense': 'present'}]
    mood = mood or next((m for m in ('imperative', 'subjunctive', 'indicative') if m in tags), 'indicative')
    numbers = [n for t, n in NUMBERS.items() if t in tags]
    if not numbers:
        return []
    persons = [p for t, p in PERSONS.items() if t in tags] or ([2] if mood == 'imperative' else [1, 2, 3])
    return [{'mood': mood, 'tense': tense if mood != 'imperative' else 'present', 'person': p, 'number': n}
            for p in persons for n in numbers]


def verb_table(entry):
    """変化表の動詞の段 → [(語形, features)]。並び: 不定詞 2つ、直説法 (人称の付いた単数、人称の無い複数)、
    接続法 (人称の無い単数・複数)、命令法 (imperative + 数)、分詞 (imperative + present / past、数の無いもの)"""
    out = []
    subjunctive = False
    for f in entry.get('forms', []):
        tags = set(f.get('tags') or [])
        form = f.get('form', '').strip()
        if not form or form in ('-', '—') or tags & SKIP_FORM_TAGS or 'alternative' in tags or ' ' in form:
            continue
        persons = tags & set(PERSONS)
        numbers = tags & set(NUMBERS)
        if 'infinitive' in tags:
            features = verb_features(tags | ({'inflected'} if form.endswith(('enne', 'anne')) else set()))
        elif 'imperative' in tags and numbers:
            features = verb_features(tags - {'past'}, 'imperative')
        elif 'imperative' in tags:
            features = verb_features((tags - {'imperative'}) | {'participle'})
        elif persons:
            features = verb_features(tags, 'indicative')
        elif numbers:
            if 'singular' in numbers:
                subjunctive = True
            features = verb_features(tags, 'subjunctive' if subjunctive else 'indicative')
        else:
            continue
        out += [(form, x) for x in features]
    return out


def merge(rows, lemmas):
    """同じ語形・同じ見出しの格の読みを1つの行に (性の無い読みは見出しの性で埋める)"""
    nominal, out = {}, {}
    for (k, lemma_id, x), surface in rows.items():
        features = json.loads(x)
        if '_' not in features:
            out[(k, lemma_id, x)] = surface
            continue
        gender = lemmas[lemma_id - 1][2].get('gender')
        genders = gender.split(',') if gender else [None]
        cng = nominal.setdefault((k, lemma_id, surface), [])
        for c, n, g in features['_']:
            for g2 in ([g] if g else genders):
                if (c, n, g2) not in cng:
                    cng.append((c, n, g2))
    for (k, lemma_id, surface), cng in nominal.items():
        if any(g for c, n, g in cng):
            cng = [x for x in cng if x[2] or not any(y[:2] == x[:2] and y[2] for y in cng)]
        out[(k, lemma_id, json.dumps({'_': cng}, ensure_ascii=False))] = surface
    return out


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('ang', 'kaikki.org-dictionary-OldEnglish.jsonl')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('ang', 'wiktionary.sqlite')
    lemmas = []                 # (key, pos, info)
    by_key = {}                 # (鍵, 品詞) → [lemma_id]
    forms = []                  # (語形, lemma_id, features)
    form_of = []                # (語形, 元の語, 品詞, features) — 後で元の語の id に
    alt_of = []                 # (異綴り, 元の語, 品詞)
    for line in open(source, encoding='utf-8'):
        entry = json.loads(line)
        if entry.get('lang_code') != 'ang':
            continue
        pos = POS.get(entry.get('pos'))
        word = entry.get('word', '')
        if pos is None or not word or word.startswith('-') or word.endswith('-'):
            continue
        genders = _genders(entry) if pos == 'noun' else []
        senses = []
        for sense in entry.get('senses', []):
            tags = set(sense.get('tags') or [])
            if tags & RARE:
                continue
            if sense.get('form_of'):
                target = sense['form_of'][0].get('word', '')
                feats = verb_features(tags) if pos == 'verb' else \
                    nominal_features(tags, genders or ([] if pos == 'noun' else ['m', 'f', 'n'])) \
                    if pos in NOMINAL else [{}]
                for x in feats:
                    form_of.append((word, target, pos, x))
                continue
            if sense.get('alt_of'):
                alt_of.append((word, sense['alt_of'][0].get('word', ''), pos))
                continue
            if sense.get('glosses'):
                senses.append(sense)
        if not senses:
            continue
        base = canonical(entry)
        info = {'pos': pos, 'base': base, 'en': english_glosses(entry, senses), 'senses': len(senses)}
        if entry.get('pos') == 'name':
            info['proper'] = True
        if genders:
            info['gender'] = ','.join(genders)
        if pos == 'verb':
            info['class'] = _verb_class(entry)
        lemma_id = len(lemmas) + 1
        lemmas.append((key(base), pos, info))
        by_key.setdefault((key(base), pos), []).append(lemma_id)
        if key(word) != key(base):
            by_key.setdefault((key(word), pos), []).append(lemma_id)
        if pos == 'verb':
            table = verb_table(entry) or [(base, {'mood': 'infinitive', 'tense': 'present'})]
        elif pos in NOMINAL:
            table = []
            for f in entry.get('forms', []):
                tags = set(f.get('tags') or [])
                form = f.get('form', '').strip()
                if form and form not in ('-', '—') and not tags & SKIP_FORM_TAGS and ' ' not in form \
                        and 'alternative' not in tags:
                    table += [(form, x) for x in nominal_features(tags, genders or ['m', 'f', 'n'])]
            if not table:   # 変化表の無い語 (固有名詞・数詞など): 見出しの形をどの格にも
                table = [(base, {'_': [(c, 'sg', g) for c in ('Nom', 'Acc', 'Gen', 'Dat')
                                       for g in (genders or [None])]})]
        else:
            table = [(base, {})]
        forms += [(f, lemma_id, x) for f, x in table]
        for f in entry.get('forms', []):   # 変化表の異綴り (cing・cining → cyning): 見出しの形の読み
            if 'alternative' in (f.get('tags') or []) and ' ' not in f.get('form', ''):
                alt_of.append((f['form'], base, pos))
    print('%d lemmas, %d table forms, %d form-of, %d alt-of (%.0fs)' %
          (len(lemmas), len(forms), len(form_of), len(alt_of), time.time() - t0), file=sys.stderr)
    for word, target, pos, x in form_of:
        for lemma_id in by_key.get((key(target), pos), ()):
            forms.append((word, lemma_id, x))
    rows = {}
    for f, lemma_id, x in forms:
        rows.setdefault((key(f), lemma_id, json.dumps(x, ensure_ascii=False, sort_keys=True)), f)
    by_form = {}
    for (k, lemma_id, x) in rows:
        by_form.setdefault(k, []).append((lemma_id, x))
    for word, target, pos in alt_of:   # 異綴りは元の語の同じ形の読みを写す (別の項目のある語は除く)
        k = key(word)
        for lemma_id, x in by_form.get(key(target), ()):
            if lemmas[lemma_id - 1][1] == pos and (k, lemma_id, x) not in rows:
                rows[(k, lemma_id, x)] = word
    rows = merge(rows, lemmas)
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE lemmas (id INTEGER PRIMARY KEY, key TEXT, pos TEXT, info TEXT);
        CREATE TABLE forms (key TEXT, surface TEXT, lemma_id INTEGER, features TEXT);
    ''')
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?)',
                   [(i + 1, k, p, json.dumps(info, ensure_ascii=False)) for i, (k, p, info) in enumerate(lemmas)])
    db.executemany('INSERT INTO forms VALUES (?, ?, ?, ?)',
                   sorted((k, surface, lemma_id, x) for (k, lemma_id, x), surface in rows.items()))
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX forms_key ON forms (key);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d lemmas, %d forms → %s (%.1fs)' % (len(lemmas), len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
