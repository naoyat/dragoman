#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 発音 (IPA の音素の列) → カタカナの共通の規則 (core/kana.py)
#
import unittest

from dragoman.core.kana import kana


class KanaTestCase(unittest.TestCase):
    def test_vowels_and_length(self):
        self.assertEqual(kana(['k', 'a', 'e', 's', 'a', 'r']), 'カエサル')
        self.assertEqual(kana(['m', 'aː', 'r', 'k', 'ʊ', 's']), 'マールクス')               # ː は「ー」
        self.assertEqual(kana(['s', 'e', 'l', 'iˑ', 'n']), 'セリン')                       # ˑ は既定では書かない
        self.assertEqual(kana(['s', 'e', 'l', 'iˑ', 'n'], long='phonetic'), 'セリーン')    # 実際の長さも「ー」に

    def test_consonants(self):
        self.assertEqual(kana(['v', 'a', 'n', 's', 'a', 'n']), 'ヴァンサン')              # v はヴ行
        self.assertEqual(kana(['θ', 'ɪ', 'ŋ', 'k']), 'シンク')                             # θ はサ行、ŋ は「ン」
        self.assertEqual(kana(['ʃ', 'a', 'r', 'l']), 'シャルル')
        self.assertEqual(kana(['tʃ', 'a', 'o']), 'チャオ')
        self.assertEqual(kana(['ts', 'a', 'r']), 'ツァル')
        self.assertEqual(kana(['b', 'a', 'x']), 'バフ')                                    # 音節末の x は「フ」
        self.assertEqual(kana(['ʁ', 'o', 'z']), 'ロズ')                                    # ʁ・l・r はラ行

    def test_yoon_and_labialized(self):
        self.assertEqual(kana(['k', 'j', 'o', 't', 'o']), 'キョト')                       # 子音 + j + 母音は拗音
        self.assertEqual(kana(['k', 'w', 'iː', 'n', 't', 'ʊ', 's']), 'クィーントゥス')

    def test_geminates(self):
        self.assertEqual(kana(['j', 'ʊ', 'pː', 'ɪ', 't', 'ɛ', 'r']), 'ユッピテル')         # 閉鎖音は「ッ」
        self.assertEqual(kana(['h', 'a', 'nː', 'ɪ', 'b', 'a', 'l']), 'ハンニバル')        # n は「ン」
        self.assertEqual(kana(['g', 'a', 'lː', 'ɪ', 'a']), 'ガリア')                      # l・r は1つ
        self.assertEqual(kana(['n', 'ɔ', 't', 't', 'e']), 'ノッテ')                        # 同じ子音を2つ並べても
        self.assertEqual(kana(['p', 'e', 'r', 'l', 'a', 'e']), 'ペルラエ')                 # r と l は別の子音

    def test_word_break(self):
        self.assertEqual(kana(['p', 'aː', 'k', 's', ' ', 'j', 'uː', 'l', 'ɪ', 'a']), 'パークスユーリア')   # 語をまたがない


