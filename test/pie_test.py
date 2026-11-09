#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 印欧祖語 (dragoman/pie): シュライヒャーの寓話の語の辞書引き・訳・カタカナ読み (データは要らない)
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.pie import analyzer, dictionary, katakana   # noqa: E402


def tr(text):
    from adverbial_test import translate
    return translate('pie', text)


class PieTestCase(unittest.TestCase):
    def test_lookup(self):
        item = dictionary.lookup('Avis')[0]
        self.assertEqual((item['ja'], item['_']), ('羊', [('Nom', 'sg', 'f')]))
        self.assertEqual(dictionary.modern('avi'), '*h₂ówis')
        self.assertIn(('la', 'ovis'), dictionary.cognates('avi'))

    def test_katakana(self):
        self.assertEqual([katakana.katakana(w) for w in ('avis', 'akvāsas', 'bhāram', 'jasmin')],
                         ['アヴィス', 'アクヴァーサス', 'バーラム', 'ヤスミン'])

    def test_sentences(self):
        cases = {
            'Avis akvabhjams ā vavakat:': '羊が / 馬に / 言った',
            'Tat kukruvants avis agram ā bhugat.': '羊が / {それを 聞いて} / 野へ / 逃げた'   # 方向の対格,
        }
        for text, expected in cases.items():
            self.assertEqual(tr(text), expected, text)
        self.assertIn('羊には / 羊毛が / ない', tr('avibhjams ka varnā na asti.'))
        self.assertIn('{その上に 羊毛が なかった}羊が', tr('Avis, jasmin varnā na ā ast, dadarka akvams.'))
        # 配分の tam「一頭は」: 分詞は tam に掛け、名詞はその目的語。分詞の無い区切りは次の区切りの分詞を補う
        self.assertIn('馬={重い車を 引いている}一頭={大きい荷を 運んでいる}一頭={人を 速く 運んでいる}一頭を / 見た',
                      tr('Avis dadarka akvams, tam, vāgham garum vaghantam, tam, bhāram magham, tam, manum āku bharantam.'))

    def test_title(self):   # 動詞の無い表題 (後置の ka の並列)
        import subprocess
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.run([sys.executable, os.path.join(root, 'dragoman.py'), 'ine', '-w', '-e', 'Avis akvāsas ka.'],
                             capture_output=True, text=True).stdout
        self.assertIn('→  羊と馬', out)

    def test_augment(self):
        words = analyzer.lookup_all(['Avis', 'ā', 'vavakat', ':'])
        self.assertEqual([w.surface for w in words], ['Avis', 'vavakat', ':'])
        self.assertTrue(words[1].items[0].attrib('augment'))


if __name__ == '__main__':
    unittest.main()
