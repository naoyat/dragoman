#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語 → 日本語の訳語の表 (SQLite) を、日本語版 Wiktionary の英語の項目 (ja-extract) と JMdict (和英辞典を逆に引く) から作る
#
#   python3 tools/build_en_ja.py
#
# 各言語の辞書で日本語の訳語が無く英語の語義 (Wiktionary・CAMeL Tools など) になっている語を、共通部分
# (core/en_ja.py) で日本語に置き換えるのに使う。品詞 (名詞・動詞・形容詞・副詞) ごとに、整えた訳語を最大4つ持つ。
#
# 入力: $DRAGOMAN_DATA/ja-extract.jsonl.gz (日本語版 Wiktionary の抽出)
#       $DRAGOMAN_DATA/JMdict_e.gz (任意。http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz、EDRDG、CC BY-SA 4.0)
# 出力: $DRAGOMAN_DATA/en-ja.sqlite (データは Wiktionary・JMdict 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#
# 動詞は JMdict の英訳の書き込みから、場面の語ごとの訳語 (verb_context: to pass (examination) → 受かる) と句動詞の訳語
# (phrasal: give up → あきらめる) の表も作る (core/en_ja.verb_in_context・phrasal)。
# 訳語のよく使う度合いの表 (common: JMdict の news1・ichi1 … と nf) も作る (core/en_ja.lookup が訳語の順を決めるのに使う)。
# Wiktionary の表を先に使い、そこに無い英語の語句を JMdict で補う。JMdict は、よく使う語の印 (news1, ichi1 …) の
# ある見出し語を、英語の訳がその語義の先頭にあるものから並べる
#
import os
import sys
import gzip
import json
import sqlite3
import re
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import en_ja, paths
from dragoman.core.wiktionary_import import japanese_gloss

POS = {'noun': 'noun', 'verb': 'verb', 'adj': 'adj', 'adv': 'adv', 'name': 'name', 'phrase': 'phrase'}


PRIORITY = {'news1': 3, 'ichi1': 3, 'spec1': 3, 'gai1': 2, 'news2': 2, 'ichi2': 2, 'spec2': 2}


def jmdict_pos(pos_texts):
    """JMdict の品詞の説明 → [(品詞, 見出し語に付ける語尾)]"""
    out = []
    for p in pos_texts:
        if 'Godan verb' in p or 'Ichidan verb' in p or 'Kuru verb' in p:
            out.append(('verb', ''))
        elif 'suru verb' in p and 'included' not in p:
            out.append(('verb', 'する'))   # サ変名詞 (勉強 → 勉強する)
        elif 'adjective (keiyoushi)' in p:
            out.append(('adj', ''))
        elif 'keiyodoshi' in p:
            out.append(('adj', 'な'))      # 形容動詞 (静か → 静かな)
        elif p.startswith('noun') or 'noun (common)' in p:
            out.append(('noun', ''))
        elif p.startswith('adverb'):
            out.append(('adv', ''))
    return out


def jmdict_rows(path):
    """JMdict → {(英語, 品詞): [(点数, 日本語)]}"""
    found = {}
    for _, entry in ET.iterparse(path):
        if entry.tag != 'entry':
            continue
        kebs = [(k.findtext('keb'), [p.text for p in k.findall('ke_pri')]) for k in entry.findall('k_ele')]
        rebs = [(r.findtext('reb'), [p.text for p in r.findall('re_pri')]) for r in entry.findall('r_ele')]
        senses = entry.findall('sense')
        kana_usually = any('usually written using kana' in (m.text or '') for s in senses for m in s.findall('misc'))
        heads = (rebs if kana_usually or not kebs else kebs)
        word, pri = heads[0]
        priority = max([PRIORITY.get(p, 0) for p in pri] or [0])
        # 頻度の順位 (nf01〜nf48。小さいほどよく使う)
        nf = min([int(p[2:]) for p in pri if p.startswith('nf')] or [49])
        if priority == 0:
            entry.clear()
            continue
        pos_texts = []
        for k, sense in enumerate(senses[:3]):
            pos_texts = [p.text for p in sense.findall('pos')] or pos_texts  # 品詞の無い語義は前の語義の品詞
            for pos, suffix in jmdict_pos(pos_texts):
                for g, gloss in enumerate(sense.findall('gloss')):
                    english = re.sub(r'\s*\([^)]*\)', '', gloss.text or '').strip().lower()
                    if pos == 'verb':
                        english = re.sub('^to ', '', english)
                    if not english or len(english.split()) > 3:
                        continue
                    score = priority * 10 - k * 3 - g - len(word) * 0.1 - nf * 0.2
                    found.setdefault((english, pos), []).append((score, word + suffix))
                    head = english.split()[-1]
                    if head != english and pos == 'noun':
                        # 複数語の英訳は末尾の語でも引く (大臣 cabinet minister → minister)
                        found.setdefault((head, pos), []).append((score - 1, word + suffix))
        entry.clear()
    return found


