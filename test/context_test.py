#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文脈の訳語 (core/analyzer.verbs_in_context): 動詞の訳語を目的語で選ぶ (take + medicine →「飲む」、tell + lie →「つく」)。
# 言語をまたいで。辞書の無い言語は飛ばす
#
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adverbial_test import available, translate   # noqa: E402

CASES = [
    ('russian', 'Она плетёт нить.', '糸を / 繰る'),           # Wiktionary の語義 spin + thread
    ('russian', 'Он принимает лекарство.', '薬を / 飲む'),    # 主格・対格の同じ形の目的語 (Nom/Acc の枠)
    ('russian', 'Он говорит ложь.', '嘘を / つく'),           # 手で決めた訳語「言う」+ 嘘
    ('greek', 'φάρμακον λαμβάνει.', '薬を / 飲む'),            # 中性名詞 (主格・対格の同じ形) + 他動詞は目的語
    ('latin', 'Medicāmentum sūmit.', '薬品}を / 飲む'),
    ('german', 'Er nimmt Medizin.', '薬を / 飲む'),           # 手で決めた訳語「取る」+ 薬
    ('german', 'Er erzählt eine Lüge.', '嘘を / つく'),
    ('french', 'Il dit un mensonge.', '嘘を / つく'),
    ('finnish', 'Hän ottaa lääkettä.', '薬を / 飲む'),
    ('english', 'He takes medicine.', '薬を / 飲む'),
    ('korean', '그는 약을 먹었다.', '薬を / 飲んだ'),            # 약 は 藥 (花札の「役」でなく)、食べる + 薬
    ('mongolian', 'Тэр эм уусан.', '彼は / {薬,薬剤}を / 飲んだ'),   # эм「薬」(「雌」でなく)、тэр は主語の代名詞
    ('portuguese', 'Ele toma remédio.', '薬を / 飲む'),         # spaCy が形容詞と読む名詞
]


class ContextTestCase(unittest.TestCase):
    def test_verbs_in_context(self):
        for module, text, expected in CASES:
            with self.subTest(module=module, text=text):
                if module != 'latin' and not available(module):
                    continue   # データの無い言語だけ飛ばす (skipTest だと残りの例も飛ぶ)
                self.assertIn(expected, translate(module, text))

    def test_suru_not_doubled(self):
        from dragoman.core import en_ja
        self.assertNotIn('服するする', en_ja.verb_in_context('take', ['medicine']) + en_ja.lookup('impose', 'verb'))
        self.assertNotIn('課するする', en_ja.lookup('impose', 'verb'))

    def test_hand_glossed_verbs_kept(self):
        # 手で決めた動詞の訳語は、表 (HAND_VERB_CONTEXTS) に無い組み合わせでは選び直さない
        if available('korean'):
            self.assertIn('送った', translate('korean', '나는 어제 친구에게 편지를 보냈습니다.'))
            self.assertIn('ご飯を / 食べた', translate('korean', '그는 밥을 먹었다.'))
        if available('mongolian'):
            self.assertIn('その人は / 来た', translate('mongolian', 'Тэр хүн ирсэн.'))   # 自動詞の前の тэр は指示詞


# 天気の動詞 (主語を補わない・形式主語を訳さない)、行き先の対格、場所のある「住む」(言語をまたいで)
SENTENCES = [
    ('latin', 'Hodiē pluit.', '今日 / 雨が降る'),
    ('french', 'Hier, il a plu.', '昨日 / 雨が降った'),
    ('finnish', 'Eilen satoi.', '昨日 / 雨が降った'),
    ('finnish', 'Lunta sataa.', '雪が / 降る'),                  # 名詞の主語があれば「降る」だけ
    ('english', 'It rained yesterday.', '昨日 / 雨が降った'),
    ('russian', 'Он пошёл домой.', '彼が / 家へ / 行った'),       # идти の語義「雨が降る」で主語を消さない
    ('latin', 'Amīcus meus Rōmam vēnit.', '私の友人が / ローマに / 来た'),   # 行き先の対格
    ('latin', 'Viam longam īmus.', '道を / 行く'),               # 通る所は「を」のまま
    ('sanskrit', 'रामः वनं गच्छति।', 'へ / 行く'),
    ('greek', 'ὁ διδάσκαλος τοῖς μαθηταῖς λέγει.', '学習者に / 言う'),   # λέγω「言う」(「集める」でなく)
    ('finnish', 'Asumme Helsingissä.', 'ヘルシンキに / 住む'),     # 場所のある「生きる」は「住む」
    ('german', 'Wir wohnen in Berlin.', 'ベルリンに / 住む'),
    ('french', 'Nous habitons à Paris.', 'パリに / 住む'),
    # 二重目的語 (受け手「〜に」+ 物「〜を」)
    ('english', 'I gave my brother the book.', '私の{兄,弟}に / 本を / 与えた'),   # spaCy が同格と読む2つ目の目的語
    ('chinese', '我给了弟弟一本书。', '弟に / 一冊の本を / 与えた'),
    ('arabic', 'أعطيت أخي الكتاب.', '私が / 私の兄弟に / 本を / 与えた'),   # ハムザ付きの文字は母音記号でない
    ('hindi', 'मैंने भाई को किताब दी।', '私が / 兄弟に / 本を / 与えた'),      # ने の付いた代名詞の1語 मैंने
    ('hindi', 'मैंने उसे देखा।', '私が / {彼,彼女,それ}を / 見た'),            # को の付いた代名詞の1語 उसे
    ('indonesian', 'Saya memberi adik saya buku.', '私の{弟,妹}に / 本を / 与える'),
    ('indonesian', 'Ibu memberi anak itu makanan.', 'その子供に / 食べ物を / 与える'),
    ('korean', '나는 동생에게 책을 주었다.', '{弟,妹}に / 本を'),
    ('tagalog', 'Nagbabasa ng libro ang bata.', '子供は / 本を / 読んでいる'),   # nag- は行為者焦点
    ('vietnamese', 'Cậu bé đọc sách.', '少年が / 本を / 読む'),
    ('vietnamese', 'Thành phố lớn.', '都市は / 大きい'),           # 動詞の無い文の形容詞は述語
    ('sanskrit', 'बालः पुस्तकं पठति।', '{子供,少年}が / 本を / 読む'),
    ('sanskrit', 'सा नारी गायति।', 'その女が / 歌う'),            # 名詞の前の tad は「その」
    ('sanskrit', 'सा जलं पिबति।', '{彼女,それ}が / 水を / 飲む'),
    ('hebrew', 'הַיֶּלֶד קוֹרֵא סֵפֶר.', 'こどもが / {本,書き物,書物}を / 呼んでいる'),   # 主語 + 能動の分詞は現在の動作
    ('finnish', 'Annoin veljelleni kirjan.', '私が / 私の兄弟に / 本を / 与えた'),   # 所有の接尾辞の付いた名詞
    ('portuguese', 'Ontem choveu.', '昨日 / 雨が降った'),
    ('arabic', 'أمطرت أمس.', '昨日 / 雨が降った'),                  # 天気の動詞は1人称を先にしない           # yesterday「昨日」(「昨日に」でなく)
]


class SentenceTestCase(unittest.TestCase):
    def test_sentences(self):
        for module, text, expected in SENTENCES:
            with self.subTest(module=module, text=text):
                if module != 'latin' and not available(module):
                    continue   # データの無い言語だけ飛ばす (skipTest だと残りの例も飛ぶ)
                self.assertIn(expected, translate(module, text))


if __name__ == '__main__':
    unittest.main()
