#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ベトナム語 (dragoman/vietnamese): カタカナ読み・語の切り分け・辞書・文の訳。辞書・Stanza が無ければ飛ばす
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402
from dragoman.vietnamese import katakana, morphology  # noqa: E402

HAVE_DATA = available('vietnamese')


def tr(text):
    return translate('vietnamese', text)


class KatakanaTestCase(unittest.TestCase):
    def test_katakana(self):
        self.assertEqual(katakana.katakana('xin chào'), 'シン チャオ')
        self.assertEqual(katakana.katakana('cảm ơn'), 'カム オン')
        self.assertEqual(katakana.katakana('Hà Nội'), 'ハー ノイ')          # 母音1つで終わる音節は長く
        self.assertEqual(katakana.katakana('phở'), 'フォー')
        self.assertEqual(katakana.katakana('bánh mì'), 'バイン ミー')        # ハノイの -anh
        self.assertEqual(katakana.katakana('áo dài'), 'アオ ザイ')           # d は [z]
        self.assertEqual(katakana.katakana('gì'), 'ジー')
        self.assertEqual(katakana.katakana('Việt Nam'), 'ヴィエット ナム')

    def test_numbers(self):
        self.assertEqual(morphology.number(['hai', 'mươi', 'ba']), 23)
        self.assertEqual(morphology.number(['một', 'trăm', 'linh', 'năm']), 105)
        self.assertEqual(morphology.kanji_number(1945), '千九百四十五')


@unittest.skipUnless(HAVE_DATA, 'ベトナム語の辞書か Stanza のモデルが無い (tools/build_vietnamese_dic.py の注)')
class VietnameseTestCase(unittest.TestCase):
    def words(self, text):
        from dragoman.vietnamese import analyzer, segment
        return analyzer.lookup_all(segment.segment(text))

    def test_segment(self):
        from dragoman.vietnamese import segment
        self.assertEqual(segment.segment('Tôi là sinh viên.'), ['Tôi', 'là', 'sinh viên', '.'])
        self.assertEqual(segment.segment('Chúng tôi học ở trường đại học.')[-2], 'trường đại học')   # 訳語の表の語
        self.assertIn('Uống', segment.segment('Uống nước nhớ nguồn.'))      # ことわざの見出しは分ける

    def test_dictionary(self):
        from dragoman.vietnamese import dictionary
        self.assertEqual(dictionary.han('sinh viên'), '生員')
        self.assertIn('học', dictionary.hanviet('學'))
        self.assertTrue(dictionary.lookup('khỏe')[0]['en'])                # 声調記号の位置の違い (khoẻ) を辿る

    def test_items(self):
        words = {w.surface: w.items[0] for w in self.words('Con mèo của tôi đang ngủ trên bàn.') if w.items}
        self.assertEqual(words['tôi'].ja, '私の')                          # của + 代名詞は所有
        self.assertEqual(words['ngủ'].attrib('tense'), 'progressive')     # đang
        self.assertEqual(words['bàn'].attrib('_')[0][0], 'Gen')           # 前置詞の目的語
        words = {w.surface: w.items[0] for w in self.words('Hai con chó này rất to.') if w.items}
        self.assertEqual(words['Hai con'].ja, '二匹の')                    # 数詞 + 量詞
        self.assertEqual(words['rất to'].ja.split(',')[0], 'とても大きい')
        words = {w.surface: w.items[0] for w in self.words('Tôi có hai người bạn.') if w.items}
        self.assertEqual(words['Tôi'].attrib('_')[0][0], 'Dat')           # có の所有者「私には」

    def test_sentences(self):
        cases = {
            'Tôi là sinh viên.': '私は / 学生である',
            'Hôm nay trời đẹp quá.': '今日 / {空,天気}は / とても美しい',
            'Tôi đã đọc quyển sách mà anh cho tôi.': '私が / 彼が私にくれた本を / 読んだ',
            'Tôi muốn đi Hà Nội.': '私が / ハノイに / 行きたい',
            'Bạn ăn cơm chưa?': 'あなたが / ご飯を / 食べたか',
            'Tôi bị mẹ mắng.': '私が / 母によって / 叱られる',
            'Tôi nghĩ rằng anh ấy là người tốt.': '私が / {彼が 良い人である}と / 思う,考える',
        }
        for text, expected in cases.items():
            self.assertEqual(tr(text), expected, text)
        self.assertEqual(tr('Nếu trời mưa thì tôi sẽ ở nhà.'), '{雨が降る}なら / 私が / 家に / いるだろう,住むだろう')   # 従属節
        self.assertEqual(tr('Tôi đã từng đi Hà Nội.'), '私が / ハノイに / 行ったことがある')   # 経験 (đã を重ねない)

    def test_detect(self):
        from dragoman import main
        self.assertEqual(main.detect('Tôi là sinh viên.'), 'vi')
        self.assertEqual(main.detect('Hôm nay trời đẹp quá.'), 'vi')
        self.assertEqual(main.detect('La forêt est très belle et le château aussi.'), 'fr')   # â ê ô だけはフランス語


if __name__ == '__main__':
    unittest.main()