PARTICLES = {'up', 'down', 'out', 'off', 'away', 'back', 'in', 'on', 'over', 'through', 'around', 'along', 'by',
             'into', 'about', 'after', 'for', 'with', 'at', 'to', 'from', 'apart', 'forward', 'together'}
CONTEXT_STOP = {'a', 'an', 'the', 'of', 'e.g', 'eg', 'etc', 'esp', 'one', "one's", 'someone', "someone's", 'something',
                'oneself', 'in', 'ref', 'to', 'and', 'or', 'with', 'for', 'on', 'at', 'by', 'from', 'as', 'be', 'is',
                'it', 'its', 'into', 'about', 'other', 'others', 'such', 'person', 'thing', 'things', 'etc.', 'usu',
                'also', 'very', 'some', 'not', 'that', 'this', 'which', 'when', 'like', 'way', 'one\'s'}


def _singular(word):
    if len(word) > 4 and word.endswith('ies'):
        return word[:-3] + 'y'
    if len(word) > 3 and word.endswith('s') and not word.endswith('ss'):
        return word[:-1]
    return word


def jmdict_contexts(path):
    """JMdict の動詞の英訳の書き込みから、(動詞, 場面の語) → [(点数, 日本語)] と、句動詞 → [(点数, 日本語)]:
    to pass (examination) → (pass, examination) 受かる、to take (medicine) → (take, medicine) 飲む、
    to pass (of time) → (pass, time) 経つ、to give up → (give up) あきらめる"""
    contexts, phrases = {}, {}
    for _, entry in ET.iterparse(path):
        if entry.tag != 'entry':
            continue
        kebs = [(k.findtext('keb'), [p.text for p in k.findall('ke_pri')]) for k in entry.findall('k_ele')]
        rebs = [(r.findtext('reb'), [p.text for p in r.findall('re_pri')]) for r in entry.findall('r_ele')]
        senses = entry.findall('sense')
        kana_usually = any('usually written using kana' in (m.text or '') for s in senses for m in s.findall('misc'))
        heads = (rebs if kana_usually or not kebs else kebs)
        word, pri = heads[0]
        priority = max([PRIORITY.get(p, 0) for p in pri] or [0])
        if priority == 0:
            entry.clear()
            continue
        pos_texts = []
        for k, sense in enumerate(senses[:5]):
            pos_texts = [p.text for p in sense.findall('pos')] or pos_texts
            verbs = [suffix for pos, suffix in jmdict_pos(pos_texts) if pos == 'verb']
            if not verbs:
                continue
            ja = word + verbs[0]
            for g, gloss in enumerate(sense.findall('gloss')):
                text = (gloss.text or '').strip()
                if not text.startswith('to '):
                    continue
                score = priority * 10 - k * 3 - g - len(word) * 0.1
                body = text[3:]
                outside = re.sub(r'\([^)]*\)', ' ', body).split()
                if not outside:
                    continue
                verb = outside[0].lower()
                rest = [w.lower().strip(',;.') for w in outside[1:]]
                if rest and rest[0] in PARTICLES and len(rest) <= 2:
                    phrases.setdefault(verb + ' ' + rest[0], []).append((score, ja))   # 句動詞 (give up)
                    if len(rest) == 1:
                        rest = []
                inside = ' '.join(re.findall(r'\(([^)]*)\)', body)).lower()
                words = re.findall(r"[a-z][a-z'-]+", inside) + [w for w in rest if re.match(r"^[a-z][a-z'-]+$", w)]
                for w in words:
                    if w in CONTEXT_STOP or w in PARTICLES or len(w) < 3:
                        continue
                    contexts.setdefault((verb, _singular(w)), []).append((score, ja))
        entry.clear()
    return contexts, phrases


