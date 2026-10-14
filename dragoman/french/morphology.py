#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語の語形: spaCy のフランス語モデル (fr_core_news_sm) で文脈の中の品詞 (UD)・原形・性・数・人称・時制を
# 付け、語の項目 (dict) にする。機能語 (冠詞・代名詞・前置詞・接続詞) の訳はここの表、内容語の訳は辞書 (Wiktionary の
# 英語の語義を core/en_ja.py で日本語に直したもの)。基本の語は GLOSSES で決めておく
#
# 名詞に格の形は無いので、格は文の中の役割 (主語・目的語・前置詞の目的語) から付ける (french/analyzer.py)。
# 代名詞は形で格が分かる (je 主格、me 対格・与格、le 対格、lui 与格、moi 前置詞の後ろ)
#
import functools
import re

from . import dictionary

NUMBERS = {'Sing': 'sg', 'Plur': 'pl'}
GENDERS = {'Masc': 'm', 'Fem': 'f'}
CASES = ('Nom', 'Acc', 'Dat')

# 人称代名詞: 形 → (訳, 人称, 数, 格の並び)。'Obl' は前置詞の後ろ・強勢形
PRONOUNS = {
    'je': ('私', 1, 'sg', ('Nom',)), "j'": ('私', 1, 'sg', ('Nom',)), 'tu': ('君', 2, 'sg', ('Nom',)),
    'il': ('彼', 3, 'sg', ('Nom',)), 'elle': ('彼女', 3, 'sg', ('Nom', 'Acc')), 'on': ('人々', 3, 'sg', ('Nom',)),
    'nous': ('私たち', 1, 'pl', ('Nom', 'Acc', 'Dat')), 'vous': ('あなた', 2, 'pl', ('Nom', 'Acc', 'Dat')),
    'ils': ('彼ら', 3, 'pl', ('Nom',)), 'elles': ('彼女ら', 3, 'pl', ('Nom', 'Acc')),
    'me': ('私', 1, 'sg', ('Acc', 'Dat')), "m'": ('私', 1, 'sg', ('Acc', 'Dat')), 'te': ('君', 2, 'sg', ('Acc', 'Dat')),
    "t'": ('君', 2, 'sg', ('Acc', 'Dat')), 'le': ('彼', 3, 'sg', ('Acc',)), 'la': ('彼女', 3, 'sg', ('Acc',)),
    "l'": ('彼', 3, 'sg', ('Acc',)), 'les': ('彼ら', 3, 'pl', ('Acc',)), 'lui': ('彼', 3, 'sg', ('Dat', 'Acc')),
    'leur': ('彼ら', 3, 'pl', ('Dat',)), 'se': ('自分', 3, 'sg', ('Acc', 'Dat')), "s'": ('自分', 3, 'sg', ('Acc', 'Dat')),
    'moi': ('私', 1, 'sg', ('Acc', 'Nom')), 'toi': ('君', 2, 'sg', ('Acc', 'Nom')), 'eux': ('彼ら', 3, 'pl', ('Acc', 'Nom')),
    'soi': ('自分', 3, 'sg', ('Acc',)), 'ce': ('それ', 3, 'sg', ('Nom',)), "c'": ('それ', 3, 'sg', ('Nom',)),
    'cela': ('それ', 3, 'sg', ('Nom', 'Acc')), 'ça': ('それ', 3, 'sg', ('Nom', 'Acc')), 'ceci': ('これ', 3, 'sg', ('Nom', 'Acc')),
    'qui': ('誰', 3, 'sg', ('Nom', 'Acc')), 'quoi': ('何', 3, 'sg', ('Acc',)), 'rien': ('何も〜ない', 3, 'sg', ('Acc', 'Nom')),
    'personne': ('誰も〜ない', 3, 'sg', ('Nom', 'Acc')), 'tout': ('すべて', 3, 'sg', ('Nom', 'Acc')),
    'quelqu\'un': ('誰か', 3, 'sg', ('Nom', 'Acc')), 'quelque chose': ('何か', 3, 'sg', ('Nom', 'Acc')),
    'y': ('そこ', 3, 'sg', ('Dat',)), 'en': ('それ', 3, 'sg', ('Acc',)),
}
# 動詞の前に置く接語の代名詞 (冠詞の le・la・les と同じ形)
CLITICS = {'me', "m'", 'te', "t'", 'se', "s'", 'le', 'la', "l'", 'les', 'lui', 'leur', 'nous', 'vous', 'y', 'en'}
RELATIVES = {'qui': ('Nom',), 'que': ('Acc',), "qu'": ('Acc',), 'dont': ('Gen',), 'où': ('Loc',), 'lequel': ('Acc',),
             'laquelle': ('Acc',), 'lesquels': ('Acc',), 'lesquelles': ('Acc',)}
