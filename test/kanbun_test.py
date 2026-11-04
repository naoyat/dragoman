#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文: 読む順序・送り仮名・置き字・再読文字 (kundoku.py) と現代語訳 (modern.py)。UD-Kanbun・KANJIDIC2 が無ければ飛ばす。
# 現代語訳の用言の見出しには中古和文UniDic を使う (無ければ規則で)
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths  # noqa: E402
from dragoman.kanbun import parse, readings  # noqa: E402

HAVE_DATA = parse.available() and readings.kanjidic_available()


class ReadingsTestCase(unittest.TestCase):
    def test_conjugation(self):
        self.assertEqual(readings.predicate('學ぶ').forms, ('學ば', '學び', '學ぶ', '學ぶ', '學べ', '學べ'))
        self.assertEqual(readings.predicate('改む/下二').form('連体'), '改むる')
        self.assertEqual(readings.predicate('出づ/下二').form('連用'), '出で')
        self.assertEqual(readings.predicate('樂し/シク').form('未然', aux=True), '樂しから')   # 助動詞の前はカリ活用
        self.assertEqual(readings.predicate('罔し').form('已然'), '罔けれ')
        self.assertEqual(readings.predicate('有り').form('連体'), '有る')
        self.assertEqual(readings.predicate('死す/サ変').form('未然'), '死せ')
        self.assertEqual(readings.predicate('可なり/ナリ').form('終止'), '可なり')

    def test_shinjitai(self):
        self.assertEqual(readings.shinjitai('學びて說ばし'), '学びて説ばし')


