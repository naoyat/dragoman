#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 見出し語の出現数の表を Universal Dependencies のコーパスから作る (文の生成の語の置き換えで、よく使う語を先にする目安。
# 辞書の語義の数だけでは ἡσυχία「静けさ」が εἰρήνη「平和」より先に来る)
#
#   python3 tools/build_lemma_counts.py --lang=grc      (grc / ru / sa / id / tl / fa / hi / ur / pt / zh / ko / de。--lang=all で全部)
#
# 見出し語は英語の索引 (en-index.tsv) と同じ形に: ロシア語はアクセント記号を除いた形、サンスクリットは SLP1。
# インドネシア語・タガログ語は、索引の見出しが接辞の付いた形 (mengangkat) なので、語形 (小文字) も数える。
# 韓国語 (KAIST) の見出し語は形態素を + でつないだ形 (가수+가、운전+하+ㄴ다) なので、XPOS の印で辞書の見出しに直す
# (名詞は先頭の名詞の形態素: 가수。動詞・形容詞は語尾の前まで + 다: 운전하다。品詞も XPOS から: 連結の形は UPOS が CCONJ)
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
LANGS = ('grc', 'ru', 'sa', 'id', 'tl', 'fa', 'hi', 'ur', 'pt', 'zh', 'ko', 'de')


def korean_key(lemma, xpos):
    """KAIST の見出し語・XPOS → (辞書の見出し, 品詞) か None (가수+가 / ncn+jcs → 가수, noun。먹+었+다 → 먹다, verb)"""
    parts, tags = lemma.split('+'), xpos.split('+')
    if len(parts) != len(tags) or not tags[0]:
        return None
    if tags[0].startswith('n'):   # 名詞 (+ 하・되 で動詞・形容詞: 운전+하 → 운전하다)
        k = 1
        while k < len(tags) and tags[k].startswith('n'):
            k += 1
        if k < len(tags) and tags[k] in ('xsv', 'xsa'):
            return ''.join(parts[:k + 1]) + '다', 'verb' if tags[k] == 'xsv' else 'adj'
        return ''.join(parts[:k]), 'noun'
    if tags[0][:2] in ('pv', 'pa', 'px'):
        k = 1
        while k < len(tags) and tags[k] in ('xsv', 'xsa', 'px'):
            k += 1
        return ''.join(parts[:k]) + '다', 'adj' if tags[0].startswith('pa') else 'verb'
    if tags[0].startswith('ma'):
        return parts[0], 'adv'
    return None


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
                if lang == 'ko':
                    lemma, pos = (korean_key(lemma, fields[4]) if len(fields) > 4 else None) or (None, None)
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
