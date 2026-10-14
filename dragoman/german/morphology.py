#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語の語形: spaCy のドイツ語モデル (de_core_news_sm) で文脈の中の品詞 (STTS)・原形・格・性・数・人称・時制を
# 付け、語の項目 (dict) にする。機能語 (冠詞・代名詞・前置詞・接続詞) の訳はここの表、内容語の訳は辞書 (Wiktionary の
# 英語の語義を core/en_ja.py で日本語に直したもの)。基本の語は GLOSSES で決めておく
#
import functools
import re

from . import dictionary

CASES = {'Nom': 'Nom', 'Acc': 'Acc', 'Dat': 'Dat', 'Gen': 'Gen'}
NUMBERS = {'Sing': 'sg', 'Plur': 'pl'}
GENDERS = {'Masc': 'm', 'Fem': 'f', 'Neut': 'n'}
ALL_CASES = ('Nom', 'Acc', 'Dat', 'Gen')

# 人称代名詞: 原形 → (訳, 人称, 数)
PRONOUNS = {'ich': ('私', 1, 'sg'), 'du': ('君', 2, 'sg'), 'er': ('彼', 3, 'sg'), 'sie': ('彼女', 3, 'sg'),
            'es': ('それ', 3, 'sg'), 'wir': ('私たち', 1, 'pl'), 'ihr': ('君たち', 2, 'pl'), 'Sie': ('あなた', 2, 'sg'),
            'man': ('人々', 3, 'sg'), 'sich': ('自分', 3, 'sg'), 'mich': ('私', 1, 'sg'), 'dich': ('君', 2, 'sg'),
            'uns': ('私たち', 1, 'pl'), 'euch': ('君たち', 2, 'pl'), 'wer': ('誰', 3, 'sg'), 'was': ('何', 3, 'sg'),
            'jemand': ('誰か', 3, 'sg'), 'niemand': ('誰も〜ない', 3, 'sg'), 'etwas': ('何か', 3, 'sg'),
            'nichts': ('何も〜ない', 3, 'sg'), 'alles': ('すべて', 3, 'sg'), 'das': ('それ', 3, 'sg'),
            'dies': ('これ', 3, 'sg'), 'dieser': ('これ', 3, 'sg'), 'der': ('それ', 3, 'sg'), 'jeder': ('誰も', 3, 'sg'),
            'einer': ('一人', 3, 'sg'), 'keiner': ('誰も〜ない', 3, 'sg'), 'viel': ('多く', 3, 'sg'), 'alle': ('みな', 3, 'pl')}
# 冠詞類・所有冠詞・指示詞: 原形 → 訳 (冠詞は訳さない)
DETERMINERS = {'der': '', 'ein': '', 'dieser': 'この', 'jener': 'あの', 'jeder': 'どの〜も', 'alle': 'すべての',
               'all': 'すべての', 'mein': '私の', 'dein': '君の', 'sein': '彼の', 'ihr': '彼女の', 'unser': '私たちの',
               'euer': '君たちの', 'Ihr': 'あなたの', 'welcher': 'どの', 'solcher': 'そのような', 'mancher': 'いくつかの',
               'viel': '多くの', 'einige': 'いくつかの', 'wenig': '少しの', 'ander': '他の', 'beide': '両方の',
               'manch': 'いくつかの', 'kein': ''}
