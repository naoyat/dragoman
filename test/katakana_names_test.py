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
        self.assertEqual([k.latin(n, 'fi') for n in ('Matti', 'Liisa', 'Anna', 'Jyväskylä')],
                         ['マッティ', 'リーサ', 'アンナ', 'ユヴァスキュラ'])           # 重子音は ッ
        self.assertEqual([k.latin(n, 'de') for n in ('Hänsel', 'Müller', 'Heinrich', 'Stefan', 'München')],
                         ['ヘンゼル', 'ミュラー', 'ハインリヒ', 'シュテファン', 'ミュンヘン'])

    def test_russian(self):
        self.assertEqual([k.russian(n) for n in ('Иван', 'Пётр', 'Чехов', 'Достоевский', 'Татьяна', 'Москва')],
                         ['イヴァン', 'ピョートル', 'チェホフ', 'ドストエフスキー', 'タティヤナ', 'モスクヴァ'])

    def test_korean(self):
        self.assertEqual([k.korean(n) for n in ('민수', '김철수', '서울', '경희', '최', '민기', '대구')],
                         ['ミンス', 'キムチョルス', 'ソウル', 'キョンヒ', 'チェ', 'ミンギ', 'テグ'])


if __name__ == '__main__':
    unittest.main()
