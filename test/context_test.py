#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文脈の訳語 (core/analyzer.verbs_in_context): 動詞の訳語を目的語で選ぶ (take + medicine →「飲む」、tell + lie →「つく」)。
# 言語をまたいで。辞書の無い言語は飛ばす
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402

CASES = [
    ('russian', 'Она плетёт нить.', '糸を / 繰る'),           # Wiktionary の語義 spin + thread
    ('russian', 'Он принимает лекарство.', '薬を / 飲む'),    # 主格・対格の同じ形の目的語 (Nom/Acc の枠)
    ('russian', 'Он говорит ложь.', '嘘を / つく'),           # 手で決めた訳語「言う」+ 嘘
    ('greek', 'φάρμακον λαμβάνει.', '薬を / 飲む'),            # 中性名詞 (主格・対格の同じ形) + 他動詞は目的語
    ('latin', 'Medicāmentum sūmit.', '薬品}を / 飲む'),
    ('german', 'Er nimmt Medizin.', '薬を / 飲む'),           # 手で決めた訳語「取る」+ 薬
    ('german', 'Er erzählt eine Lüge.', '嘘を / つく'),
    ('french', 'Il dit un mensonge.', '嘘を / つく'),
    ('finnish', 'Hän ottaa lääkettä.', '薬を / 飲む'),
    ('english', 'He takes medicine.', '薬を / 飲む'),
    ('korean', '그는 약을 먹었다.', '薬を / 飲んだ'),            # 약 は 藥 (花札の「役」でなく)、食べる + 薬
    ('mongolian', 'Тэр эм уусан.', '彼は / {薬,薬剤}を / 飲んだ'),   # эм「薬」(「雌」でなく)、тэр は主語の代名詞
    ('portuguese', 'Ele toma remédio.', '薬を / 飲む'),         # spaCy が形容詞と読む名詞
]


class ContextTestCase(unittest.TestCase):
    def test_verbs_in_context(self):
        for module, text, expected in CASES:
            with self.subTest(module=module, text=text):
                if not available(module):
                    self.skipTest('%s のデータが無い' % module)
                self.assertIn(expected, translate(module, text))

    def test_suru_not_doubled(self):
        from dragoman.core import en_ja
        self.assertNotIn('服するする', en_ja.verb_in_context('take', ['medicine']) + en_ja.lookup('impose', 'verb'))
        self.assertNotIn('課するする', en_ja.lookup('impose', 'verb'))

    def test_hand_glossed_verbs_kept(self):
        # 手で決めた動詞の訳語は、表 (HAND_VERB_CONTEXTS) に無い組み合わせでは選び直さない
        if available('korean'):
            self.assertIn('送った', translate('korean', '나는 어제 친구에게 편지를 보냈습니다.'))
            self.assertIn('ご飯を / 食べた', translate('korean', '그는 밥을 먹었다.'))
        if available('mongolian'):
            self.assertIn('その人は / 来た', translate('mongolian', 'Тэр хүн ирсэн.'))   # 自動詞の前の тэр は指示詞


if __name__ == '__main__':
    unittest.main()