NEGATIVE_ARTICLE = 'kein'
# 前置詞: (原形, 格) → 訳。格の無い組は (原形, None)
PREPOSITIONS = {
    ('in', 'Dat'): '〜で,〜の中で', ('in', 'Acc'): '〜へ,〜の中へ', ('an', 'Dat'): '〜で,〜のそばで', ('an', 'Acc'): '〜へ',
    ('auf', 'Dat'): '〜の上で', ('auf', 'Acc'): '〜の上へ', ('über', 'Dat'): '〜の上方で', ('über', 'Acc'): '〜について,〜を越えて',
    ('unter', 'Dat'): '〜の下で', ('unter', 'Acc'): '〜の下へ', ('vor', 'Dat'): '〜の前で', ('vor', 'Acc'): '〜の前へ',
    ('hinter', 'Dat'): '〜の後ろで', ('hinter', 'Acc'): '〜の後ろへ', ('neben', 'Dat'): '〜の横で', ('neben', 'Acc'): '〜の横へ',
    ('zwischen', 'Dat'): '〜の間で', ('zwischen', 'Acc'): '〜の間へ', ('mit', None): '〜と,〜で', ('von', None): '〜から,〜の',
    ('zu', None): '〜へ,〜のところへ', ('nach', None): '〜へ,〜の後で', ('aus', None): '〜から,〜の中から',
    ('bei', None): '〜のところで,〜の際に', ('seit', None): '〜以来', ('für', None): '〜のために', ('durch', None): '〜を通って',
    ('gegen', None): '〜に対して', ('ohne', None): '〜なしで', ('um', None): '〜の周りに,〜時に', ('bis', None): '〜まで',
    ('während', None): '〜の間に', ('wegen', None): '〜のために', ('trotz', None): '〜にもかかわらず',
    ('statt', None): '〜の代わりに', ('außer', None): '〜以外', ('gegenüber', None): '〜の向かいに', ('ab', None): '〜から',
    ('entlang', None): '〜に沿って', ('laut', None): '〜によれば', ('pro', None): '〜あたり', ('als', None): '〜として',
    ('wie', None): '〜のように',
}
# 前置詞の支配する格 (2つあるものは名詞の格で決める)
GOVERNS = {'mit': 'Dat', 'von': 'Dat', 'zu': 'Dat', 'nach': 'Dat', 'aus': 'Dat', 'bei': 'Dat', 'seit': 'Dat',
           'gegenüber': 'Dat', 'außer': 'Dat', 'ab': 'Dat', 'für': 'Acc', 'durch': 'Acc', 'gegen': 'Acc',
           'ohne': 'Acc', 'um': 'Acc', 'bis': 'Acc', 'entlang': 'Acc', 'während': 'Gen', 'wegen': 'Gen',
           'trotz': 'Gen', 'statt': 'Gen', 'laut': 'Dat'}
# 前置詞と冠詞の融合形 → (前置詞, 格)
CONTRACTIONS = {'im': ('in', 'Dat'), 'ins': ('in', 'Acc'), 'am': ('an', 'Dat'), 'ans': ('an', 'Acc'),
                'zum': ('zu', 'Dat'), 'zur': ('zu', 'Dat'), 'vom': ('von', 'Dat'), 'beim': ('bei', 'Dat'),
                'aufs': ('auf', 'Acc'), 'durchs': ('durch', 'Acc'), 'fürs': ('für', 'Acc'), 'ums': ('um', 'Acc'),
                'übers': ('über', 'Acc'), 'unterm': ('unter', 'Dat'), 'vorm': ('vor', 'Dat'), 'hinterm': ('hinter', 'Dat')}
CONJUNCTIONS = {'und': 'そして,〜と', 'oder': 'または', 'aber': 'しかし', 'denn': 'というのは', 'sondern': 'ではなく',
                'doch': 'しかし', 'sowie': 'および', 'dass': '〜ということ', 'weil': '〜なので', 'wenn': '〜なら,〜するとき',
                'als': '〜したとき', 'ob': '〜かどうか', 'obwohl': '〜にもかかわらず', 'damit': '〜するために',
                'bevor': '〜する前に', 'nachdem': '〜した後で', 'während': '〜する間に', 'da': '〜なので', 'falls': '〜の場合',
                'seit': '〜して以来', 'seitdem': '〜して以来', 'bis': '〜するまで', 'sobald': '〜するとすぐ', 'indem': '〜することによって',
                'um': '〜するために', 'ohne': '〜せずに', 'statt': '〜する代わりに', 'wie': '〜のように', 'so': 'そのように'}
NEGATIONS = {'nicht': '〜ない', 'nie': '決して〜ない', 'niemals': '決して〜ない', 'kein': '〜ない'}
# 話法の助動詞: 原形 → 本動詞に付ける形
MODALS = {'können': 'ことができる', 'müssen': 'なければならない', 'wollen': 'たい', 'sollen': 'べきだ', 'dürfen': 'てもよい',
          'mögen': 'たい', 'möchten': 'たい', 'lassen': 'させる'}
