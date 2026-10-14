#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語・フィンランド語の辞書 ($DRAGOMAN_DATA/<lang>/wiktionary.sqlite) の語形の表を小さくする
#
#   python3 tools/shrink_dic.py --lang=fi      (de / fi)
#   python3 tools/shrink_dic.py --lang=de --dry-run    # 減る行数だけ表示 (辞書は変えない)
#
# - 語形の表を見出し順に並べて持つ (WITHOUT ROWID。主キー (lemma, pos, form, tags))。見出しから引く索引
#   (forms_lemma) が要らなくなる。ドイツ語は解析で語形から見出しを引くので語形の索引 (forms_form) は残す
# - 使わない語形を除く
#   fi: 動詞の不定詞の格の形 (lukiessa・lukemaan …) と所有の接尾辞の付いた形、名詞・形容詞の具格 (instructive)
#       (文の生成 generate/finnish.py は動詞の定形・分詞と名詞の格の形 (具格以外) だけを引く)
#   de: 形容詞の語形は印 (格・性・強弱) を除いて (語形, 見出し) を1行に (形容詞の語尾は規則で付けるので、
#       解析で語形を知っているかどうかだけに使う)
#
# 元の辞書は wiktionary.sqlite.bak に残す (確かめたら消してよい)。作り直すときは tools/build_<言語>_dic.py の後で
#
import getopt
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

CASES = {'nominative', 'genitive', 'partitive', 'accusative', 'inessive', 'elative', 'illative', 'adessive', 'ablative',
         'allative', 'essive', 'translative', 'abessive', 'comitative', 'instructive'}


def keep(lang, pos, tags):
    """(残すか, 書き換えた印)"""
    tagset = set(tags.split(',')) if tags else set()
    if lang == 'fi':
        if pos == 'verb' and (tagset & CASES or 'possessive' in tagset):
            return False, tags   # 不定詞の格の形 (lukiessa)・所有の接尾辞 (lukeakseni)
        if pos != 'verb' and 'instructive' in tagset:
            return False, tags
        return True, tags
    if lang == 'de' and pos == 'adj':
        return True, ''
    return True, tags


def shrink(lang, dry_run=False):
    path = paths.data(lang, 'wiktionary.sqlite')
    src = sqlite3.connect(path)
    total = src.execute('SELECT count(*) FROM forms').fetchone()[0]

    def kept_rows():
        for lemma, pos, form, tags in src.execute('SELECT lemma, pos, form, tags FROM forms'):
            ok, tags = keep(lang, pos, tags)
            if ok:
                yield lemma, pos, form, tags

    if dry_run:
        kept = sum(1 for _ in kept_rows())
        print('%s: 語形 %d → %d (除く %d)' % (lang, total, kept, total - kept))
        return
    out = path + '.new'
    if os.path.exists(out):
        os.remove(out)
    dst = sqlite3.connect(out)
    dst.execute('CREATE TABLE forms (lemma TEXT, pos TEXT, form TEXT, tags TEXT, PRIMARY KEY (lemma, pos, form, tags)) '
                'WITHOUT ROWID')
    dst.executemany('INSERT OR IGNORE INTO forms VALUES (?, ?, ?, ?)', kept_rows())
    print('%s: 語形 %d → %d' % (lang, total, dst.execute('SELECT count(*) FROM forms').fetchone()[0]))
    if lang == 'de':
        dst.execute('CREATE INDEX forms_form ON forms (form)')
    # 見出しの表はそのまま写す
    schema = src.execute("SELECT sql FROM sqlite_master WHERE name = 'lemmas'").fetchone()[0]
    dst.execute(schema)
    columns = len(src.execute('SELECT * FROM lemmas LIMIT 1').description)
    dst.executemany('INSERT INTO lemmas VALUES (%s)' % ', '.join('?' * columns), src.execute('SELECT * FROM lemmas'))
    dst.execute('CREATE INDEX lemmas_key ON lemmas (key)')
    dst.commit()
    lemmas = (src.execute('SELECT count(*) FROM lemmas').fetchone()[0], dst.execute('SELECT count(*) FROM lemmas').fetchone()[0])
    forms = dst.execute('SELECT count(*) FROM forms').fetchone()[0]
    dst.execute('VACUUM')
    dst.close()
    src.close()
    if lemmas[0] != lemmas[1] or forms == 0:
        print('見出しの数が合わない (%d / %d) か語形が空: %s は置き換えない' % (lemmas[0], lemmas[1], out))
        sys.exit(1)
    os.replace(path, path + '.bak')
    os.replace(out, path)
    print('%s (%dMB → %dMB。元は %s.bak)' % (path, os.path.getsize(path + '.bak') >> 20, os.path.getsize(path) >> 20,
                                          os.path.basename(path)))


def main():
    opts, _ = getopt.getopt(sys.argv[1:], '', ['lang=', 'dry-run'])
    opts = dict(opts)
    lang = opts.get('--lang')
    if lang not in ('de', 'fi'):
        print('--lang=de|fi')
        sys.exit(1)
    shrink(lang, '--dry-run' in opts)


if __name__ == '__main__':
    main()
