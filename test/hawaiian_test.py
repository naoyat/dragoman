#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語: 綴りの鍵と ʻokina の揺れ (hawaiian.orthography)、小辞からの語の役割・時制と相・動詞の無い文・受け身・
# 否定と禁止・所有と日本語訳 (hawaiian.analyzer)、音読の音素 (hawaiian.phonology)。辞書 (tools/build_hawaiian_dic.py)
# が無ければ解析の試験は飛ばす
#
import unittest

from dragoman.hawaiian import orthography, dictionary, morphology, phonology


class OrthographyTestCase(unittest.TestCase):
    def test_key_and_okina(self):
        self.assertEqual(orthography.key('Kaʻū'), 'kau')
        self.assertEqual(orthography.normalize("Hawai'i"), 'Hawaiʻi')   # ' ‘ ` → ʻ
        self.assertEqual(orthography.normalize('Hawai‘i'), 'Hawaiʻi')
        self.assertTrue(orthography.marked('kāne'))
        self.assertFalse(orthography.marked('kane'))

    def test_candidates(self):
        # 印の無い kau は kaʻu「私の」と kāu「君の」の両方、印があればその綴りだけ
        self.assertEqual([w for w, _ in morphology.candidates(morphology.POSSESSIVES, 'kau')], ['kaʻu', 'kāu'])
        self.assertEqual([w for w, _ in morphology.candidates(morphology.POSSESSIVES, 'kaʻu')], ['kaʻu'])


class PhonologyTestCase(unittest.TestCase):
    def test_espeak(self):
        self.assertEqual(phonology.espeak_word('paʻu'), "p'a?u")       # ʻokina は声門閉鎖音
        self.assertEqual(phonology.espeak_word('kāne'), "k'a:ne")       # 長母音
        self.assertEqual(phonology.espeak_word('ʻāina'), "?'a:ina")     # 頭子音の無い音節の前の長母音に強勢
        self.assertEqual(phonology.espeak_word('wahine'), "wah'ine")    # 終わりから2番目
        self.assertEqual(phonology.espeak_word('iwi'), "'ivi")          # i の後ろの w は [v]
        self.assertEqual(phonology.espeak_word('lei'), "l'ei")          # 二重母音は1音節


@unittest.skipUnless(dictionary.available(), 'ハワイ語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        from dragoman.hawaiian import analyzer
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_word_order_and_tam(self):
        self.assertEqual(self.ja('Ua ʻai ke keiki i ka poi.'), '子供が / ポイを / 食べた')
        self.assertEqual(self.ja('E heluhelu ana ka haumāna i ka puke.'), '生徒が / 本を / 読むだろう')
        self.assertEqual(self.ja('Ke hīmeni nei ka wahine.'), '{女,妻}が / 歌っている')
        self.assertEqual(self.ja('Ua hele ke kanaka i ke kula.'), '人が / 学校[に,へ] / 行った')   # 移動の動詞の i

    def test_verbless(self):
        self.assertEqual(self.ja('He kumu ʻo ia.'), '彼は / 先生である')
        self.assertEqual(self.ja('ʻO Kimo koʻu inoa.'), '私の名前は / キモである')
        self.assertEqual(self.ja('Aia ka puke ma luna o ka papa.'), '本が / {テーブル,板}の上に / ある,いる')

    def test_negation_passive(self):
        self.assertEqual(self.ja('ʻAʻole i hele ke kanaka.'), '人が / 行かなかった')
        self.assertEqual(self.ja('Mai hele!'), '行くな')
        self.assertEqual(self.ja('Ua ʻai ʻia ka iʻa e ka pōpoki.'), '魚が / 猫によって / 食べられた')

    def test_number(self):
        from dragoman.hawaiian import analyzer

        def number(text, ix=1):
            a = next(analyzer.analyze_text(text))
            word = next(w for w in a.words if getattr(w, 'token_ix', None) == ix)
            return word.items[0]._[0][1]
        self.assertEqual(number('Ua hele ke kanaka i ke kula.', 2), 'sg')   # 単数 (複数形 kānaka と鍵が同じでも)
        self.assertEqual(number('Ua hele nā kanaka i ke kula.', 2), 'pl')   # 冠詞 nā
        self.assertEqual(number('Ua hele nā kānaka i ke kula.', 2), 'pl')

    def test_unmarked_spelling(self):
        from dragoman.hawaiian import analyzer
        self.assertEqual(self.ja('Ua ai ke keiki i ka poi.'), '子供が / ポイを / 食べた')
        a = next(analyzer.analyze_text('Aloha au ia oe.'))
        self.assertEqual(analyzer.spelled(a), ['Aloha', 'au', 'iā', 'ʻoe', '.'])   # 音読の綴り


if __name__ == '__main__':
    unittest.main()
