#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古典ギリシア語の転写 (greek.romanize)
#
import unittest

from dragoman.greek.romanize import romanize, romanize_word


class RomanizeTestCase(unittest.TestCase):
    def test_sentence(self):
        self.assertEqual(romanize('ἐν ἀρχῇ ἦν ὁ λόγος'), 'en archêi ên ho lógos')

    def test_breathing_on_diphthong(self):
        self.assertEqual(romanize_word('οἱ'), 'hoi')
        self.assertEqual(romanize_word('αἱ'), 'hai')
        self.assertEqual(romanize_word('υἱός'), 'hyiós')

    def test_consonants(self):
        self.assertEqual(romanize_word('ἄγγελος'), 'ángelos')   # γγ → ng
        self.assertEqual(romanize_word('ῥήτωρ'), 'rhḗtōr')      # 語頭の ῥ → rh
        self.assertEqual(romanize_word('εὐαγγέλιον'), 'euangélion')
        self.assertEqual(romanize_word('Σωκράτης'), 'Sōkrátēs')



@unittest.skipUnless(__import__('dragoman.greek.dictionary', fromlist=['x']).available(), 'ギリシア語の辞書が無い')
class FromLatinTestCase(unittest.TestCase):
    def test_academic(self):
        from dragoman.greek.romanize import from_latin
        self.assertEqual(from_latin('en archêi ên ho lógos'), 'ἐν ἀρχῇ ἦν ὁ λόγος')   # ēi → ῃ、h → 有気
        self.assertEqual(from_latin('Mênin áeide theá'), 'Μῆνιν ἄειδε θεά')
        self.assertEqual(from_latin('huiós'), 'υἱός')                                # 二重母音の気息は2つ目の字に
        self.assertEqual(from_latin('rhētōr angelos'), 'ῥητωρ ἀγγελος')               # 語頭の ρ は有気、ng → γγ

    def test_beta_code(self):
        from dragoman.greek.romanize import from_latin
        self.assertEqual(from_latin('e)n a)rxh=| h)=n o( lo/gos'), 'ἐν ἀρχῇ ἦν ὁ λόγος')

    def test_untouched(self):
        from dragoman.greek.romanize import from_latin
        self.assertEqual(from_latin('λόγος'), 'λόγος')


if __name__ == '__main__':
    unittest.main()
