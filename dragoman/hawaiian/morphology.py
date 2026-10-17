#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の機能語の表 (冠詞・指示詞・代名詞・所有の語・時制と相の小辞・前置詞・接続詞・方向の小辞) と、訳語を決めておく語
#
# 表の鍵は ʻokina・長音符付きの綴り (小文字)。本文に ʻokina・長音符があればその綴りで、無ければ鍵 (orthography.key) の
# 同じ語をすべて (kaʻu「私の」と kāu「君の」、ia「彼」・iā「〜を」・ʻia「〜される」・iʻa「魚」) 引く: candidates()
#
from . import orthography

# 冠詞: 鍵 → (見出し, 数, 定か)。ke は k・e・a・o と一部の ʻ の前、ka はほかの音の前 (ke kanaka・ka hale)
ARTICLES = {'ke': ('ke', 'sg', True), 'ka': ('ka', 'sg', True), 'nā': ('nā', 'pl', True), 'he': ('he', 'sg', False),
            'kekahi': ('kekahi', 'sg', False)}
# 指示詞 (名詞の前): 鍵 → (見出し, 訳)
DEMONSTRATIVES = {'kēia': ('kēia', 'この'), 'kēlā': ('kēlā', 'あの'), 'kēnā': ('kēnā', 'その')}
# 名詞の後ろの指示の小辞 (ka hale nei「この家」、kēlā kanaka lā「あの人」)
POST_DEMONSTRATIVES = {'nei': ('nei', 'この'), 'lā': ('lā', 'あの'), 'ala': ('ala', 'あの')}
# 人称代名詞: 鍵 → (見出し, 訳, 人称, 数)。両数 (kāua・māua …) と、1人称の複数・両数の包括 (聞き手を含む) と除外を区別する
PRONOUNS = {
    'au': ('au', '私', 1, 'sg'), 'wau': ('wau', '私', 1, 'sg'), 'ʻoe': ('ʻoe', '君', 2, 'sg'), 'ia': ('ia', '彼', 3, 'sg'),
    'kāua': ('kāua', '私たち二人 (君と私)', 1, 'du'), 'māua': ('māua', '私たち二人 (君を除く)', 1, 'du'),
    'kākou': ('kākou', '私たち (君たちを含む)', 1, 'pl'), 'mākou': ('mākou', '私たち (君たちを除く)', 1, 'pl'),
    'ʻolua': ('ʻolua', '君たち二人', 2, 'du'), 'ʻoukou': ('ʻoukou', '君たち', 2, 'pl'),
    'lāua': ('lāua', '彼ら二人', 3, 'du'), 'lākou': ('lākou', '彼ら', 3, 'pl'),
    'iaʻu': ('iaʻu', '私', 1, 'sg'),   # i + au (目的語「私を」)
}
# 所有の語 (名詞の前): 鍵 → (見出し, 訳, 類)。a 類 (自分で得たもの・作ったもの・子・配偶者: kaʻu keiki「私の子」) と
# o 類 (生まれつきのもの・親・体・家・乗り物: koʻu makuahine「私の母」)。kuʻu は愛情をこめた「私の」
POSSESSIVES = {
    'kaʻu': ('kaʻu', '私の', 'a'), 'koʻu': ('koʻu', '私の', 'o'), 'kāu': ('kāu', '君の', 'a'), 'kou': ('kou', '君の', 'o'),
    'kāna': ('kāna', '彼の', 'a'), 'kona': ('kona', '彼の', 'o'), 'kuʻu': ('kuʻu', '私の', 'o'),
    'kā': ('kā', 'の', 'a'), 'ko': ('ko', 'の', 'o'),   # kā mākou「私たちの」・ko lākou「彼らの」(代名詞が後ろに続く)
}
# 時制・相の小辞 (動詞の前): 鍵 → (見出し, 時制, 後ろの小辞)
TAM = {'ua': ('ua', 'perfect', None), 'e': ('e', 'future', 'ana'), 'ke': ('ke', 'progressive', 'nei')}
# 否定: ʻaʻole (+ i で過去)、mai (禁止「〜するな」)、ʻaʻohe (「〜が無い」)
NEGATIONS = {'ʻaʻole': ('ʻaʻole', '〜ない'), 'ʻaʻohe': ('ʻaʻohe', '〜がない')}
# 前置詞: 鍵 → [(見出し, 支配する格, 訳)]。i は目的語 (対格) か場所・方向「〜に・〜へ」、iā は名前・代名詞の前の i
PREPOSITIONS = {
    'i': [('i', 'Acc', ''), ('i', 'Dat', '〜に,〜へ')], 'iā': [('iā', 'Acc', '')],
    'ma': [('ma', 'Dat', '〜で,〜に')], 'mai': [('mai', 'Dat', '〜から')], 'me': [('me', 'Dat', '〜と,〜と一緒に')],
    'no': [('no', 'Dat', '〜のために,〜について,〜から')], 'na': [('na', 'Dat', '〜のために,〜によって')],
    'e': [('e', 'Dat', '〜によって')], 'ā': [('ā', 'Dat', '〜まで')],
}
# 所有の前置詞 (名詞の後ろ: ka hale o ke aliʻi「首長の家」)
GENITIVES = {'o': ('o', 'o'), 'a': ('a', 'a')}
# 場所の名詞 (ma luna o「〜の上に」、i loko o「〜の中に」): 鍵 → 訳
LOCATIVES = {'luna': '〜の上に', 'lalo': '〜の下に', 'loko': '〜の中に', 'waho': '〜の外に', 'mua': '〜の前に',
             'hope': '〜の後に', 'kai': '〜の海の方に', 'uka': '〜の山の方に', 'kahi': '〜のところに'}
