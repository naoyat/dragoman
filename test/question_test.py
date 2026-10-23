#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 間接疑問 (共通の解析器の core/Question.py と、言語の設定の question_verbs・interrogatives) を言語をまたいで
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402


class IndirectQuestionTestCase(unittest.TestCase):
    def check(self, module, text, expected):
        if not available(module):
            self.skipTest('%s のデータが無い' % module)
        self.assertEqual(translate(module, text), expected)

    def test_french(self):
        self.check('french', 'Je ne sais pas où il habite.', '私が / {{彼,それ}が どこで 住む}かを / 知らない')
        self.check('french', "Je ne sais pas s'il vient.", '私が / {{彼,それ}が 来る}かどうかを / 知らない')

    def test_german(self):
        self.check('german', 'Ich weiß nicht, wo er wohnt.', '私が / {彼が どこで 住む}かを / 知らない')
        self.check('german', 'Ich frage, ob er kommt.', '私が / {彼が 来る}かどうかを / 尋ねる')

    def test_russian(self):   # когда は接続詞「〜するとき」でなく「いつ」
        self.assertIn('{彼が いつ 来るだろう', translate('russian', 'Я не знаю, когда он придёт.'))
        self.assertIn('}かを / 知らない', translate('russian', 'Я не знаю, где он живёт.'))   # 知る,知っている → 知らない (1つ)

    def test_finnish(self):
        self.check('finnish', 'En tiedä, missä hän asuu.', '私が / {彼が どこで 住む}かを / 知らない')

    def test_hindi(self):   # 補文の कि は訳さない
        self.assertIn('どこに 住む,とどまる}かを / 知らない', translate('hindi', 'मैं नहीं जानता कि वह कहाँ रहता है।'))

    def test_indonesian(self):   # di mana は1語の「どこで」
        self.check('indonesian', 'Saya tidak tahu di mana dia tinggal.', '私が / {どこで 彼が 住む}かを / 知らない')
        self.check('indonesian', 'Di mana kamu tinggal?', 'どこで / あなたが / 住むか')


class SecondNominativeTestCase(unittest.TestCase):
    def test_russian(self):   # 主格にしか読めない語と並んだ、対格にも読める語は目的語
        self.assertEqual(translate('russian', 'Она любит мать.'), '彼女が / 母を / 好む,愛する')


if __name__ == '__main__':
    unittest.main()
