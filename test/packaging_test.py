#!/usr/bin/env python
# -*- coding: utf-8 -*-
# パッケージ: 実行に要るデータ (ラテン語の手作りの辞書) はパッケージの中にあり、wheel に同梱する設定がある
import glob
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dragoman.latin import words  # noqa: E402


class PackagingTestCase(unittest.TestCase):
    def test_dictionary_inside_package(self):
        package = os.path.dirname(os.path.abspath(words.__file__))
        self.assertEqual(os.path.dirname(words.WORDS_DIR), package)   # ソースツリーの配置に頼らない
        names = {os.path.basename(p) for p in glob.glob(os.path.join(words.WORDS_DIR, '*.def'))}
        self.assertTrue({'noun.def', 'verb.def', 'adj.def', 'adv.def', 'prep.def', 'other.def'} <= names)

    def test_package_data_declared(self):
        try:
            import tomllib
        except ImportError:
            self.skipTest('tomllib が無い (Python 3.11 未満)')
        with open(os.path.join(ROOT, 'pyproject.toml'), 'rb') as f:
            config = tomllib.load(f)
        self.assertIn('data/*.def', config['tool']['setuptools']['package-data']['dragoman.latin'])


if __name__ == '__main__':
    unittest.main()
