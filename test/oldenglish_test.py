#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語: 綴りの鍵と揺れ (oldenglish.orthography)、冠詞の掛け先・前置詞の格・助動詞と本動詞・否定の縮約・関係節・
# 呼びかけ・辞書に無い語の推定と日本語訳 (oldenglish.analyzer)。辞書 (tools/build_oldenglish_dic.py) が無ければ
# 解析の試験は飛ばす
#
import unittest

from dragoman.oldenglish import orthography, dictionary


class OrthographyTestCase(unittest.TestCase):
    def test_key(self):
        self.assertEqual(orthography.key('Sēo'), 'seo')
        self.assertEqual(orthography.key('ġiefan'), 'giefan')
        self.assertEqual(orthography.key('onginneð'), 'onginneþ')   # ð = þ
        self.assertEqual(orthography.key('ƿeorþan'), 'weorþan')     # ウィン
        self.assertEqual(orthography.key('⁊'), 'and')

    def test_lemma_key_keeps_macrons(self):
        self.assertNotEqual(orthography.lemma_key('gōd'), orthography.lemma_key('god'))
        self.assertEqual(orthography.lemma_key('dæġ'), orthography.lemma_key('dæg'))

    def test_variants(self):
        self.assertIn('hieran', list(orthography.variants('hyran')))
        self.assertIn('man', list(orthography.variants('mon')))
        self.assertIn('weorþan', list(orthography.variants('wurþan')))
        self.assertIn('timbred', list(orthography.variants('getimbrod', depth=2)))


class PhonologyTestCase(unittest.TestCase):
    def ipa(self, word, lemma=None):
        from dragoman.oldenglish import phonology
        return phonology.ipa(word, lemma)

    def test_consonants(self):
        self.assertEqual(self.ipa('ċild'), 'tʃˈild')
        self.assertEqual(self.ipa('cild'), 'tʃˈild')      # 点が無くても前舌母音の前は口蓋音
        self.assertEqual(self.ipa('cyning'), 'kˈyniŋg')    # y の前は口蓋化しない
        self.assertEqual(self.ipa('dæġ'), 'dˈæj')
        self.assertEqual(self.ipa('scip'), 'ʃˈip')
        self.assertEqual(self.ipa('ecg'), 'ˈedʒ')
        self.assertEqual(self.ipa('niht'), 'nˈiçt')
        self.assertEqual(self.ipa('dohtor'), 'dˈoxtor')
        self.assertEqual(self.ipa('dagas'), 'dˈɑɣɑs')

    def test_voicing_and_length(self):
        self.assertEqual(self.ipa('ofer'), 'ˈover')
        self.assertEqual(self.ipa('wesan'), 'wˈezɑn')
        self.assertEqual(self.ipa('oþþe'), 'ˈoθːe')        # 重子音は無声のまま長く
        self.assertEqual(self.ipa('stān'), 'stˈɑːn')
        self.assertEqual(self.ipa('ġēar'), 'jˈæːɑr')

    def test_prefixes(self):
        self.assertEqual(self.ipa('ġesēon'), 'jesˈeːon')   # 接頭辞の後ろの s は無声、強勢はその次
        self.assertEqual(self.ipa('beran'), 'bˈerɑn')

    def test_espeak(self):
        from dragoman.oldenglish import phonology
        self.assertEqual(phonology.espeak_phonemes('Hwæt! Wē', phonology.ESPEAK_DE), "[[hw'Et _: w'e:]]")
        self.assertEqual(phonology.espeak_phonemes('Hwæt! Wē', phonology.ESPEAK_ANG), "[[hw'&t _: w'e:]]")   # 古英語の音声


@unittest.skipUnless(dictionary.available(), '古英語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        from dragoman.oldenglish import analyzer
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_cases_and_articles(self):
        self.assertEqual(self.ja('Se cyning sealde þǣm biscope gold.'), '王が / 主教に / 金を / 与えた')
        self.assertEqual(self.ja('God lufaþ þā men.'), '神が / 人を / 愛する')    # 大文字の God、men = menn
        self.assertEqual(self.ja('Hēr fōr se here tō Lundenbyriġ.'), 'ここで / 軍が / ロンドン[へ,に] / 行った')

    def test_verb_groups(self):
        self.assertEqual(self.ja('Ic wille singan.'), '私が / 歌いたい')
        self.assertEqual(self.ja('Hē hæfde þone cyning ġesewen.'), '彼が / 王を / 見た')
        self.assertEqual(self.ja('Þæt hūs wæs ġetimbrod.'), '家が / 建てられた')            # 綴りの揺れ -od = -ed
        self.assertEqual(self.ja('Hē ne mihte þone weg findan.'), '彼が / 道を / 見つけることができなかった')

    def test_negation_and_copula(self):
        self.assertEqual(self.ja('Nis hē on þǣm hūse.'), '彼は / 家に / いない')
        self.assertEqual(self.ja('Hē wæs on þǣm hūse.'), '彼は / 家に / いた')

    def test_relative_and_vocative(self):
        self.assertEqual(self.ja('Se cyning þe on Westseaxum rīcsode wæs wīs.'),
                         '{ウェストサクソン[で,の上で] 支配した}王は / 賢かった')
        self.assertIn('私たちの父', self.ja('Fæder ūre, þū þe eart on heofonum, sī þīn nama ġehālgod.'))
        self.assertIn('君の名前が', self.ja('Fæder ūre, þū þe eart on heofonum, sī þīn nama ġehālgod.'))

    def test_genitive_before_head(self):
        self.assertIn('王の栄光を', self.ja('Wē Gārdena in ġeārdagum þēodcyninga þrym ġefrūnon.'))

    def test_spelled_restores_long_vowels(self):
        from dragoman.oldenglish import analyzer
        a = next(analyzer.analyze_text('He forlet þa burh.'))
        self.assertEqual([s for s, _ in analyzer.spelled(a)], ['Hē', 'forlēt', 'þā', 'burh', '.'])
        from dragoman.oldenglish import phonology
        self.assertIn("fORl'e:t", phonology.espeak_words(analyzer.spelled(a)))   # 見出し forlǣtan の for- に強勢を置かない

    def test_guesses(self):
        from dragoman.oldenglish import analyzer
        verb = analyzer.word_items('gyrnde')    # 語尾 -de を外して ġeornan (綴りの揺れ y = eo) の過去
        self.assertTrue(verb and verb[0]['pos'] == 'verb' and verb[0]['tense'] == 'perfect')
        noun = analyzer.word_items('leorningcnihtas')    # 複合語 leorning + cniht
        self.assertTrue(noun and noun[0]['pos'] == 'noun' and ('Nom', 'pl', 'm') in noun[0]['_'])


if __name__ == '__main__':
    unittest.main()
