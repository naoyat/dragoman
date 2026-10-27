#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語の語形: spaCy のポルトガル語モデル (pt_core_news_sm) で文脈の中の品詞 (UD)・原形・性・数・人称・時制と
# 依存関係を付け、語の項目 (dict) にする。機能語 (冠詞・代名詞・前置詞・接続詞) の訳はここの表、内容語の訳は辞書
# (Wiktionary の英語の語義を core/en_ja.py で日本語に直したもの)。基本の語は GLOSSES で決めておく
#
# ブラジル (pt-br) とポルトガル (pt-pt) の両方を読む: 綴りの違い (fato / facto) は辞書の語形の表、主語の você (ブラジルの
# 2人称) は3人称の動詞を取る「あなた」、tu + 3人称の動詞 (ブラジルの口語) も「君」
#
import functools
import re

from . import dictionary

NUMBERS = {'Sing': 'sg', 'Plur': 'pl'}
GENDERS = {'Masc': 'm', 'Fem': 'f'}
CASES = ('Nom', 'Acc', 'Dat')

# 人称代名詞: 形 → (訳, 人称, 数, 格の並び)。人称は動詞の一致の人称 (você・vocês は3人称の動詞を取る)
PRONOUNS = {
    'eu': ('私', 1, 'sg', ('Nom',)), 'tu': ('君', 2, 'sg', ('Nom',)), 'você': ('あなた', 3, 'sg', ('Nom', 'Acc')),
    'ele': ('彼,それ', 3, 'sg', ('Nom', 'Acc')), 'ela': ('彼女,それ', 3, 'sg', ('Nom', 'Acc')),
    'nós': ('私たち', 1, 'pl', ('Nom', 'Acc')), 'vós': ('あなたたち', 2, 'pl', ('Nom', 'Acc')),
    'vocês': ('あなたたち', 3, 'pl', ('Nom', 'Acc')), 'eles': ('彼ら,それら', 3, 'pl', ('Nom', 'Acc')),
    'elas': ('彼女ら,それら', 3, 'pl', ('Nom', 'Acc')),
    # 接語 (動詞の前か、ハイフンで動詞の後ろ)
    'me': ('私', 1, 'sg', ('Acc', 'Dat')), 'te': ('君', 2, 'sg', ('Acc', 'Dat')),
    'o': ('彼,それ', 3, 'sg', ('Acc',)), 'a': ('彼女,それ', 3, 'sg', ('Acc',)), 'os': ('彼ら,それら', 3, 'pl', ('Acc',)),
    'as': ('彼女ら,それら', 3, 'pl', ('Acc',)), 'lo': ('彼,それ', 3, 'sg', ('Acc',)), 'la': ('彼女,それ', 3, 'sg', ('Acc',)),
    'los': ('彼ら,それら', 3, 'pl', ('Acc',)), 'las': ('彼女ら,それら', 3, 'pl', ('Acc',)),
    'no': ('彼,それ', 3, 'sg', ('Acc',)), 'na': ('彼女,それ', 3, 'sg', ('Acc',)),
    'lhe': ('彼,彼女,あなた', 3, 'sg', ('Dat',)), 'lhes': ('彼ら,あなたたち', 3, 'pl', ('Dat',)),
    'nos': ('私たち', 1, 'pl', ('Acc', 'Dat')), 'vos': ('あなたたち', 2, 'pl', ('Acc', 'Dat')),
    'se': ('自分', 3, 'sg', ('Acc', 'Dat')),
    # 前置詞の後ろの形
    'mim': ('私', 1, 'sg', ('Gen',)), 'ti': ('君', 2, 'sg', ('Gen',)), 'si': ('自分', 3, 'sg', ('Gen',)),
    'comigo': ('私と', 1, 'sg', ('Gen',)), 'contigo': ('君と', 2, 'sg', ('Gen',)), 'conosco': ('私たちと', 1, 'pl', ('Gen',)),
    'connosco': ('私たちと', 1, 'pl', ('Gen',)), 'consigo': ('自分と', 3, 'sg', ('Gen',)),
    # 指示・不定・疑問の代名詞
    'isto': ('これ', 3, 'sg', ('Nom', 'Acc')), 'isso': ('それ', 3, 'sg', ('Nom', 'Acc')),
    'aquilo': ('あれ', 3, 'sg', ('Nom', 'Acc')), 'tudo': ('すべて', 3, 'sg', ('Nom', 'Acc')),
    'nada': ('何も', 3, 'sg', ('Nom', 'Acc')), 'ninguém': ('誰も', 3, 'sg', ('Nom', 'Acc')),
    'alguém': ('誰か', 3, 'sg', ('Nom', 'Acc')), 'algo': ('何か', 3, 'sg', ('Nom', 'Acc')),
    'quem': ('誰', 3, 'sg', ('Nom', 'Acc')), 'que': ('何', 3, 'sg', ('Nom', 'Acc')), 'qual': ('どれ', 3, 'sg', ('Nom', 'Acc')),
    'quais': ('どれ', 3, 'pl', ('Nom', 'Acc')),
}
CLITICS = {'me', 'te', 'o', 'a', 'os', 'as', 'lo', 'la', 'los', 'las', 'no', 'na', 'lhe', 'lhes', 'nos', 'vos', 'se'}
SUBJECT_PRONOUNS = {'eu', 'tu', 'você', 'ele', 'ela', 'nós', 'vós', 'vocês', 'eles', 'elas'}
RELATIVES = {'que': ('Nom', 'Acc'), 'quem': ('Acc',), 'onde': ('Loc',), 'qual': ('Nom', 'Acc'), 'quais': ('Nom', 'Acc'),
             'cujo': ('Gen',), 'cuja': ('Gen',), 'cujos': ('Gen',), 'cujas': ('Gen',)}
