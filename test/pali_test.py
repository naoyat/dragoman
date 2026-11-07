#!/usr/bin/env python
# -*- coding: utf-8 -*-
# パーリ語 (dragoman/pali): 文字の変換・カタカナ読み・辞書引き (Digital Pāḷi Dictionary)・解析
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dragoman.pali import script  # noqa: E402
    HAVE_VIDYUT = True
except ImportError:
    HAVE_VIDYUT = False

if HAVE_VIDYUT:
    from dragoman.pali import dictionary, katakana  # noqa: E402
    HAVE_DATA = dictionary.available()
else:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_VIDYUT, 'vidyut が無い')
class ScriptTestCase(unittest.TestCase):
    def test_roundtrip(self):
        text = 'namo tassa bhagavato veḷuvana buddhaṃ ñāṇa'
        for name in ('Sinhala', 'Thai', 'Burmese', 'Devanagari'):
            self.assertEqual(script.to_roman(script.convert(text, name)), text)

    def test_conventions(self):
        self.assertEqual(script.convert('tassa', 'Burmese'), 'တဿ')         # ss の合字
        self.assertEqual(script.convert('dhammaṃ', 'Thai'), 'ธมฺมํ')       # 点 (phinthu) と niggahīta
        self.assertEqual(script.to_roman('ධම්මපදං'), 'dhammapadaṃ')
        self.assertEqual(script.normalize('dhammaṁ'), 'dhammaṃ')            # SuttaCentral の ṁ

    def test_katakana(self):
        self.assertEqual(katakana.katakana('sammāsambuddhassa'), 'サンマーサンブッダッサ')
        self.assertEqual(katakana.katakana('saraṇaṃ'), 'サラナン')           # ṃ は「ン」
        self.assertEqual(katakana.katakana('metta'), 'メッタ')               # 重子音の前の e は短い
        self.assertEqual(katakana.katakana('veḷuvana'), 'ヴェールヴァナ')     # ḷ は子音
        self.assertEqual(katakana.katakana('pañca'), 'パンチャ')
        self.assertEqual(katakana.katakana('paññā'), 'パンニャー')


@unittest.skipUnless(HAVE_DATA, 'パーリ語の辞書が無い (DPD の dpd.db と tools/build_pali_dic.py)')
class DictionaryTestCase(unittest.TestCase):
    def test_noun(self):
        item = dictionary.lookup('dhammā')[0]
        self.assertEqual((item['pos'], item['base'], item['ja']), ('noun', 'dhamma', '法'))   # サンスクリットの仏典の訳語
        self.assertIn(('Nom', 'pl', 'm'), item['_'])
        self.assertEqual(dictionary.lookup('bhikkhave')[0]['_'], [('Voc', 'pl', 'm')])

    def test_verb(self):
        item = dictionary.lookup('gacchāmi')[0]
        self.assertEqual((item['pos'], item['person'], item['number'], item['tense']), ('verb', 1, 'sg', 'present'))
        self.assertEqual(dictionary.lookup('gantvā')[0]['ja'], '行って')    # 絶対分詞
        self.assertEqual(dictionary.lookup('akkocchi')[0]['tense'], 'aorist')

    def test_participle_and_pronoun(self):
        items = dictionary.lookup('paduṭṭhena')
        self.assertEqual([i['pos'] for i in items], ['participle', 'adj'])   # padussati の過去分詞・「悪い」
        self.assertEqual(dictionary.lookup('naṃ')[0]['base'], 'ta')
        self.assertEqual(dictionary.lookup('me')[0]['ja'], '私')

    def test_ranking(self):
        self.assertEqual(dictionary.lookup('veraṃ')[0]['base'], 'vera')   # vāti の反射態・願望法より名詞を先に
        self.assertEqual(dictionary.lookup('ve')[0]['ja'], '実に')
        self.assertEqual(dictionary.lookup('tato')[0]['pos'], 'adv')

    def test_deconstruct(self):
        self.assertEqual(dictionary.deconstruct('sammantīdha'), ['sammanti', 'idha'])

    def test_analyzer(self):
        from dragoman.pali import analyzer
        words = analyzer.lookup_all(analyzer.tokens('Tato naṃ dukkhamanveti.'))
        self.assertEqual([w.surface for w in words], ['tato', 'naṃ', 'dukkhaṃ', 'anveti', '.'])   # ṃ + 母音の連声を分ける
        words = analyzer.lookup_all(analyzer.tokens('pāpaṃ me katan ti'))
        self.assertEqual(words[2].surface, 'kataṃ')                        # ti の前の n は ṃ
        analysis = next(analyzer.analyze_text('නමෝ තස්ස භගවතෝ.'))          # シンハラ文字の入力
        self.assertEqual(analysis.tokens, ['namo', 'tassa', 'bhagavato', '.'])
        self.assertEqual(analysis.script, 'Sinhala')

    def test_detect(self):
        from dragoman import main
        self.assertEqual(main.detect('Manopubbaṅgamā dhammā, manoseṭṭhā manomayā.'), 'pi')
        self.assertEqual(main.detect('නමෝ තස්ස භගවතෝ'), 'pi')
        self.assertEqual(main.detect('rāmo vanaṃ gacchati'), 'la')   # 重子音の無いローマ字はパーリ語にしない


if __name__ == '__main__':
    unittest.main()
