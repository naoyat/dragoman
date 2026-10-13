#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語・トルコ語・モンゴル語・ドイツ語・フィンランド語の出口 (generate/korean.py・turkish.py・mongolian.py・german.py):
# 活用・格の接尾辞・母音調和・冠詞と形容詞の語尾。ドイツ語は辞書 (語形の表) が無ければ飛ばす
#
import unittest

from dragoman.generate import korean, turkish, mongolian, german, finnish
from dragoman.generate.name_script import hangul


class KoreanTestCase(unittest.TestCase):
    def test_conjugation(self):
        self.assertEqual([korean.present(v) for v in ('읽다', '가다', '살다')], ['읽는다', '간다', '산다'])
        self.assertEqual([korean.past(v) for v in ('가다', '오다', '마시다', '하다', '아름답다', '듣다', '모르다', '만들다')],
                         ['갔다', '왔다', '마셨다', '했다', '아름다웠다', '들었다', '몰랐다', '만들었다'])
        self.assertEqual(korean.future('읽다'), '읽을 것이다')
        self.assertEqual(korean.adnominal('보다', 'perfect'), '본')                  # 過去の連体形
        self.assertEqual(korean.adnominal('아름답다', adjective=True), '아름다운')    # ㅂ 不規則

    def test_particles_and_names(self):
        self.assertEqual(korean.particle('책', '을', '를'), '책을')
        self.assertEqual(korean.particle('장미', '을', '를'), '장미를')
        self.assertEqual([hangul(n) for n in ('Mārcus', 'Iūlia', 'Rōma')], ['마르쿠스', '율리아', '로마'])


class TurkishTestCase(unittest.TestCase):
    def test_cases(self):
        self.assertEqual([turkish.case_form('kitap', c) for c in ('Acc', 'Dat', 'Loc', 'Abl', 'Gen')],
                         ['kitabı', 'kitaba', 'kitapta', 'kitaptan', 'kitabın'])     # 有声化と d → t
        self.assertEqual(turkish.case_form('bahçe', 'Acc'), 'bahçeyi')              # 母音の後ろの y
        self.assertEqual(turkish.case_form('Ankara', 'Loc', proper=True), "Ankara'da")
        self.assertEqual(turkish.case_form('şehir', 'Acc'), 'şehri')                # 母音の脱落

    def test_verbs(self):
        self.assertEqual(turkish.conjugate('görmek', 'present'), 'görüyor')
        self.assertEqual(turkish.conjugate('beklemek', 'present'), 'bekliyor')
        self.assertEqual(turkish.conjugate('gitmek', 'future', 1), 'gideceğim')
        self.assertEqual(turkish.conjugate('okumak', 'perfect', negated=True), 'okumadı')
        self.assertEqual(turkish.participle('görmek', 'object'), 'gördüğü')
        self.assertEqual(turkish.participle('gitmek', 'object'), 'gittiği')


class MongolianTestCase(unittest.TestCase):
    def test_cases(self):
        self.assertEqual([mongolian.case_form('ном', c) for c in ('Gen', 'Acc', 'Dat', 'Abl', 'Ins', 'Com')],
                         ['номын', 'номыг', 'номд', 'номоос', 'номоор', 'номтой'])   # 母音調和 (о)
        self.assertEqual(mongolian.case_form('гэр', 'Dat'), 'гэрт')
        self.assertEqual(mongolian.case_form('ээж', 'Dat'), 'ээжид')

    def test_verbs(self):
        self.assertEqual(mongolian.conjugate('унших'), 'уншина')
        self.assertEqual(mongolian.conjugate('өгөх', 'perfect'), 'өгсөн')
        self.assertEqual(mongolian.conjugate('явах', 'perfect', negated=True), 'явсангүй')
        self.assertEqual(mongolian.conjugate('хайрлах'), 'хайрлана')


@unittest.skipUnless(german._db() is not None, 'ドイツ語の辞書が無い')
class GermanTestCase(unittest.TestCase):
    def test_noun_phrase(self):
        from dragoman.generate.frame import NP, Lex
        rose = NP(Lex('Rose', 'noun', lang='de'), modifiers=[Lex('schön', 'adj', lang='de')])
        self.assertEqual(german.noun_phrase(rose, 'Acc'), 'die schöne Rose')
        garden = NP(Lex('Garten', 'noun', lang='de'), prep=Lex('in', 'preposition'), case='Abl')
        self.assertEqual(german.prepositional(garden), 'im Garten')            # in + dem → im
        books = NP(Lex('Buch', 'noun', lang='de'), number='pl')
        self.assertEqual(german.noun_phrase(books, 'Dat'), 'den Büchern')     # 与格複数 -n

    def test_verbs(self):
        self.assertEqual(german.finite('sehen', 'present', 3, 'sg'), ('sieht', ''))
        self.assertEqual(german.finite('sehen', 'past', 3, 'pl'), ('sahen', ''))
        self.assertEqual(german.finite('anrufen', 'present', 3, 'sg'), ('ruft', 'an'))   # 分離動詞
        self.assertEqual(german.participle_form('lesen'), 'gelesen')


@unittest.skipUnless(finnish._db() is not None, 'フィンランド語の辞書 (語形の表) が無い')
class FinnishTestCase(unittest.TestCase):
    def test_cases(self):
        self.assertEqual([finnish.case_form('talo', c) for c in ('Gen', 'Par', 'Ine', 'Ela', 'Ill', 'Ade', 'All')],
                         ['talon', 'taloa', 'talossa', 'talosta', 'taloon', 'talolla', 'talolle'])
        self.assertEqual(finnish.case_form('talo', 'Ine', 'pl'), 'taloissa')

    def test_verbs(self):
        from dragoman.generate.frame import Clause, Lex
        clause = Clause(Lex('lukea', 'verb', lang='fi'), tense='perfect')
        self.assertEqual(finnish.verb_form(clause, 3, 'sg'), 'luki')
        clause = Clause(Lex('lukea', 'verb', lang='fi'), negated=True)
        self.assertEqual(finnish.verb_form(clause, 1, 'sg'), 'en lue')        # 否定動詞 + 本動詞


if __name__ == '__main__':
    unittest.main()
