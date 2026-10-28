#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ルビ (フリガナ) 用のカタカナ (core/ruby.py): 元の文の文字の範囲とカナ、語をまたぐ音の載せ方 (next・prev・merge)
#
import unittest

from dragoman.core import ruby


def kanas(segments):
    return [(s['text'], s['kana']) for s in segments]


class RubyTestCase(unittest.TestCase):
    def test_tokens_keep_offsets(self):
        text = '«Ich liebe dich», sagte er.'
        segments = ruby.ruby(text, 'de')
        self.assertEqual(''.join(text[s['start']:s['end']] for s in segments), text.replace(' ', ''))
        self.assertEqual(kanas(segments)[:3], [('«', ''), ('Ich', 'イヒ'), ('liebe', 'リーベ')])   # 句読点はカナを空に

    def test_french_liaison(self):
        from dragoman.french import katakana
        if not katakana.available():
            self.skipTest('espeak-ng が無い')
        self.assertEqual(kanas(ruby.ruby('Les enfants sont arrivés.', 'fr')),
                         [('Les', 'レ'), ('enfants', 'ザンファン'), ('sont', 'ソン'), ('arrivés', 'タリヴェ'), ('.', '')])
        self.assertEqual([k for _, k in kanas(ruby.ruby('Il y a un chat.', 'fr'))][:3], ['イ', 'リ', 'ヤ'])   # il y a
        self.assertEqual([k for _, k in kanas(ruby.ruby('Les enfants sont arrivés.', 'fr', liaison='prev'))][:4],
                         ['レズ', 'アンファン', 'ソント', 'アリヴェ'])   # 前の語に残す
        self.assertEqual(kanas(ruby.ruby('Les enfants sont arrivés.', 'fr', liaison='merge'))[:2],
                         [('Les enfants', 'レザンファン'), ('sont arrivés', 'ソンタリヴェ')])   # つながった語をまとめる

    def test_russian_preposition(self):
        # 母音で始まる語には続け、子音で始まる語の前では前置詞だけで読む (有声・無声の同化は残す)
        self.assertEqual(kanas(ruby.ruby('в Италии', 'ru')), [('в', ''), ('Италии', 'ヴィターリイ')])
        self.assertEqual(kanas(ruby.ruby('в Москве', 'ru')), [('в', 'ヴ'), ('Москве', 'マスクヴェー')])
        self.assertEqual(kanas(ruby.ruby('в театр', 'ru')), [('в', 'フ'), ('театр', 'チアトル')])

    def test_english(self):
        from dragoman.english import katakana
        if not katakana.available():
            self.skipTest('CMUdict も espeak-ng も無い')
        self.assertEqual(kanas(ruby.ruby("I don't know.", 'en')), [('I', 'アイ'), ("don't", 'ドウント'), ('know', 'ノウ'), ('.', '')])


    def test_chinese_characters(self):
        from dragoman.chinese import morphology
        if not morphology.available():
            self.skipTest('中国語の辞書が無い')
        self.assertEqual(kanas(ruby.ruby('我喜欢去银行。', 'zh')),
                         [('我', 'ウォ'), ('喜欢', 'シファン'), ('去', 'チュ'), ('银行', 'インハン'), ('。', '')])
        # 漢字1字ごと: 読みは語の拼音の音節 (银行 の行 → háng)。漢字でない字はまとめてカナを空に
        segments = ruby.ruby('我喜欢去银行。2024年', 'zh', unit='char')
        self.assertEqual(kanas(segments), [('我', 'ウォ'), ('喜', 'シ'), ('欢', 'ファン'), ('去', 'チュ'), ('银', 'イン'),
                                           ('行', 'ハン'), ('。', ''), ('2024', ''), ('年', 'ニエン')])
        self.assertEqual([(s['start'], s['end']) for s in segments][-3:], [(6, 7), (7, 11), (11, 12)])
        self.assertEqual(kanas(ruby.ruby('Les enfants', 'de', unit='char'))[0][0], 'Les')   # ほかの言語は語ごとのまま


    def test_korean_characters(self):
        # ハングルの字ごと: 連音で動いた子音は次の字に、促音の「ッ」は前の字に。つなげば語のカナ
        self.assertEqual(kanas(ruby.ruby('한국어를 배웁니다.', 'ko', unit='char')),
                         [('한', 'ハン'), ('국', 'グ'), ('어', 'ゴ'), ('를', 'ルル'), ('배', 'ペ'), ('웁', 'ウム'), ('니', 'ニ'),
                          ('다', 'ダ'), ('.', '')])
        self.assertEqual(kanas(ruby.ruby('학교 아빠', 'ko', unit='char')),
                         [('학', 'ハッ'), ('교', 'キョ'), ('아', 'アッ'), ('빠', 'パ')])
        # 括弧・数字をまたいで連音しない。句読点は1字ずつ、ほかのハングルでない字はまとめてカナを空に
        self.assertEqual(kanas(ruby.ruby('학교(2024년)에', 'ko', unit='char')),
                         [('학', 'ハッ'), ('교', 'キョ'), ('(', ''), ('2024', ''), ('년', 'ニョン'), (')', ''), ('에', 'エ')])
        from dragoman.korean.katakana import katakana, syllable_katakana
        for word in ('감사합니다', '맛있어요', '떡볶이', '독립', '같이', '앉아요'):
            self.assertEqual(''.join(syllable_katakana(word)), katakana(word), word)


if __name__ == '__main__':
    unittest.main()