ARTICLES = {'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas'}
# 限定詞: 形 → 訳 (冠詞は訳さない)
DETERMINERS = {'este': 'この', 'esta': 'この', 'estes': 'これらの', 'estas': 'これらの', 'esse': 'その', 'essa': 'その',
               'esses': 'それらの', 'essas': 'それらの', 'aquele': 'あの', 'aquela': 'あの', 'aqueles': 'あれらの',
               'aquelas': 'あれらの', 'meu': '私の', 'minha': '私の', 'meus': '私の', 'minhas': '私の', 'teu': '君の',
               'tua': '君の', 'teus': '君の', 'tuas': '君の', 'seu': '彼の,あなたの', 'sua': '彼の,あなたの',
               'seus': '彼の,あなたの', 'suas': '彼の,あなたの', 'nosso': '私たちの', 'nossa': '私たちの',
               'nossos': '私たちの', 'nossas': '私たちの', 'vosso': 'あなたたちの', 'vossa': 'あなたたちの',
               'vossos': 'あなたたちの', 'vossas': 'あなたたちの', 'todo': 'すべての', 'toda': 'すべての',
               'todos': 'すべての', 'todas': 'すべての', 'cada': 'それぞれの', 'outro': '他の', 'outra': '他の',
               'outros': '他の', 'outras': '他の', 'algum': 'ある', 'alguma': 'ある', 'alguns': 'いくつかの',
               'algumas': 'いくつかの', 'muito': '多くの', 'muita': '多くの', 'muitos': '多くの', 'muitas': '多くの',
               'pouco': '少しの', 'pouca': '少しの', 'poucos': '少しの', 'poucas': '少しの', 'qual': 'どの', 'quais': 'どの',
               'que': 'どの', 'mesmo': '同じ', 'mesma': '同じ', 'mesmos': '同じ', 'mesmas': '同じ', 'vários': 'いくつもの',
               'várias': 'いくつもの', 'tanto': 'それほど多くの', 'tanta': 'それほど多くの', 'tantos': 'それほど多くの',
               'tantas': 'それほど多くの', 'quanto': 'どれほどの', 'quanta': 'どれほどの', 'quantos': 'いくつの',
               'quantas': 'いくつの', 'nenhum': '', 'nenhuma': ''}
