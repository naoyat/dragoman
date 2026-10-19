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

    def test_relative_and_fronted(self):
        self.assertEqual(self.ja('Ua ʻike au i ka wahine i hīmeni.'), '私が / 歌った女を / 見た,知った')
        self.assertEqual(self.ja('Ua ʻike au i ka wahine e hīmeni ana.'), '私が / 歌っている女を / 見た,知った')
        self.assertEqual(self.ja('Ua hele mai ke kanaka i ʻike ai au.'), '私が見た人が / 来た')   # ai: 目的語の空所
        self.assertEqual(self.ja('ʻElua kanaka i hele mai.'), '二つの人が / 来た')   # 前に出した名詞句、hele mai
        self.assertEqual(self.ja('Ua hele mai ke keiki mai ka hale mai.'), '子供が / 家から / 来た')

    def test_possession_and_questions(self):
        self.assertEqual(self.ja('He kaʻa koʻu.'), '私には / 車が / ある,いる')
        self.assertEqual(self.ja('Naʻu kēia puke.'), 'この本は / 私のものである')
        self.assertEqual(self.ja('Loaʻa iaʻu ke kaʻa.'), '車が / 私に / ある,手に入る')
        self.assertEqual(self.ja('He aha kēia?'), 'これは / 何であるか')
        self.assertEqual(self.ja('ʻO wai kou inoa?'), '君の名前は / 何であるか')
        self.assertEqual(self.ja('Ua hele ʻoe i hea?'), '君は / どこ[に,へ] / 行ったか')
        self.assertEqual(self.ja('No ke aha ʻoe i hele ai?'), 'なぜ / 君が / 行ったか')

    def test_bible_1868(self):
        """1868年の聖書 (パブリックドメイン。ʻokina・長音符の無い綴り) の節"""
        self.assertEqual(self.ja('I kinohi hana ke Akua i ka lani a me ka honua.'),
                         '神が / 初め[に,へ] / 天と{大地,世界}を / 作る,する')   # 文頭の前置詞句、a me
        self.assertIn('神が / 言った', self.ja('Olelo mai la ke Akua, I malamalama, a ua malamalama.'))   # 語りの lā
        self.assertIn('良かった', self.ja('Ike mai la ke Akua i ka malamalama, ua maikai.'))   # 状態の動詞の述語
        self.assertIn('とても / 愛した', self.ja('No ka mea, ua aloha nui mai ke Akua i ko ke ao nei.'))
        out = self.ja('Pomaikai ka poe naau haahaa, no ka mea, no lakou ke aupuni o ka lani.')
        self.assertIn('低い心の人々は / 幸いである', out)   # 名詞の修飾の名詞、Andrews の見出しの手の訳
        self.assertIn('彼らのものである', out)              # no + 代名詞の述語

    def test_exact_spelling_first(self):
        """印の無い綴りは、綴りのそのまま合う見出しを先に (mauna「山」を māuna「無駄にする」より、kea「白い」を keʻa「十字」より)"""
        from dragoman.hawaiian import analyzer
        a = next(analyzer.analyze_text('mauna kea'))
        self.assertEqual([w.items[0].ja.split(',')[0] for w in a.words if w.items], ['山', '白い'])
        self.assertEqual(self.ja('Ua hele au i Mauna Kea.'), '私が / 白い山[に,へ] / 行った')
        self.assertEqual(self.ja('Ua aloha nui loa au iā ʻoe.'), 'とても / 私が / 君を / 愛した')   # nui loa は1つの「とても」

    def test_number(self):
        from dragoman.hawaiian import analyzer

        def number(text, ix=1):
            a = next(analyzer.analyze_text(text))
            word = next(w for w in a.words if getattr(w, 'token_ix', None) == ix)
            return word.items[0]._[0][1]
        self.assertEqual(number('Ua hele ke kanaka i ke kula.', 3), 'sg')   # 単数 (複数形 kānaka と鍵が同じでも)
        self.assertEqual(number('Ua hele nā kanaka i ke kula.', 3), 'pl')   # 冠詞 nā
        self.assertEqual(number('Ua hele nā kānaka i ke kula.', 3), 'pl')

    def test_token_rows(self):
        """語の一覧には、語の列から外した小辞 (ua・ʻia) と名詞に掛けた冠詞も出す"""
        from dragoman.hawaiian import analyzer, command
        a = next(analyzer.analyze_text('Ua ʻai ʻia ka iʻa e ka pōpoki.'))
        rows = command.token_rows(a)
        self.assertEqual([r[0] for r in rows], a.original)
        self.assertIn('完了', rows[0][2][0])         # ua
        self.assertIn('受け身', rows[2][2][0])       # ʻia
        self.assertIn('冠詞', rows[3][2][0])         # ka

    def test_unmarked_spelling(self):
        from dragoman.hawaiian import analyzer
        self.assertEqual(self.ja('Ua ai ke keiki i ka poi.'), '子供が / ポイを / 食べた')
        a = next(analyzer.analyze_text('Aloha au ia oe.'))
        self.assertEqual(analyzer.spelled(a), ['Aloha', 'au', 'iā', 'ʻoe', '.'])   # 音読の綴り


if __name__ == '__main__':
    unittest.main()
