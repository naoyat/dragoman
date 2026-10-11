#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 回帰テスト: 文の生成 (tools/generate.py) の結果を、言語ごとの正解ファイルと比較する
#
#   python3 test/generate_golden_test.py                     # 比較
#   UPDATE_GOLDEN=1 python3 test/generate_golden_test.py     # 意図して出力を変えたときに更新
#
# - 入力は samples/samples.txt (このために作った例文)。正解ファイルは test/golden/generate/<言語>.out と、
#   文の枠の部分 (述語・名詞句の役割) の frame.out
# - 解析は手作りの辞書だけで、タガーを使わずに (LATIN_WIKTIONARY=0, LATIN_TAGGER=0)。作る言語の辞書 (ロシア語・
#   アラビア語 …) は環境にあるものを使い、無い言語 (出力に出ない言語) は飛ばす
#
import os
import re
import sys
import difflib
import functools
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN_DIR = os.path.join(ROOT, 'test', 'golden', 'generate')
SAMPLES = os.path.join(ROOT, 'samples', 'samples.txt')
LANGUAGE_LINE = re.compile(r'^  (\S[^:：]*?):\s')
CONTINUATION = ' ' * 12

# 出力の見出し → 正解ファイルの名前
LABELS = {'英語': 'en', 'ロシア語': 'ru', '梵語': 'sa', 'ギリシア語': 'grc', 'インドネシア語': 'id', 'タガログ語': 'tl',
          'アラビア語': 'ar', 'ヘブライ語': 'he', 'ペルシア語': 'fa', 'ヒンディー語': 'hi', 'ウルドゥー語': 'ur',
          'アイヌ語': 'ain', 'チベット語': 'bo', '日本語': 'ja', '古文': 'kobun', 'ラテン語': 'la'}


@functools.lru_cache(maxsize=1)
def generated():
    """言語の名前 → 生成結果 (文ごとに、元の文の行 + その言語の行)。文の枠は 'frame'"""
    result = subprocess.run([sys.executable, os.path.join('tools', 'generate.py'), SAMPLES], cwd=ROOT,
                            capture_output=True, text=True,
                            env=dict(os.environ, PYTHONHASHSEED='0', LATIN_WIKTIONARY='0', LATIN_TAGGER='0'))
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    out = {}
    current = None
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        if not line.startswith(' '):   # 元の文
            for lines in out.values():
                lines.append(line)
            out.setdefault('frame', [line])
            current = None
            continue
        m = LANGUAGE_LINE.match(line)
        if m and m.group(1) in LABELS:
            current = LABELS[m.group(1)]
            out.setdefault(current, [])
            out[current].append(line)
        elif line.startswith(CONTINUATION) and current is not None:
            out[current].append(line)
        else:   # 文の枠 (述語・役割) と、作れない言語の行
            current = None
            out['frame'].append(line)
    return {lang: '\n'.join(lines) + '\n' for lang, lines in out.items()}


class GenerateGoldenTestCase(unittest.TestCase):
    maxDiff = None


def make_test(lang):
    def test(self):
        golden_file = os.path.join(GOLDEN_DIR, lang + '.out')
        actual = generated().get(lang)
        if actual is None:
            self.skipTest('%s の辞書が無い (生成結果に出ない)' % lang)
        if os.environ.get('UPDATE_GOLDEN') or not os.path.exists(golden_file):
            os.makedirs(GOLDEN_DIR, exist_ok=True)
            with open(golden_file, 'w', encoding='utf-8') as f:
                f.write(actual)
            return
        with open(golden_file, encoding='utf-8') as f:
            expected = f.read()
        if actual != expected:
            diff = ''.join(difflib.unified_diff(expected.splitlines(True), actual.splitlines(True),
                                                lang + '.out', 'actual', n=1))
            self.fail('%s の生成結果が変わりました:\n%s' % (lang, diff))
    return test


for _lang in ['frame'] + sorted(set(LABELS.values())):
    setattr(GenerateGoldenTestCase, 'test_' + _lang, make_test(_lang))


if __name__ == '__main__':
    unittest.main()
