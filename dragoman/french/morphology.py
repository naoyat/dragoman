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
    'il': ('彼,それ', 3, 'sg', ('Nom',)), 'elle': ('彼女,それ', 3, 'sg', ('Nom', 'Acc')), 'on': ('人々', 3, 'sg', ('Nom',)),
    'nous': ('私たち', 1, 'pl', ('Nom', 'Acc', 'Dat')), 'vous': ('あなた', 2, 'pl', ('Nom', 'Acc', 'Dat')),
    'ils': ('彼ら,それら', 3, 'pl', ('Nom',)), 'elles': ('彼女ら,それら', 3, 'pl', ('Nom', 'Acc')),
    'me': ('私', 1, 'sg', ('Acc', 'Dat')), "m'": ('私', 1, 'sg', ('Acc', 'Dat')), 'te': ('君', 2, 'sg', ('Acc', 'Dat')),
    # 3人称の目的語の接語は人にも物にも (le「彼,それ」、l' は le・la のどちらも「彼,彼女,それ」)
    "t'": ('君', 2, 'sg', ('Acc', 'Dat')), 'le': ('彼,それ', 3, 'sg', ('Acc',)), 'la': ('彼女,それ', 3, 'sg', ('Acc',)),
    "l'": ('彼,彼女,それ', 3, 'sg', ('Acc',)), 'les': ('彼ら,それら', 3, 'pl', ('Acc',)),
    'lui': ('彼,彼女', 3, 'sg', ('Dat', 'Acc')), 'leur': ('彼ら,彼女ら', 3, 'pl', ('Dat',)), 'se': ('自分', 3, 'sg', ('Acc', 'Dat')), "s'": ('自分', 3, 'sg', ('Acc', 'Dat')),
    'moi': ('私', 1, 'sg', ('Acc', 'Nom')), 'toi': ('君', 2, 'sg', ('Acc', 'Nom')), 'eux': ('彼ら', 3, 'pl', ('Acc', 'Nom')),
    'soi': ('自分', 3, 'sg', ('Acc',)), 'ce': ('それ', 3, 'sg', ('Nom',)), "c'": ('それ', 3, 'sg', ('Nom',)),
    'chacun': ('各人', 3, 'sg', ('Nom', 'Acc')),
    'uns': ('ある人々', 3, 'pl', ('Nom', 'Acc')), 'unes': ('ある人々', 3, 'pl', ('Nom', 'Acc')), 'chacune': ('各人', 3, 'sg', ('Nom', 'Acc')),
    'celui': ('人,もの', 3, 'sg', ('Nom', 'Acc')), 'celle': ('人,もの', 3, 'sg', ('Nom', 'Acc')),
    'ceux': ('人々', 3, 'pl', ('Nom', 'Acc')), 'celles': ('人々,もの', 3, 'pl', ('Nom', 'Acc')),
    'cela': ('それ', 3, 'sg', ('Nom', 'Acc')), 'ça': ('それ', 3, 'sg', ('Nom', 'Acc')), 'ceci': ('これ', 3, 'sg', ('Nom', 'Acc')),
    'qui': ('誰', 3, 'sg', ('Nom', 'Acc')), 'quoi': ('何', 3, 'sg', ('Acc',)), 'rien': ('何', 3, 'sg', ('Acc', 'Nom')),
    'personne': ('誰', 3, 'sg', ('Nom', 'Acc')), 'tout': ('すべて', 3, 'sg', ('Nom', 'Acc')),
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
# 人を表す目的語の接語 (me・te・se・nous・vous) の格を決める動詞の表。le・la・les は対格、lui・leur は与格で決まる
# 間接他動詞 (à + 人「〜に」): Il me parle「私に話す」
INDIRECT_VERBS = {'parler', 'téléphoner', 'répondre', 'ressembler', 'plaire', 'déplaire', 'obéir', 'désobéir',
                  'sourire', 'mentir', 'succéder', 'nuire', 'convenir', 'appartenir', 'manquer', 'suffire', 'échapper',
                  'pardonner', 'résister', 'arriver', 'écrire', 'faire confiance', 'survivre', 'plaire', 'parvenir',
                  'importer', 'sembler', 'paraître', 'falloir', 'rester', 'revenir', 'tenir', 'répliquer'}
