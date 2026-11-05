#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語: 語形の規則 (格・副動詞・分詞・否定)、転写からの入力、語順のままの訳 (mongolian.*)。
# 辞書 (tools/build_mongolian_dic.py) が無ければ解析の試験を飛ばす
#
import unittest

from dragoman.mongolian import script

try:
    from dragoman.mongolian import analyzer, dictionary, morphology
    HAVE_DATA = dictionary.available()
except ImportError:
    HAVE_DATA = False


class ScriptTestCase(unittest.TestCase):
    def test_from_latin(self):
        self.assertEqual(script.from_latin('Xüü öcigdör oxin-d nom ög-sön.'), 'Хүү өчигдөр охинд ном өгсөн.')
        self.assertEqual(script.from_latin('sajn'), 'сайн')        # 母音の後ろの j は й
        self.assertEqual(script.from_latin('soyoo'), 'соёо')       # y + 母音は ё
        self.assertEqual(script.from_latin('Сайн байна уу'), 'Сайн байна уу')


class TraditionalTestCase(unittest.TestCase):
    # 伝統的なモンゴル文字 (mongolian/traditional.py): 転写との対応、規則での推定、接尾辞
    def test_script(self):
        from dragoman.mongolian import traditional as t
        self.assertEqual(t.to_script('köbegün'), 'ᠬᠥᠪᠡᠭᠦᠨ')
        self.assertEqual(t.to_script('aq-a'), 'ᠠᠬ\u180eᠠ')            # 語末の母音の前は母音分離記号
        self.assertEqual(t.to_script('ökin-dür'), 'ᠥᠬᠢᠨ\u202fᠳᠦᠷ')    # 接尾辞の前は狭い空白
        self.assertEqual(t.latin('ᠵᠠᠬᠢᠶ᠎ᠠ'), 'ǰaqiy-a')
        self.assertEqual(t.latin('ᠪᠢᠴᠢᠬᠦ'), 'bičikü')                # 前舌母音の語の ᠬ は k
        self.assertEqual(t._guess('урт'), 'urtu')                      # 語末の子音の連続に u
        self.assertEqual(t._guess('бага'), 'baγ-a')
        self.assertEqual(t._case('ger', 'Dat', False), 'ger-tür')       # r の後ろは -tür
        self.assertEqual(t._case('mongγol', 'Dat', True), 'mongγol-dur')
        self.assertEqual(t._case('sirege', 'Gen', False), 'sirege-yin')

    @unittest.skipUnless(HAVE_DATA, 'モンゴル語の辞書が無い')
    def test_sentence(self):
        a = next(analyzer.analyze_text('Хүү өчигдөр охинд ном өгсөн.'))
        self.assertEqual(' '.join(w['latin'] for w in a.traditional), 'köbegün öčügedür ökin-dür nom ögügsen')
        a = next(analyzer.analyze_text('Тэр сандал дээр суугаад ном уншиж байна.'))
        self.assertEqual(' '.join(w['latin'] for w in a.traditional),
                         'tere sandali degere saγuγad nom ungsiǰu bayin-a')
        a = next(analyzer.analyze_text('Бид өчигдөр кино үзсэнгүй.'))
        self.assertEqual(a.traditional[-1]['latin'], 'üǰegsen ügei')   # 否定は別の語
        a = next(analyzer.analyze_text('Багш оюутнуудад ном заасан.'))
        self.assertEqual(a.traditional[1]['latin'], 'oyutad-tur')   # n の語幹の複数は n を d に

    @unittest.skipUnless(HAVE_DATA, 'モンゴル語の辞書が無い')
    def test_dative_after_cluster(self):
        # 子音の連続の後の与位格 -од・-ад (хотод は хот。хото + д の хотон でなく)、複数 + 与位格
        first = lambda w: morphology.analyses(w)[0]
        self.assertEqual((first('хотод')['lemma'], first('хотод')['case']), ('хот', 'Dat'))
        r = first('оюутнуудад')
        self.assertEqual((r['lemma'], r['case'], r['number']), ('оюутан', 'Dat', 'pl'))
        self.assertEqual(first('байхдаа')['kind'], 'verb')
        self.assertEqual(self.lit_('Улаанбаатар хотод олон хүн амьдардаг.'), 'ウランバートルの 町に 多くの 人が 住む。')
        self.assertEqual(self.lit_('Заан хоёр том соёотой.'), '象は 二つの 大きい 牙を 持つ。')   # 共同格の述語は所有

    def lit_(self, text):
        return next(analyzer.analyze_text(text)).literal


@unittest.skipUnless(HAVE_DATA, 'モンゴル語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def lit(self, text):
        return next(analyzer.analyze_text(text)).literal

    def test_morphology(self):
        first = lambda w: morphology.analyses(w)[0]
        self.assertEqual((first('номыг')['lemma'], first('номыг')['case']), ('ном', 'Acc'))
        r = first('явсангүй')
        self.assertEqual((r['lemma'], r['tense'], r['negated']), ('явах', 'perfect', True))
        r = first('иртэл')
        self.assertEqual((r['lemma'], r['converb']), ('ирэх', 'until'))
        self.assertEqual(first('амьдардаг')['lemma'], 'амьдрах')        # 語幹の母音の挿入

    def test_literal(self):
        self.assertEqual(self.lit('Хүү өчигдөр охинд ном өгсөн.'), '少年は 昨日 少女に 本を 与えた。')
        self.assertEqual(self.lit('Би Монголд байхдаа энэ номыг авсан.'), '私は モンゴルに いる時に この 本を 取った。')
        self.assertEqual(self.lit('Би чамайг иртэл хүлээнэ.'), '私は 君を 来るまで 待つ。')
        self.assertEqual(self.lit('Тэр сандал дээр суугаад ном уншиж байна.'), 'その 椅子の上で 座って 本を 読んでいる。')
        self.assertEqual(self.lit('Бид өчигдөр кино үзсэнгүй.'), '私たちは 昨日 映画を 見なかった。')
        self.assertEqual(self.lit('Батын бичсэн захиа ширээн дээр байна.'), 'バトが 書いた 手紙は 机の上に ある。')
        self.assertEqual(self.lit('Энэ бол миний ном.'), 'これは 私の 本だ。')

    def test_latin_input(self):
        self.assertEqual(self.lit('Xüü öcigdör oxin-d nom ög-sön.'), '少年は 昨日 少女に 本を 与えた。')

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('Хүү өчигдөр охинд ном өгсөн.'), 'mn')
        self.assertEqual(detect('Я люблю тебя.'), 'ru')


if __name__ == '__main__':
    unittest.main()
