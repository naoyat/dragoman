#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 見出し語の出現数の表を Universal Dependencies のコーパスから作る (文の生成の語の置き換えで、よく使う語を先にする目安。
# 辞書の語義の数だけでは ἡσυχία「静けさ」が εἰρήνη「平和」より先に来る)
#
#   python3 tools/build_lemma_counts.py --lang=grc      (grc / ru / sa / id / tl / fa / hi / ur / pt / zh。--lang=all で全部)
#
# 見出し語は英語の索引 (en-index.tsv) と同じ形に: ロシア語はアクセント記号を除いた形、サンスクリットは SLP1。
# インドネシア語・タガログ語は、索引の見出しが接辞の付いた形 (mengangkat) なので、語形 (小文字) も数える
#
# 入力: $DRAGOMAN_DATA/<lang>/ud/*.conllu (Universal Dependencies。ライセンスはツリーバンクごと: CC BY-SA など)
# 出力: $DRAGOMAN_DATA/<lang>/lemma-counts.tsv (見出し語 TAB 出現数)
#       $DRAGOMAN_DATA/<lang>/lemma-pos-counts.tsv (見出し語 TAB 品詞 TAB 出現数。品詞は UD の UPOS を noun・verb・adj・adv に。
#       同じ形の別の品詞の語を分ける: インドネシア語の serang「攻撃する」(menyerang) と serang「広い」)
#
import os
import sys
import glob
import getopt
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

UPOS = {'NOUN': 'noun', 'PROPN': 'noun', 'VERB': 'verb', 'AUX': 'verb', 'ADJ': 'adj', 'ADV': 'adv'}
LANGS = ('grc', 'ru', 'sa', 'id', 'tl', 'fa', 'hi', 'ur', 'pt', 'zh')


def key(lang, lemma):
    lemma = unicodedata.normalize('NFC', lemma)
    if lang == 'ru':
        from dragoman.russian import script
        return script.key(lemma)
    if lang == 'sa':
        from dragoman.sanskrit import script
        return script.to_slp1(lemma)
    return lemma


def build(lang):
    counts = Counter()
    by_pos = Counter()
    for path in sorted(glob.glob(os.path.join(paths.data(lang, 'ud'), '*.conllu'))):
        with open(path, encoding='utf-8') as f:
            for line in f:
                if not line or line[0] in '#\n':
                    continue
                fields = line.split('\t')
                if len(fields) < 4 or '-' in fields[0] or '.' in fields[0] or fields[3] == 'PUNCT':
                    continue
                form, lemma = fields[1], fields[2]
                pos = UPOS.get(fields[3])
                if lemma and lemma != '_':
                    counts[key(lang, lemma)] += 1
                    if pos:
                        by_pos[key(lang, lemma), pos] += 1
                if lang in ('id', 'tl') and form.lower() != lemma.lower():
                    counts[form.lower()] += 1
                    if pos:
                        by_pos[form.lower(), pos] += 1
    out = paths.data(lang, 'lemma-counts.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        for lemma, n in counts.most_common():
            f.write('%s\t%d\n' % (lemma, n))
    with open(paths.data(lang, 'lemma-pos-counts.tsv'), 'w', encoding='utf-8') as f:
        for (lemma, pos), n in by_pos.most_common():
            f.write('%s\t%s\t%d\n' % (lemma, pos, n))
    print('%d lemmas → %s' % (len(counts), out))


def main():
    opts, _ = getopt.getopt(sys.argv[1:], '', ['lang='])
    lang = dict(opts).get('--lang', 'grc')
    for code in (LANGS if lang == 'all' else [lang]):
        build(code)


if __name__ == '__main__':
    main()
