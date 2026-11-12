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
    ('greek', 'φάρμακον λαμβάνει.', '飲む'),
    ('german', 'Er nimmt Medizin.', '薬を / 飲む'),           # 手で決めた訳語「取る」+ 薬
    ('german', 'Er erzählt eine Lüge.', '嘘を / つく'),
    ('french', 'Il dit un mensonge.', '嘘を / つく'),
    ('finnish', 'Hän ottaa lääkettä.', '薬を / 飲む'),
    ('english', 'He takes medicine.', '薬を / 飲む'),
]


class ContextTestCase(unittest.TestCase):
    def test_verbs_in_context(self):
        for module, text, expected in CASES:
            with self.subTest(module=module, text=text):
                if not available(module):
                    self.skipTest('%s のデータが無い' % module)
                self.assertIn(expected, translate(module, text))

    def test_hand_glossed_verbs_kept(self):
        # 手で決めた動詞の訳語は、表 (HAND_VERB_CONTEXTS) に無い組み合わせでは選び直さない
        if available('korean'):
            self.assertIn('送った', translate('korean', '나는 어제 친구에게 편지를 보냈습니다.'))


if __name__ == '__main__':
    unittest.main()
