#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 17世紀のフランス語の綴り → 今の綴り (french/orthography.py)。フランス語の辞書が無ければ飛ばす
#
import unittest

from dragoman.french import dictionary, orthography as o


@unittest.skipUnless(dictionary.available(), 'フランス語の辞書が無い')
class OrthographyTestCase(unittest.TestCase):
    def test_rules(self):
        words = ('estoit', 'avoit', 'estoient', 'teste', 'escrire', 'maistre', 'luy', 'cecy', 'bontez', 'enfans',
                 'sçavoir', 'foible', 'auoir', 'vn', 'iamais', 'connoissance', 'cognoistre', 'isle', 'hostel',
                 'plustost', 'ſçay', 'diſcours')
        self.assertEqual([o.modern(w, True) for w in words],
                         ['était', 'avait', 'étaient', 'tête', 'écrire', 'maître', 'lui', 'ceci', 'bontés', 'enfants',
                          'savoir', 'faible', 'avoir', 'un', 'jamais', 'connaissance', 'connaître', 'île', 'hôtel',
                          'plutôt', 'sais', 'discours'])

    def test_descartes(self):
        # 『方法序説』(1637。Adam・Tannery 版の綴り) の語: u と v、アクサンの無い e、見出しの語 (est・esprit) はそのまま
        words = ('eſt', 'eſprit', 'ſouuent', 'liures', 'peuuent', 'ſuiure', 'conuerſation', 'auoit', 'verité', 'extreme',
                 'deſirer', 'moymeſme', 'peuteſtre', 'eſcholes', 'acheué', 'vraye', 'celebres', 'ames')
        self.assertEqual([o.modern(w, True) for w in words],
                         ['est', 'esprit', 'souvent', 'livres', 'peuvent', 'suivre', 'conversation', 'avait', 'vérité',
                          'extrême', 'désirer', 'moi-même', 'peut-être', 'écoles', 'achevé', 'vraie', 'célèbres', 'âmes'])
        self.assertEqual(o.tokens('il a eſcrit vne lettre a ſon pere'.split())[0][:6],
                         ['il', 'a', 'écrit', 'une', 'lettre', 'à'])   # アクサンの無い前置詞 a

    def test_modern_words_kept(self):
        # 今の綴りにもよくある並び (oi) の語はそのまま: soit を sait、François を Français にしない
        self.assertEqual([o.modern(w, True) for w in ('soit', 'doit', 'croit', 'François', 'avez')],
                         ['soit', 'doit', 'croit', 'François', 'avez'])
        self.assertEqual(o.modern('teste', False), 'teste')   # 古い綴りの印の無い文では「試す」のまま

    def test_old_style(self):
        self.assertTrue(o.old_style('Il estoit vn Roy'))
        self.assertTrue(o.old_style('de ſon diſcours'))
        self.assertFalse(o.old_style('Le bon sens est la chose du monde la mieux partagée.'))


if __name__ == '__main__':
    unittest.main()
