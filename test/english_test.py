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
        self.assertEqual(self.ja('She gave me a beautiful flower.'), '彼女が / 私に / 美しい{花,草花}を / 与えた')
        self.assertEqual(self.ja("John's sister can speak Japanese."),
                         'ジョンの{姉,妹}が / {日本語,日本の公用語}を / 話すことができる')

    def test_verb_groups(self):
        self.assertEqual(self.ja('The letter was written by my father.'),
                         '{文字,手紙}が / 私の父によって / 書かれた,著作された')
        self.assertEqual(self.ja('We are studying English now.'), '私たちが / {英語,イングランド語}を / 今 / 勉強している')
        self.assertEqual(self.ja('He will come tomorrow.'), '彼が / 明日 / 来るだろう')
        self.assertEqual(self.ja('I want to go to London.'), '私が / ロンドン[へ,に] / 行きたい')
        self.assertEqual(self.ja('They began to sing.'), '彼らが / 歌い始めた')

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
                         'あなたが / {誰が この{本,書物}を 書いた,著作した}かを / 知っているか')
        self.assertEqual(self.ja('I wonder whether he will come.'), '私が / {彼が 来るだろう}かどうかを / 不思議に思う,驚く')
        self.assertEqual(self.ja('Tell me where you live.'), '私に / {どこで あなたが 住む}かを / 話せ,伝えろ')

    def test_detect(self):
        from dragoman.main import detect
        for text in ('The boy reads a book.', 'Do you like cats?', "John's sister can speak Japanese."):
            self.assertEqual(detect(text), 'en', text)
        self.assertEqual(detect('Gallia est omnis divisa in partes tres.'), 'la')


if __name__ == '__main__':
    unittest.main()