class LanguageKatakanaTestCase(unittest.TestCase):
    """言語ごとの発音 → 共通の規則"""

    def test_wa_option(self):
        self.assertEqual(kana(['m', 'i', 'n', 'ɛ', 'r', 'w', 'a']), 'ミネルワ')                 # 既定は「ワ」
        self.assertEqual(kana(['m', 'i', 'n', 'ɛ', 'r', 'w', 'a'], wa='ウァ'), 'ミネルウァ')    # 西洋古典学の慣習

    def test_greek(self):
        from dragoman.greek.katakana import katakana
        self.assertEqual([katakana(w) for w in ('Σωκράτης', 'Ἀθῆναι', 'Ὀδυσσεύς', 'φιλοσοφία')],
                         ['ソークラテース', 'アテーナイ', 'オデュッセウス', 'ピロソピアー'])   # 長さは辞書から

    def test_sanskrit(self):
        from dragoman.sanskrit.katakana import katakana
        self.assertEqual([katakana(w) for w in ('rāma', 'kṛṣṇa', 'śiva', 'buddha', 'gaṅgā')],
                         ['ラーマ', 'クリシュナ', 'シヴァ', 'ブッダ', 'ガンガー'])

    def test_old_english(self):
        from dragoman.oldenglish.phonology import katakana
        self.assertEqual([katakana(w) for w in ('Æþelstān', 'Bēowulf', 'Ēadweard')],
                         ['エゼルスターン', 'ベーオウルフ', 'エーアドウェアルド'])   # æ はエ段

    def test_ipa_string_and_nasal(self):
        self.assertEqual(kana('ʒˈɑ̃'), 'ジャン')                       # IPA の文字列も。鼻母音は「ン」
        self.assertEqual(kana('ʒyljˈɛt', final_sokuon=True), 'ジュリエット')   # 語末の閉鎖音の前の「ッ」、j + e は「エ」

    def test_french(self):
        from dragoman.french import katakana as fr
        if not fr.available():
            self.skipTest('espeak-ng が無い')
        self.assertEqual([fr.katakana(w) for w in ('Emmanuel', 'Vincent', 'François', 'Juliette', 'Pierre', 'Céline',
                                                   'Anne', 'Rousseau', 'Jean', 'Hugues')],
                         ['エマニュエル', 'ヴァンサン', 'フランソワ', 'ジュリエット', 'ピエール', 'セリーヌ', 'アンヌ',
                          'ルソー', 'ジャン', 'ユグ'])

    def test_hawaiian(self):
        from dragoman.hawaiian.phonology import katakana
        self.assertEqual([katakana(w) for w in ('Hawaiʻi', 'Kalākaua', 'Kamehameha')],
                         ['ハワイイ', 'カラーカウア', 'カメハメハ'])


class SentenceKanaTestCase(unittest.TestCase):
    """文のカタカナ読み (--kana): 言語のコマンドの katakana (解析で選んだ読みの綴りから)"""

    def test_latin(self):
        from dragoman.latin import latindic, analyzer, main
        latindic.load()

        class Options:
            kana_options = {}
        a = next(analyzer.analyze_text('Gallia est omnis divisa in partes tres.'))
        self.assertEqual(main.latin_kana(a, Options()), 'ガリア エスト オムニス ディーウィーサ イン パルテース トレース')
        a = next(analyzer.analyze_text('Senatus populusque Romanus.'))
        self.assertEqual(main.latin_kana(a, Options()), 'セナートゥス ポプルスクェ ローマーヌス')   # 後接語 -que

    def test_hawaiian_and_old_english(self):
        from dragoman.hawaiian import analyzer as haw, command as haw_command
        from dragoman.oldenglish import analyzer as ang, command as ang_command, dictionary as ang_dictionary
        from dragoman.hawaiian import dictionary as haw_dictionary
        if haw_dictionary.available():
            a = next(haw.analyze_text('Aloha au ia oe.'))
            self.assertEqual(' '.join(haw_command.katakana(a, {})), 'アロハ アウ イアー オエ')   # 印の無い ia は iā
        if ang_dictionary.available():
            a = next(ang.analyze_text('He forlet þa burh.'))
            self.assertEqual(' '.join(ang_command.katakana(a, {})), 'ヘー フォルレート サー ブルフ')

    def test_french_sentence(self):
        from dragoman.french import katakana as fr
        if not fr.available():
            self.skipTest('espeak-ng が無い')
        cases = {
            'Il y a un chat dans le jardin.': 'イリヤ アン シャ ダン ル ジャルダン',   # il y a は1語、ə はウ段
            "Je sais que tu m'aimes.": 'ジュ セ ク テュ メム',                       # 文の中の読み (m'aimes)
            'Les enfants sont arrivés.': 'レ ザンファン ソン タリヴェ',               # リエゾンは次の語の頭に
            'Il y avait une femme.': 'イリヤヴェ テュヌ ファム',
            'Antoine et Étienne.': 'アントワーヌ エ エティエンヌ',                   # 綴りでも読む語末の子音は動かさない
            'Il est arrivé.': 'イレ タリヴェ',                                         # il・elle + 母音は1語
            'Elle aime Paris.': 'エレム パリ',
            'Ils ont un chien.': 'イル ゾン タン シャン',
        }
        for text, expected in cases.items():
            self.assertEqual(' '.join(fr.sentence(text)), expected, text)


if __name__ == '__main__':
    unittest.main()
