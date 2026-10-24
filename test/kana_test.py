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
        self.assertEqual(kana(['θ', 'ɪ', 'ŋ', 'k']), 'スィンク')                           # θ はサ行、ŋ は「ン」
        self.assertEqual([kana('si'), kana('ʃi'), kana('zi'), kana('ʒi')], ['スィ', 'シ', 'ズィ', 'ジ'])   # [si] と [ʃi] を分ける
        self.assertEqual([kana('si', si='シ'), kana('zi', si='シ')], ['シ', 'ジ'])                       # 慣用の「シ」「ジ」
        self.assertEqual([kana('kœln'), kana('kœln', oe='オ'), kana('nøː', oe='オ')], ['ケルン', 'コルン', 'ノー'])   # [ø]・[œ] の段
        self.assertEqual([kana('sja'), kana('vjo'), kana('fju'), kana('ʃa')], ['スャ', 'ヴョ', 'フュ', 'シャ'])
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

    def test_german(self):
        from dragoman.german import katakana as de
        if not de.available():
            self.skipTest('espeak-ng が無い')
        self.assertEqual([de.katakana(w) for w in ('Heinrich', 'Müller', 'Mozart', 'Bach', 'Zürich', 'Freud', 'Hamburg',
                                                   'Nietzsche', 'Deutschland', 'Wolfgang', 'Mutter', 'Buch')],
                         ['ハインリヒ', 'ミュラー', 'モーツァルト', 'バッハ', 'ツューリヒ', 'フロイト', 'ハンブルク',
                          'ニーチェ', 'ドイチュラント', 'ヴォルフガング', 'ムッター', 'ブーフ'])
        self.assertEqual([de.katakana(w) for w in ('Anna', 'Lisa', 'Sie')], ['アンナ', 'リーザ', 'ズィー'])

    def test_russian(self):
        from dragoman.russian.katakana import katakana
        self.assertEqual([katakana(w) for w in ('Москва́', 'молоко́', 'Пу́тин', 'Татья́на', 'ма́ть', 'во́дка', 'вокза́л',
                                                 'сего́дня', 'нахо́дится', 'Дми́трий', 'Че́хов', 'А́нна')],
                         ['マスクヴァー', 'マラコー', 'プーチン', 'タチヤーナ', 'マチ', 'ヴォトカ', 'ヴァグザル',
                          'シヴォードニャ', 'ナホージッツァ', 'ドミートリー', 'チェーハフ', 'アンナ'])
        self.assertEqual(katakana('Москва́', long='phonemic'), 'マスクヴァ')
        self.assertEqual([katakana(w) for w in ('сча́стья', 'кры́лья', 'мно́го', 'того́', 'всё', 'маши́ны')],
                         ['シャスチヤ', 'クルィリヤ', 'ムノーガ', 'タヴォー', 'フスョー', 'マシーヌィ'])   # сч → щ、ы → ウ段 + ィ
        self.assertEqual([katakana(w) for w in ('си́ла', 'сы́р', 'Росси́я', 'звёздной')],
                         ['シーラ', 'スィル', 'ラッシーヤ', 'ズヴョーズナイ'])   # си は「シ」、сы は「スィ」、軟らかい с・з・в + ё は「スョ」「ヴョ」

    def test_russian_ambiguous_stress(self):
        from dragoman.russian import morphology
        from dragoman.russian.katakana import katakana
        if morphology.stressed('моя') == 'моя':
            self.skipTest('ロシア語の辞書が無い')
        # 同じ綴りで強勢の違う形 (мо́я「洗いながら」/ моя́「私の」) は一番ありそうな見出し語 (мой) の形を
        self.assertEqual([katakana(morphology.stressed(w)) for w in ('моя', 'мою')], ['マヤー', 'マユー'])

    def test_russian_yo(self):
        from dragoman.russian import morphology
        if morphology.stressed('всё') == 'всё' and morphology.stressed('все') == 'все':
            self.skipTest('ロシア語の辞書が無い')
        self.assertEqual((morphology.stressed('всё'), morphology.stressed('все')), ('всё', 'все́'))   # ё を元の表記に

    def test_finnish(self):
        from dragoman.finnish.katakana import katakana
        self.assertEqual([katakana(w) for w in ('Matti', 'Liisa', 'Anna', 'Jyväskylä', 'Ville', 'Lahti', 'Helsinki',
                                                 'Helsingissä', 'Emma')],
                         ['マッティ', 'リーサ', 'アンナ', 'ユヴァスキュラ', 'ヴィッレ', 'ラハティ', 'ヘルスィンキ',
                          'ヘルスィンギッサ', 'エンマ'])   # l の重子音も「ッ」、母音の続かない h は前の母音の段

    def test_turkish(self):
        from dragoman.turkish.katakana import katakana
        self.assertEqual([katakana(w) for w in ('Ali', 'Ayşe', 'Çağlar', 'İstanbul', 'Türkiye', 'Kılıç', 'değil',
                                                 'Allah', 'Kâzım', 'teşekkür')],
                         ['アリ', 'アイシェ', 'チャーラル', 'イスタンブル', 'テュルキイェ', 'クルチ', 'デイル',
                          'アッラフ', 'キャーズム', 'テシェッキュル'])

    def test_mongolian(self):
        from dragoman.mongolian.katakana import katakana
        self.assertEqual([katakana(w) for w in ('Бат', 'Дорж', 'Улаанбаатар', 'Дулмаа', 'Сүхбаатар', 'Ёндон', 'Батсүхийн')],
                         ['バト', 'ドルジ', 'ウラーンバータル', 'ドゥルマー', 'スフバータル', 'ヨンドン', 'バトスヒーン'])

    def test_korean(self):
        from dragoman.korean.katakana import katakana
        self.assertEqual([katakana(w) for w in ('민수', '김철수', '서울', '경희', '최', '민기', '대구')],
                         ['ミンス', 'キムチョルス', 'ソウル', 'キョンヒ', 'チェ', 'ミンギ', 'テグ'])
        self.assertEqual([katakana(w) for w in ('한국어', '감사합니다', '좋아요', '학교', '같이', '신라', '독립', '아빠',
                                                 '맛있어요', '괜찮아요', '김밥')],
                         ['ハングゴ', 'カムサハムニダ', 'チョアヨ', 'ハッキョ', 'カチ', 'シルラ', 'トンニプ', 'アッパ',
                          'マシッソヨ', 'クェンチャナヨ', 'キムバプ'])   # 連音・鼻音化・流音化・口蓋音化・濃音

    def test_english(self):
        from dragoman.english import katakana as en
        if not en.available():
            self.skipTest('CMUdict も espeak-ng も無い')
        words = ('about', 'water', 'car', 'think', 'music', 'nation', 'table', 'happy', 'cat', 'here', 'more',
                 'horse', 'bird', 'sing', 'beautiful', 'little', 'the')
        self.assertEqual([en.katakana(w) for w in words],
                         ['アバウト', 'ウォーター', 'カー', 'スィンク', 'ミューズィック', 'ネイション', 'テイブル', 'ハッピー',
                          'キャット', 'ヒア', 'モア', 'ホース', 'バード', 'スィング', 'ビューティフル', 'リットル', 'ザ'])
        if en.shutil.which('espeak-ng'):
            self.assertEqual([en.katakana(w, accent='gb') for w in ('hot', 'water', 'doctor', 'more', 'fire')],
                             ['ホット', 'ウォーター', 'ドクター', 'モー', 'ファイア'])   # 英音

    def test_english_homographs(self):
        from dragoman.english import katakana as en
        if not en.available():
            self.skipTest('CMUdict も espeak-ng も無い')
        try:
            from dragoman.english import morphology
            morphology.nlp()
        except (ImportError, OSError):
            self.skipTest('spaCy の英語モデルが無い')
        # 品詞で発音の変わる語は文の品詞から (必要なときだけ spaCy)
        self.assertEqual(en.sentence('Where do you live?')[-1], 'リヴ')
        self.assertEqual(en.sentence('Live music is fun.')[0], 'ライヴ')
        self.assertEqual(en.sentence('I read books every day.'), ['アイ', 'リード', 'ブックス', 'エヴァリー', 'デイ'])
        self.assertEqual(en.sentence('I have read this book.')[2], 'レッド')
        self.assertEqual(en.sentence('The cats sing a song.'), ['ザ', 'キャッツ', 'スィング', 'ア', 'ソング'])

    def test_english_colloquial(self):
        from dragoman.english import katakana as en
        if not en.available():
            self.skipTest('CMUdict も espeak-ng も無い')
        # 口語の綴り (CMUdict に無いか誤っているもの) と、g を落とした -in' (-ing の発音の ŋ を n に)
        self.assertEqual([en.katakana(w) for w in ('tryna', 'outta', 'imma', "lovin'", "rollin'")],
                         ['トライナ', 'アウタ', 'アイマ', 'ラヴィン', 'ロウリン'])
        # -n't の n は音節になる (前の弱い母音を書かない)
        self.assertEqual([en.katakana(w) for w in ("weren't", "wasn't", "aren't", "didn't")],
                         ['ワーント', 'ワズント', 'アーント', 'ディドント'])

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

    def test_russian_sentence(self):
        from dragoman.russian.katakana import sentence
        self.assertEqual(sentence(['Ива́н', 'и', 'Ната́ша', 'живу́т', 'в', 'Москве́', '.']),
                         ['イヴァン', 'イ', 'ナターシャ', 'ジヴト', 'ヴマスクヴェー'])   # в は次の語に続ける
        self.assertEqual(sentence(['Он', 'не', 'зна́ет', '.']), ['オン', 'ニ', 'ズナーイト'])

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



