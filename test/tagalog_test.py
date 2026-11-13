#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# タガログ語: 焦点の接辞とアスペクト (重複) の解析、名詞句の標識と焦点からの格、焦点の名詞を「は」で先頭に。
# 辞書が無ければ飛ばす
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.tagalog import dictionary, morphology, script  # noqa: E402

HAVE_DATA = dictionary.available()


class CandidatesTestCase(unittest.TestCase):
    def test_affixes_and_aspect(self):
        c = morphology.candidates
        self.assertIn(('bili', 'actor', 'progressive'), c('bumibili'))      # -um- + 重複
        self.assertIn(('bili', 'object', 'completive'), c('binili'))         # -in-
        self.assertIn(('sulat', 'actor', 'progressive'), c('nagsusulat'))    # nag- + 重複
        self.assertIn(('sulat', 'conveyance', 'completive'), c('isinulat'))  # i- + -in-
        self.assertIn(('linis', 'object', 'contemplative'), c('lilinisin'))  # 重複 + -in
        self.assertIn(('alis', 'actor', 'completive'), c('umalis'))          # 母音で始まる語根は um-
        self.assertIn(('bili', 'object', 'infinitive'), c('bilhin'))         # 母音の脱落 (bili + hin)

    def test_voice_of_lemmas(self):
        self.assertEqual(script.verb_voice('bumili', 'buy'), 'actor')
        self.assertEqual(script.verb_voice('bilhin', 'buy something'), 'object')
        self.assertEqual(script.verb_voice('makita', 'happen to see'), 'object')


