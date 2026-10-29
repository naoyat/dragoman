#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# データの置き場所 ($DRAGOMAN_DATA) の辞書・索引をまとめて作り直す
#
#   python3 tools/rebuild_data.py --lang=all            全部 (入力の無い工程は飛ばす)
#   python3 tools/rebuild_data.py --lang=de,ko          言語を絞る (la はラテン語、ja は英和・和英の表)
#   python3 tools/rebuild_data.py --only=dic,index      工程の種類を絞る (dic / index / names / counts / ja)
#   python3 tools/rebuild_data.py --lang=all --dry-run  何をするかだけ (作らない)
#   python3 tools/rebuild_data.py --manifest            入力の一覧 MANIFEST.tsv だけを書く
#
# - 作る前に出力の控えを取る (wiktionary.sqlite.bak-20261030。同じ日の2回目からは .bak-20261030b, c …)
# - 順は 英和・和英 → 辞書 → 英語の索引・名前の表 → 出現数 (英語の索引は辞書から、ウルドゥー語はヒンディー語の辞書から、
#   中国語の辞書は英和の表から作るので)
# - 最後に出力ごとの変化を出す: TSV は変わった行の数、SQLite は表ごとの行数の前後
# - $DRAGOMAN_DATA/MANIFEST.tsv に入力の一覧 (道筋・大きさ・日付・取得元・ライセンス。無いものは missing) を書く。
#   生データを手元に置いていない言語 (取り直すときの手がかり)
#
import os
import sys
import csv
import glob
import shutil
import sqlite3
import getopt
import subprocess
import time
from collections import namedtuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dragoman.core import paths

KAIKKI = 'https://kaikki.org/dictionary/'
WIKTIONARY = 'CC BY-SA (Wiktionary)'
JMDICT = ('http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz', 'CC BY-SA 4.0 (EDRDG)')

# 工程: 種類・言語・コマンド (tools/ の後ろ)・入力 [(道筋, 取得元, ライセンス)]・出力。入力の先頭が無ければ飛ばす
Step = namedtuple('Step', 'kind lang command inputs outputs')


def _kaikki(lang, name, page, url=None):
    return (os.path.join(lang, name) if lang else name, url or KAIKKI + page + '/', WIKTIONARY)


