#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語 (ブラジル・ポルトガル)
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402

HAVE_DATA = available('portuguese')


def tr(text):
    return translate('portuguese', text)


@unittest.skipUnless(HAVE_DATA, 'spaCy の pt_core_news_sm かポルトガル語の辞書 (tools/build_portuguese_dic.py) が無い')
class AnalyzerTestCase(unittest.TestCase):
    def test_svo_and_genitive(self):   # 名詞 + de (da) + 名詞は属格、前置詞と冠詞の縮約形 (na) は前置詞
        self.assertEqual(tr('O menino leu o livro da professora na escola.'), '少年が / 学校[で,に] / 先生の本を / 読んだ')

    def test_clitics(self):
        self.assertEqual(tr('Você me deu o livro?'), 'あなたが / 私に / 本を / 与えたか')   # 目的語の名詞があれば me は与格
        self.assertEqual(tr('Dei-lhe o livro.'), '私が / {彼,彼女,あなた}に / 本を / 与えた')   # ハイフンの接語
        self.assertEqual(tr('O homem que veio me viu.'), '来た男が / 私を / 見た')   # 動詞の前の接語は後ろの動詞に

    def test_verb_groups(self):
        self.assertEqual(tr('Estou lendo um livro.'), '私が / 本を / 読んでいる')     # ブラジルの進行形
        self.assertEqual(tr('Estou a ler um livro.'), '私が / 本を / 読んでいる')     # ポルトガルの進行形
        self.assertEqual(tr('A casa foi construída pelo pai.'), '家が / 父によって / 建てられた')
        self.assertEqual(tr('Eu quero falar português.'), '私が / ポルトガル語を / 話したい')
        self.assertEqual(tr('Tenho que estudar.'), '私が / 勉強しなければならない')
        self.assertIn('食べるだろう', tr('Vou comer no restaurante.'))

    def test_clauses(self):
        self.assertEqual(tr('Eu não sei onde ele mora.'), '私が / {{彼,それ}が どこで 住む}かを / 知らない')
        self.assertTrue(tr('Quando ele chegou, eu o vi.').startswith('{{彼,それ}が 着いた}とき / '))
        self.assertIn('私を 愛する}と / 言った', tr('Ela disse que me ama.'))   # 補文の que

    def test_possessive_dele(self):
        self.assertEqual(tr('O livro dele é bonito.'), '彼の本は / 美しい')


@unittest.skipUnless(HAVE_DATA, 'ポルトガル語のデータが無い')
class RelativeAndParticipleTestCase(unittest.TestCase):
    def test_relative_after_numeral(self):   # 数詞 + 名詞 + que (que の格は節の中の働きで)
        self.assertEqual(tr('Vi os seis homens que moram aqui.'), '私が / {ここで 住む}六つの男を / 見た')
        self.assertEqual(tr('O homem que vi é alto.'), '{私が 見た}男は / 高い')

    def test_participles(self):   # 辞書に無い過去分詞は動詞の受動で
        self.assertEqual(tr('Os livros vendidos são caros.'), '売られた本は / 高価,親愛である')

    def test_spacy_slips(self):
        self.assertEqual(tr('A menina canta enquanto o menino lê um livro.'),
                         '{少年が 本を 読む}間に / 少女が / 歌う')   # spaCy が副詞と読む文中の enquanto
        self.assertEqual(tr('Quando ele vem?'), 'いつ / {彼,それ}が / 来るか')   # 文頭の疑問詞

    def test_dashes(self):   # 「--」の入った文で落ちない
        self.assertTrue(tr('White -- Acho que sim .'))


@unittest.skipUnless(HAVE_DATA, 'ポルトガル語のデータが無い')
class KanaTestCase(unittest.TestCase):
    def test_brazil_and_portugal(self):
        from dragoman.portuguese.katakana import katakana
        cases = {'obrigado': ('オブリガドゥ', 'オブリガドゥ'), 'cidade': ('スィダジ', 'スィダド'), 'noite': ('ノイチ', 'ノイト'),
                 'Rio': ('ヒウ', 'リウ'), 'coração': ('コラサウン', 'クラサウン'), 'mãe': ('マイン', 'マイン'),
                 'gente': ('ジェンチ', 'ジェント'), 'também': ('タンベイン', 'タンベイン'), 'vocês': ('ヴォセス', 'ヴセシュ'),
                 'Brasil': ('ブラズィウ', 'ブラズィル'), 'o': ('ウ', 'ウ')}
        for word, (br, pt) in cases.items():
            self.assertEqual(katakana(word), br, word)
            self.assertEqual(katakana(word, pt='pt'), pt, word)


class DetectTestCase(unittest.TestCase):
    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('O menino leu o livro da professora.'), 'pt')
        self.assertEqual(detect('Eu não sei onde ele mora.'), 'pt')
        self.assertEqual(detect('Le garçon lit un livre.'), 'fr')


if __name__ == '__main__':
    unittest.main()
