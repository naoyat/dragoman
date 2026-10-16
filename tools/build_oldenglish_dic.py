#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の辞書 (SQLite) を Wiktionary (kaikki.org の抽出データ) から作る
#
#   python3 tools/build_oldenglish_dic.py [FILE.jsonl [OUT.sqlite]]
#
# 入力: kaikki.org-dictionary-OldEnglish.jsonl (https://kaikki.org/dictionary/Old%20English/。CC BY-SA)
# 出力: $DRAGOMAN_DATA/ang/wiktionary.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#   lemmas (id, key, pos, info): 見出し語ごとの品詞・見出し (長音符付き)・英語の語義・名詞の性・動詞の強弱と類・
#     比較級の見出しの原級 (betera ← gōd)
#   forms (key, lemma_id, features): 語形 (oldenglish/orthography.key の鍵) → 見出し・格・数・性 / 法・時制・人称・数。
#     形容詞は強変化・弱変化 (decl) と比較級・最上級 (rank '+' / '++'。原級の項目の strengra から変化した形も作る)
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


ALL3 = ('m', 'f', 'n')


def _cng(cases, numbers, genders=ALL3):
    return [(c, n, g) for c in cases for n in numbers for g in genders]


# 比較級は弱変化 (strengra・strengre・strengran …)、最上級は強変化と弱変化 (strenġest・strenġestne・se strenġesta …)
COMPARATIVE_ENDINGS = (
    ('a', [('Nom', 'sg', 'm')]), ('e', [('Nom', 'sg', 'f'), ('Nom', 'sg', 'n'), ('Acc', 'sg', 'n')]),
    ('an', [('Acc', 'sg', 'm'), ('Acc', 'sg', 'f')] + _cng(('Gen', 'Dat', 'Ins'), ('sg',)) + _cng(('Nom', 'Acc'), ('pl',))),
    ('ena', _cng(('Gen',), ('pl',))), ('ra', _cng(('Gen',), ('pl',))), ('um', _cng(('Dat',), ('pl',))),
)
SUPERLATIVE_ENDINGS = (
    ('', _cng(('Nom',), ('sg',)) + [('Acc', 'sg', 'n'), ('Nom', 'pl', 'n'), ('Acc', 'pl', 'n')]),
    ('ne', [('Acc', 'sg', 'm')]), ('e', [('Acc', 'sg', 'f'), ('Ins', 'sg', 'm'), ('Ins', 'sg', 'n'), ('Nom', 'pl', 'm'),
                                       ('Acc', 'pl', 'm')]),
    ('es', [('Gen', 'sg', 'm'), ('Gen', 'sg', 'n')]), ('re', [('Gen', 'sg', 'f'), ('Dat', 'sg', 'f')]),
    ('um', [('Dat', 'sg', 'm'), ('Dat', 'sg', 'n')] + _cng(('Dat',), ('pl',))), ('ra', _cng(('Gen',), ('pl',))),
    ('a', [('Nom', 'sg', 'm'), ('Nom', 'pl', 'f'), ('Acc', 'pl', 'f')]),
    ('an', [('Acc', 'sg', 'm'), ('Acc', 'sg', 'f')] + _cng(('Gen', 'Dat', 'Ins'), ('sg',)) + _cng(('Nom', 'Acc'), ('pl',))),
)


