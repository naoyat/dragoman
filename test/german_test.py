#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語: 格・冠詞、動詞の組 (完了・受動・未来・話法の助動詞)、分離動詞、副文、関係節、日本語訳 (german.analyzer)。
# spaCy のドイツ語モデルか辞書 (tools/build_german_dic.py) が無ければ飛ばす
#
import unittest

try:
    from dragoman.german import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'spaCy のドイツ語モデルかドイツ語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_cases_and_articles(self):
        self.assertEqual(self.ja('Der Mann liest das Buch.'), '男が / 本を / 読む')
        self.assertEqual(self.ja('Das Buch des Lehrers liegt auf dem Tisch.'),
                         '先生の本が / 机の上で / 横たわっている,ある')

    def test_verb_groups(self):
        self.assertEqual(self.ja('Ich habe meiner Mutter einen Brief geschrieben.'), '私が / 私の母に / 手紙を / 書いた')
        self.assertEqual(self.ja('Sie ist gestern in die Stadt gegangen.'), '彼女が / 町[へ,の中へ] / 昨日 / 行った')
        self.assertEqual(self.ja('Das Buch wurde von dem Lehrer gelesen.'), '本が / 先生によって / 読まれた')
        self.assertEqual(self.ja('Ich kann heute nicht kommen.'), '私が / 今日 / 来ることができない')

    def test_separable_and_existential(self):
        self.assertEqual(self.ja('Er ruft seine Mutter an.'), '彼が / 彼の母を / 電話する')
        self.assertEqual(self.ja('Es gibt keinen Zucker.'), '砂糖が / ない,いない')

    def test_adverbial_clauses(self):
        self.assertEqual(self.ja('Ich bleibe zu Hause, weil es regnet.'), '{雨が降る}ので / 私が / 家[へ,のところへ] / とどまる')
        self.assertEqual(self.ja('Bevor er isst, wäscht er die Hände.'), '{彼が 食べる}前に / 彼が / 手を / 洗う')
        self.assertEqual(self.ja('Obwohl sie müde war, arbeitete sie.'), '{彼女が 疲れていた}けれども / 彼女が / 働いた')

    def test_clauses(self):
        self.assertEqual(self.ja('Ich weiß, dass du mich liebst.'), '私が / 知っている / 〜ということ / 君が / 私を / 愛する')
        self.assertEqual(self.ja('Das Haus, das ich gekauft habe, ist sehr schön.'), 'とても / {私が 買った}家は / 美しい')

    def test_old_spelling(self):
        from dragoman.german import orthography as o
        self.assertEqual([o.modern(w) for w in ('roth', 'Thüre', 'todt', 'gieng', 'erschrack', 'daß', 'wußte', 'Waare',
                                                'übermüthig')],
                         ['rot', 'Türe', 'tot', 'ging', 'erschrak', 'dass', 'wusste', 'Ware', 'übermütig'])
        # 今の綴りの語・固有名詞はそのまま
        self.assertEqual([o.modern(w) for w in ('die', 'rief', 'saß', 'großen', 'Theater', 'Stadt', 'Amiens', 'May')],
                         ['die', 'rief', 'saß', 'großen', 'Theater', 'Stadt', 'Amiens', 'May'])
        self.assertEqual(o.tokens(['ich', 'wills', 'nicht'])[0], ['ich', 'will', 'es', 'nicht'])

    def test_diminutives(self):
        from dragoman.german import orthography as o
        self.assertEqual([o.diminutive_base(w) for w in ('Spieglein', 'Töchterlein', 'Häuslein', 'Stühlchen',
                                                          'Gäbelchen', 'Löffelein')],
                         ['Spiegel', 'Tochter', 'Haus', 'Stuhl', 'Gabel', 'Löffel'])

    def test_fairy_tale(self):
        # グリム童話『白雪姫』(1857年版。パブリックドメイン) の綴りのまま
        self.assertEqual(self.ja('Da war sie zufrieden, denn sie wußte daß der Spiegel die Wahrheit sagte.'),
                         'そこで,その後すぐ / 彼女は / 満足していた / というのは / 彼女が / 知っていた / 〜ということ / 鏡が / 真実を / 言った')
        self.assertEqual(self.ja('Da erschrack die Königin.'), 'そこで,その後すぐ / 女王が / 驚いた')

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('Der Mann liest das Buch.'), 'de')
        self.assertEqual(detect('Gallia est omnis divisa in partes tres.'), 'la')


if __name__ == '__main__':
    unittest.main()
