#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢字の表記 → 読みの表を JMdict から作る
#
#   python3 tools/build_ja_readings.py
#
# 漢文のノートの振り仮名 (dragoman/kanbun/ruby.py) で、名詞・熟語の読み (遠方 えんぽう・生 せい) を
# 語義 (UD-Kanbun の Gloss) で選ぶのに使う。
#
# 入力: $DRAGOMAN_DATA/JMdict_e.gz (http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz、EDRDG、CC BY-SA 4.0)
# 出力: $DRAGOMAN_DATA/ja-readings.tsv (漢字の表記 TAB 読み (ひらがな) TAB 英語の訳語 (読点区切り)。
#       JMdict の見出しの順 (よく使う語が先)。JMdict 由来 (CC BY-SA))
#
import os
import sys
import gzip
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from build_ja_en import glosses   # noqa: E402


def main():
    rows = []
    with gzip.open(paths.data('JMdict_e.gz')) as f:
        for _, entry in ET.iterparse(f):
            if entry.tag != 'entry':
                continue
            english = ','.join(glosses(entry, limit=8))
            kanji = [k.findtext('keb') for k in entry.findall('k_ele')]
            for r in entry.findall('r_ele'):
                if r.find('re_nokanji') is not None:
                    continue
                restr = [x.text for x in r.findall('re_restr')]
                for k in kanji:
                    if k and (not restr or k in restr):
                        rows.append((k, r.findtext('reb'), english))
            entry.clear()
    out = paths.data('ja-readings.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        for row in rows:
            f.write('\t'.join(row) + '\n')
    print('%d readings → %s' % (len(rows), out))


if __name__ == '__main__':
    main()