def degree_forms(form, rank):
    """比較級 (rank '+'、主格男性単数の -a / -ra の形) ・最上級 ('++'、-est / -ost の形) → [(語形, features)]"""
    if rank == '+':
        if not form.endswith('a'):
            return []
        stem = form[:-1]
        return [(stem + e, {'_': cng, 'rank': '+'}) for e, cng in COMPARATIVE_ENDINGS]
    stem = form[:-1] if form.endswith(('a', 'e')) else form
    return [(stem + e, {'_': cng, 'rank': '++'}) for e, cng in SUPERLATIVE_ENDINGS]


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
        cng, decls = nominal.setdefault((k, lemma_id, surface, features.get('rank'), bool(features.get('alt'))),
                                        ([], set()))
        for c, n, g in features['_']:
            for g2 in ([g] if g else genders):
                if (c, n, g2) not in cng:
                    cng.append((c, n, g2))
        decls.update(d for d in (features.get('decl') or '').split(',') if d)
    for (k, lemma_id, surface, rank, alt), (cng, decls) in nominal.items():
        if any(g for c, n, g in cng):
            cng = [x for x in cng if x[2] or not any(y[:2] == x[:2] and y[2] for y in cng)]
        merged = {'_': cng}
        if alt:
            merged['alt'] = True
        if rank:
            merged['rank'] = rank
        if decls:
            merged['decl'] = ','.join(sorted(decls))   # 強変化・弱変化 (どちらの形でもあれば両方)
        out[(k, lemma_id, json.dumps(merged, ensure_ascii=False))] = surface
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
                if pos == 'adj' and tags & {'comparative', 'superlative'}:
                    rank = '+' if 'comparative' in tags else '++'   # māra「より多い」(miċel の比較級)
                    feats = [dict(x, rank=rank) for x in feats]
                    if not any(x.get('_') for x in feats):
                        for f2, x in degree_forms(word, rank):
                            form_of.append((f2, target, pos, x))
                        continue
                elif pos == 'adj' and tags & {'strong', 'weak'}:
                    feats = [dict(x, decl=','.join(sorted(tags & {'strong', 'weak'}))) for x in feats]
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
        positive = next((f['form'] for f in entry.get('forms', []) if 'positive' in (f.get('tags') or [])), None)
        if pos == 'adj' and positive:   # 比較級・最上級の見出し (betera ← gōd)
            info.update(positive=positive, rank='++' if base.endswith(('est', 'ost', 'esta', 'osta')) else '+')
        lemma_id = len(lemmas) + 1
        lemmas.append((key(base), pos, info))
        by_key.setdefault((key(base), pos), []).append(lemma_id)
        if key(word) != key(base):
            by_key.setdefault((key(word), pos), []).append(lemma_id)
        if pos == 'verb':
            table = verb_table(entry) or [(base, {'mood': 'infinitive', 'tense': 'present'})]
        elif pos in NOMINAL:
            table = []
            strength = None
            for f in entry.get('forms', []):
                tags = set(f.get('tags') or [])
                form = f.get('form', '').strip()
                if 'table-tags' in tags and form in ('strong', 'weak'):
                    strength = form   # 形容詞の変化表の段 (強変化・弱変化)
                    continue
                if pos == 'adj' and tags & {'comparative', 'superlative'} and ' ' not in form and form:
                    table += degree_forms(form, '+' if 'comparative' in tags else '++')
                    continue
                if form and form not in ('-', '—') and not tags & SKIP_FORM_TAGS and ' ' not in form \
                        and 'alternative' not in tags:
                    feats = nominal_features(tags, genders or ['m', 'f', 'n'])
                    if pos == 'adj' and strength:
                        feats = [dict(x, decl=strength) for x in feats]
                    table += [(form, x) for x in feats]
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
    for word, target, pos, x in form_of:   # 変化形だけの項目の形 (方言の seh・sæh も) は、生成では見出しの表の形の後に
        for lemma_id in by_key.get((key(target), pos), ()):
            forms.append((word, lemma_id, dict(x, alt=True)))
    rows = {}
    for f, lemma_id, x in forms:
        rows.setdefault((key(f), lemma_id, json.dumps(x, ensure_ascii=False, sort_keys=True)), f)
        if '-' in f:   # ハイフンの入った見出し (Gār-Dene) は、ハイフンを除いた綴り (Gārdena) でも引けるように
            rows.setdefault((key(f).replace('-', ''), lemma_id, json.dumps(x, ensure_ascii=False, sort_keys=True)), f)
    by_form = {}
    for (k, lemma_id, x) in rows:
        by_form.setdefault(k, []).append((lemma_id, x))
    for word, target, pos in alt_of:   # 異綴りは元の語の同じ形の読みを写す (別の項目のある語は除く)
        k = key(word)
        for lemma_id, x in by_form.get(key(target), ()):
            alt = json.dumps(dict(json.loads(x), alt=True), ensure_ascii=False, sort_keys=True)   # 生成では後に
            if lemmas[lemma_id - 1][1] == pos and (k, lemma_id, x) not in rows and (k, lemma_id, alt) not in rows:
                rows[(k, lemma_id, alt)] = word
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
    db.executescript('CREATE INDEX lemmas_key ON lemmas (key); CREATE INDEX forms_key ON forms (key); '
                     'CREATE INDEX forms_lemma ON forms (lemma_id);')   # 見出し → 語形 (生成で)
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d lemmas, %d forms → %s (%.1fs)' % (len(lemmas), len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
