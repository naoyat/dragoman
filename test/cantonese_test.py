#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 広東語 (dragoman/cantonese): カタカナ読み・語の切り分け・普通話への置き換え・文の訳。辞書・PyCantonese が無ければ飛ばす
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402
from dragoman.cantonese import katakana   # noqa: E402

HAVE_DATA = available('cantonese')


def tr(text):
    return translate('cantonese', text)


class KatakanaTestCase(unittest.TestCase):
    def test_syllables(self):
        self.assertEqual(katakana.from_jyutping('nei5 hou2'), 'ネイ ホウ')
        self.assertEqual(katakana.from_jyutping('m4 goi1'), 'ム ゴイ')               # 音節だけの m
        self.assertEqual(katakana.from_jyutping('hoeng1 gong2'), 'ヒョン ゴン')       # oe は拗音
        self.assertEqual(katakana.from_jyutping('gwong2 dung1 waa2'), 'グォン ドン ワ')   # u + ng はオン
        self.assertEqual(katakana.from_jyutping('syu1 luk6 ng5'), 'シュ ロック ン')
        self.assertEqual(katakana.from_jyutping('keoi5 jam2 caa4'), 'コイ ヤム チャ')


@unittest.skipUnless(HAVE_DATA, '広東語の辞書か PyCantonese か普通話のモデルが無い (tools/build_cantonese_dic.py の注)')
class CantoneseTestCase(unittest.TestCase):
    def pairs(self, text):
        from dragoman.cantonese import morphology, segment
        return [m for _, m in morphology.rewrite(segment.segment(text))]

    def test_segment(self):
        from dragoman.cantonese import segment
        self.assertEqual(segment.segment('佢畀本書我。'), ['佢', '畀', '本', '書', '我', '。'])   # 辞書に無い 畀本書 は分ける
        self.assertEqual(segment.segment('我唔係老師。'), ['我', '唔', '係', '老師', '。'])

    def test_rewrite(self):
        self.assertEqual(self.pairs('佢係我嘅朋友。'), ['他', '是', '我', '的', '朋友', '。'])
        self.assertEqual(self.pairs('我高過佢。'), ['我', '比', '他', '高', '。'])               # 比較
        self.assertEqual(self.pairs('佢畀本書我。'), ['他', '给', '我', '书', '。'])             # 二重目的語
        self.assertEqual(self.pairs('我畀老師鬧。'), ['我', '被', '老师', '骂', '。'])           # 受動
        self.assertEqual(self.pairs('你去唔去？'), ['你', '去', '吗', '？'])                     # 反復疑問
        self.assertEqual(self.pairs('佢食緊飯。'), ['他', '在', '吃饭', '。'])                # 進行 (食 + 飯 は1語に)
        self.assertEqual(self.pairs('你食咗飯未呀？')[-3:], ['吗', '啊', '？'])                  # 文末の 未

    def test_sentences(self):
        cases = {
            '佢係我嘅朋友。': '彼は / 私の友人である',
            '我唔係老師。': '私は / 先生ではない',
            '你食咗飯未呀？': 'あなたが / {飯,食事}を / 食べたか',
            '佢畀本書我。': '彼が / 私に / 本を / 与える',
            '我唔知佢喺邊度。': '私が / {彼が どこ いる,ある}かを / 知らない',
            '我想去香港。': '私が / 香港に / 行きたい',
            '佢識講廣東話。': '彼が / 広東語を / 話すことができる',
            '我好鍾意睇戲。': 'とても / 私が / 映画を / 見るのが好きだ',
        }
        for text, expected in cases.items():
            self.assertEqual(tr(text), expected, text)
        self.assertIn('彼より', tr('我高過佢。'))

    def test_detect(self):
        from dragoman import main
        self.assertEqual(main.detect('我食咗飯喇。'), 'yue')
        self.assertEqual(main.detect('佢係我嘅朋友。'), 'yue')
        self.assertEqual(main.detect('我吃了饭。'), 'zh')


if __name__ == '__main__':
    unittest.main()
