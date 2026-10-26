#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語 (普通話)
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402

HAVE_DATA = available('chinese')


def tr(text):
    return translate('chinese', text)


@unittest.skipUnless(HAVE_DATA, 'spaCy の zh_core_web_sm か中国語の辞書 (tools/build_chinese_dic.py) が無い')
class SegmentTestCase(unittest.TestCase):
    def test_segment(self):
        from dragoman.chinese.segment import segment
        self.assertEqual(segment('我是日本人。'), ['我', '是', '日本人', '。'])
        self.assertEqual(segment('我昨天买了一本书。'), ['我', '昨天', '买', '了', '一', '本', '书', '。'])   # 量詞で切る
        self.assertEqual(segment('他把书放在桌子上。')[2:4], ['书', '放'])   # 辞書に無い 书放 は分け直す
        self.assertEqual(segment('我們學習中文。'), ['我們', '學習', '中文', '。'])   # 繁体字


@unittest.skipUnless(HAVE_DATA, '中国語のデータが無い')
class AnalyzerTestCase(unittest.TestCase):
    def test_classifier_and_aspect(self):
        self.assertEqual(tr('我昨天买了一本书。'), '昨日 / 私が / 一冊の本を / 買った')
        self.assertEqual(tr('我没去过中国。'), '私が / 中国に / 行ったことがない')
        self.assertEqual(tr('他正在吃饭。'), '彼が / 食事をしている')

    def test_de(self):
        self.assertEqual(tr('妈妈的书在桌子上。'), '母の本が / 机の上に / ある,いる')
        self.assertEqual(tr('我买的书很有意思。'), '私が買う本は / とても面白い')
        self.assertEqual(tr('月亮代表我的心。'), '月が / 私の心を / 表す,代表する')

    def test_ba_bei_and_prepositions(self):
        self.assertEqual(tr('他把书放在桌子上。'), '彼が / 机の上に / 本を / 置く')
        self.assertEqual(tr('书被他拿走了。'), '本が / 彼によって / 持ち去られた')
        self.assertEqual(tr('他在图书馆看书。'), '彼が / 図書館で / 本を / 見る,読む')

    def test_clauses_and_questions(self):
        self.assertEqual(tr('因为下雨，我没去。'), '{雨が降る}ので / 私が / 行かなかった')
        self.assertEqual(tr('我知道他住在哪儿。'), '私が / {彼が どこに 住む}かを / 知っている')
        self.assertEqual(tr('你吃饭了吗？'), 'あなたが / 食事をしたか')
        self.assertEqual(tr('这个问题很难。'), 'この問題は / とても難しい')


@unittest.skipUnless(HAVE_DATA, '中国語のデータが無い')
class KanaTestCase(unittest.TestCase):
    def test_kana(self):
        from dragoman.chinese.katakana import katakana
        cases = {'九': 'ジョウ', '对': 'ドゥェイ', '北京': 'ベイジン', '中国': 'ジョングオ', '的': 'ダ', '了': 'ラ',
                 '月亮': 'ユエリャン', '女儿': 'ニュアル', '中文': 'ジョンウェン', '去': 'チュ', '四': 'ス', '是': 'シ',
                 '我们': 'ウォメン'}
        for word, expected in cases.items():
            self.assertEqual(katakana(word), expected, word)

    def test_ruby(self):
        from dragoman.core.ruby import ruby
        self.assertEqual([(r['text'], r['kana']) for r in ruby('我們學習中文。', 'zh')],
                         [('我們', 'ウォメン'), ('學習', 'シュエシ'), ('中文', 'ジョンウェン'), ('。', '')])


class DetectTestCase(unittest.TestCase):
    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('月亮代表我的心。'), 'zh')
        self.assertEqual(detect('いと思ふ人'), 'kobun')


if __name__ == '__main__':
    unittest.main()
