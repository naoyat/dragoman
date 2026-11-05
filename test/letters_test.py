#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ノートの文字の図 (core/letters.py): 塊の切り分け・字の名前・語の中の形・図にする語
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import letters  # noqa: E402


class LettersTestCase(unittest.TestCase):
    def test_clusters(self):
        self.assertEqual(letters.clusters('كتاب'), ['ك', 'ت', 'ا', 'ب'])
        self.assertEqual(letters.clusters('قَرَأَ'), ['قَ', 'رَ', 'أَ'])          # 母音記号は前の字に
        self.assertEqual(letters.clusters('गच्छति'), ['ग', 'च्छ', 'ति'])      # ヴィラーマの後ろの子音は同じ塊に
        self.assertEqual(letters._parts('학'), ['ᄒ', 'ᅡ', 'ᆨ'])  # ハングルは字母に

    def test_labels(self):
        self.assertEqual(letters.unicode_label('ة'), 'teh marbuta')
        self.assertEqual(letters.unicode_label('ि'), '母音記号 i')
        self.assertEqual(letters.unicode_label('᠎'), '母音分離記号')

    def test_forms(self):
        seq = letters.clusters('كتاب')
        self.assertEqual(letters._form(seq, 0), 'ك‍')           # 語頭の形
        self.assertEqual(letters._form(seq, 1), '‍ت‍')     # 語中
        self.assertEqual(letters._form(seq, 3), 'ب')                 # ا は後ろにつながらない

    def test_persian_urdu(self):
        seq = letters.clusters('می\u200cروم')                          # ZWNJ は前の字の塊に
        self.assertEqual(seq[1], 'ی\u200c')
        self.assertEqual(letters._form(seq, 2), 'ر')                   # ZWNJ の後ろはつなげない
        self.assertEqual(letters.words_of('لڑکا کتاب پڑھتا ہے۔'), ['لڑکا', 'کتاب', 'پڑھتا', 'ہے'])   # ۔ は句点
        self.assertIn('lang="ur"', letters.part_html(['کتاب'], lang='ur'))   # 書体を言語で (ナスタアリーク体)

    def test_part(self):
        self.assertEqual(letters.part_html(['Puella', 'rosam']), '')   # ラテン文字は図にしない
        html = letters.part_html(['⁧كتاب⁩', 'كتاب'])            # 方向の制御の文字は除き、同じ語は1度
        self.assertEqual(html.count('<div class="lw"'), 1)
        self.assertIn('dir="rtl"', html)
        self.assertIn(' lv', letters.part_html(['ᠨᠣᠮ']))                 # モンゴル文字は縦に


if __name__ == '__main__':
    unittest.main()
