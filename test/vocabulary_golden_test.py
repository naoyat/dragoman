#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 回帰テスト: 基本の語の訳語 (tools/generate.py --vocabulary) を、言語ごとの正解ファイルと比較する
#
#   python3 test/vocabulary_golden_test.py                     # 比較
#   UPDATE_GOLDEN=1 python3 test/vocabulary_golden_test.py     # 意図して訳語を変えたときに更新
#
# - 語は手作りの辞書の名詞・動詞・形容詞 (固有名詞・比較級を除く)。正解ファイルは test/golden/vocabulary/<言語>.out
#   (1行1語: 語 (品詞) 日本語 TAB 選んだ語)
# - 辞書を作り直したときの影響を語の単位で見る (文のゴールデン generate_golden_test.py は例文に出る語しか見えない)。
#   語を選んだ理由は tools/generate.py --why=語 --to=言語 で
# - 解析は手作りの辞書だけで (LATIN_WIKTIONARY=0, LATIN_TAGGER=0)。作る言語の辞書が無い言語は飛ばす
#
import os
import sys
import difflib
import functools
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_DIR = os.path.join(ROOT, 'test', 'golden', 'vocabulary')
LANGS = ('en', 'ru', 'de', 'fr', 'pt', 'fi', 'ang', 'sa', 'grc', 'id', 'tl', 'ar', 'he', 'fa', 'hi', 'ur', 'ain', 'tr',
         'mn', 'ko', 'zh', 'bo')


@functools.lru_cache(maxsize=1)
def generated():
    """言語 → 訳語の表 (1行1語)"""
    result = subprocess.run([sys.executable, os.path.join('tools', 'generate.py'), '--vocabulary'], cwd=ROOT,
                            capture_output=True, text=True,
                            env=dict(os.environ, PYTHONHASHSEED='0', LATIN_WIKTIONARY='0', LATIN_TAGGER='0'))
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    out = {}
    for line in result.stdout.splitlines():
        lang, _, rest = line.partition('\t')
        out.setdefault(lang, []).append(rest)
    return {lang: '\n'.join(lines) + '\n' for lang, lines in out.items()}


class VocabularyGoldenTestCase(unittest.TestCase):
    maxDiff = None


def make_test(lang):
    def test(self):
        golden_file = os.path.join(GOLDEN_DIR, lang + '.out')
        actual = generated().get(lang)
        if actual is None:
            self.skipTest('%s の辞書が無い (表に出ない)' % lang)
        if os.environ.get('UPDATE_GOLDEN') or not os.path.exists(golden_file):
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(golden_file, 'w', encoding='utf-8') as f:
                f.write(actual)
            return
        with open(golden_file, encoding='utf-8') as f:
            expected = f.read()
        if actual != expected:
            diff = ''.join(difflib.unified_diff(expected.splitlines(True), actual.splitlines(True),
                                                lang + '.out', 'actual', n=0))
            changed = sum(1 for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++'))
            self.fail('%s の訳語が %d 語変わりました:\n%s' % (lang, changed, diff))
    return test


for _lang in LANGS:
    setattr(VocabularyGoldenTestCase, 'test_' + _lang, make_test(_lang))


if __name__ == '__main__':
    unittest.main()
