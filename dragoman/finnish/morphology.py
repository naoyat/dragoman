#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フィンランド語の語形: spaCy のフィンランド語モデル (fi_core_news_sm) で文脈の中の品詞・原形・格 (15格)・数・人称・
# 時制・所有の接尾辞と依存関係を付ける。格の日本語の助詞、機能語の訳はここの表、内容語の訳は辞書 (Wiktionary の英語の
# 語義を core/en_ja.py で日本語に直したもの)
#
import functools

from . import dictionary

# spaCy (UD) の格 → この解析器の格の名前と既定の助詞
CASES = {'Nom': 'Nom', 'Gen': 'Gen', 'Par': 'Par', 'Acc': 'Acc', 'Ine': 'Ine', 'Ela': 'Ela', 'Ill': 'Ill',
         'Ade': 'Ade', 'Abl': 'Abl', 'All': 'All', 'Ess': 'Ess', 'Tra': 'Tra', 'Abe': 'Abe', 'Com': 'Com', 'Ins': 'Ins'}
CASE_JA = {'Nom': 'が', 'Gen': 'の', 'Par': 'を', 'Acc': 'を', 'Ine': 'で', 'Ela': 'から', 'Ill': 'へ',
           'Ade': 'で', 'Abl': 'から', 'All': 'に', 'Ess': 'として', 'Tra': 'に', 'Abe': 'なしで', 'Com': 'と共に',
           'Ins': 'で'}
CASE_NAMES = {'Nom': '主格', 'Gen': '属格', 'Par': '分格', 'Acc': '対格', 'Ine': '内格「〜の中で」', 'Ela': '出格「〜の中から」',
              'Ill': '入格「〜の中へ」', 'Ade': '所格「〜で、〜の上で」', 'Abl': '離格「〜から」', 'All': '向格「〜に、〜へ」',
              'Ess': '様格「〜として」', 'Tra': '変格「〜に (なる)」', 'Abe': '欠格「〜なしで」', 'Com': '共格「〜と共に」',
              'Ins': '具格「〜で」'}
NUMBERS = {'Sing': 'sg', 'Plur': 'pl'}
PRONOUNS = {'minä': ('私', 1, 'sg'), 'sinä': ('君', 2, 'sg'), 'hän': ('彼', 3, 'sg'), 'me': ('私たち', 1, 'pl'),
            'te': ('あなたたち', 2, 'pl'), 'he': ('彼ら', 3, 'pl'), 'se': ('それ', 3, 'sg'), 'ne': ('それら', 3, 'pl'),
            'tämä': ('これ', 3, 'sg'), 'tuo': ('あれ', 3, 'sg'), 'nämä': ('これら', 3, 'pl'), 'kuka': ('誰', 3, 'sg'),
            'mikä': ('何', 3, 'sg'), 'joku': ('誰か', 3, 'sg'), 'jokin': ('何か', 3, 'sg'), 'itse': ('自分', 3, 'sg'),
            'kaikki': ('すべて', 3, 'pl'), 'mä': ('私', 1, 'sg'), 'sä': ('君', 2, 'sg')}
DETERMINERS = {'tämä': 'この', 'tuo': 'あの', 'se': 'その', 'nämä': 'これらの', 'nuo': 'あれらの', 'ne': 'それらの',
               'kaikki': 'すべての', 'jokainen': 'どの〜も', 'joku': 'ある', 'jokin': 'ある', 'mikä': 'どの', 'monta': '多くの',
               'moni': '多くの', 'muu': '他の', 'toinen': '他の,二番目の', 'sama': '同じ'}
POSSESSORS = {('1', 'Sing'): '私の', ('2', 'Sing'): '君の', ('3', 'Sing'): '彼の', ('1', 'Plur'): '私たちの',
              ('2', 'Plur'): 'あなたたちの', ('3', 'Plur'): '彼らの'}
ADPOSITIONS = {'kanssa': '〜と一緒に', 'jälkeen': '〜の後で', 'ennen': '〜の前に', 'aikana': '〜の間に', 'takia': '〜のために',
               'vuoksi': '〜のために', 'kautta': '〜を通って', 'mukaan': '〜によれば', 'luona': '〜のところで',
               'luokse': '〜のところへ', 'päällä': '〜の上で', 'alla': '〜の下で', 'edessä': '〜の前で', 'takana': '〜の後ろで',
               'vieressä': '〜の横で', 'sisällä': '〜の中で', 'ulkopuolella': '〜の外で', 'kohti': '〜に向かって',
               'ilman': '〜なしで', 'yli': '〜を越えて', 'ympäri': '〜の周りを', 'lähellä': '〜の近くで', 'välillä': '〜の間で',
               'puolesta': '〜のために', 'avulla': '〜の助けで', 'sijaan': '〜の代わりに', 'asti': '〜まで', 'saakka': '〜まで',
               'mennessä': '〜までに', 'varten': '〜のために', 'lisäksi': '〜に加えて', 'myötä': '〜とともに', 'läpi': '〜を通して'}
CONJUNCTIONS = {'ja': 'そして,〜と', 'sekä': '〜と', 'tai': 'または', 'vai': 'それとも', 'mutta': 'しかし', 'vaan': 'ではなく',
                'että': '〜ということ', 'koska': '〜なので', 'kun': '〜するとき', 'jos': '〜なら', 'vaikka': '〜けれども',
                'jotta': '〜するために', 'kuin': '〜より,〜のように', 'kunnes': '〜するまで', 'ennen kuin': '〜する前に',
                'sillä': 'というのは', 'eli': 'すなわち', 'joten': 'だから'}
