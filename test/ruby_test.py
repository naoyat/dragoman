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
        self.assertEqual(kanas(ruby.ruby('в Москве', 'ru')), [('в', ''), ('Москве', 'ヴマスクヴェー')])

    def test_english(self):
        from dragoman.english import katakana
        if not katakana.available():
            self.skipTest('CMUdict も espeak-ng も無い')
        self.assertEqual(kanas(ruby.ruby("I don't know.", 'en')), [('I', 'アイ'), ("don't", 'ドウント'), ('know', 'ノウ'), ('.', '')])


if __name__ == '__main__':
    unittest.main()