# 動詞の後ろの方向の小辞 (訳に出さない): mai「こちらへ」、aku「あちらへ」、iho「下へ・自分で」、aʻe「上へ・次の」
DIRECTIONALS = {'mai': 'mai', 'aku': 'aku', 'iho': 'iho', 'aʻe': 'aʻe'}
PASSIVE = 'ʻia'    # 動詞の後ろ: ʻai ʻia「食べられる」
CONJUNCTIONS = {
    'a': ('a', 'そして'), 'akā': ('akā', 'しかし'), 'inā': ('inā', '〜なら'), 'ʻoiai': ('ʻoiai', '〜する間'),
}
# 文頭の小辞: ʻo (主語・主題の名詞句の印)、aia (所在「〜にある・いる」)、he (「〜である」の述語の名詞の冠詞)
TOPIC = 'ʻo'
EXISTENTIAL = 'aia'
# 2語以上の機能語 (先に1語にまとめる): 綴り → 1語の綴り
MULTIWORD = {('no', 'ka', 'mea'): 'no ka mea', ('a', 'i', 'ʻole'): 'a i ʻole', ('a', 'me'): 'a me',
             ('i', 'mea', 'e'): 'i mea e'}
CONJUNCTIONS.update({'no ka mea': ('no ka mea', '〜なので'), 'a i ʻole': ('a i ʻole', 'または'), 'a me': ('a me', 'と'),
                     'i mea e': ('i mea e', '〜するために')})
ADVERBS = {'paha': 'たぶん', 'nō': 'まさに', 'loa': 'とても', 'wale': 'ただ', 'pū': '一緒に', 'mau': 'いつも',
           'hou': '再び', 'koke': 'すぐに', 'nehinei': '昨日', 'ʻapōpō': '明日', 'ʻānō': '今', 'eia': 'ここに',
           'pēlā': 'そのように', 'pēnei': 'このように', 'ʻaneʻi': 'ここで', 'laila': 'そこで'}