# 冠詞類・所有形容詞・指示形容詞: 原形 → 訳 (冠詞は訳さない)
ARTICLES = {'le', 'la', "l'", 'les', 'un', 'une', 'des', 'du', 'de', "d'", 'au', 'aux'}
DETERMINERS = {'ce': 'この', 'cet': 'この', 'cette': 'この', 'ces': 'これらの', 'mon': '私の', 'ma': '私の', 'mes': '私の',
               'ton': '君の', 'ta': '君の', 'tes': '君の', 'son': '彼の', 'sa': '彼の', 'ses': '彼の', 'notre': '私たちの',
               'nos': '私たちの', 'votre': 'あなたの', 'vos': 'あなたの', 'leur': '彼らの', 'leurs': '彼らの',
               'quel': 'どの', 'quelle': 'どの', 'quels': 'どの', 'quelles': 'どの', 'tout': 'すべての', 'toute': 'すべての',
               'tous': 'すべての', 'toutes': 'すべての', 'chaque': 'それぞれの', 'plusieurs': 'いくつもの',
               'quelques': 'いくつかの', 'aucun': '', 'aucune': '', 'autre': '他の', 'autres': '他の', 'même': '同じ',
               'certains': 'ある', 'certaines': 'ある'}
# 所有形容詞 → (人称, 数) (文の枠で所有形容詞 meus … に)
POSSESSIVES = {'mon': (1, 'sg'), 'ma': (1, 'sg'), 'mes': (1, 'sg'), 'ton': (2, 'sg'), 'ta': (2, 'sg'), 'tes': (2, 'sg'),
               'son': (3, 'sg'), 'sa': (3, 'sg'), 'ses': (3, 'sg'), 'notre': (1, 'pl'), 'nos': (1, 'pl'),
               'votre': (2, 'pl'), 'vos': (2, 'pl'), 'leur': (3, 'pl'), 'leurs': (3, 'pl')}
# 前置詞: 原形 → 訳
PREPOSITIONS = {
    'à': '〜に,〜で', 'de': '〜の,〜から', 'en': '〜に,〜で', 'dans': '〜の中で,〜で', 'sur': '〜の上で,〜について',
    'sous': '〜の下で', 'avec': '〜と,〜で', 'sans': '〜なしで', 'pour': '〜のために', 'par': '〜によって,〜を通って',
    'chez': '〜の家で', 'vers': '〜の方へ', 'entre': '〜の間で', 'devant': '〜の前で', 'derrière': '〜の後ろで',
    'après': '〜の後で', 'avant': '〜の前に', 'depuis': '〜以来', 'pendant': '〜の間', 'contre': '〜に対して',
    'selon': '〜によれば', 'parmi': '〜の中で', 'jusque': '〜まで', "jusqu'": '〜まで', 'près': '〜の近くで',
    'comme': '〜として,〜のように', 'malgré': '〜にもかかわらず', 'sauf': '〜を除いて', 'durant': '〜の間',
    'hors': '〜の外で', 'auprès': '〜のそばで', 'loin': '〜から遠く',
}
# 前置詞と冠詞の縮約形 → 前置詞
CONTRACTIONS = {'au': 'à', 'aux': 'à', 'du': 'de', 'des': 'de'}
CONJUNCTIONS = {'et': 'そして,〜と', 'ou': 'または', 'mais': 'しかし', 'donc': 'だから', 'car': 'というのは',
                'ni': '〜も〜ない', 'or': 'ところで', 'que': '〜ということ', "qu'": '〜ということ', 'parce': '〜なので',
                'si': '〜なら', "s'": '〜なら', 'quand': '〜するとき', 'lorsque': '〜するとき', "lorsqu'": '〜するとき',
                'comme': '〜なので,〜のように', 'puisque': '〜なので', 'bien': '〜けれども', 'pendant': '〜する間',
                'tandis': '〜する一方', 'avant': '〜する前に', 'après': '〜した後で', 'pour': '〜するために',
                'afin': '〜するために', 'sans': '〜せずに', 'dès': '〜するとすぐ', 'jusqu\'à': '〜するまで',
                'quoique': '〜けれども'}
# ne … pas などの否定 (ne は落とし、後ろの語を否定に)
NEGATIONS = {'pas': '〜ない', 'jamais': '決して〜ない', 'plus': 'もう〜ない', 'rien': '何も〜ない', 'personne': '誰も〜ない',
             'point': '〜ない', 'guère': 'ほとんど〜ない', 'aucun': 'どの〜も〜ない', 'aucune': 'どの〜も〜ない', 'nul': '〜ない'}
