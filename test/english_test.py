#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語: 格 (依存関係から)、冠詞・所有格、助動詞の組 (受動・完了・進行・未来・法の助動詞)、want to などの不定詞、
# there is、関係節、日本語訳 (english.analyzer)。spaCy の英語モデルか英和の表が無ければ飛ばす
#
import unittest

try:
    from dragoman.english import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


@unittest.skipUnless(HAVE_DATA, 'spaCy の英語モデルか英和の表が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_cases_and_articles(self):
        self.assertEqual(self.ja('She gave me a beautiful flower.'), '彼女が / 私に / 美しい花を / 与えた')
        self.assertEqual(self.ja("John's sister can speak Japanese."),
                         'ジャンの{姉,妹}が / {日本語,日本の公用語}を / 話すことができる')

    def test_verb_groups(self):
        self.assertEqual(self.ja('The letter was written by my father.'),
                         '手紙が / 私の{父,父親}によって / 書かれた')
        self.assertEqual(self.ja('We are studying English now.'), '私たちが / {英語,イングランド語}を / 今 / 勉強している')
        self.assertEqual(self.ja('He will come tomorrow.'), '彼が / 明日 / 来るだろう')
        self.assertEqual(self.ja('I want to go to London.'), '私が / ロンドン[へ,に] / 行きたい')
        self.assertEqual(self.ja('They began to sing.'), '彼らが / 歌い始めた')

    def test_going_to_and_colloquial(self):
        self.assertEqual(self.ja("I'm going to eat."), '私が / 食べるつもりだ')        # be going to + 原形
        self.assertEqual(self.ja("It's going to rain."), 'それが / 雨が降るだろう')   # 人でない主語は未来
        self.assertEqual(self.ja('I was going to call you.'), '私が / あなたを / 呼ぶつもりだった')
        self.assertEqual(self.ja("I'm going to school."), '私が / {学校,高校}[へ,に] / 行っている')
        self.assertEqual(self.ja("I've got to go."), '私が / 行かなければならない')
        self.assertEqual(self.ja("I'm trying to sleep."), '私が / 眠ろうとする')
        self.assertEqual(self.ja('I wanted to sleep.'), '私が / 眠りたかった')
        self.assertEqual(self.ja("I didn't want to sleep."), '私が / 眠りたくなかった')
        self.assertEqual(self.ja('You ought to go.'), 'あなたが / 行くべきだ')
        # 縮まった形は元の形で解析し、語の表には縮まった形のまま
        self.assertEqual(self.ja("I'm gonna eat."), '私が / 食べるつもりだ')
        self.assertEqual(self.ja('I gotta go.'), '私が / 行かなければならない')
        self.assertEqual(self.ja('I wanna sleep.'), '私が / 眠りたい')
        self.assertEqual(self.ja("I'm tryna sleep."), '私が / 眠ろうとする')
        self.assertEqual(self.ja('You oughta go.'), 'あなたが / 行くべきだ')
        self.assertEqual(analyzer.tokens("I'm gonna eat."), ['I', "'m", 'gonna', 'eat', '.'])
        words = analyzer.lookup_all(['I', 'gotta', 'go', '.'])
        self.assertEqual(words[1].surface, 'gotta go')
        self.assertIn('gotta = got to', words[1].items[0].attrib('form'))

    def test_negation_in_verb(self):
        # not・n't は動詞にまとめる (語の表に単独で出さない)
        for text, surface, ja in [("I can't go.", "can't go", '私が / 行くことができない'),
                                  ('I do not know.', 'do not know', '私が / 知らない'),
                                  ('I dunno.', "don't know", '私が / 知らない'),
                                  ("I didn't want to sleep.", "didn't want to sleep", '私が / 眠りたくなかった'),
                                  ("He isn't a doctor.", "isn't", '彼は / 医者ではない'),
                                  ("Don't you know?", "Don't … know", 'あなたが / 知らないか'),
                                  ("Don't go!", "Don't go", '行くな')]:
            words = analyzer.lookup_all(next(analyzer.sentences(text)))
            self.assertIn(surface, [w.surface for w in words], text)
            self.assertNotIn("n't", [w.surface for w in words], text)
            self.assertEqual(self.ja(text), ja)
        self.assertEqual(self.ja('I never sleep.'), '私が / 眠らない,寝ない')   # never は副詞のまま

    def test_existential_and_relative(self):
        self.assertEqual(self.ja('There is a cat in the garden.'), '庭に / 猫が / いる')
        self.assertEqual(self.ja('The man who lives here is my teacher.'), '{ここで 住む}男は / 私の先生,教師である')

    def test_questions(self):
        self.assertEqual(self.ja('Where do you live?'), 'どこで / あなたは / 住むか')   # 疑問詞のある疑問文の主語は「は」
        self.assertEqual(self.ja('Do you like cats?'), 'あなたが / 猫を / 好むか')
        self.assertEqual(self.ja('Who is that man?'), 'その男は / 誰であるか')         # 疑問詞は補語
        self.assertEqual(self.ja('How old are you?'), 'あなたは / 何歳であるか')
        self.assertEqual(self.ja('What are you talking about?'), 'あなたは / 何について / 話しているか')   # 取り残された前置詞
        self.assertEqual(self.ja('Have you ever been to Japan?'), '今までに / あなたが / 日本[へ,に] / 行ったか')

    def test_indirect_questions(self):
        self.assertEqual(self.ja("I don't know what you're talking about."),
                         '私が / {あなたが 何について 話している}かを / 知らない')
        self.assertEqual(self.ja('Do you know who wrote this book?'),
                         'あなたが / {誰が この本を 書いた}かを / 知っているか')
        self.assertEqual(self.ja('I wonder whether he will come.'), '私が / {彼が 来るだろう}かどうかを / 不思議に思う,驚く')
        self.assertEqual(self.ja('Tell me where you live.'), '私に / {どこで あなたが 住む}かを / 話せ,伝えろ')

    def test_adverbial_clauses(self):
        self.assertEqual(self.ja('I saw her when she came.'), '{彼女が 来た}とき / 私が / 彼女を / 見た')
        self.assertEqual(self.ja('When she came, I saw her.'), '{彼女が 来た}とき / 私が / 彼女を / 見た')   # 文の頭の副詞節
        self.assertEqual(self.ja('If you study, you will pass the exam.'),
                         '{あなたが 勉強する}なら / あなたが / {試験,テスト}に / 受かるだろう')
        self.assertEqual(self.ja('He left after the meeting ended.'), '{{会議,会合}が 終わった}後で / 彼が / 去った')
        self.assertEqual(self.ja('Wash your hands before you eat.'),
                         '{あなたが 食べる,食う}前に / あなたの手を / 洗え')   # before の節は現在

    def test_glosses_in_context(self):
        self.assertEqual(self.ja('You will pass the exam.'), 'あなたが / {試験,テスト}に / 受かるだろう')   # 目的語で動詞の訳語 (JMdict)
        self.assertEqual(self.ja("Don't give up."), '諦めるな,見限るな')                           # 句動詞 (否定の命令)
        self.assertEqual(self.ja('Take this medicine.'), 'この薬を / 飲め,受け付けろ')            # 対訳文 (Tatoeba) で薬
        self.assertEqual(self.ja('She is looking after her brother.'), '彼女が / 彼女の{兄,弟}を / 世話している')

    def test_detect(self):
        from dragoman.main import detect
        for text in ('The boy reads a book.', 'Do you like cats?', "John's sister can speak Japanese."):
            self.assertEqual(detect(text), 'en', text)
        self.assertEqual(detect('Gallia est omnis divisa in partes tres.'), 'la')


if __name__ == '__main__':
    unittest.main()
