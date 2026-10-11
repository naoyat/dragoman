#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 固有名詞の表 (英語の名前 → 各言語の名前) を Wiktionary (kaikki.org の抽出データ) の固有名詞 (pos: name) の項目から作る
# (文の生成 dragoman/generate で、Iēsus → Jesus → Иисус・Ἰησοῦς・يَسُوع のように固有名詞を置き換えるのに使う)
#
#   python3 tools/build_name_index.py --lang=ru      (ru / grc / sa / id / tl / ar / he。--lang=all で全部)
#
# 各行: 名前 (アラビア語・ヘブライ語は見出しの行の母音記号付きの形、サンスクリットは SLP1)、英語の名前 (読点区切り)、
#       性 (m / f。分からなければ空)、語義の数
#   英語の名前は語義ごとの頭の名前らしい語句 (大文字で始まる): "Jesus, Jeshua" → Jesus ("Asea, Greece" の Greece は取らない)、
#   "a male given name, Mark" → Mark、"… equivalent to English Christopher" → Christopher
#
# 入力: tools/build_english_index.py と同じ kaikki.org の抽出データ (CC BY-SA)
# 出力: $DRAGOMAN_DATA/<lang>/names.tsv (Wiktionary 由来 (CC BY-SA))
#
import os
import re
import sys
import gzip
import json
import getopt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

FILES = {'ru': 'kaikki-Russian.jsonl.gz', 'sa': 'kaikki-Sanskrit.jsonl.gz', 'grc': 'kaikki-AncientGreek.jsonl.gz',
         'id': 'kaikki.org-dictionary-Indonesian.jsonl', 'tl': 'kaikki.org-dictionary-Tagalog.jsonl',
         'ar': 'kaikki-Arabic.jsonl.gz', 'he': 'kaikki-Hebrew.jsonl.gz'}
NAME = re.compile(r"[A-Z][\w'’-]*(?: (?:of |the |de )?[A-Z][\w'’-]*){0,3}")
EQUIVALENT = re.compile(r'equivalent to English ([A-Z][\w-]+)')
GIVEN = re.compile(r'(?:given name|surname|patronymic)\b[^,]*,\s*([A-Z][\w-]+)')
GENDER = re.compile(r'\)\s*(m|f)\b|•\s*\([^)]*\)\s*(m|f)\b')


def name_keys(gloss):
    """語義 → 英語の名前の列 ("Jesus, Jeshua, Yeshua" → [Jesus, Jeshua, Yeshua])"""
    keys = [m.group(1) for m in (EQUIVALENT.search(gloss), GIVEN.search(gloss)) if m]
    head = re.sub(r'\([^)]*\)', '', gloss).split(';')[0].split(':')[0]
    # 読点の前の頭の語句だけ (後ろは別名か所在: "Asea, Greece" の Greece は名前でない)。or の並びは全部
    # ("Messiah or Christ" → Messiah, Christ)
    for part in head.split(',')[0].split(' or '):
        part = part.strip().rstrip('.')
        if NAME.fullmatch(part) and part not in keys:
            keys.append(part)
    return keys


def headword(entry):
    """見出しの行の形 (母音記号付き: الْقُدْس・יְרוּשָׁלַיִם)。無ければ見出し語"""
    for h in entry.get('head_templates', []):
        form = h.get('expansion', '').split(' • ')[0].strip()
        if form and ' ' not in form.strip() or form.count(' ') == entry['word'].count(' '):
            return form
    return entry['word']


def entries(lang):
    from dragoman.sanskrit import script as sa_script
    path = paths.data(lang, FILES[lang])
    with (gzip.open(path, 'rt', encoding='utf-8') if path.endswith('.gz') else open(path, encoding='utf-8')) as f:
        for line in f:
            if '"pos": "name"' not in line:
                continue
            entry = json.loads(line)
            if entry.get('pos') != 'name':
                continue
            senses = [s for s in entry.get('senses', []) if s.get('glosses') and 'form_of' not in s and
                      'alt_of' not in s]
            keys = []
            for sense in senses:
                for key in name_keys(sense['glosses'][0]):
                    if key not in keys:
                        keys.append(key)
            if not keys:
                continue
            head = ' '.join(h.get('expansion', '') for h in entry.get('head_templates', []))
            m = GENDER.search(head)
            gender = (m.group(1) or m.group(2)) if m else ''
            if lang in ('ar', 'he'):
                word = headword(entry)
            elif lang == 'sa':
                word = sa_script.to_slp1(entry['word'])
            else:
                word = entry['word']
            yield word, ','.join(keys[:8]), gender, len(senses)


def build(lang):
    out = paths.data(lang, 'names.tsv')
    seen = set()
    n = 0
    with open(out, 'w', encoding='utf-8') as f:
        for word, keys, gender, senses in entries(lang):
            if (word, keys) in seen:
                continue
            seen.add((word, keys))
            f.write('\t'.join((word, keys, gender, str(senses))) + '\n')
            n += 1
    print('%d names → %s' % (n, out))


def main():
    opts, _ = getopt.getopt(sys.argv[1:], '', ['lang='])
    lang = dict(opts).get('--lang', 'ru')
    for code in (FILES if lang == 'all' else [lang]):
        build(code)


if __name__ == '__main__':
    main()