@unittest.skipUnless(HAVE_DATA, 'no Tagalog dictionary (tools/build_tagalog_dic.py)')
class TagalogTestCase(unittest.TestCase):
    def ja(self, text):
        from dragoman.tagalog import analyzer
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_focus(self):
        self.assertEqual(self.ja('Bumili ang lalaki ng isda.'), '男は / 魚を / 買った')       # 行為者焦点
        self.assertEqual(self.ja('Binili ng lalaki ang isda.'), '魚は / 男が / 買った')       # 対象焦点
        self.assertEqual(self.ja('Binilhan ng lalaki ng isda ang tindahan.'), '店には / 男が / 魚を / 買った')  # 場所焦点
        self.assertEqual(self.ja('Kumakain ako ng kanin.'), '私は / ご飯を / 食べている')    # 進行
        self.assertEqual(self.ja('Nakatira ako sa Maynila.'), '私は / Maynilaに / 住んでいる')   # 状態の naka-
        self.assertEqual(self.ja('Nakaupo siya sa silya.'), '彼は / 椅子に / 座っている')
        self.assertEqual(self.ja('Nakatulog ang bata.'), '子供は / 眠った')                 # naka- の完了 (行為者焦点)
        self.assertEqual(self.ja('Hindi ako makatulog.'), '私は / 眠ることができない')        # 可能の maka-
        self.assertEqual(self.ja('Makakabili ako ng libro.'), '私は / 本を / 買うことができるだろう')
        self.assertEqual(self.ja('Nakasuot siya ng puting damit.'), '彼は / 白い衣服を / 着ている')   # puti「白い」
        self.assertEqual(self.ja('Binuksan niya ang pinto.'), 'ドアは / 彼が / 開けた')    # 場所焦点でも対象 (buksan)

    def test_bukas(self):
        # bukas: 副詞「明日」、述語・名詞の前は「開いている」、bukas ng umaga「明日の朝」
        self.assertEqual(self.ja('Pupunta ako bukas.'), '私は / 明日 / 行くだろう')
        self.assertEqual(self.ja('Aalis kami bukas ng gabi.'), '私たちは / 明日の夜 / 出発するだろう')
        self.assertEqual(self.ja('Bukas ang tindahan.'), '店は / 開いている')
        self.assertEqual(self.ja('Bukas na ang tindahan.'), '店は / もう / 開いている')
        self.assertEqual(self.ja('Ang tindahan ay bukas.'), '店は / 開いている')
        self.assertEqual(self.ja('Isara mo ang bukas na pinto.'), '開いているドアは / あなたが / 閉める')

    def test_days_numbers_existence(self):
        # Linggo「日曜日」(小文字の linggo は「週」)、曜日・月
        self.assertEqual(self.ja('Bukas ay Linggo.'), '明日 / 日曜日である')
        self.assertEqual(self.ja('Pupunta ako sa simbahan sa Linggo.'), '私は / 教会に / 日曜日に / 行くだろう')   # 時の sa の句は副詞
        # 数詞 + 繋ぎ + 名詞: 期間は「一週間」、人・動物は「二人の」「三匹の」、ほかは「二つの」
        self.assertEqual(self.ja('Nag-aaral ako sa gabi.'), '私は / 夜に / 勉強している')
        self.assertEqual(self.ja('Isang linggo ang bakasyon.'), '休暇は / 一週間である')
        self.assertEqual(self.ja('Bumili ako ng dalawang libro.'), '私は / 二つの本を / 買った')
        self.assertEqual(self.ja('Bumili ako ng tatlong isda.'), '私は / 三匹の魚を / 買った')
        self.assertEqual(self.ja('Bumili siya ng isang magandang bahay.'), '彼は / 一つの美しい家を / 買った')
        # 存在: 生き物は「いる」、ang の代名詞は所有者「〜には」、sa の代名詞は「〜に」
        self.assertEqual(self.ja('May aso sa bahay.'), '犬が / 家に / いる')
        self.assertEqual(self.ja('May libro ako.'), '私には / 本が / ある')
        self.assertEqual(self.ja('Mayroon akong kapatid.'), '私には / 兄弟が / いる')
        self.assertEqual(self.ja('Walang tao dito.'), '人が / ここに / いない')

    def test_place_and_time(self):
        # 動作の場所の sa は「で」、移動・存在は「に」、買う相手は「から」
        self.assertEqual(self.ja('Kumain kami sa bahay ni Juan sa Sabado.'), '私たちは / Juanの家で / 土曜日に / 食べた')
        self.assertEqual(self.ja('Bumili ako ng isda sa palengke.'), '私は / 市場で / 魚を / 買った')
        self.assertEqual(self.ja('Bumili ako ng libro kay Juan.'), '私は / Juanから / 本を / 買った')
        self.assertEqual(self.ja('Pumunta ako sa Maynila.'), '私は / Maynilaに / 行った')
        self.assertEqual(self.ja('Nakatira ako sa Maynila.'), '私は / Maynilaに / 住んでいる')
        # ipinanganak「生まれた」、noong・sa + 年・月
        self.assertEqual(self.ja('Ipinanganak ako sa Mayo.'), '私は / 5月に / 生まれた')
        self.assertEqual(self.ja('Ipinanganak siya noong 1990.'), '彼は / 1990年に / 生まれた')
        self.assertEqual(self.ja('Dumating siya noong Lunes.'), '彼は / 月曜日に / 着いた')
        self.assertEqual(self.ja('Lumipat kami sa Cebu sa 2020.'), '私たちは / Cebuに / 2020年に / 移った')

    def test_pati(self):
        # pati (na rin)「〜も、それに」: 名詞類の間は並列「と」、文頭は後ろの名詞の「〜も」
        self.assertEqual(self.ja('Kumain ako ng mansanas, pati na rin saging.'), '私は / 林檎とバナナを / 食べた')
        self.assertEqual(self.ja('Dumating si Maria pati si Juan.'), 'MariaとJuanが / 着いた')
        self.assertEqual(self.ja('Pati si Juan ay dumating.'), 'Juanも / 着いた')
        self.assertEqual(self.ja('Pati ako ay kumain.'), '私も / 食べた')

    def test_possessor_copula_relative(self):
        self.assertIn('子供の', self.ja('Binili ng lalaki ang libro ng bata.'))
        self.assertEqual(self.ja('Maganda ang bahay.'), '家は / 美しい')
        self.assertEqual(self.ja('Si Juan ay guro.'), 'Juanは / 先生である')
        self.assertIn('魚を買った男は', self.ja('Ang lalaking bumili ng isda ay guro.'))

    def test_contractions_and_gerunds(self):
        from dragoman.tagalog import analyzer
        self.assertEqual(analyzer.tokens("ngayo'y sa'kin"), ['ngayon', 'ay', 'sa', 'akin'])
        items, _ = morphology.analyze('pag-ikot')
        self.assertEqual(items[0]['pos'], 'noun')                                          # 動名詞 pag-
        items, _ = morphology.analyze('magandang')
        self.assertEqual(items[0]['pos'], 'adj')                                           # 繋ぎ -ng


if __name__ == '__main__':
    unittest.main()
