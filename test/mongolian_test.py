#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語: 語形の規則 (格・副動詞・分詞・否定)、転写からの入力、語順のままの訳 (mongolian.*)。
# 辞書 (tools/build_mongolian_dic.py) が無ければ解析の試験を飛ばす
#
import unittest

from dragoman.mongolian import script

try:
    from dragoman.mongolian import analyzer, dictionary, morphology
    HAVE_DATA = dictionary.available()
except ImportError:
    HAVE_DATA = False


class ScriptTestCase(unittest.TestCase):
    def test_from_latin(self):
        self.assertEqual(script.from_latin('Xüü öcigdör oxin-d nom ög-sön.'), 'Хүү өчигдөр охинд ном өгсөн.')
        self.assertEqual(script.from_latin('sajn'), 'сайн')        # 母音の後ろの j は й
        self.assertEqual(script.from_latin('soyoo'), 'соёо')       # y + 母音は ё
        self.assertEqual(script.from_latin('Сайн байна уу'), 'Сайн байна уу')


@unittest.skipUnless(HAVE_DATA, 'モンゴル語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def lit(self, text):
        return next(analyzer.analyze_text(text)).literal

    def test_morphology(self):
        first = lambda w: morphology.analyses(w)[0]
        self.assertEqual((first('номыг')['lemma'], first('номыг')['case']), ('ном', 'Acc'))
        r = first('явсангүй')
        self.assertEqual((r['lemma'], r['tense'], r['negated']), ('явах', 'perfect', True))
        r = first('иртэл')
        self.assertEqual((r['lemma'], r['converb']), ('ирэх', 'until'))
        self.assertEqual(first('амьдардаг')['lemma'], 'амьдрах')        # 語幹の母音の挿入

    def test_literal(self):
        self.assertEqual(self.lit('Хүү өчигдөр охинд ном өгсөн.'), '少年は 昨日 少女に 本を 与えた。')
        self.assertEqual(self.lit('Би Монголд байхдаа энэ номыг авсан.'), '私は モンゴルに いる時に この 本を 取った。')
        self.assertEqual(self.lit('Би чамайг иртэл хүлээнэ.'), '私は 君を 来るまで 待つ。')
        self.assertEqual(self.lit('Тэр сандал дээр суугаад ном уншиж байна.'), 'その 椅子の上で 座って 本を 読んでいる。')
        self.assertEqual(self.lit('Бид өчигдөр кино үзсэнгүй.'), '私たちは 昨日 映画を 見なかった。')
        self.assertEqual(self.lit('Батын бичсэн захиа ширээн дээр байна.'), 'バトが 書いた 手紙は 机の上に ある。')
        self.assertEqual(self.lit('Энэ бол миний ном.'), 'これは 私の 本だ。')

    def test_latin_input(self):
        self.assertEqual(self.lit('Xüü öcigdör oxin-d nom ög-sön.'), '少年は 昨日 少女に 本を 与えた。')

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('Хүү өчигдөр охинд ном өгсөн.'), 'mn')
        self.assertEqual(detect('Я люблю тебя.'), 'ru')


if __name__ == '__main__':
    unittest.main()