GLOSSES = {
    'olla': 'ある,いる', 'tulla': '来る,なる', 'mennä': '行く', 'nähdä': '見る', 'katsoa': '見る', 'lukea': '読む',
    'kirjoittaa': '書く', 'syödä': '食べる', 'juoda': '飲む', 'antaa': '与える', 'ottaa': '取る', 'saada': '得る',
    'tehdä': 'する,作る', 'sanoa': '言う', 'puhua': '話す', 'tietää': '知る', 'tuntea': '知る,感じる', 'rakastaa': '愛する',
    'pitää': '好む,保つ', 'haluta': '望む', 'voida': 'できる', 'täytyä': 'ねばならない', 'asua': '住む', 'elää': '生きる',
    'nukkua': '眠る', 'laulaa': '歌う', 'tanssia': '踊る', 'opiskella': '勉強する', 'oppia': '学ぶ', 'opettaa': '教える',
    'tehdä työtä': '働く', 'työskennellä': '働く', 'ostaa': '買う', 'myydä': '売る', 'odottaa': '待つ', 'etsiä': '探す',
    'löytää': '見つける', 'kysyä': '尋ねる', 'vastata': '答える', 'ajatella': '考える', 'ymmärtää': '理解する',
    'avata': '開ける', 'sulkea': '閉める', 'istua': '座る', 'seistä': '立つ', 'kävellä': '歩く', 'juosta': '走る',
    'poika': '少年,息子', 'tyttö': '少女,娘', 'mies': '男', 'nainen': '女', 'lapsi': '子供', 'äiti': '母', 'isä': '父',
    'veli': '兄弟', 'sisko': '姉妹', 'sisar': '姉妹', 'ystävä': '友達', 'opettaja': '先生', 'oppilas': '生徒',
    'opiskelija': '学生', 'kirja': '本', 'koulu': '学校', 'talo': '家', 'koti': '家', 'huone': '部屋', 'pöytä': '机',
    'tuoli': '椅子', 'ovi': 'ドア', 'ikkuna': '窓', 'kaupunki': '町', 'maa': '国,土地', 'maailma': '世界', 'järvi': '湖',
    'meri': '海', 'metsä': '森', 'puu': '木', 'kukka': '花', 'kissa': '猫', 'koira': '犬', 'lintu': '鳥', 'vesi': '水',
    'leipä': 'パン', 'kahvi': 'コーヒー', 'ruoka': '食べ物', 'päivä': '日', 'yö': '夜', 'aamu': '朝', 'ilta': '夕方',
    'vuosi': '年', 'aika': '時間', 'kieli': '言語', 'sana': '言葉', 'nimi': '名前', 'kirje': '手紙', 'juna': '列車',
    'auto': '車', 'raha': 'お金', 'työ': '仕事', 'laulu': '歌', 'rakkaus': '愛', 'sydän': '心', 'silmä': '目',
    'käsi': '手', 'suomi': 'フィンランド語', 'Suomi': 'フィンランド', 'Helsinki': 'ヘルシンキ', 'hyvä': '良い',
    'huono': '悪い', 'iso': '大きい', 'suuri': '大きい', 'pieni': '小さい', 'uusi': '新しい', 'vanha': '古い,年老いた',
    'nuori': '若い', 'kaunis': '美しい', 'pitkä': '長い', 'lyhyt': '短い', 'kylmä': '寒い,冷たい', 'kuuma': '暑い,熱い',
    'lämmin': '暖かい', 'iloinen': '嬉しい', 'surullinen': '悲しい', 'nopea': '速い', 'hidas': '遅い',
    'eilen': '昨日', 'tänään': '今日', 'huomenna': '明日', 'nyt': '今', 'aina': 'いつも', 'usein': 'しばしば',
    'jo': 'もう', 'vielä': 'まだ', 'myös': '〜も', 'hyvin': 'よく,とても', 'paljon': 'たくさん', 'vähän': '少し',
    'täällä': 'ここで', 'siellä': 'そこで', 'kotiin': '家へ', 'kotona': '家で', 'ei': '〜ない', 'kyllä': 'はい',
    'yksi': '一', 'kaksi': '二', 'kolme': '三', 'neljä': '四', 'viisi': '五', 'kuusi': '六', 'seitsemän': '七',
    'kahdeksan': '八', 'yhdeksän': '九', 'kymmenen': '十', 'sata': '百', 'tuhat': '千', 'omena': 'りんご', 'talo': '家',
}


@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    return spacy.load('fi_core_news_sm')


def available():
    try:
        nlp()
    except (ImportError, OSError):
        return False
    return dictionary.available()


def parse(surfaces):
    from spacy.tokens import Doc
    model = nlp()
    return model(Doc(model.vocab, words=list(surfaces)))


def morph(token):
    return {k: v for f in str(token.morph).split('|') if '=' in f for k, v in [f.split('=', 1)]}


@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    from dragoman.core import en_ja
    if lemma in GLOSSES:
        return GLOSSES[lemma], 'ja', None
    poses = {'noun': ('noun', 'name', 'pronoun', 'num'), 'name': ('name', 'noun'), 'verb': ('verb',),
             'adj': ('adj', 'noun'), 'adv': ('adv', 'adj', 'particle', 'conj')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if row is None:
        return None, None, None
    if row['pos'] == 'name':
        name = row['en'].split(',')[0]
        ja = en_ja.translate(name, 'noun')
        return (ja, 'ja', row) if ja else (row['word'], 'en', row)
    ja = en_ja.translate(row['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
    return (ja, 'ja', row) if ja else (row['en'], 'en', row)
