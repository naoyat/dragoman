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
        self.assertEqual(tr('他把书放在桌子上。'), '彼が / 本を / 机の上に / 置く')   # 把の目的語を先に
        self.assertEqual(tr('书被他拿走了。'), '本が / 彼によって / 持ち去られた')
        self.assertEqual(tr('他在图书馆看书。'), '彼が / 図書館で / 本を / 見る,読む')

    def test_clauses_and_questions(self):
        self.assertEqual(tr('因为下雨，我没去。'), '{雨が降る}ので / 私が / 行かなかった')
        self.assertEqual(tr('我知道他住在哪儿。'), '私が / {彼が どこに 住む}かを / 知っている')
        self.assertEqual(tr('你吃饭了吗？'), 'あなたが / 食事をしたか')
        self.assertEqual(tr('这个问题很难。'), 'この問題は / とても難しい')


    def test_complements(self):   # 結果・方向・可能・様態の補語
        self.assertEqual(tr('我看完了这本书。'), '私が / この本を / 見終えた,読み終えた')
        self.assertEqual(tr('他走进来了。'), '彼が / 歩いて入って来た')
        self.assertEqual(tr('我听得懂中文。'), '私が / 中国語を / 聞いて分かることができる')
        self.assertEqual(tr('我看不懂这本书。'), '私が / この本を / 読んで分かることができない')
        self.assertEqual(tr('他跑得很快。'), '彼が / とても速く走る')
        self.assertEqual(tr('我想起来了。'), '私が / 思い出した')

    def test_subject_adverbs_and_people(self):
        self.assertEqual(tr('如果你去，我也去。'), '{あなたが 行く}なら / 私も / 行く')
        self.assertEqual(tr('我们都是学生。'), '私たちはみな / 学生である')
        self.assertEqual(tr('我有两个朋友。'), '私には / 二人の友人が / いる')   # 人を数える 个

    def test_you(self):   # 所有・存在の 有、没有 + 名詞
        self.assertEqual(tr('桌子上有一本书。'), '机の上に / 一冊の本が / ある')
        self.assertEqual(tr('我没有钱。'), '私には / {硬貨,金銭}が / ない')
        self.assertEqual(tr('他有很多书。'), '彼には / たくさんの本が / ある')
        self.assertEqual(tr('这里有人吗？'), 'ここに / 人が / いるか')
        self.assertEqual(tr('屋里没有人。'), '家の中には / 人が / いない')
        self.assertEqual(tr('人很多。'), '人は / とても多い')
        self.assertEqual(tr('书在桌子上。'), '本が / 机の上に / ある,いる')

    def test_complement_clauses(self):   # 補文 (接続詞なし)
        self.assertEqual(tr('教堂完成了主体大修工程。'), '教会が / 本体のリニューアルの{エンジニアリング,計画}を / 完成させた,成し遂げた')
        self.assertEqual(tr('有人说他是老师。'), 'ある人が / {彼が 先生である}と / 言う,話す')
        self.assertEqual(tr('我觉得他会来。'), '私が / {彼が 来るだろう}と / 思う,感じる')
        self.assertEqual(tr('我希望你来。'), '私が / {あなたが 来る}ことを / 望む,願う')
        self.assertEqual(tr('他会说中文。'), '彼が / 中国語を / 話すことができる')


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
