#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の辞書の補い: Andrews『A Dictionary of the Hawaiian Language』(Parker の改訂版、1922年。パブリックドメイン) の
# OCR のテキストから、見出し語・品詞・英語の語義を取り出す
#
#   python3 tools/build_hawaiian_andrews.py [FILE.txt [OUT.sqlite]]
#
# 入力: $DRAGOMAN_DATA/haw/andrews-parker-1922_djvu.txt
#       (https://archive.org/details/ofhawadictionary00andrrich の ofhawadictionary00andrrich_djvu.txt)
# 出力: $DRAGOMAN_DATA/haw/andrews.sqlite  lemmas (key, word, pos, en, senses)。鍵は hawaiian/orthography.key
#
# 項目の形: 「Ahonui  (a-h6-nu'-i),  adj.  Patient;  enduring; long  suffering.」。見出し (大文字で始まる語 + 括弧の発音)
# の行から次の見出しまでを1項目に。行末のハイフンで切れた語をつなぎ、語源の [ … ] とハワイ語の用例 (: の後ろ) を除いて、
# ; で区切った語義の最初の3つを英語の訳語に。19世紀の綴りなので ʻokina・長音符は無い (Wiktionary の語を先に引く)
#
import os
import re
import sys
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.hawaiian.orthography import key

HEAD = re.compile(r"^([A-Z][a-zA-Z'-]*)(?:\s+or\s+[A-Z][a-zA-Z'-]*)?\s*\(")
POS = re.compile(r"^\)?\s*[,.]?\s*(?:(interrog)\.?\s*)?(n|v|adj|adv|prep|conj|int|interj|pron|part)\s*\.", re.I)
POS_NAMES = {'n': 'noun', 'v': 'verb', 'adj': 'adj', 'adv': 'adv', 'prep': 'preposition', 'conj': 'conj',
             'int': 'intj', 'interj': 'intj', 'pron': 'pronoun', 'part': 'particle'}
SKIP = re.compile(r"^(see|same as|not used|plural form|syn|the same|passive|used|a word|name of|form of)\b", re.I)


def entries(lines):
    current = None
    for line in lines:
        line = line.rstrip('\n')
        m = HEAD.match(line)
        if m:
            if current:
                yield current
            current = [line]
        elif current is not None:
            if line.strip():
                current.append(line)
            elif len(current) > 12:   # 空行の続く長い項目は打ち切り (ページの区切りの後の本文の混入を避ける)
                yield current
                current = None
    if current:
        yield current


def parse(lines):
    text = ' '.join(l.strip() for l in lines)
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)   # 行末で切れた語 (en- during)
    text = re.sub(r'\s+', ' ', text)
    m = HEAD.match(text)
    head = m.group(1)
    close = text.find(')', m.end())
    if close < 0:
        return None
    rest = text[close:]
    p = POS.match(rest)
    if not p:
        return None
    pos = POS_NAMES[p.group(2).lower()]
    if p.group(1) and pos == 'adv':
        pos = 'adv'
    body = rest[p.end():]
    body = re.sub(r'\[[^\]]*\]', ' ', body)   # 語源
    glosses = []
    for sense in re.split(r'\b\d+\.\s', body):
        sense = sense.split(':')[0]   # ハワイ語の用例
        sense = re.split(r'\.\s', sense)[0]   # 文の終わりの後ろ (次の項目の頭の紛れ込み: learn. kula! (…), n)
        for chunk in sense.split(';'):
            chunk = re.sub(r'\s+', ' ', chunk).strip(' .,')
            chunk = re.sub(r'^(to|a|an|the)\s+', '', chunk, flags=re.I)
            if not chunk or len(chunk) > 50 or SKIP.match(chunk) or not re.search('[a-z]', chunk) or \
                    re.search(r'\b(ka|ke|ua|ia|na|he|ma|mai|aku|kona|lakou)\b', chunk):   # ハワイ語の混入
                continue
            if chunk.lower() not in (g.lower() for g in glosses):
                glosses.append(chunk.lower() if not chunk[:1].isupper() or pos != 'noun' else chunk)
            if len(glosses) >= 3:
                break
        if len(glosses) >= 3:
            break
    if not glosses:
        return None
    return head.lower(), pos, ','.join(glosses)


def main():
    t0 = time.time()
    source = sys.argv[1] if len(sys.argv) > 1 else paths.data('haw', 'andrews-parker-1922_djvu.txt')
    out = sys.argv[2] if len(sys.argv) > 2 else paths.data('haw', 'andrews.sqlite')
    rows, seen = [], set()
    with open(source, encoding='utf-8', errors='replace') as f:
        for lines in entries(f):
            parsed = parse(lines)
            if parsed is None:
                continue
            word, pos, en = parsed
            if (word, pos) in seen:
                continue
            seen.add((word, pos))
            rows.append((key(word), word, pos, en, en.count(',') + 1))
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE lemmas (key TEXT, word TEXT, pos TEXT, en TEXT, senses INTEGER)')
    db.executemany('INSERT INTO lemmas VALUES (?, ?, ?, ?, ?)', rows)
    db.execute('CREATE INDEX lemmas_key ON lemmas (key)')
    db.commit()
    db.close()
    os.replace(tmp, out)
    print('%d entries → %s (%.1fs)' % (len(rows), out, time.time() - t0))


if __name__ == '__main__':
    main()
