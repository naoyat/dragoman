#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 広東語の辞書 (SQLite) を CC-Canto から作る
#
#   python3 tools/build_cantonese_dic.py [DIR] [OUT.sqlite]
#
# 入力: $DRAGOMAN_DATA/yue/ (https://cantonese.org/download.html。どちらも CC BY-SA 3.0)
#   cccanto-webdist.txt                 (cccanto-170202.zip): 広東語・英語の辞書 (約3万4千語)
#   cccedict-canto-readings-150923.txt  (cccedict-canto-readings-150923.zip): CC-CEDICT の見出しの広東語の読み (約10万語)
# 出力: $DRAGOMAN_DATA/yue/cantonese.sqlite (CC-Canto 由来 (CC BY-SA 3.0)。出力ファイルもその条件に従う)
#   words: traditional (繁体字)・simplified (簡体字)・pinyin・jyutping (粤拼: sik6 faan6)・en (英語の語義を ',' で6つまで。
#          読みの表の語は空)・
#          mandarin (語義の「Mandarin equivalent: 看」の普通話の語)・senses (語義の数)・source ('canto' / 'readings')
#
# 解析には PyCantonese (pip install pycantonese。MIT) も使う (語の切り分け・品詞・粤拼)
#
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dragoman.core import paths
from build_chinese_dic import glosses   # noqa: E402

LINE = re.compile(r'^(\S+) (\S+) \[([^\]]*)\] \{([^}]*)\}(?: /(.*)/)?\s*(?:#.*)?$')
MANDARIN = re.compile(r'^Mandarin equivalent: ([㐀-鿿]+)')
FILES = (('cccanto-webdist.txt', 'canto'), ('cccedict-canto-readings-150923.txt', 'readings'))


def entries(path, source):
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            m = LINE.match(line.strip())
            if not m:
                continue
            trad, simp, pinyin, jyutping, senses = m.groups()
            parts = [p.strip() for p in re.split(r'/|\s(?=\d+\.\s)', senses or '') if p.strip()]
            mandarin = next((MANDARIN.match(p).group(1) for p in parts if MANDARIN.match(p)), '')
            parts = [re.sub(r'^\d+\.\s*', '', p) for p in parts if not MANDARIN.match(p)]
            parts = [re.sub(r'\((?:Cantonese|verb|noun|adjective|adverb|dialect|slang)\)', '', p).strip() for p in parts]
            en = glosses([p for p in parts if p]) if parts else ''
            yield trad, simp, pinyin, jyutping.strip(), en, mandarin, len(parts), source


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else paths.data('yue')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('yue', 'cantonese.sqlite')
    start = time.time()
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE words (traditional TEXT, simplified TEXT, pinyin TEXT, jyutping TEXT, en TEXT, mandarin TEXT, senses INTEGER, source TEXT)')
    n = 0
    for name, source in FILES:
        rows = list(entries(os.path.join(src, name), source))
        db.executemany('INSERT INTO words VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
        n += len(rows)
        print('%s: %d' % (name, len(rows)))
    db.execute('CREATE INDEX words_trad ON words (traditional)')
    db.execute('CREATE INDEX words_simp ON words (simplified)')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d words -> %s (%.1fs)' % (n, out, time.time() - start))


if __name__ == '__main__':
    main()