# 所有の限定詞 → (人称, 数)
POSSESSIVES = {'meu': (1, 'sg'), 'minha': (1, 'sg'), 'meus': (1, 'sg'), 'minhas': (1, 'sg'), 'teu': (2, 'sg'),
               'tua': (2, 'sg'), 'teus': (2, 'sg'), 'tuas': (2, 'sg'), 'seu': (3, 'sg'), 'sua': (3, 'sg'),
               'seus': (3, 'sg'), 'suas': (3, 'sg'), 'nosso': (1, 'pl'), 'nossa': (1, 'pl'), 'nossos': (1, 'pl'),
               'nossas': (1, 'pl'), 'vosso': (2, 'pl'), 'vossa': (2, 'pl'), 'vossos': (2, 'pl'), 'vossas': (2, 'pl')}
# 前置詞: 原形 → 訳
PREPOSITIONS = {
    'a': '〜に,〜へ', 'de': '〜の,〜から', 'em': '〜で,〜に', 'para': '〜のために,〜へ', 'pra': '〜のために,〜へ',
    'por': '〜によって,〜を通って', 'com': '〜と,〜で', 'sem': '〜なしで', 'sobre': '〜の上に,〜について',
    'entre': '〜の間で', 'até': '〜まで', 'desde': '〜以来', 'contra': '〜に対して', 'sob': '〜の下で', 'após': '〜の後で',
    'perante': '〜の前で', 'durante': '〜の間', 'segundo': '〜によれば', 'como': '〜として,〜のように',
    'trás': '〜の後ろで', 'antes': '〜の前に', 'depois': '〜の後で', 'perto': '〜の近くで', 'longe': '〜から遠く',
    'dentro': '〜の中で', 'fora': '〜の外で', 'junto': '〜のそばで', 'através': '〜を通って', 'conforme': '〜によれば',
}
# 前置詞と代名詞の縮約形 (dele「彼の」・nele「彼の中で」) → (前置詞, 代名詞)
PRONOUN_CONTRACTIONS = {'dele': ('de', 'ele'), 'dela': ('de', 'ela'), 'deles': ('de', 'eles'), 'delas': ('de', 'elas'),
                        'nele': ('em', 'ele'), 'nela': ('em', 'ela'), 'neles': ('em', 'eles'), 'nelas': ('em', 'elas'),
                        'disso': ('de', 'isso'), 'disto': ('de', 'isto'), 'daquilo': ('de', 'aquilo'),
                        'nisso': ('em', 'isso'), 'nisto': ('em', 'isto'), 'naquilo': ('em', 'aquilo')}
CONJUNCTIONS = {'e': 'そして,〜と', 'ou': 'または', 'mas': 'しかし', 'porém': 'しかし', 'contudo': 'しかし',
                'todavia': 'しかし', 'pois': 'というのは', 'portanto': 'だから', 'então': 'それから,だから', 'nem': '〜も〜ない',
                'que': '〜ということ', 'se': '〜なら,〜かどうか', 'quando': '〜するとき', 'porque': '〜なので',
                'como': '〜なので,〜のように', 'embora': '〜けれども', 'enquanto': '〜する間', 'caso': '〜なら',
                'conforme': '〜につれて'}
# 副詞節の従属接続詞 → (節の後ろに付ける形, 節の動詞の時制[, 否定]) (core/Adverbial.py)。いくつかの語のものは1語にまとめる
SUBORDINATORS = {'quando': ('とき', None), 'se': ('なら', None), 'porque': ('ので', None), 'como': ('ので', None),
                 'embora': ('けれども', None), 'enquanto': ('間に', None), 'caso': ('なら', None),
                 'ainda que': ('けれども', None), 'mesmo que': ('ても', None), 'já que': ('ので', None),
                 'visto que': ('ので', None), 'uma vez que': ('ので', None), 'antes que': ('前に', 'present'),
                 'depois que': ('後で', 'perfect'), 'logo que': ('とすぐに', None), 'assim que': ('とすぐに', None),
                 'até que': ('まで', 'present'), 'para que': ('ように', 'present'), 'a fim de que': ('ように', 'present'),
                 'sem que': ('まま', None, True), 'desde que': ('以来', None), 'contanto que': ('なら', None)}