# 訳語を決めておく語 (Wiktionary の最初の語義が外れるもの・日本語に直しにくいもの)
GLOSSES = {
    'sein': 'ある,いる', 'haben': '持つ', 'werden': 'なる', 'gehen': '行く', 'kommen': '来る', 'sehen': '見る',
    'lesen': '読む', 'schreiben': '書く', 'sprechen': '話す', 'sagen': '言う', 'machen': 'する,作る', 'geben': '与える',
    'nehmen': '取る', 'essen': '食べる', 'trinken': '飲む', 'wohnen': '住む', 'leben': '生きる,住む', 'lieben': '愛する',
    'spielen': '遊ぶ,演奏する', 'kaufen': '買う', 'finden': '見つける,思う', 'wissen': '知っている', 'kennen': '知っている',
    'denken': '考える', 'glauben': '信じる,思う', 'arbeiten': '働く', 'lernen': '学ぶ', 'fahren': '行く,運転する',
    'laufen': '走る,歩く', 'stehen': '立っている', 'liegen': '横たわっている,ある', 'sitzen': '座っている', 'bleiben': 'とどまる',
    'heißen': '〜という名前である', 'helfen': '助ける', 'zeigen': '見せる', 'bringen': '持ってくる', 'singen': '歌う',
    'anrufen': '電話する', 'aufstehen': '起きる', 'ankommen': '到着する', 'einkaufen': '買い物をする', 'mitkommen': '一緒に来る',
    'fernsehen': 'テレビを見る', 'verstehen': '理解する', 'beginnen': '始める', 'schlafen': '眠る', 'warten': '待つ',
    'fragen': '尋ねる', 'antworten': '答える', 'hören': '聞く', 'brauchen': '必要とする', 'suchen': '探す', 'öffnen': '開ける',
    'Mann': '男', 'Junge': '少年', 'Bauer': '農夫', 'Dichter': '詩人', 'Feind': '敵', 'Krieg': '戦争', 'Gott': '神',
    'Insel': '島', 'Frau': '女,妻', 'Kind': '子供', 'Mutter': '母', 'Vater': '父', 'Haus': '家', 'Buch': '本',
    'Brief': '手紙', 'Lehrer': '先生', 'Lehrerin': '先生', 'Schule': '学校', 'Stadt': '町', 'Land': '国,田舎',
    'Welt': '世界', 'Zeit': '時間', 'Tag': '日', 'Nacht': '夜', 'Jahr': '年', 'Wasser': '水', 'Brot': 'パン',
    'Hund': '犬', 'Katze': '猫', 'Garten': '庭', 'Wetter': '天気', 'Zucker': '砂糖', 'Freund': '友達', 'Freundin': '友達',
    'Liebe': '愛', 'Herz': '心', 'Auge': '目', 'Hand': '手', 'Kopf': '頭', 'Weg': '道', 'Baum': '木', 'Blume': '花',
    'Himmel': '空', 'Meer': '海', 'Sonne': '太陽', 'Mond': '月', 'Stern': '星', 'Lied': '歌', 'Wort': '言葉',
    'Name': '名前', 'Leben': '生活,命', 'Arbeit': '仕事', 'Geld': 'お金', 'Auto': '車', 'Zug': '列車', 'Tisch': '机',
    'Tür': 'ドア', 'Fenster': '窓', 'Zimmer': '部屋', 'Straße': '通り', 'Mensch': '人間', 'Leute': '人々',
    'gut': '良い', 'schön': '美しい', 'groß': '大きい', 'klein': '小さい', 'neu': '新しい', 'alt': '古い,年老いた',
    'jung': '若い', 'lang': '長い', 'kurz': '短い', 'hoch': '高い', 'schnell': '速い', 'langsam': '遅い', 'viel': '多い',
    'wenig': '少ない', 'warm': '暖かい', 'kalt': '寒い,冷たい', 'heiß': '暑い,熱い', 'rot': '赤い', 'blau': '青い',
    'weiß': '白い', 'schwarz': '黒い', 'grün': '緑の', 'glücklich': '幸せな', 'traurig': '悲しい', 'müde': '疲れた',
    'sehr': 'とても', 'auch': '〜も', 'noch': 'まだ', 'schon': 'もう', 'immer': 'いつも', 'oft': 'しばしば', 'hier': 'ここで',
    'dort': 'そこで', 'heute': '今日', 'gestern': '昨日', 'morgen': '明日', 'jetzt': '今', 'dann': 'それから', 'nur': '〜だけ',
    'gern': '好んで', 'gerne': '好んで', 'wieder': '再び', 'zusammen': '一緒に', 'ja': 'はい', 'nein': 'いいえ',
    'vielleicht': 'たぶん', 'wirklich': '本当に', 'bald': 'まもなく', 'zu': 'あまりに',
    # 童話の語 (グリム童話: 白雪姫 …)
    'Sneewittchen': '白雪姫', 'Schneewittchen': '白雪姫', 'Schneeweißchen': '白雪姫', 'König': '王', 'Königin': '女王',
    'Prinz': '王子', 'Königssohn': '王子', 'Prinzessin': '王女', 'Königstochter': '王女', 'Schnee': '雪', 'Spiegel': '鏡',
    'Zwerg': '小人', 'Jäger': '狩人', 'Wald': '森', 'Stiefmutter': '継母', 'Apfel': 'りんご', 'Sarg': '棺', 'Kamm': '櫛',
    'Gift': '毒', 'Wand': '壁', 'Holz': '木', 'Rahmen': '枠', 'Blut': '血', 'Tropfen': '滴', 'Feder': '羽', 'Nadel': '針',
    'Finger': '指', 'Ebenholz': '黒檀', 'Gemahlin': '妃', 'Gemahl': '夫', 'Schönheit': '美しさ', 'Neid': '妬み',
    'Hochmut': '高慢', 'Unkraut': '雑草', 'Ruhe': '安らぎ', 'Leib': '体', 'Stunde': '時', 'Tochter': '娘', 'Sohn': '息子',
    'Mädchen': '少女', 'Wahrheit': '真実', 'Berg': '山', 'Erz': '鉱石', 'Gold': '金', 'Glas': 'ガラス', 'Teller': '皿',
    'Gabel': 'フォーク', 'Messer': 'ナイフ', 'Löffel': 'スプーン', 'Becher': '杯', 'Bett': 'ベッド', 'Licht': '明かり',
    'Stuhl': '椅子', 'Gemüse': '野菜', 'Wein': 'ワイン', 'Hirsch': '鹿', 'Lunge': '肺', 'Leber': '肝臓', 'Tier': '動物',
    'Krämerin': '小間物売りの女', 'Bäuerin': '農婦', 'Ware': '品物', 'Schnürriemen': '紐', 'Atem': '息', 'Backe': '頬',
    'Pantoffel': '上靴', 'Schuh': '靴', 'Feuer': '火', 'Hochzeit': '結婚式', 'Fest': '祝宴', 'Diener': '召使い', 'Hals': '喉',
    'Stück': 'かけら', 'Sau': '豚', 'Frischling': '子猪', 'Mitleid': '哀れみ', 'Mitleiden': '哀れみ', 'Ordnung': '秩序',
    'Haushalt': '家事', 'Essen': '食事', 'Freude': '喜び', 'Morgen': '朝', 'Abend': '夕方', 'Abends': '夕方に',
    'Morgens': '朝に', 'Winter': '冬', 'Schneeflocke': '雪片', 'Fenster': '窓', 'Kind': '子供', 'Augen': '目',
    'fallen': '落ちる', 'nähen': '縫う', 'stechen': '刺す', 'aussehen': '見える', 'bekommen': '得る', 'sterben': '死ぬ',
    'leiden': '耐える', 'übertreffen': '上回る', 'erblicken': '見つける', 'hassen': '憎む', 'wachsen': '育つ',
    'rufen': '呼ぶ', 'sprechen': '言う', 'antworten': '答える', 'erschrecken': '驚く', 'töten': '殺す', 'umbringen': '殺す',
    'essen': '食べる', 'fressen': '(動物が) 食べる', 'schlafen': '眠る', 'erwachen': '目覚める', 'klopfen': 'たたく',
    'verkaufen': '売る', 'kochen': '料理する', 'waschen': '洗う', 'stricken': '編む', 'tanzen': '踊る',
    'springen': '跳ぶ', 'beißen': 'かじる', 'schenken': '贈る', 'heiraten': '結婚する', 'weinen': '泣く',
    'gefallen': '気に入る', 'erzählen': '語る', 'heißen': '〜という名前である', 'aufblicken': '見上げる',
    'beschauen': '眺める', 'herbeilaufen': '駆け寄る', 'ziehen': '引く', 'tragen': '運ぶ', 'legen': '置く,横たえる',
    'bitten': '頼む', 'warnen': '警告する', 'hüten': '用心する', 'rot': '赤い', 'schön': '美しい', 'stolz': '誇り高い',
    'übermütig': '傲慢な', 'wunderbar': 'すばらしい', 'zufrieden': '満足した', 'klar': '澄んだ', 'gelb': '黄色い',
    'grün': '緑の', 'gottlos': '邪悪な', 'tot': '死んだ', 'lebendig': '生きている', 'arm': 'かわいそうな',
    'schwarzhaarig': '黒髪の', 'feil': '売り物の', 'tausendmal': '千倍', 'mitten': '真ん中に', 'heraus': '外へ',
    'herein': '中へ', 'davon': 'そこから', 'aber': 'しかし', 'einmal': 'あるとき', 'ach': 'ああ', 'ei': 'おや',
    'müssen': 'ねばならない', 'können': 'できる', 'wollen': '欲する', 'sollen': 'べきだ', 'dürfen': '許されている',
    'lassen': 'させる,放っておく', 'Herz': '心', 'Krämerfrau': '小間物売りの女', 'geschwind': '急いで', 'lieb': '愛しい',
    'Abendzeit': '夕方', 'unkenntlich': '見分けのつかない', 'Hexenkunst': '魔法', 'Tür': 'ドア', 'Türe': 'ドア', 'Backen': '頬', 'Bäurin': '農婦', 'Hirschfänger': '狩猟刀', 'hernach': 'その後',
    'einander': '互いに', 'mutterseelenallein': 'ひとりぼっちで', 'schneeweiß': '雪のように白い', 'passen': '合う',
}
NUMBERS_JA = {'eins': '一', 'ein': '一', 'zwei': '二', 'drei': '三', 'vier': '四', 'fünf': '五', 'sechs': '六',
              'sieben': '七', 'acht': '八', 'neun': '九', 'zehn': '十', 'elf': '十一', 'zwölf': '十二', 'zwanzig': '二十',
              'hundert': '百', 'tausend': '千'}
