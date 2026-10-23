#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# マレー語 (解析はインドネシア語と共通で、マレー語の辞書の項目を先に引く)
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402


@unittest.skipUnless(available('malay'), 'マレー語の辞書が無い (tools/build_indonesian_dic.py)')
class MalayTestCase(unittest.TestCase):
    def test_sentence(self):
        self.assertEqual(translate('malay', 'Saya membaca buku.'), '私が / 本を / 読む')

    def test_malay_spellings(self):   # kerana (インドネシア語の karena) の副詞節
        self.assertIn('}ので / ', translate('malay', 'Saya makan kerana saya lapar.'))

    def test_kana(self):
        from dragoman.core.ruby import ruby
        self.assertEqual([r['kana'] for r in ruby('Saya pergi ke sekolah.', 'ms')], ['サヤ', 'ペルギ', 'ケ', 'セコラ', ''])


if __name__ == '__main__':
    unittest.main()