# 否定 (não は動詞を否定に。nunca・nada … は後ろでも前でも)
NEGATIONS = {'não': '〜ない', 'nunca': '決して〜ない', 'jamais': '決して〜ない', 'nem': '〜も〜ない',
             'nada': '何も〜ない', 'ninguém': '誰も〜ない', 'nenhum': 'どの〜も〜ない', 'nenhuma': 'どの〜も〜ない',
             'tampouco': '〜もまた〜ない'}
# 話法の助動詞・動詞の組 (+ 不定詞): 原形 → 本動詞に付ける形 (ir + 不定詞は未来、ter que / de は義務)
MODALS = {'poder': 'ことができる', 'querer': 'たい', 'dever': 'なければならない', 'precisar': '必要がある',
          'conseguir': 'ことができる', 'saber': 'ことができる', 'gostar': 'のが好きだ', 'costumar': 'のが常だ',
          'tentar': 'ようとする', 'começar': '始める', 'acabar': 'たところだ', 'voltar': '再び', 'deixar': 'させておく',
          'mandar': 'させる', 'fazer': 'させる', 'ter': 'なければならない', 'haver': 'なければならない'}
# 人の接語 (me・te・nos・vos) を与格「〜に」にする動詞 (目的語の名詞が無くても: Ela me disse「私に言った」)
DATIVE_VERBS = {'dizer', 'perguntar', 'responder', 'telefonar', 'ligar', 'escrever', 'contar', 'explicar', 'mostrar',
                'dar', 'mandar', 'enviar', 'emprestar', 'oferecer', 'pedir', 'agradecer', 'obedecer', 'parecer',
                'pertencer', 'faltar', 'acontecer', 'sorrir', 'mentir', 'ensinar', 'prometer', 'falar'}
# 補文の que「〜と」を取る言う・思う動詞 (ほかは「〜ことを」)
SAY_VERBS = {'dizer', 'falar', 'contar', 'responder', 'perguntar', 'pensar', 'achar', 'acreditar', 'crer', 'escrever',
             'gritar', 'afirmar', 'explicar', 'sentir', 'esperar', 'jurar', 'prometer'}
# 進行形 (estar + 現在分詞 (ブラジル)・estar a + 不定詞 (ポルトガル)) を作る動詞と、動詞の組の前置詞
PROGRESSIVE = {'estar', 'ficar', 'andar', 'continuar', 'seguir', 'viver'}
# 訳語を決めておく語 (Wiktionary の最初の語義が外れるもの・日本語に直しにくいもの)
GLOSSES = {'porão': '地下室,船倉', 'caro': '高価な,親愛な', 
    'ser': '〜である', 'estar': '〜である,いる', 'ter': '持つ,ある', 'haver': 'ある', 'fazer': 'する,作る', 'ir': '行く',
    'vir': '来る', 'dar': '与える', 'dizer': '言う', 'ver': '見る', 'saber': '知る', 'poder': 'できる', 'querer': '欲しい',
    'ficar': '留まる,〜になる', 'deixar': '残す,させる', 'falar': '話す', 'comer': '食べる', 'beber': '飲む', 'ler': '読む',
    'escrever': '書く', 'morar': '住む', 'viver': '生きる,住む', 'gostar': '好む', 'amar': '愛する', 'chegar': '着く',
    'sair': '出る', 'conhecer': '知っている', 'pensar': '思う', 'achar': '思う,見つける', 'encontrar': '見つける,会う',
    'chamar': '呼ぶ', 'levar': '持って行く', 'trazer': '持って来る', 'pôr': '置く', 'trabalhar': '働く',
    'estudar': '勉強する', 'cantar': '歌う', 'dançar': '踊る', 'chorar': '泣く', 'sonhar': '夢見る', 'esperar': '待つ,望む',
    'perder': '失う', 'ganhar': '得る', 'olhar': '見る', 'ouvir': '聞く', 'sentir': '感じる', 'voltar': '戻る',
    'partir': '出発する', 'entrar': '入る', 'abrir': '開ける', 'fechar': '閉める', 'comprar': '買う', 'vender': '売る',
    'pagar': '払う', 'dormir': '眠る', 'acordar': '目覚める', 'correr': '走る', 'andar': '歩く', 'nadar': '泳ぐ',
    'menino': '少年', 'menina': '少女', 'casa': '家', 'livro': '本', 'escola': '学校', 'professor': '先生',
    'professora': '先生', 'homem': '男', 'mulher': '女', 'pai': '父', 'mãe': '母', 'filho': '息子', 'filha': '娘',
    'amor': '愛', 'coração': '心', 'saudade': '懐かしさ,恋しさ', 'mar': '海', 'vida': '人生,生活', 'mundo': '世界',
    'dia': '日', 'noite': '夜', 'tempo': '時間,天気', 'gente': '人々', 'coisa': '物,事', 'cidade': '町', 'rua': '通り',
    'água': '水', 'céu': '空', 'sol': '太陽', 'lua': '月', 'olho': '目', 'mão': '手', 'carro': '車', 'bolo': 'ケーキ',
    'amigo': '友人', 'amiga': '友人', 'pessoa': '人', 'restaurante': 'レストラン', 'cachorro': '犬', 'cão': '犬',
    'gato': '猫', 'chuva': '雨', 'flor': '花', 'estrela': '星', 'canção': '歌', 'música': '音楽',
    'bonito': '美しい', 'lindo': '美しい', 'grande': '大きい', 'pequeno': '小さい', 'novo': '新しい', 'velho': '古い,年老いた',
    'bom': '良い', 'mau': '悪い', 'feliz': '幸せな', 'triste': '悲しい', 'alto': '高い', 'baixo': '低い',
}
# 小文字の言語名の名詞は言語 (falar português「ポルトガル語」)
LANGUAGE_NOUNS = {'português': 'ポルトガル語', 'inglês': '英語', 'francês': 'フランス語', 'alemão': 'ドイツ語',
                  'japonês': '日本語', 'espanhol': 'スペイン語', 'italiano': 'イタリア語', 'latim': 'ラテン語',
                  'chinês': '中国語', 'russo': 'ロシア語', 'árabe': 'アラビア語', 'coreano': '韓国語'}