# 話法の助動詞 (+ 不定詞): 原形 → 本動詞に付ける形
MODALS = {'pouvoir': 'ことができる', 'vouloir': 'たい', 'devoir': 'なければならない', 'savoir': 'ことができる',
          'falloir': 'なければならない', 'aimer': 'のが好きだ', 'aller': 'つもりだ', 'venir': 'に来る', 'faire': 'させる',
          'laisser': 'させておく'}
# 複合過去で être を取る動詞 (移動・変化。代名動詞も être)
ETRE_VERBS = {'aller', 'venir', 'arriver', 'partir', 'entrer', 'sortir', 'naître', 'mourir', 'monter', 'descendre',
              'tomber', 'rester', 'retourner', 'devenir', 'revenir', 'rentrer', 'passer', 'parvenir', 'survenir',
              'intervenir', 'décéder', 'apparaître', 'repartir', 'ressortir', 'redescendre', 'remonter'}
# 訳語を決めておく語 (Wiktionary の最初の語義が外れるもの・日本語に直しにくいもの)
GLOSSES = {
    'être': 'ある,いる', 'avoir': '持つ', 'faire': 'する,作る', 'aller': '行く', 'venir': '来る', 'voir': '見る',
    'lire': '読む', 'écrire': '書く', 'parler': '話す', 'dire': '言う', 'donner': '与える', 'prendre': '取る',
    'manger': '食べる', 'boire': '飲む', 'habiter': '住む', 'vivre': '生きる,住む', 'aimer': '愛する,好む',
    'jouer': '遊ぶ,演奏する', 'acheter': '買う', 'trouver': '見つける,思う', 'savoir': '知っている', 'connaître': '知っている',
    'penser': '考える', 'croire': '信じる,思う', 'travailler': '働く', 'apprendre': '学ぶ', 'chanter': '歌う',
    'danser': '踊る', 'dormir': '眠る', 'attendre': '待つ', 'demander': '尋ねる', 'répondre': '答える',
    'entendre': '聞こえる,聞く', 'écouter': '聞く', 'chercher': '探す', 'ouvrir': '開ける', 'fermer': '閉める',
    'partir': '出発する', 'arriver': '着く', 'entrer': '入る', 'sortir': '出る', 'rester': 'とどまる', 'tomber': '落ちる',
    'mourir': '死ぬ', 'naître': '生まれる', 'devenir': '〜になる', 'comprendre': '理解する', 'commencer': '始める',
    'finir': '終える', 'mettre': '置く', 'porter': '運ぶ,身につける', 'montrer': '見せる', 'appeler': '呼ぶ',
    "s'appeler": '〜という名前である', 'aider': '助ける', 'envoyer': '送る', 'recevoir': '受け取る', 'courir': '走る',
    'marcher': '歩く', 'regarder': '見る', 'aimer bien': '好む', 'vouloir': '欲する', 'pouvoir': 'できる',
    'devoir': 'ねばならない', 'rendre': '返す', 'tenir': '持つ', 'perdre': '失う', 'gagner': '勝つ,稼ぐ',
    'homme': '男', 'femme': '女,妻', 'garçon': '少年', 'fille': '少女,娘', 'enfant': '子供', 'mère': '母', 'père': '父',
    'frère': '兄弟', 'sœur': '姉妹', 'ami': '友達', 'amie': '友達', 'maison': '家', 'livre': '本', 'lettre': '手紙',
    'professeur': '先生', 'école': '学校', 'ville': '町', 'pays': '国', 'monde': '世界', 'temps': '時間,天気',
    'jour': '日', 'nuit': '夜', 'an': '年', 'année': '年', 'eau': '水', 'pain': 'パン', 'chien': '犬', 'chat': '猫',
    'jardin': '庭', 'roi': '王', 'reine': '女王', 'prince': '王子', 'princesse': '王女', 'fois': '度', 'marché': '市場',
    'film': '映画', 'table': '机', 'porte': 'ドア', 'fenêtre': '窓', 'rue': '通り', 'vin': 'ワイン', 'lait': '牛乳',
    'fleur': '花', 'arbre': '木', 'ciel': '空', 'mer': '海', 'soleil': '太陽', 'lune': '月', 'étoile': '星',
    'cœur': '心', 'œil': '目', 'yeux': '目', 'main': '手', 'tête': '頭', 'chemin': '道', 'voiture': '車', 'train': '列車',
    'chambre': '部屋', 'argent': 'お金', 'travail': '仕事', 'vie': '生活,命', 'amour': '愛', 'mot': '言葉',
    'nom': '名前', 'gens': '人々', 'personne': '人', 'peuple': '民族', 'guerre': '戦争', 'dieu': '神', 'île': '島',
    'bon': '良い', 'beau': '美しい', 'belle': '美しい', 'grand': '大きい', 'petit': '小さい', 'nouveau': '新しい',
    'vieux': '古い,年老いた', 'jeune': '若い', 'long': '長い', 'court': '短い', 'haut': '高い', 'rapide': '速い',
    'chaud': '暑い,熱い', 'froid': '寒い,冷たい', 'rouge': '赤い', 'bleu': '青い', 'blanc': '白い', 'noir': '黒い',
    'vert': '緑の', 'heureux': '幸せな', 'triste': '悲しい', 'fatigué': '疲れた', 'content': '満足した', 'joli': 'かわいい',
    'tout': 'すべての', 'tous': 'すべての', 'toute': 'すべての', 'toutes': 'すべての', 'très': 'とても', 'aussi': '〜も', 'encore': 'まだ', 'déjà': 'もう', 'toujours': 'いつも', 'souvent': 'しばしば',
    'ici': 'ここで', 'là': 'そこで', 'aujourd\'hui': '今日', 'hier': '昨日', 'demain': '明日', 'maintenant': '今',
    'puis': 'それから', 'ensuite': 'それから', 'seulement': '〜だけ', 'bien': 'よく', 'mal': '悪く', 'beaucoup': 'たくさん',
    'peu': '少し', 'trop': 'あまりに', 'ensemble': '一緒に', 'oui': 'はい', 'non': 'いいえ', 'peut-être': 'たぶん',
    'vraiment': '本当に', 'bientôt': 'まもなく', 'vite': '速く', 'tard': '遅く', 'tôt': '早く', 'là-bas': 'あそこで',
}
NUMBERS_JA = {'un': '一', 'une': '一', 'deux': '二', 'trois': '三', 'quatre': '四', 'cinq': '五', 'six': '六',
              'sept': '七', 'huit': '八', 'neuf': '九', 'dix': '十', 'onze': '十一', 'douze': '十二', 'vingt': '二十',
              'cent': '百', 'mille': '千'}