def candidates(table, token):
    """機能語の表の候補 [(綴り, 値)]: 本文に ʻokina・長音符があれば綴りの合うもの、無ければ鍵の同じものすべて"""
    spelled = orthography.normalize(token).lower()
    if spelled in table:
        return [(spelled, table[spelled])]
    if orthography.marked(token):
        return []
    k = orthography.key(token)
    return [(w, v) for w, v in table.items() if orthography.key(w) == k]
# 訳語を決めておく語 (見出しの鍵 → 訳)
GLOSSES = {
    'hele': '行く', 'ʻai': '食べる', 'inu': '飲む', 'ʻike': '見る,知る', 'aloha': '愛する', 'hana': 'する,働く',
    'noho': '住む,座る', 'heluhelu': '読む', 'kākau': '書く', 'ʻōlelo': '言う,話す', 'hīmeni': '歌う', 'mele': '歌う',
    'hula': '踊る', 'ʻauʻau': '泳ぐ', 'honi': 'キスする', 'hoʻi': '帰る', 'holo': '走る', 'lele': '飛ぶ', 'moe': '眠る',
    'ala': '起きる', 'kū': '立つ', 'nānā': '見る', 'lohe': '聞く', 'aʻo': '教える,学ぶ', 'hoʻomaka': '始める',
    'pau': '終わる', 'make': '死ぬ', 'ola': '生きる', 'loaʻa': '得る', 'kūʻai': '売る,買う', 'hāʻawi': '与える',
    'lawe': '持って行く', 'hānau': '生まれる', 'manaʻo': '思う', 'makemake': '欲しい,望む', 'kāhea': '呼ぶ',
    'nīnau': '尋ねる', 'pane': '答える', 'kōkua': '手伝う', 'mahalo': '感謝する', 'hoʻomaikaʻi': '祝福する',
    'kula': '学校', 'kumu': '先生', 'haumāna': '生徒', 'kāne': '男,夫', 'wahine': '女,妻', 'keiki': '子供',
    'kanaka': '人', 'hale': '家', 'wai': '水', 'ʻāina': '土地', 'moana': '海', 'kai': '海', 'lani': '天',
    'aliʻi': '首長', 'ʻohana': '家族', 'makua': '親', 'makuahine': '母', 'makuakāne': '父', 'inoa': '名前',
    'iʻa': '魚', 'poi': 'ポイ', 'lā': '日', 'pō': '夜', 'manu': '鳥', 'ʻīlio': '犬', 'pōpoki': '猫', 'waʻa': 'カヌー',
    'kaʻa': '車', 'puke': '本', 'nalu': '波', 'mauna': '山', 'pua': '花', 'lau': '葉', 'lima': '手', 'maka': '目',
    'poʻo': '頭', 'naʻau': '心', 'akua': '神', 'mea': 'もの', 'ʻōlelo#noun': '言葉', 'mele#noun': '歌',
    'hula#noun': 'フラ', 'ʻai#noun': '食べ物', 'papa': 'テーブル,板', 'kauhale': '村', 'kūlanakauhale': '町',
    'nui': '大きい', 'liʻiliʻi': '小さい', 'nani': '美しい', 'maikaʻi': '良い', 'hauʻoli': 'うれしい', 'kaumaha': '悲しい',
    'wela': '暑い', 'anuanu': '寒い', 'hou#adj': '新しい', 'kahiko': '古い', 'lōʻihi': '長い', 'pōkole': '短い',
    'ikaika': '強い', 'akamai': '賢い', 'ʻono': 'おいしい', 'uliuli': '青い', 'ʻulaʻula': '赤い', 'keʻokeʻo': '白い',
    'ʻeleʻele': '黒い', 'ʻōmaʻomaʻo': '緑の', 'melemele': '黄色い', 'wikiwiki': '速い',
}
def gloss(word, pos):
    """手で決めた訳語 (品詞ごとの鍵 'ʻōlelo#noun' を先に)。辞書の見出しの綴りで引く"""
    w = orthography.normalize(word).lower()
    return GLOSSES.get('%s#%s' % (w, pos)) or GLOSSES.get(w)
