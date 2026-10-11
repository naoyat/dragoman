#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 日本語 → 英語の表を JMdict から作る
#
#   python3 tools/build_ja_en.py
#
# 文の生成 (dragoman/generate) の語の置き換えで、手作りの辞書の日本語の訳語 (tollō「取り去る」) に合う英語の語義
# (remove・take away) を、Wiktionary の英語の語義の並び (lift up, raise, remove …) より先に試すのに使う。
#
# 入力: $DRAGOMAN_DATA/JMdict_e.gz (http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz、EDRDG、CC BY-SA 4.0)
# 出力: $DRAGOMAN_DATA/ja-en.tsv (見出し語 (漢字の表記・読み) TAB 英語の訳語 (語義の順に読点区切り。動詞の to は除く)。
#       JMdict 由来 (CC BY-SA))
#
import os
import re
import sys
import gzip
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

NOTE = re.compile(r'\s*\([^)]*\)\s*')


def glosses(entry, limit=12):
    out = []
    for sense in entry.findall('sense'):
        for g in sense.findall('gloss'):
            text = NOTE.sub(' ', g.text or '').strip()
            text = re.sub(r'^to ', '', text)   # to pity → pity
            if text and ',' not in text and text not in out:
                out.append(text)
    return out[:limit]


def main():
    table = {}
    with gzip.open(paths.data('JMdict_e.gz')) as f:
        for _, entry in ET.iterparse(f):
            if entry.tag != 'entry':
                continue
            english = glosses(entry)
            if english:
                for word in [k.findtext('keb') for k in entry.findall('k_ele')] + \
                        [r.findtext('reb') for r in entry.findall('r_ele')]:
                    if word:
                        merged = table.setdefault(word, [])
                        merged.extend(e for e in english if e not in merged)
            entry.clear()
    out = paths.data('ja-en.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        for word, english in table.items():
            f.write('%s\t%s\n' % (word, ','.join(english[:16])))
    print('%d words → %s' % (len(table), out))


if __name__ == '__main__':
    main()
