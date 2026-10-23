#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 関係節 (共通の解析器の core/Relative.py と、解析器が名詞の訳に組み込むもの) を言語をまたいで
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402


class RelativeTestCase(unittest.TestCase):
    def check(self, module, text, expected):
        if not available(module):
            self.skipTest('%s のデータが無い' % module)
        tr = translate(module, text)
        self.assertIn(expected, tr)

    def test_german(self):   # 名詞 + カンマの後ろの der (spaCy は指示代名詞にすることがある)
        self.check('german', 'Der Mann, der kam, sah mich.', '来た男が / 私を / 見た')
        self.check('german', 'Ich sah den Mann, der kam.', '来た男を')

    def test_sanskrit(self):   # yaḥ … saḥ (前の関係節の中の先行詞 naraḥ を saḥ の訳に)
        self.check('sanskrit', 'यः नरः आगच्छत् सः माम् अपश्यत्।', '}人間が / 私を')

    def test_hindi(self):   # जो … उसने
        self.check('hindi', 'जो आदमी आया उसने मुझे देखा।', '来た{男,人}が')

    def test_hebrew(self):   # 名詞の後ろの אֲשֶׁר
        self.check('hebrew', 'הָאִישׁ אֲשֶׁר בָּא רָאָה אֹתִי.', '入った{男,男性,夫}が / 私を')

    def test_persian(self):   # 名詞 + -i + که
        self.check('persian', 'مردی که آمد مرا دید.', '来た男が / 私を / 見た')
        self.check('persian', 'کتابی که خواندم خوب بود.', '{私が 読んだ,歌った}本は / 良かった')   # 主節の主語

    def test_indonesian(self):   # yang + 動作主 + 動詞
        self.check('indonesian', 'Buku yang saya baca bagus.', '私が読む本は / 良い')

    def test_turkish(self):   # 分詞 (形容詞 gelen「次の」でなく)
        self.check('turkish', 'Gelen adam beni gördü.', '来る男は')
        self.check('turkish', 'Kitap okuyan çocuk geldi.', '{本を 読む}子供は / 来た')

    def test_mongolian(self):   # 分詞 (形容詞 ирсэн「訪問の」でなく)、間投詞でない хүн、分詞の後ろの名詞は主語
        self.check('mongolian', 'Ирсэн хүн намайг харсан.', '来た人は / 私を / 見た')
        self.check('mongolian', 'Номыг уншсан хүүхэд ирсэн.', '}{子供,仔やぎの革}は / 来た')


if __name__ == '__main__':
    unittest.main()