class SpellingKanaTestCase(unittest.TestCase):
    """綴り・転写から読む言語 (2026-10-23 に足したもの)"""
    def test_indonesian(self):
        from dragoman.indonesian.katakana import katakana
        cases = {'saya': 'サヤ', 'bapak': 'バパッ', 'rumah': 'ルマ', 'nyanyi': 'ニャニ', 'bunga': 'ブンガ', 'syukur': 'シュクル',
                 'pulau': 'プラウ', 'anak-anak': 'アナッアナッ', 'cinta': 'チンタ', 'khabar': 'ハバル'}
        for word, expected in cases.items():
            self.assertEqual(katakana(word), expected, word)

    def test_tagalog(self):
        from dragoman.tagalog.katakana import katakana
        cases = {'salamat': 'サラマト', 'ngayon': 'ンガヨン', 'mga': 'マンガ', 'ng': 'ナン', 'araw-araw': 'アラウアラウ',
                 'tsinelas': 'ツィネラス'}
        for word, expected in cases.items():
            self.assertEqual(katakana(word), expected, word)

    def test_hindi(self):
        from dragoman.hindi.katakana import word_katakana
        cases = {'आदमी': 'アードミー', 'किताब': 'キターブ', 'नमस्ते': 'ナマステー', 'है': 'ヘー', 'और': 'オール', 'मैं': 'メーン',
                 'कहाँ': 'カハーン', 'धन्यवाद': 'ダンヤワード', 'में': 'メーン'}
        for word, expected in cases.items():
            self.assertEqual(word_katakana(word), expected, word)

    def test_arabic(self):
        from dragoman.arabic.katakana import katakana
        cases = {'kitābun': 'キターブン', 'al-waladu': 'アルワラドゥ', 'ad-darsa': 'アッダルサ', 'ḏahaba': 'ザハバ',
                 'ʿarabiyyun': 'アラビーユン', 'muḥammad': 'ムハンマド', 'bayt': 'バイト'}
        for word, expected in cases.items():
            self.assertEqual(katakana(word), expected, word)

    def test_persian(self):
        from dragoman.persian.katakana import katakana
        cases = {'ketâb': 'ケターブ', 'xarid': 'ハリード', 'šahr': 'シャフル', 'dust-e': 'ドゥーステ', 'xeyli': 'ヘイリー',
                 'dowlat': 'ドウラト'}
        for word, expected in cases.items():
            self.assertEqual(katakana(word), expected, word)

    def test_hebrew(self):   # 聖書の時代の再建音: 既定は摩擦音化の前の古い時代、tiberian で母音記号どおり
        from dragoman.hebrew.katakana import word_katakana
        cases = {'בְּרֵאשִׁית': ('ベレーシート', 'ベレーシース'), 'אֱלֹהִים': ('エローヒーム', 'エローヒーム'),
                 'הַשָּׁמַיִם': ('ハッシャーマイム', 'ハッシャーマイム'), 'דָּבָר': ('ダーバール', 'ダーヴァール'),
                 'מֶלֶךְ': ('メレク', 'メレフ'), 'שָׁלוֹם': ('シャーローム', 'シャーローム'), 'רוּחַ': ('ルーアフ', 'ルーアフ')}
        for word, (early, tiberian) in cases.items():
            self.assertEqual(word_katakana(word), early, word)
            self.assertEqual(word_katakana(word, hebrew='tiberian'), tiberian, word)

    def test_tibetan(self):   # ラサ発音
        from dragoman.tibetan.katakana import word_katakana
        cases = {'ལྷ་ས': 'ラサ', 'བཀྲ་ཤིས': 'タシ', 'བཀྲ་ཤིས་བདེ་ལེགས': 'タシデレ', 'སངས་རྒྱས': 'サンギェ',
                 'ཐུགས་རྗེ་ཆེ': 'トゥジェチェ'}
        for word, expected in cases.items():
            self.assertEqual(word_katakana(word), expected, word)

    def test_ainu(self):
        try:
            import ainu_utils  # noqa: F401
        except ImportError:
            self.skipTest('ainu-utils が無い')
        from dragoman.ainu.katakana import katakana
        self.assertEqual(katakana('cep'), 'チェㇷ゚')
        self.assertEqual(katakana('cep', small='off'), 'チェッ')     # 閉鎖音は「ッ」
        self.assertEqual(katakana('pirka', small='off'), 'ピリカ')   # r は前の母音の段
        self.assertEqual(katakana('kor', small='off'), 'コロ')

    def test_kobun(self):
        from dragoman.kobun import mecab
        if not mecab.available():
            self.skipTest('中古和文 UniDic が無い')
        from dragoman.kobun.katakana import sentence
        self.assertEqual(sentence('いと思ふ人'), ['イト', 'オモウ', 'ヒト'])
        self.assertEqual(sentence('いと思ふ人', kobun='historical'), ['イト', 'オモフ', 'ヒト'])

    def test_ruby_punctuation(self):   # ダンダ・アラビア文字の句点は区切り (カナは空)
        from dragoman.core.ruby import ruby
        self.assertEqual([(r['text'], r['kana']) for r in ruby('वह आया।', 'hi')],
                         [('वह', 'ワフ'), ('आया', 'アーヤー'), ('।', '')])


if __name__ == '__main__':
    unittest.main()