STEPS = [
    Step('ja', 'ja', ['build_en_ja.py'],
         [('ja-extract.jsonl.gz', 'https://kaikki.org/dictionary/downloads/ja/ja-extract.jsonl.gz', WIKTIONARY),
          ('JMdict_e.gz',) + JMDICT], ['en-ja.sqlite']),
    Step('ja', 'ja', ['build_ja_en.py'], [('JMdict_e.gz',) + JMDICT], ['ja-en.tsv']),
    Step('ja', 'ja', ['build_ja_transitivity.py'], [('JMdict_e.gz',) + JMDICT], ['ja-transitivity.tsv']),
    Step('dic', 'la', ['build_wiktionary_dic.py'], [_kaikki('', 'kaikki-Latin.jsonl.gz', 'Latin')], ['wiktionary.sqlite']),
    Step('dic', 'la', ['build_latin_english.py'], [_kaikki('', 'kaikki-Latin.jsonl.gz', 'Latin')], ['la-en.tsv']),
    Step('dic', 'ar', ['build_arabic_dic.py'], [_kaikki('ar', 'kaikki-Arabic.jsonl.gz', 'Arabic')], ['ar/wiktionary.sqlite']),
    Step('dic', 'ang', ['build_oldenglish_dic.py'], [_kaikki('ang', 'kaikki.org-dictionary-OldEnglish.jsonl', 'Old%20English')],
         ['ang/wiktionary.sqlite']),
    Step('dic', 'de', ['build_german_dic.py'], [_kaikki('de', 'kaikki.org-dictionary-German.jsonl', 'German')],
         ['de/wiktionary.sqlite']),
    Step('dic', 'fa', ['build_persian_dic.py'], [_kaikki('fa', 'kaikki-Persian.jsonl.gz', 'Persian')], ['fa/wiktionary.sqlite']),
    Step('dic', 'fi', ['build_finnish_dic.py'], [_kaikki('fi', 'kaikki.org-dictionary-Finnish.jsonl', 'Finnish')],
         ['fi/wiktionary.sqlite']),
    Step('dic', 'fr', ['build_french_dic.py'], [_kaikki('fr', 'kaikki.org-dictionary-French.jsonl', 'French')],
         ['fr/wiktionary.sqlite']),
    Step('dic', 'grc', ['build_greek_dic.py'], [_kaikki('grc', 'kaikki-AncientGreek.jsonl.gz', 'Ancient%20Greek')],
         ['grc/wiktionary.sqlite']),
    Step('dic', 'haw', ['build_hawaiian_dic.py'], [_kaikki('haw', 'kaikki.org-dictionary-Hawaiian.jsonl', 'Hawaiian')],
         ['haw/wiktionary.sqlite']),
    Step('dic', 'he', ['build_hebrew_dic.py'],
         [('he/oshb', 'https://github.com/openscriptures/morphhb', 'WLC: public domain、解析: CC BY 4.0'),
          ('he/lexicon', 'https://github.com/openscriptures/HebrewLexicon', 'CC BY 4.0'),
          _kaikki('he', 'kaikki-Hebrew.jsonl.gz', 'Hebrew')], ['he/hebrew.sqlite']),
    Step('dic', 'hi', ['build_hindi_dic.py'], [_kaikki('hi', 'kaikki-Hindi.jsonl.gz', 'Hindi')], ['hi/wiktionary.sqlite']),
    Step('dic', 'ur', ['build_urdu_dic.py'], [_kaikki('ur', 'kaikki-Urdu.jsonl.gz', 'Urdu')], ['ur/urdu.sqlite']),
    Step('dic', 'id', ['build_indonesian_dic.py'],
         [_kaikki('id', 'kaikki.org-dictionary-Indonesian.jsonl', 'Indonesian'),
          _kaikki('ms', 'kaikki.org-dictionary-Malay.jsonl', 'Malay')], ['id/wiktionary.sqlite']),
    Step('dic', 'ko', ['build_korean_dic.py'], [_kaikki('ko', 'kaikki.org-dictionary-Korean.jsonl', 'Korean')],
         ['ko/wiktionary.sqlite']),
    Step('dic', 'mn', ['build_mongolian_dic.py'], [_kaikki('mn', 'kaikki.org-dictionary-Mongolian.jsonl', 'Mongolian')],
         ['mn/wiktionary.sqlite']),
    Step('dic', 'pt', ['build_portuguese_dic.py'], [_kaikki('pt', 'kaikki.org-dictionary-Portuguese.jsonl', 'Portuguese')],
         ['pt/wiktionary.sqlite']),
    Step('dic', 'ru', ['build_russian_dic.py'], [_kaikki('ru', 'kaikki-Russian.jsonl.gz', 'Russian')], ['ru/wiktionary.sqlite']),
    Step('dic', 'sa', ['build_sanskrit_dic.py'], [_kaikki('sa', 'kaikki-Sanskrit.jsonl.gz', 'Sanskrit')],
         ['sa/wiktionary.sqlite']),
    Step('dic', 'tl', ['build_tagalog_dic.py'], [_kaikki('tl', 'kaikki.org-dictionary-Tagalog.jsonl', 'Tagalog')],
         ['tl/wiktionary.sqlite']),
    Step('dic', 'tr', ['build_turkish_dic.py'], [_kaikki('tr', 'kaikki.org-dictionary-Turkish.jsonl', 'Turkish')],
         ['tr/wiktionary.sqlite']),
    Step('dic', 'bo', ['build_tibetan_dic.py'],
         [_kaikki('bo', 'kaikki/kaikki.org-dictionary-Tibetan.jsonl', 'Tibetan'),
          ('bo/hill/lex/Lexicons/classical-lexicon.txt', 'doi:10.5281/zenodo.574876 (Hill & Garrett 2017)', 'CC BY 4.0')],
         ['bo/tibetan.sqlite']),
    Step('dic', 'zh', ['build_chinese_dic.py'],
         [('zh/cedict_1_0_ts_utf-8_mdbg.txt.gz', 'https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz',
           'CC BY-SA 4.0 (CC-CEDICT)')], ['zh/cedict.sqlite']),
]
# 英語の索引 (辞書から。ロシア語などは生データから): tools/build_english_index.py
INDEX_INPUTS = {'ru': 'ru/wiktionary.sqlite', 'sa': 'sa/wiktionary.sqlite', 'grc': 'grc/wiktionary.sqlite',
                'id': 'id/wiktionary.sqlite', 'tl': 'tl/wiktionary.sqlite', 'ko': 'ko/wiktionary.sqlite',
                'de': 'de/wiktionary.sqlite', 'fr': 'fr/wiktionary.sqlite', 'mn': 'mn/wiktionary.sqlite',
                'ang': 'ang/wiktionary.sqlite', 'pt': 'pt/wiktionary.sqlite', 'fi': 'fi/wiktionary.sqlite',
                'tr': 'tr/wiktionary.sqlite', 'zh': 'zh/cedict.sqlite'}
for _lang, _dic in INDEX_INPUTS.items():
    STEPS.append(Step('index', _lang, ['build_english_index.py', '--lang=' + _lang], [(_dic, '(辞書から)', '')],
                      [_lang + '/en-index.tsv']))
# 名前の表: tools/build_name_index.py (固有名詞の言語ごとの綴り)
for _lang in ('ru', 'sa', 'grc', 'id', 'tl', 'ar', 'he', 'fa', 'hi', 'ur', 'ko', 'de', 'fr', 'tr', 'mn', 'fi', 'ang', 'pt'):
    STEPS.append(Step('names', _lang, ['build_name_index.py', '--lang=' + _lang], [(_lang + '/names.tsv', '(作り直す表)', '')],
                      [_lang + '/names.tsv']))
