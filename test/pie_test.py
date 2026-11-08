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
            'Tat kukruvants avis agram ā bhugat.': '羊が / {それを 聞いて} / 野を / 逃げた',
        }
        for text, expected in cases.items():
            self.assertEqual(tr(text), expected, text)
        self.assertIn('羊には / 羊毛が / ない', tr('avibhjams ka varnā na asti.'))
        self.assertIn('{羊毛が なかった}羊が', tr('Avis, jasmin varnā na ā ast, dadarka akvams.'))

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