# 二重目的語の動詞 (物を対格・人を与格): Il me donne le livre「私に本を与える」。目的語が無くても人は与格 (Il me montre)
DITRANSITIVE_VERBS = {'donner', 'dire', 'envoyer', 'montrer', 'prêter', 'offrir', 'raconter', 'expliquer', 'demander',
                      'apprendre', 'enseigner', 'promettre', 'permettre', 'conseiller', 'proposer', 'rendre', 'apporter',
                      'présenter', 'vendre', 'annoncer', 'interdire', 'souhaiter', 'confier', 'servir', 'lire', 'poser',
                      'adresser', 'accorder', 'remettre', 'transmettre', 'indiquer', 'décrire', 'reprocher', 'avouer',
                      'cacher', 'emprunter', 'voler', 'acheter', 'payer', 'ordonner', 'défendre', 'signaler', 'rappeler',
                      'garder', 'laisser', 'faire', 'écrire'}
# 中性代名詞 en (de + それ) の助詞: de を取る動詞なら de の意味で (s'en apercevoir「それに気づく」)。ほかは「それを」(J'en mange)
EN_PARTICLES = {'se apercevoir': 'に', 'se méfier': 'に', 'se rendre compte': 'に', 'parler': 'について',
                'se plaindre': 'について', 'discuter': 'について', 'se souvenir': 'を', 'se moquer': 'を', 'se occuper': 'を',
                'se servir': 'を', 'profiter': 'を', 'rêver': 'を', 'douter': 'を', 'avoir besoin': 'が', 'venir': 'から',
                'revenir': 'から', 'sortir': 'から', 'partir': 'から', 'se éloigner': 'から', 'dépendre': 'に'}


# de + 名詞が目的語にあたる動詞 (s'apercevoir de son erreur「誤りに気づく」= notice his error) → 日本語の助詞。
# 解析では de を外して目的語に、フランス語に戻すときは de を付ける (generate/french.py)
DE_OBJECT_VERBS = {'se apercevoir': 'に', 'se méfier': 'を', 'se souvenir': 'を', 'se moquer': 'を', 'se servir': 'を',
                   'se occuper': 'を', 'profiter': 'を', 'douter': 'を', 'se rendre compte': 'に', 'avoir besoin': 'が'}


def display_lemma(lemma):
    """見出しの表示 (辞書の鍵 se apercevoir → s'apercevoir。母音・無音の h の前はエリジオン)"""
    if lemma.startswith('se ') and lemma[3:4] in 'aeiouyhàâéèêîôû':
        return "s'" + lemma[3:]
    return lemma


# que の後ろを接続法にする主節の動詞 (意志・必要・感情: il faut que je parte、je veux que tu viennes)
SUBJUNCTIVE_TRIGGERS = {'falloir', 'vouloir', 'souhaiter', 'désirer', 'exiger', 'demander', 'ordonner', 'préférer',
                        'aimer', 'attendre', 'craindre', 'regretter', 'douter', 'permettre', 'interdire', 'empêcher',
                        'suffire', 'valoir', 'importer', 'convenir'}
# 後ろを接続法にする接続詞 (前置詞・副詞 + que。解析で1語にした見出し)
# 副詞節の従属接続詞 → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py)
SUBORDINATORS = {'quand': ('とき', None), 'lorsque': ('とき', None), "lorsqu'": ('とき', None), 'parce': ('ので', None),
                 'parce que': ('ので', None), "parce qu'": ('ので', None), 'puisque': ('ので', None),
                 "puisqu'": ('ので', None), 'comme': ('ので', None), 'si': ('なら', None), "s'": ('なら', None),
                 'bien que': ('けれども', None), 'quoique': ('けれども', None), 'avant que': ('前に', 'present'),
                 'après que': ('後で', 'perfect'), 'pendant que': ('間に', None), 'tandis que': ('一方で', None),
                 'dès que': ('とすぐに', None), "jusqu'à ce que": ('まで', 'present'), 'pour que': ('ように', 'present'),
                 'afin que': ('ように', 'present'), 'sans que': ('まま', None, True)}   # 3つ目: 節を否定に
SUBJUNCTIVE_CONJUNCTIONS = {'sans que', 'pour que', 'afin que', 'avant que', 'bien que', 'quoique', 'à condition que',
                            'de sorte que', 'jusqu\'à ce que'}
# 人が与格・物が主語の動詞 (経験者の構文): 日本語では人を主題「は」に (Tu me manques「私は 君が いなくて寂しい」、
# Ce livre me plaît「私は この本が 気に入っている」)
EXPERIENCER_VERBS = {'manquer': 'いなくて寂しい', 'plaire': '気に入っている'}
# 複合過去で être を取る動詞 (移動・変化。代名動詞も être)
ETRE_VERBS = {'aller', 'venir', 'arriver', 'partir', 'entrer', 'sortir', 'naître', 'mourir', 'monter', 'descendre',
              'tomber', 'rester', 'retourner', 'devenir', 'revenir', 'rentrer', 'passer', 'parvenir', 'survenir',
              'intervenir', 'décéder', 'apparaître', 'repartir', 'ressortir', 'redescendre', 'remonter'}
