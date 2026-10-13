#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 固有名詞のカタカナ表記 (core/katakana_names.py): トルコ語・モンゴル語・ラテン文字の名前
#
import unittest

from dragoman.core import katakana_names as k


class KatakanaNamesTestCase(unittest.TestCase):
    def test_turkish(self):
        self.assertEqual([k.turkish(n) for n in ('Ali', 'Ayşe', 'Çağlar', 'İstanbul', 'Gönül', 'Türkiye')],
                         ['アリ', 'アイシェ', 'チャーラル', 'イスタンブル', 'ギョニュル', 'テュルキイェ'])

    def test_mongolian(self):
        self.assertEqual([k.mongolian(n) for n in ('Бат', 'Дорж', 'Улаанбаатар', 'Дулмаа', 'Сүхбаатар')],
                         ['バト', 'ドルジ', 'ウラーンバータル', 'ドゥルマー', 'スフバータル'])

    def test_latin_script(self):
        self.assertEqual([k.latin(n) for n in ('Helsinki', 'Berlin')], ['ヘルシンキ', 'ベルリン'])


if __name__ == '__main__':
    unittest.main()
