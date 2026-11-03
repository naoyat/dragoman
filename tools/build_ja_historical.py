#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢字の読みの歴史的仮名遣いの表を、英語版 Wiktionary の日本語の語 (kaikki) から作る
#
#   python3 tools/build_ja_historical.py
#
# 漢文の振り仮名 (dragoman/kanbun/ruby.py) を歴史的仮名遣いにするのに使う (王 おう → わう、遠方 えんぽう → ゑんぱう、
# 思 おも → おも、教 おし → をし)。語の見出しの振り仮名 (字ごとの現代仮名遣い) と歴史的仮名遣い (hhira) から、
# 字ごとの歴史的仮名遣いを dragoman/kanbun/kana.py で突き合わせて分ける。
#
# 入力: $DRAGOMAN_DATA/ja/kaikki.org-dictionary-Japanese.jsonl (https://kaikki.org/dictionary/Japanese/、
#       CC BY-SA (Wiktionary))
# 出力: $DRAGOMAN_DATA/ja/historical-kana.tsv
#       W TAB 語 TAB 字ごとの現代仮名遣い (| 区切り) TAB 字ごとの歴史的仮名遣い (| 区切り)
#       C TAB 字 TAB 現代仮名遣い TAB 歴史的仮名遣い TAB 語の数   (Wiktionary 由来 (CC BY-SA))
#
import os
import re
import sys
import json
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.kanbun.kana import same

KANJI = re.compile(r'[㐀-鿿豈-﫿々]')


def hiragana(kana):
    return ''.join(chr(ord(c) - 0x60) if 'ァ' <= c <= 'ヶ' else c for c in kana)


def historical(entry):
    for t in entry.get('head_templates') or []:
        args = t.get('args') or {}
        for key in ('hhira', 'hist'):
            if args.get(key):
                return hiragana(args[key]).replace('%', '').replace(' ', '').replace('-', '')
    for f in entry.get('forms') or []:
        if 'historical' in f.get('tags', []) and 'hiragana' in f.get('tags', []):
            return hiragana(f['form'])
    return None


def ruby(entry):
    for f in entry.get('forms') or []:
        if 'canonical' in f.get('tags', []) and f.get('ruby'):
            return f['form'], f['ruby']
    return None, None


def split(word, parts, hist):
    """語の字ごとの現代仮名遣い (parts: [(字か仮名の並び, 読み)]) に合わせて歴史的仮名遣いを分ける"""
    out = []
    rest = hist
    for k, (text, reading) in enumerate(parts):
        last = k == len(parts) - 1
        on = bool(KANJI.match(text)) and len(text) == 1
        found = None
        for n in range(len(rest), 0, -1) if last else range(1, len(rest) + 1):
            if same(rest[:n], reading, on) or same(rest[:n], reading, False):
                found = n
                break
        if found is None:
            return None
        out.append(rest[:found])
        rest = rest[found:]
    return out if not rest else None


def main():
    src = paths.data('ja', 'kaikki.org-dictionary-Japanese.jsonl')
    words = {}
    chars = Counter()
    with open(src, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            hist = historical(entry)
            if not hist:
                continue
            word, rb = ruby(entry)
            if not word or not KANJI.search(word):
                continue
            # 語を (字, 読み) と送り仮名 (仮名, 仮名) に分ける
            parts = []
            k = 0
            pairs = [(a, hiragana(b)) for a, b in rb]
            for a, b in pairs:
                while k < len(word) and not word.startswith(a, k):
                    parts.append((word[k], hiragana(word[k])))
                    k += 1
                parts.append((a, b))
                k += len(a)
            parts += [(c, hiragana(c)) for c in word[k:]]
            pieces = split(word, parts, hist)
            if pieces is None:
                continue
            kanji_parts = [(a, b, h) for (a, b), h in zip(parts, pieces) if KANJI.match(a)]
            if all(len(a) == 1 for a, _, _ in kanji_parts):
                words[word] = ('|'.join(b for _, b, _ in kanji_parts), '|'.join(h for _, _, h in kanji_parts))
                for a, b, h in kanji_parts:
                    chars[(a, b, h)] += 1
    out = paths.data('ja', 'historical-kana.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        for word, (mod, hist) in words.items():
            f.write('W\t%s\t%s\t%s\n' % (word, mod, hist))
        for (a, b, h), n in chars.most_common():
            f.write('C\t%s\t%s\t%s\t%d\n' % (a, b, h, n))
    print('%d words, %d character readings → %s' % (len(words), len(chars), out))


if __name__ == '__main__':
    main()