ORDINALS_JA = {'erst': '一番目の', 'zweit': '二番目の', 'dritt': '三番目の', 'viert': '四番目の', 'fünft': '五番目の',
               'sechst': '六番目の', 'siebent': '七番目の', 'siebt': '七番目の', 'acht': '八番目の', 'letzt': '最後の'}


@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    return spacy.load('de_core_news_sm')


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


def cngs(feats, default_gender=None):
    """spaCy の格・数・性 → [(格, 数, 性)]。分からない所はすべての値"""
    cases = [CASES[feats['Case']]] if feats.get('Case') in CASES else list(ALL_CASES)
    numbers = [NUMBERS[feats['Number']]] if feats.get('Number') in NUMBERS else ['sg', 'pl']
    genders = [GENDERS[feats['Gender']]] if feats.get('Gender') in GENDERS else \
        ([default_gender] if default_gender in ('m', 'f', 'n') else ['m', 'f', 'n'])
    return [(c, n, g) for c in cases for n in numbers for g in genders]


# ----------------------------------------------------------------------
# 訳語

@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    """見出し語 → (訳, 'ja' / 'en', 辞書の項目)"""
    from dragoman.core import en_ja
    poses = {'noun': ('noun', 'name'), 'name': ('name', 'noun'), 'verb': ('verb',), 'adj': ('adj', 'participle'),
             'adv': ('adv', 'adj', 'particle')}.get(pos, (pos,))
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
        elif j.endswith('な'):
            out.append(j[:-1] + 'に')
        elif j.endswith('の'):
            out.append(j[:-1] + 'に')
        else:
            out.append(j + 'に' if re.search('[一-龥ぁ-んァ-ン]$', j) else j)
    return ','.join(out)


def auxiliary(lemma):
    """完了の助動詞 (辞書から。sein を取る移動・変化の動詞)"""
    rows = dictionary.lemmas(lemma, 'verb')
    return rows[0]['aux'] if rows and rows[0]['aux'] else 'haben'


def separable(prefix, lemma):
    """分離動詞の見出し (an + rufen → anrufen)。辞書に無ければ None"""
    word = prefix + lemma
    return word if dictionary.lemmas(word, 'verb') or word in GLOSSES else None