NUMBERS_JA = {'um': '一', 'uma': '一', 'dois': '二', 'duas': '二', 'três': '三', 'quatro': '四', 'cinco': '五',
              'seis': '六', 'sete': '七', 'oito': '八', 'nove': '九', 'dez': '十', 'onze': '十一', 'doze': '十二',
              'vinte': '二十', 'cem': '百', 'cento': '百', 'mil': '千'}


@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    return spacy.load('pt_core_news_sm')


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
    return model(Doc(model.vocab, words=list(surfaces)))


def morph(token):
    return {k: v for f in str(token.morph).split('|') if '=' in f for k, v in [f.split('=', 1)]}


def cngs(cases, feats=None, default_gender=None):
    """格の並び・spaCy の数・性 → [(格, 数, 性)]。分からない所はすべての値"""
    feats = feats or {}
    numbers = [NUMBERS[feats['Number']]] if feats.get('Number') in NUMBERS else ['sg', 'pl']
    genders = [GENDERS[feats['Gender']]] if feats.get('Gender') in GENDERS else \
        ([default_gender] if default_gender in ('m', 'f') else ['m', 'f'])
    return [(c, n, g) for c in cases for n in numbers for g in genders]


@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    """見出し語 → (訳, 'ja' / 'en', 辞書の項目)。ブラジルとポルトガルの綴りの違いは語形の表で相手の綴りも引く"""
    from dragoman.core import en_ja
    poses = {'noun': ('noun', 'name'), 'name': ('name', 'noun'), 'verb': ('verb',), 'adj': ('adj',),
             'adv': ('adv', 'adj')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if lemma in GLOSSES and pos in ('noun', 'verb', 'adj', 'adv', 'name'):
        return GLOSSES[lemma], 'ja', row
    if row is None:
        other = next((l for l, p, tags in dictionary.forms(lemma) if p in poses and not tags), None)
        if other and other != lemma:   # 綴りの違いだけの語形 (fato → facto)
            return gloss(other, pos)
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
    """語形の表で動詞として引く → [(見出し語, 印の集合)]"""
    return [(lemma, set(tags)) for lemma, pos, tags in dictionary.forms(word) if pos == 'verb' and tags]