# 訳語を決めておく語 (Wiktionary の最初の語義が外れるもの・日本語に直しにくいもの)
GLOSSES = {
    'nommer': '呼ぶ,名付ける', 'appeler': '呼ぶ', 'raison': '理性,理由', 'opinion': '意見', 'diversité': '多様さ',
    'juger': '判断する', 'distinguer': '区別する', 'réussir': '成功する', 'chercher': '探す', 'travailler': '働く', 'contenter': '満足させる', 'pourvoir': '備える',
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
    'se appeler': '呼ばれている', 'se en aller': '立ち去る', 'aller': '行く', 'téléphoner': '電話する', 'se lever': '起きる', 'se coucher': '寝る', 'se promener': '散歩する',
    'se souvenir': '思い出す,覚えている', 'se trouver': 'ある,いる', 'se sentir': '感じる', 'se laver': '体を洗う',
    'se dépêcher': '急ぐ', 'se reposer': '休む', 'se marier': '結婚する', 'se taire': '黙る', 'se tromper': '間違える',
    'se moquer': 'からかう', 'se demander': '自問する,〜かしらと思う', 'se rendre': '行く', 'se passer': '起こる',
    'se battre': '戦う', 'se réveiller': '目を覚ます', 'se habiller': '服を着る', 'se asseoir': '座る',
    'manquer': '欠ける,足りない', 'aider': '助ける', 'envoyer': '送る', 'recevoir': '受け取る', 'courir': '走る',
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
    # ラテン語の教科書によく出る語 (文の生成で稀な語より先に選ぶ: soldat を drille より、agriculteur を culto より)
    'agriculteur': '農夫', 'paysan': '農民', 'soldat': '兵士', 'ennemi': '敵', 'armée': '軍隊', 'bataille': '戦い',
    'camp': '陣営', 'chef': '指導者', 'général': '将軍', 'cheval': '馬', 'épée': '剣', 'arme': '武器', 'maître': '主人',
    'serviteur': '召使い', 'esclave': '奴隷', 'déesse': '女神', 'temple': '神殿', 'forêt': '森', 'champ': '畑',
    'route': '道', 'mur': '壁', 'porte de la ville': '城門', 'citoyen': '市民', 'sénateur': '元老院議員', 'consul': '執政官',
    'empereur': '皇帝', 'empire': '帝国', 'loi': '法', 'paix': '平和', 'victoire': '勝利', 'courage': '勇気',
    'poète': '詩人', 'histoire': '歴史,物語', 'fable': '寓話', 'reine': '女王', 'fils': '息子', 'oncle': 'おじ',
    'tante': 'おば', 'mari': '夫', 'épouse': '妻', 'voisin': '隣人', 'hôte': '客', 'esprit': '精神', 'corps': '体',
    'vie': '生活,命', 'mort': '死', 'âme': '魂', 'lieu': '場所', 'terre': '土地,大地', 'eau': '水', 'feu': '火',
    'air': '空気', 'vent': '風', 'pluie': '雨', 'neige': '雪', 'montagne': '山', 'rivière': '川', 'fleuve': '川',
    'navire': '船', 'bateau': '船', 'port': '港', 'rivage': '岸', 'oiseau': '鳥', 'loup': '狼', 'lion': 'ライオン',
    'vache': '牛', 'cerf': '鹿', 'renard': '狐', 'rose': 'バラ', 'lettre': '手紙', 'nouvelle': '知らせ',
    'vaincre': '打ち負かす', 'gagner': '勝つ,稼ぐ', 'combattre': '戦う', 'tuer': '殺す', 'conduire': '導く',
    'envoyer': '送る', 'recevoir': '受け取る', 'craindre': '恐れる', 'louer': '褒める', 'aider': '助ける',
    'appeler': '呼ぶ', 'construire': '建てる', 'détruire': '破壊する', 'raconter': '語る', 'enseigner': '教える',
    'nager': '泳ぐ', 'naviguer': '航海する', 'labourer': '耕す', 'cultiver': '耕す', 'préparer': '準備する',
    'garder': '守る', 'défendre': '守る', 'attaquer': '攻撃する', 'fuir': '逃げる', 'cacher': '隠す',
    'malade': '病気な', 'content': 'うれしい', 'heureux': '幸せな,うれしい', 'désolé': '残念な,申し訳ない', 'falloir': '必要である', 'rire': '笑う', 'pleuvoir': '雨が降る', 'neiger': '雪が降る', 'juste': 'ちょうど',
    'bon': '良い', 'beau': '美しい', 'belle': '美しい', 'grand': '大きい', 'petit': '小さい', 'nouveau': '新しい',
    'vieux': '古い,年老いた', 'jeune': '若い', 'long': '長い', 'court': '短い', 'haut': '高い', 'rapide': '速い',
    'chaud': '暑い,熱い', 'froid': '寒い,冷たい', 'rouge': '赤い', 'bleu': '青い', 'blanc': '白い', 'noir': '黒い',
    'vert': '緑の', 'heureux': '幸せな', 'triste': '悲しい', 'fatigué': '疲れた', 'joli': 'かわいい',
    'tout': 'すべての', 'tous': 'すべての', 'toute': 'すべての', 'toutes': 'すべての', 'très': 'とても', 'aussi': '〜も', 'encore': 'まだ', 'déjà': 'もう', 'toujours': 'いつも', 'souvent': 'しばしば',
    'ici': 'ここで', 'là': 'そこで', 'aujourd\'hui': '今日', 'hier': '昨日', 'demain': '明日', 'maintenant': '今',
    'puis': 'それから', 'ensuite': 'それから', 'seulement': '〜だけ', 'bien': 'よく', 'mal': '悪く', 'beaucoup': 'たくさん',
    'peu': '少し', 'trop': 'あまりに', 'ensemble': '一緒に', 'oui': 'はい', 'non': 'いいえ', 'peut-être': 'たぶん',
    'vraiment': '本当に', 'bientôt': 'まもなく', 'vite': '速く', 'tard': '遅く', 'tôt': '早く', 'là-bas': 'あそこで',
}
# 小文字の言語名の名詞は言語 (parler français「フランス語」。大文字の Français は人、形容詞は「フランスの」)
LANGUAGE_NOUNS = {'français': 'フランス語', 'anglais': '英語', 'allemand': 'ドイツ語', 'japonais': '日本語',
                  'espagnol': 'スペイン語', 'italien': 'イタリア語', 'latin': 'ラテン語', 'grec': 'ギリシア語',
                  'chinois': '中国語', 'russe': 'ロシア語', 'arabe': 'アラビア語', 'portugais': 'ポルトガル語',
                  'coréen': '韓国語', 'hébreu': 'ヘブライ語'}
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
    if lemma.startswith("s'"):
        lemma = 'se ' + lemma[2:]   # 表示の形 (s'apercevoir) → 辞書の鍵 (se apercevoir)
    poses = {'noun': ('noun', 'name'), 'name': ('name', 'noun'), 'verb': ('verb',), 'adj': ('adj',),
             'adv': ('adv', 'adj')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if lemma in GLOSSES:
        return GLOSSES[lemma], 'ja', row
    old = dictionary.reform_spellings()[0].get(lemma.lower())
    if old and old != lemma.lower():   # 1990年の新しい綴り (cout) は従来の綴り (coût) の語義で訳す
        found = gloss(old, pos)
        if found[0]:
            return found
    if row is None:
        return None, None, None
    if row['pos'] == 'name':
        name = row['en'].split(',')[0]
        ja = en_ja.translate(name, 'noun')
        return (ja, 'ja', row) if ja else (lemma, 'en', row)
    ja = en_ja.translate(row['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
    return (ja, 'ja', row) if ja else (row['en'], 'en', row)


def reform_note(surface, lemma):
    """1990年の綴りの改革の注: ('new', 新しい綴り) か ('old', 従来の綴り)。改革で変わらない語は None。
    見出しの新旧が î・û の記号だけの違いなら、活用形にも同じ規則で (connaît → connait)"""
    new_to_old, old_to_new = dictionary.reform_spellings()
    word, lemma = surface.lower(), (lemma or surface).lower()
    if word in old_to_new and ' ' not in old_to_new[word]:   # 句の項目 (être sur son trente-et-un) は語の注にしない
        return 'new', old_to_new[word]
    if word in new_to_old and ' ' not in new_to_old[word]:
        return 'old', new_to_old[word]
    plain = lambda w: w.replace('î', 'i').replace('û', 'u')
    if lemma in old_to_new and plain(lemma) == old_to_new[lemma] and plain(word) != word:
        return 'new', plain(word)                     # connaît → connait (connaître → connaitre)
    if lemma in new_to_old and plain(new_to_old[lemma]) == lemma:
        restored = _restore_circumflex(word, new_to_old[lemma])   # connait → connaît
        if restored != word:
            return 'old', restored
    return None


def _restore_circumflex(word, old_lemma):
    """新しい綴りの語形に、従来の綴りの見出しの記号を戻す (connait + connaître → connaît)。語幹の同じ位置の i・u だけ"""
    out = list(word)
    for k, c in enumerate(old_lemma):
        if c in 'îû' and k < len(out) and out[k] == {'î': 'i', 'û': 'u'}[c]:
            out[k] = c
    return ''.join(out)


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
