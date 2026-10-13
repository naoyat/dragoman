#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語: 読みの選択、格・所有の接尾辞、時制・人称、繋辞の補い、分詞の関係節、副動詞、語順のままの訳 (turkish.analyzer)。
# zeyrek か辞書 (tools/build_turkish_dic.py) が無ければ飛ばす
#
import unittest

try:
    from dragoman.turkish import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'zeyrek かトルコ語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def analyze(self, text):
        return next(analyzer.analyze_text(text))

    def ja(self, text):
        a = self.analyze(text)
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def lit(self, text):
        return self.analyze(text).literal

    def test_cases(self):
        self.assertEqual(self.ja('Çocuk okulda kitap okudu.'), '子供は / 学校で / 本を / 読んだ')   # 不定の目的語
        self.assertEqual(self.ja('Annem bana bir mektup yazdı.'), '私の母は / 私に / 手紙を / 書いた')
        self.assertEqual(self.ja("Yarın İstanbul'a gideceğiz."), '明日 / 我々が / イスタンブールに / 行くだろう')

    def test_copula(self):
        self.assertEqual(self.ja('Ben öğretmenim.'), '私は / 先生である')
        self.assertEqual(self.ja('Kitap masada.'), '机に / 本は / ある')     # 位格の述語は存在
        self.assertEqual(self.ja('Bu ev çok büyük değil.'), 'とても,多い / {この}家は / 大きくない')

    def test_literal(self):
        self.assertEqual(self.lit("Ali'nin okuduğu kitap güzeldi."), 'Aliが 読んだ 本は 美しかった。')
        self.assertEqual(self.lit('Eve gelince yemek yedik.'), '家に 来ると 食事を 食べた。')
        self.assertEqual(self.lit('Kitap okuyan çocuk benim kardeşim.'), '本を 読む 子供は 私の 兄弟だ。')
        self.assertEqual(self.lit('Kapıyı açıp içeri girdi.'), 'ドアを 開けて 中へ 入った。')
        self.assertEqual(self.lit('Dün akşam evde değildim.'), '昨日 夕方 家に いなかった。')
        self.assertEqual(self.lit('Sen bu filmi gördün mü?'), '君は この 映画を 見たか？')
        self.assertEqual(self.lit('Bu kitap Ali tarafından yazıldı.'), 'この 本は Ali によって 書かれた。')

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('Çocuk okulda kitap okudu.'), 'tr')


if __name__ == '__main__':
    unittest.main()