@unittest.skipUnless(HAVE_DATA, 'no UD-Kanbun or KANJIDIC2')
class KanbunTestCase(unittest.TestCase):
    def analyze(self, text):
        from dragoman.kanbun import analyzer
        return analyzer.analyze_sentence(text)

    def assertReads(self, text, kakikudashi, modern=None):
        a = self.analyze(text)
        self.assertEqual(a.kakikudashi, kakikudashi)
        if modern is not None:
            self.assertEqual(a.modern, modern)

    def test_order_and_okurigana(self):
        # 目的語・補語を動詞の前に、否定・助動詞を後ろに。送り仮名は後ろの語が求める活用形
        self.assertReads('學而時習之、不亦說乎。', '學びて時に之を習ふ、亦た說ばしからずや。',
                         '学んで時々これを習う、またうれしいではないか。')
        self.assertReads('有朋自遠方來、不亦樂乎。', '朋有り遠方より來たる、亦た樂しからずや。')
        self.assertReads('知者樂水。', '知者は水を樂しむ。', '知者は水を楽しむ。')   # 目的語を取る 樂 は 樂しむ
        self.assertReads('己所不欲、勿施於人。', '己の欲せざる所、人に施すこと勿かれ。',
                         '自分の望まないこと、人に施してはならない。')

    def test_conditionals(self):
        self.assertReads('不入虎穴、不得虎子。', '虎穴に入らずんば、虎子を得ず。', '虎穴に入らなければ、虎子を得ない。')
        self.assertReads('學而不思則罔。', '學びて思はざれば則ち罔し。', '学んで思わなければ道理が分からない。')

    def test_okiji_and_comparison(self):
        # 置き字 於: 起点・比較は より、而 は前の用言を連用形 + て に
        self.assertReads('青出於藍而青於藍。', '青は藍より出でて藍より青し。', '青は藍から出て藍よりも青い。')

    def test_saidoku_and_rhetorical(self):
        self.assertReads('未知生、焉知死。', '未だ生を知らず、焉くんぞ死を知らん。', 'まだ生を知らない、どうして死を知ろうか。')
        self.assertReads('豈不悲哉。', '豈に悲しまずや。', 'どうして悲しまないことがあろうか。')

    def test_auxiliaries(self):
        self.assertReads('兔不可復得。', '兔復た得べからず。', '兔は再び得ることができない。')   # 不可 → べからず
        self.assertReads('王使人學之。', '王人をして之を學ばしむ。', '王は人にこれを学ばせる。')      # 使役
        self.assertReads('信而見疑、忠而被謗。', '信じて疑はる、忠して謗らる。')                         # 受身
        self.assertReads('吾日三省吾身。', '吾日に三たび吾が身を省みる。')

    def test_word_readings(self):
        a = self.analyze('未知生、焉知死。')
        mi = a.phrases[0][0]
        self.assertEqual(a.reading_of(mi), '未だ…ず')   # 再読文字は前と後ろで読む

    def test_note_units(self):
        # ノートの縦書きの訓点: (字, 振り仮名, 右の送り仮名, 返り点, 左の送り仮名)。置き字 於 の助詞は前の名詞に
        from dragoman.kanbun import note, ruby
        units = note.units(self.analyze('學而時習之、不亦說乎。'))
        self.assertEqual([(u[0],) + u[2:] for u in units[:5]],
                         [('學', 'ビテ', '', ''), ('而', '', '', ''), ('時', 'ニ', '', ''), ('習', 'フ', 'レ', ''),
                          ('之', 'ヲ', '', '')])
        self.assertEqual([(u[0],) + u[2:] for u in note.units(self.analyze('將入城。'))[:2]],
                         [('將', 'ニ', 'レ', 'ス'), ('入', 'ラント', 'レ', '')])
        self.assertIn(('人', 'ニ', '一', ''), [(u[0],) + u[2:] for u in note.units(self.analyze('己所不欲、勿施於人。'))])
        self.assertIn('part kunten', note.html_of(self.analyze('將入城。')))
        if ruby.available():
            self.assertEqual([u[1] for u in units[:5]], ['まな', '', 'とき', 'なら', 'これ'])

    @unittest.skipUnless(HAVE_DATA and os.path.exists(os.path.join(paths.data(), 'ja-readings.tsv')), 'no ja-readings.tsv')
    def test_yomi(self):
        # 振り仮名: 用言は KANJIDIC2 の訓の語幹 (送り仮名の行で)、名詞・熟語は JMdict (語義で選び、1字なら訓を先に)、
        # 助字・副詞・代名詞は手作りの表。どれも歴史的仮名遣いに (Wiktionary の語から作った表: 遠方 ゑんぱう・王 わう)
        self.assertEqual(self.analyze('有朋自遠方來、不亦樂乎。').yomi, 'ともありゑんぱうよりきたる、またたのしからずや。')
        self.assertEqual(self.analyze('己所不欲、勿施於人。').yomi, 'おのれのほつせざるところ、ひとにほどこすことなかれ。')
        self.assertEqual(self.analyze('子曰、學而不思則罔。').yomi, 'しいはく、まなびておもはざればすなはちくらし。')
        self.assertEqual(self.analyze('不入虎穴、不得虎子。').yomi, 'こけつにいらずんば、こしをえず。')
        self.assertEqual(self.analyze('未知生、焉知死。').yomi, 'いまだせいをしらず、いづくんぞしをしらん。')
        self.assertEqual(self.analyze('王使人學之。').yomi, 'わうひとをしてこれをまなばしむ。')
        self.assertEqual(self.analyze('青出於藍而青於藍。').yomi, 'あをはあゐよりいでてあゐよりあをし。')
        self.assertTrue(self.analyze('城春草木深。').yomi.endswith('ふかし。'))   # 形容詞の文語の活用
        a = self.analyze('溫故而知新、可以爲師矣。')   # 可以 の 以て は 以 の字に
        self.assertEqual(a.yomi, 'ゆゑをあたためてあたらしきをしる、もつてしとなるべし。')

    def test_topic_wa(self):
        # 主語の「は」は既定では書き下しに付けない (教科書どおり。者 の後ろは付ける)。--wa で付ける。現代語訳には残す
        from dragoman.kanbun import kundoku
        self.assertReads('春眠不覺曉。', '春眠曉を覺えず。', '春眠は曉を覚えない。')
        self.assertEqual(self.analyze('知者樂水。').kakikudashi[:3], '知者は')
        # 決まった言い回し (readings.WA_KEPT) は既定でも付ける
        self.assertReads('百聞不如一見。', '百聞は一見に如かず。')
        self.assertReads('忠言逆於耳。', '忠言は耳に逆らふ。')
        kundoku.TOPIC_WA = True
        try:
            self.assertReads('春眠不覺曉。', '春眠は曉を覺えず。')
        finally:
            kundoku.TOPIC_WA = False

    def test_parse_repair(self):
        # UD-Kanbun の係り受けの誤りを直す (parse.repair)。返り点もそれに合わせて付く
        self.assertReads('春眠不覺曉。', '春眠曉を覺えず。', '春眠は曉を覚えない。')
        self.assertEqual(self.analyze('春眠不覺曉。').kaeriten, '春眠不㆑覺㆑曉。')
        self.assertReads('百聞不如一見。', '百聞は一見に如かず。', '百聞は一見に及ばない。')
        self.assertReads('國破山河在。', '國破れて山河在り。', '国が破れて山河はある。')
        self.assertReads('歲月不待人。', '歲月は人を待たず。', '歳月は人を待たない。')
        self.assertReads('學不可以已。', '學は以て已むべからず。')
        self.assertReads('過猶不及。', '過ぎたるは猶ほ及ばざるがごとし。')
        self.assertReads('天時不如地利、地利不如人和。', '天の時は地の利に如かず、地の利は人の和に如かず。')
        self.assertReads('少年易老、學難成。', '少年老い易く、學成り難し。', '少年は老いやすく、学は成りにくい。')
        self.assertReads('少年易老學難成。', '少年老い易く學成り難し。', '少年は老いやすく学は成りにくい。')
        self.assertReads('大器晩成。', '大器は晩成す。', '大器は晩成する。')

    def test_set_phrases(self):
        # 決まった言い回しの読み: 体の部分の 於 は に、苦し (ク) は にがし、良藥 りやうやく
        a = self.analyze('良藥苦於口。')
        self.assertEqual(a.kakikudashi, '良藥は口に苦し。')
        self.assertEqual(a.modern, '良薬は口に苦い。')
        self.assertEqual(a.yomi, 'りやうやくはくちににがし。')
        self.assertEqual(self.analyze('學不可以已。').yomi, 'がくはもつてやむべからず。')
        self.assertEqual(self.analyze('地利不如人和。').yomi, 'ちのりはひとのわにしかず。')
        self.assertEqual(self.analyze('大器晩成。').yomi, 'たいきはばんせいす。')

if __name__ == '__main__':
    unittest.main()