@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    return spacy.load('fr_core_news_sm')


def available():
    try:
        nlp()
    except (ImportError, OSError):
        return False
    return dictionary.available()


def parse(surfaces):
    """語の列 → spaCy の Doc (語の切れ目はそのまま)"""
    from spacy.tokens import Doc
    model = nlp()
    doc = Doc(model.vocab, words=list(surfaces))
    return model(doc)


def morph(token):
    return {k: v for f in str(token.morph).split('|') if '=' in f for k, v in [f.split('=', 1)]}


def cngs(cases, feats=None, default_gender=None):
    """格の並び・spaCy の数・性 → [(格, 数, 性)]。分からない所はすべての値"""
    feats = feats or {}
    numbers = [NUMBERS[feats['Number']]] if feats.get('Number') in NUMBERS else ['sg', 'pl']
    genders = [GENDERS[feats['Gender']]] if feats.get('Gender') in GENDERS else \
        ([default_gender] if default_gender in ('m', 'f') else ['m', 'f'])
    return [(c, n, g) for c in cases for n in numbers for g in genders]


# ----------------------------------------------------------------------
# 訳語

@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    """見出し語 → (訳, 'ja' / 'en', 辞書の項目)"""
    from dragoman.core import en_ja
    poses = {'noun': ('noun', 'name'), 'name': ('name', 'noun'), 'verb': ('verb',), 'adj': ('adj',),
             'adv': ('adv', 'adj')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if lemma in GLOSSES:
        return GLOSSES[lemma], 'ja', row
    if row is None:
        return None, None, None
    if row['pos'] == 'name':
        name = row['en'].split(',')[0]
        ja = en_ja.translate(name, 'noun')
        return (ja, 'ja', row) if ja else (lemma, 'en', row)
    ja = en_ja.translate(row['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
    return (ja, 'ja', row) if ja else (row['en'], 'en', row)


def adverbial(ja):
    """形容詞の訳 → 副詞の形 (速い → 速く、静かな → 静かに)"""
    out = []
    for j in ja.split(','):
        if j.endswith('い') and not j.endswith(('きれい', 'きらい')):
            out.append(j[:-1] + 'く')
        elif j.endswith(('な', 'の')):
            out.append(j[:-1] + 'に')
        else:
            out.append(j + 'に' if re.search('[一-龥ぁ-んァ-ン]$', j) else j)
    return ','.join(out)


def verb_forms(word):
    """語形の表で動詞の定形として引く → [(見出し語, 印の集合)]"""
    return [(lemma, set(tags)) for lemma, pos, tags in dictionary.forms(word) if pos == 'verb' and tags]


def auxiliary(lemma):
    """複合過去の助動詞 (être を取る移動・変化の動詞)"""
    return 'être' if lemma in ETRE_VERBS else 'avoir'
