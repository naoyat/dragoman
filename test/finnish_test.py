#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語: 格 (15格)、目的語の格の読み替え、否定動詞・完了・話法の動詞のまとめ、所有の構文 (finnish.analyzer)。
# spaCy のフィンランド語モデルか辞書 (tools/build_finnish_dic.py) が無ければ飛ばす
#
import unittest

try:
    from dragoman.finnish import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'spaCy のフィンランド語モデルかフィンランド語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_cases(self):
        self.assertEqual(self.ja('Menen huomenna Helsinkiin junalla.'), '明日 / 私が / ヘルシンキへ / 列車で / 行く')
        self.assertIn('子供に', self.ja('Äiti antoi lapselle omenan.'))           # 向格「〜に」
        self.assertIn('りんごを', self.ja('Äiti antoi lapselle omenan.'))         # 目的語の属格 → 対格

    def test_verb_groups(self):
        self.assertEqual(self.ja('Olen lukenut tämän kirjan.'), '私が / この本を / 読んだ')       # 完了
        self.assertIn('来なかった', self.ja('Hän ei tullut eilen kotiin.'))                        # 否定動詞 ei
        self.assertEqual(self.ja('Voin puhua suomea.'), '私が / フィンランド語を / 話すことができる')

    def test_possession(self):
        self.assertEqual(self.ja('Minulla on kaksi kissaa.'), '私には / 二つの猫が / いる')         # 所格 + olla

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('Minulla on kaksi kissaa.'), 'fi')


if __name__ == '__main__':
    unittest.main()