def jmdict_commonness(path):
    """JMdict の見出し語 → よく使う度合い (よく使う語の印 news1・ichi1 … と頻度の順位 nf から)。サ変名詞は「〜する」も"""
    out = {}
    for _, entry in ET.iterparse(path):
        if entry.tag != 'entry':
            continue
        suru = any(('suru verb' in (p.text or '') or 'aux. verb suru' in (p.text or '')) and 'included' not in (p.text or '')
                   for s in entry.findall('sense') for p in s.findall('pos'))
        adjective_na = any('keiyodoshi' in (p.text or '') for s in entry.findall('sense') for p in s.findall('pos'))
        for tag, pri_tag in (('k_ele', 'ke_pri'), ('r_ele', 're_pri')):
            for k in entry.findall(tag):
                word = k.findtext('keb' if tag == 'k_ele' else 'reb')
                pri = [p.text for p in k.findall(pri_tag)]
                priority = max([PRIORITY.get(p, 0) for p in pri] or [0])
                nf = min([int(p[2:]) for p in pri if p.startswith('nf')] or [24])
                score = priority * 10 - nf * 0.2 if priority else 0   # 0 は JMdict にあって印の無い語
                for form in [word] + ([word + 'する'] if suru else []) + ([word + 'な'] if adjective_na else []):
                    out[form] = max(out.get(form, 0), score)
        entry.clear()
    return out


def _best(cands, limit=3):
    words = []
    for _, word in sorted(cands, key=lambda c: -c[0]):
        if word not in words:
            words.append(word)
    return ','.join(words[:limit])


def main():
    t0 = time.time()
    out = en_ja.DB_PATH
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE en_ja (en TEXT, pos TEXT, ja TEXT, UNIQUE (en, pos))')
    n = 0
    with gzip.open(paths.data('ja-extract.jsonl.gz'), 'rt') as fp:
        for line in fp:
            if '"lang_code": "en"' not in line:
                continue
            entry = json.loads(line)
            if entry.get('lang_code') != 'en' or entry.get('pos') not in POS:
                continue
            pos = POS[entry['pos']]
            glosses = en_ja.clean(japanese_gloss(entry, limit=8), pos)
            if not glosses:
                continue
            db.execute('INSERT OR IGNORE INTO en_ja VALUES (?, ?, ?)',
                       (en_ja.key(entry['word']), pos, ','.join(glosses[:4])))
            n += 1
    n_wiktionary = n
    jmdict = paths.data('JMdict_e.gz')
    if os.path.exists(jmdict):
        with gzip.open(jmdict) as fp:
            for (english, pos), cands in jmdict_rows(fp).items():
                words = []
                for _, word in sorted(cands, key=lambda c: -c[0]):
                    if word not in words:
                        words.append(word)
                cur = db.execute('INSERT OR IGNORE INTO en_ja VALUES (?, ?, ?)', (english, pos, ','.join(words[:4])))
                n += cur.rowcount
    print('Wiktionary %d, JMdict %d' % (n_wiktionary, n - n_wiktionary))
    # 動詞の場面ごとの訳語・句動詞 (JMdict の英訳の書き込みから)
    db.execute('CREATE TABLE common (ja TEXT PRIMARY KEY, score REAL)')
    if os.path.exists(jmdict):
        with gzip.open(jmdict) as fp:
            db.executemany('INSERT INTO common VALUES (?, ?)', jmdict_commonness(fp).items())
    db.execute('CREATE TABLE verb_context (verb TEXT, context TEXT, ja TEXT, UNIQUE (verb, context))')
    db.execute('CREATE TABLE phrasal (phrase TEXT PRIMARY KEY, ja TEXT)')
    if os.path.exists(jmdict):
        with gzip.open(jmdict) as fp:
            contexts, phrases = jmdict_contexts(fp)
        db.executemany('INSERT OR IGNORE INTO verb_context VALUES (?, ?, ?)',
                       [(v, c, _best(cands)) for (v, c), cands in contexts.items()])
        db.executemany('INSERT OR IGNORE INTO phrasal VALUES (?, ?)', [(p, _best(cands)) for p, cands in phrases.items()])
        print('verb contexts %d, phrasal verbs %d' % (len(contexts), len(phrases)))
        db.execute('CREATE INDEX verb_context_verb ON verb_context (verb)')
    db.execute('CREATE INDEX en_ja_en ON en_ja (en)')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries -> %s (%.1fMB, %.0fs)' % (n, out, os.path.getsize(out) / 1e6, time.time() - t0))


if __name__ == '__main__':
    main()
