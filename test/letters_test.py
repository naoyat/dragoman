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
        self.assertEqual(letters.unicode_label('ة'), 'ta marbuta')        # 慣用の名前 (Unicode は teh marbuta)
        self.assertEqual(letters.unicode_label('ھ'), 'do-chashmi he')    # Unicode は heh doachashmee
        self.assertEqual(letters.unicode_label('འ'), "'a (a chung)")       # Unicode は -a
        self.assertEqual(letters.unicode_label('ि'), '母音記号 i')
        self.assertEqual(letters.unicode_label('ा'), '母音記号 ā')
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

    def test_native_names(self):
        from dragoman.core import letter_names
        self.assertEqual(letter_names.native('ar')('ب'), ('باء', 'bāʾ'))
        self.assertEqual(letter_names.native('ur')('ے'), ('بڑی یے', 'baṛī ye'))
        self.assertEqual(letter_names.native('ko')('\u11a8'), ('기역', 'giyeok'))     # 終声の ㄱ
        self.assertEqual(letter_names.native('sa')('ि'), ('इकार', 'ikāra'))
        self.assertEqual(letter_names.native('hi')('ा'), ('आ की मात्रा', 'ā kī mātrā'))
        self.assertEqual(letter_names.native('mn')('ᠨ'), ('ᠨᠠ', 'na (на)'))   # 子音は a を付けた音節
        self.assertEqual(letter_names.native('mn')('ᠥ'), ('ᠥ', 'ö (ө)'))
        self.assertEqual(letter_names.native('mn')('ᠬ', 'ᠬᠥᠪᠡᠭᠦᠨ'), ('ᠬᠡ', 'ke (кэ)'))   # 前舌母音の語は ke
        self.assertEqual(letter_names.native('mn')('ᠬ', 'ᠬᠠᠭᠠᠨ'), ('ᠬᠠ', 'qa (ха)'))
        self.assertIsNone(letter_names.native('la'))
        self.assertIn('باء', letters.part_html(['كتاب'], lang='ar'))
        self.assertEqual(letters.unicode_label('ढ'), 'ḍha')

    def test_greek_cyrillic(self):
        from dragoman.core import letter_names
        self.assertEqual(letters._parts('ἄ'), ['α', '\u0313', '\u0301'])   # 合成済みの字は分解して
        self.assertEqual(letters.unicode_label('Ω'), '大文字 omega')
        self.assertEqual(letters.unicode_label('λ'), 'lambda')          # 慣用の名前 (Unicode は lamda)
        self.assertEqual(letters.unicode_label('Е'), '大文字 ye')       # Unicode は ie
        self.assertEqual(letters.unicode_label('\u0314'), 'rough breathing')
        self.assertEqual(letters.unicode_label('ח'), 'ḥet')                      # ヘブライ文字
        self.assertEqual(letters.unicode_label('\u05bc'), '点 dagesh')          # Unicode は dagesh or mapiq
        self.assertEqual(letters.unicode_label('\u110c'), '初声 jieut')         # ハングル (Unicode は cieuc)
        self.assertEqual(letters.unicode_label('\u11a8'), '終声 giyeok')
        self.assertEqual(letters.unicode_label('\u1165'), '中声 eo')
        self.assertEqual(letter_names.native('grc')('\u0314'), ('δασεῖα', 'daseia (有気記号)'))
        self.assertEqual(letter_names.native('ru')('Ь'), ('мягкий знак', 'myagkiy znak'))   # 大文字も小文字の表で
        self.assertEqual(letter_names.native('mn')('ө', 'өгсөн'), ('ө', 'ö'))             # モンゴル語のキリル文字
        self.assertEqual(letter_names.native('mn')('л', 'ном'), ('эл', 'el'))
        self.assertIn('final sigma', letters.part_html(['λόγος']))   # ギリシア文字も図に
        self.assertEqual(letters.part_html(['Puella']), '')

    def test_part(self):
        self.assertEqual(letters.part_html(['Puella', 'rosam']), '')   # ラテン文字は図にしない
        html = letters.part_html(['⁧كتاب⁩', 'كتاب'])            # 方向の制御の文字は除き、同じ語は1度
        self.assertEqual(html.count('<div class="lw"'), 1)
        self.assertIn('dir="rtl"', html)
        self.assertIn(' lv', letters.part_html(['ᠨᠣᠮ']))                 # モンゴル文字は縦に

    def test_siddham(self):
        hrih = '\U000115ae\U000115bf\U000115a8\U000115b1\U000115be'   # 悉曇文字の hrīḥ は1つの塊
        self.assertEqual(letters.clusters(hrih), [hrih])
        self.assertEqual(letters.unicode_label('\U0001158e'), 'ka')      # 同じ名前のデーヴァナーガリーの字の IAST
        self.assertEqual(letters.unicode_label('\U000115b1'), '母音記号 ī')
        from dragoman.core import letter_names
        names = letter_names.native('sa')
        self.assertEqual(names('\U0001158e'), ('キャ', ''))              # 日本の字母の読み
        self.assertEqual(names('\U000115bd'), ('空点', 'ン'))
        self.assertEqual(names('\U000115af'), ('修行点', 'アー'))
        self.assertEqual(names('क'), ('ककार', 'kakāra'))                # デーヴァナーガリーはそのまま


if __name__ == '__main__':
    unittest.main()
