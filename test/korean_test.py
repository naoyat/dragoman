#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語: ローマ字 (korean.script)、助詞・語尾からの格と時制、補助用言、連体形、日本語訳 (korean.analyzer)。
# kiwipiepy か辞書 (tools/build_korean_dic.py) が無ければ解析の試験を飛ばす
#
import unittest

from dragoman.korean import script

try:
    from dragoman.korean import analyzer, morphology
    HAVE_DATA = morphology.available()
except ImportError:
    HAVE_DATA = False


class ScriptTestCase(unittest.TestCase):
    def test_romanize(self):
        self.assertEqual(script.romanize('학교'), 'hakgyo')
        self.assertEqual(script.romanize('읽어요'), 'ilgeoyo')     # 音節末の子音の連音
        self.assertEqual(script.romanize('서울'), 'seoul')
        self.assertEqual(script.romanize('달리다'), 'dallida')     # ㄹㄹ → ll


@unittest.skipUnless(HAVE_DATA, 'kiwipiepy か韓国語の辞書が無い')
class AnalyzerTestCase(unittest.TestCase):
    def ja(self, text):
        a = next(analyzer.analyze_text(text))
        return ' / '.join(c.predicate.translate()[0] for c in a.clauses if c.predicate)

    def test_cases_and_tense(self):
        self.assertEqual(self.ja('소년이 학교에서 책을 읽었다.'), '少年が / 学校[で,から] / 本を / 読んだ')
        self.assertEqual(self.ja('나는 어제 친구에게 편지를 보냈습니다.'), '私は / 昨日 / 友達に / 手紙を / 送った')

    def test_copula_and_adjective(self):
        self.assertEqual(self.ja('저는 학생입니다.'), '私は / 学生である')
        self.assertEqual(self.ja('이것은 책이 아니다.'), 'これは / 本ではない')
        self.assertEqual(self.ja('그 사람은 키가 크다.'), 'その人は / 背が / 高い')     # 二重主語
        self.assertEqual(self.ja('나는 선생님이 되었다.'), '私は / 先生に / なった')         # 補格の 되다

    def test_auxiliaries(self):
        self.assertEqual(self.ja('그는 한국어를 공부하고 있다.'), '彼は / 韓国語を / 勉強している')
        self.assertEqual(self.ja('저는 한국 음식을 먹고 싶어요.'), '私は / 韓国の食べ物を / 食べたい')
        self.assertEqual(self.ja('나는 한국어를 읽을 수 있다.'), '私は / 韓国語を / 読むことができる')
        self.assertEqual(self.ja('비가 오지 않았다.'), '雨が / 降らなかった')
        self.assertEqual(self.ja('나는 그 영화를 못 봤다.'), '私は / その映画を / 見ることができなかった')

    def test_attributive_and_coordination(self):
        self.assertEqual(self.ja('나는 어머니가 만든 음식을 먹었다.'), '私は / {母が 作った}食べ物を / 食べた')
        self.assertEqual(self.ja('예쁜 꽃이 피었다.'), '{美しい,かわいい}花が / 咲いた')
        self.assertEqual(self.ja('고양이와 개가 마당에서 논다.'), '猫と犬が / 庭[で,から] / 遊ぶ')

    def test_literal(self):
        from dragoman.korean.literal import literal
        lit = lambda t: literal(next(analyzer.sentences(t)))
        self.assertEqual(lit('소년이 학교에서 책을 읽었다.'), '少年が 学校で 本を 読んだ。')
        self.assertEqual(lit('비가 와서 집에 있었다.'), '雨が 降って 家に いた。')            # -어서「〜て」、있다「いる」
        self.assertEqual(lit('나는 어머니가 만든 음식을 먹었다.'), '私は 母が 作った 食べ物を 食べた。')
        self.assertEqual(lit('내 친구는 일본에서 왔습니다.'), '私の 友達は 日本から 来た。')     # 移動の動詞の 에서「から」
        self.assertEqual(lit('날씨가 좋으면 공원에 가자.'), '天気が 良いなら 公園に 行こう。')
        self.assertEqual(lit('그는 밥을 먹으면서 텔레비전을 봤다.'), '彼は ご飯を 食べながら テレビを 見た。')
        self.assertEqual(lit('이것은 책이 아니다.'), 'これは 本ではない。')

    def test_detect(self):
        from dragoman.main import detect
        self.assertEqual(detect('소년이 책을 읽었다.'), 'ko')


if __name__ == '__main__':
    unittest.main()