# 出現数: tools/build_lemma_counts.py (UD のツリーバンクから)
for _lang in ('grc', 'ru', 'sa', 'id', 'tl', 'fa', 'hi', 'ur', 'pt', 'zh', 'ko', 'de', 'fr', 'fi', 'tr'):
    STEPS.append(Step('counts', _lang, ['build_lemma_counts.py', '--lang=' + _lang],
                      [(_lang + '/ud', 'https://universaldependencies.org/', 'ツリーバンクごと (ud/LICENSE*)')],
                      [_lang + '/lemma-counts.tsv', _lang + '/lemma-pos-counts.tsv']))


def backup_name(path, day):
    """控えの名前: path.bak-YYYYMMDD、同じ日に既にあれば b, c …"""
    for suffix in [''] + list('bcdefghijklmnopqrstuvwxyz'):
        candidate = '%s.bak-%s%s' % (path, day, suffix)
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError('控えの名前が尽きた: ' + path)


def snapshot(path):
    """変化を比べるための中身の要約: TSV は行の集合、SQLite は表ごとの行数。無ければ None"""
    if not os.path.exists(path):
        return None
    if path.endswith('.sqlite'):
        db = sqlite3.connect('file:%s?mode=ro' % path, uri=True)
        try:
            tables = [name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
            return {name: db.execute('SELECT COUNT(*) FROM "%s"' % name).fetchone()[0] for name in tables}
        finally:
            db.close()
    with open(path, encoding='utf-8', errors='replace') as f:
        return set(f)


def describe_change(before, after):
    if before is None:
        return '新規'
    if after is None:
        return '出力なし'
    if isinstance(after, dict):
        changes = ['%s %d → %d' % (t, before.get(t, 0), n) for t, n in after.items() if before.get(t, 0) != n]
        return ', '.join(changes) or '行数は同じ'
    return '%d 行変わった (%d 行 → %d 行)' % (len(after - before), len(before), len(after))


def manifest(steps):
    """入力の一覧 (MANIFEST.tsv) を書く"""
    seen = {}
    for step in steps:
        for path, source, license in step.inputs:
            if source.startswith('('):
                continue   # ほかの工程の出力
            seen.setdefault(path, (source, license))
    out = paths.data('MANIFEST.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        f.write('# dragoman のデータの入力の一覧 (tools/rebuild_data.py が書く)。path\tsize\tmodified\tsource\tlicense\n')
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        for path, (source, license) in sorted(seen.items()):
            full = paths.data(path)
            if os.path.isdir(full):
                files = [p for p in glob.glob(os.path.join(full, '**'), recursive=True) if os.path.isfile(p)]
                size = sum(os.path.getsize(p) for p in files)
                modified = max((os.path.getmtime(p) for p in files), default=0)
            elif os.path.exists(full):
                size, modified = os.path.getsize(full), os.path.getmtime(full)
            else:
                writer.writerow([path, 'missing', '', source, license])
                continue
            writer.writerow([path, size, time.strftime('%Y-%m-%d', time.localtime(modified)), source, license])
    return out


def main():
    opts, _ = getopt.getopt(sys.argv[1:], '', ['lang=', 'only=', 'dry-run', 'manifest'])
    opts = dict(opts)
    if '--manifest' in opts:
        print(manifest(STEPS))
        return
    if '--lang' not in opts and '--only' not in opts:
        print(__doc__ if __doc__ else 'usage: rebuild_data.py --lang=all')
        return
    langs = opts.get('--lang', 'all')
    kinds = opts.get('--only', 'dic,index,names,counts,ja').split(',')
    steps = [s for s in STEPS if s.kind in kinds and (langs == 'all' or s.lang in langs.split(','))]
    day = time.strftime('%Y%m%d')
    results = []
    for step in steps:
        name = ' '.join(step.command)
        missing = paths.data(step.inputs[0][0])
        if not os.path.exists(missing):
            results.append((name, '飛ばした (入力が無い: %s)' % step.inputs[0][0]))
            print('-- %s: 入力が無い (%s)' % (name, step.inputs[0][0]), flush=True)
            continue
        if '--dry-run' in opts:
            print('%s → %s' % (name, ', '.join(step.outputs)))
            continue
        before = {}
        for out in step.outputs:
            full = paths.data(out)
            before[out] = snapshot(full)
            if os.path.exists(full):
                shutil.copy2(full, backup_name(full, day))
        print('== %s' % name, flush=True)
        t0 = time.time()
        done = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', step.command[0])] + step.command[1:],
                              cwd=ROOT, capture_output=True, text=True)
        last = (done.stdout.strip().splitlines() or [''])[-1]
        if done.returncode != 0:
            results.append((name, '失敗: ' + ((done.stderr.strip().splitlines() or [''])[-1])))
            print('   失敗 (%d)\n%s' % (done.returncode, done.stderr[-2000:]), flush=True)
            continue
        print('   %s (%.0fs)' % (last, time.time() - t0), flush=True)
        for out in step.outputs:
            results.append(('%s: %s' % (name, out), describe_change(before[out], snapshot(paths.data(out)))))
    if '--dry-run' not in opts:
        print('\n変化:')
        for name, change in results:
            print('  %s  %s' % (name, change))
        print('\n入力の一覧 → %s' % manifest(STEPS))


if __name__ == '__main__':
    main()
