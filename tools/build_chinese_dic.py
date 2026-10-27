#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語の辞書 (SQLite) を CC-CEDICT から作る
#
#   python3 tools/build_chinese_dic.py [cedict_1_0_ts_utf-8_mdbg.txt.gz] [OUT.sqlite]
#
# 入力: $DRAGOMAN_DATA/zh/cedict_1_0_ts_utf-8_mdbg.txt.gz
#       (https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz。CC BY-SA 4.0)
# 出力: $DRAGOMAN_DATA/zh/cedict.sqlite (データは CC-CEDICT 由来 (CC BY-SA 4.0)。出力ファイルもその条件に従う)
#   words: simplified (簡体字)・traditional (繁体字)・pinyin (数字の声調: shu1)・en (英語の語義を ',' で6つまで)・
#          classifiers (量詞: 本,册)・proper (固有名詞: 拼音が大文字で始まる)・senses (語義の数)・
#          pos (品詞の見当: 語義が 'to ' で始まれば verb、英語の訳語が形容詞になれば adj、ほかは noun。文の生成の
#          語の置き換え (en-index.tsv) に使う)
#   語の切り分け (最長一致) に使う見出しの長さは words の simplified・traditional の索引から
#
import gzip
import os
import re
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

LINE = re.compile(r'^(\S+) (\S+) \[([^\]]*)\] /(.*)/\s*$')
CLASSIFIER = re.compile(r'^CL:(.*)$')


def glosses(senses, limit=6):
    """語義の列 → 英語の訳語 (括弧の注を除き、'to ' を落とす)。CL: (量詞) や variant of … は除く"""
    out = []
    for sense in senses:
        if sense.startswith(('CL:', 'variant of', 'old variant of', 'see ', 'see also', 'abbr. for', 'used in ')):
            continue
        while re.search(r'\([^()]*\)', sense):   # 括弧の注 (入れ子も)
            sense = re.sub(r'\([^()]*\)', '', sense)
        sense = sense.strip()
        sense = re.sub(r'\|[^\[\]]*', '', sense)   # 書經|书经 → 書經
        sense = re.sub(r'\[[^\]]*\]', '', sense).strip()
        for chunk in re.split(r'[;,]', sense):
            chunk = re.sub(r'^(to|a|an|the) ', '', chunk.strip(), flags=re.I).strip()
            if chunk and chunk not in out and not re.search('[\u3400-\u9fff"()]', chunk):   # 漢字・引用の残りは除く
                out.append(chunk)
            if len(out) >= limit:
                return ','.join(out)
    return ','.join(out)


def _english_pos():
    """英語の語 → 品詞の集合 (en-ja.sqlite。無ければ空)"""
    path = paths.data('en-ja.sqlite')
    table = {}
    if os.path.exists(path):
        for en, pos in sqlite3.connect(path).execute('SELECT en, pos FROM en_ja'):
            table.setdefault(en, set()).add(pos)
    return table


ENGLISH_POS = None


def part_of_speech(senses, en, pinyin):
    """品詞の見当: 固有名詞 name、最初の語義が 'to ' で始まれば verb、最初の訳語が英語で形容詞になれば adj (冠詞の付いた語義は除く)、ほかは noun"""
    global ENGLISH_POS
    if pinyin[:1].isupper():
        return 'name'
    first = next((s for s in senses if s and not s.startswith(('CL:', 'variant of', 'old variant of', 'see ', 'abbr.'))), '')
    if first.startswith('to '):
        return 'verb'
    if ENGLISH_POS is None:
        ENGLISH_POS = _english_pos()
    head = (en or '').split(',')[0].strip().lower()
    poses = ENGLISH_POS.get(head, set())
    if 'adj' in poses and not first.startswith(('a ', 'an ', 'the ')):
        return 'adj'   # beautiful (形容詞にも名詞にもなる英語の語は、冠詞の無い語義なら形容詞)
    return 'noun'


def classifiers(senses):
    for sense in senses:
        m = CLASSIFIER.match(sense)
        if m:
            return ','.join(re.sub(r'\[[^\]]*\]', '', c).split('|')[-1] for c in m.group(1).split(','))
    return None


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('zh', 'cedict_1_0_ts_utf-8_mdbg.txt.gz')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('zh', 'cedict.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE words (simplified TEXT, traditional TEXT, pinyin TEXT, en TEXT, classifiers TEXT, proper INTEGER,
                            senses INTEGER, pos TEXT);
    ''')
    rows = []
    opener = gzip.open if source.endswith('.gz') else open
    with opener(source, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                continue
            m = LINE.match(line.strip())
            if not m:
                continue
            traditional, simplified, pinyin, body = m.groups()
            senses = body.split('/')
            en = glosses(senses)
            if not en and not classifiers(senses):
                continue
            rows.append((simplified, traditional, pinyin, en, classifiers(senses), int(pinyin[:1].isupper()),
                         len(senses), part_of_speech(senses, en, pinyin)))
    db.executemany('INSERT INTO words VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
    db.executescript('CREATE INDEX words_simplified ON words (simplified); CREATE INDEX words_traditional ON words (traditional);')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries → %s (%.1fs)' % (len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
