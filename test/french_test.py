#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語: 役割からの格、冠詞・縮約形・部分冠詞、接語の代名詞、動詞の組 (複合過去・受動・話法の助動詞)、
# 否定、il y a、関係節、de 句の属格、日本語訳 (french.analyzer)。名前のカタカナ。
# spaCy のフランス語モデルか辞書 (tools/build_french_dic.py) が無ければ飛ばす
#
import unittest

from dragoman.core.katakana_names import latin

try:
    from dragoman.french import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'spaCy のフランス語モデルかフランス語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_roles_and_articles(self):
        self.assertEqual(self.ja("Le garçon lit un livre à l'école."), '少年が / {学校}〜に,〜で / 本を / 読む')   # lit を動詞に
        self.assertEqual(self.ja('Le livre du professeur est sur la table.'), '{机}〜の上に / {先生の}本が / ある')
        self.assertEqual(self.ja('Je veux manger du pain.'), '私が / パンを / 食べたい')            # 部分冠詞
        self.assertEqual(self.ja('Nous parlons du film.'), '私たちが / {映画}〜について / 話す')    # parler de

    def test_clitics_and_verb_groups(self):
        self.assertEqual(self.ja('Je le lui ai donné hier.'), '私が / 彼に / 彼を / 昨日 / 与えた')
        self.assertEqual(self.ja('Elle est allée au marché avec son ami.'),
                         '彼女が / {市場}〜に,〜で / {{彼の}友達}〜と,〜で / 行った')                # être + 移動の動詞
        self.assertEqual(self.ja('Le livre a été écrit par le professeur.'), '本が / {先生}〜によって / 書かれた')
        self.assertEqual(self.ja('Nous voulons lire un livre.'), '私たちが / 本を / 読みたい')

    def test_negation_existential_clauses(self):
        self.assertEqual(self.ja('Il ne mange pas de pain.'), '彼が / パンを / 食べない')
        self.assertEqual(self.ja('Il y a un chat dans le jardin.'), '猫が / {庭}〜の中で,〜で / ある,いる')
        self.assertEqual(self.ja('La fille qui chante est ma sœur.'), '{歌う}少女,娘は / {私の}姉妹である')
        self.assertEqual(self.ja("Je sais que tu m'aimes."), '私が / 知っている / 〜ということ / 君が / 私を / 愛する,好む')

    def test_names(self):
        self.assertEqual(self.ja('Jean aime Marie.'), 'ジャンが / マリを / 愛する,好む')


class KatakanaTestCase(unittest.TestCase):
    def test_french_names(self):
        self.assertEqual([latin(n, 'fr') for n in ('Jean', 'Paris', 'Rousseau', 'Michel', 'Camus', 'Claude', 'Vincent')],
                         ['ジャン', 'パリ', 'ルソー', 'ミシェル', 'カミュ', 'クロード', 'ヴァンサン'])


if __name__ == '__main__':
    unittest.main()
