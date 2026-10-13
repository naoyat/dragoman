#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語の語形: 形態素解析器 zeyrek (Zemberek の Python 版) の解析 (見出し語と形態素の列: kitabı → kitap
# Noun A3sg Acc) から、読みを文脈で選び、語の記録 (名詞の格・所有・数、用言の時制・人称・否定・可能・使役・受動、
# 分詞・副動詞・名詞化) にまとめる。格・時制・接続の日本語の形の表もここに置く
#
#   evlerimizden → ev + 複数 + 1人称複数の所有 + 奪格「私たちの家々から」
#   okuduğum kitap → oku- + 過去分詞 + 1人称単数の所有「私が読んだ (本)」
#   gelmeyecekmiş → gel- + 否定 + 未来 + 伝聞「来ないだろうそうだ」
#
import functools
import logging
import re

from . import dictionary

CASES = {'Nom': 'Nom', 'Acc': 'Acc', 'Dat': 'Dat', 'Loc': 'Loc', 'Abl': 'Abl', 'Gen': 'Gen', 'Ins': 'Ins',
         'Equ': 'Equ'}
CASE_JA = {'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Loc': 'で', 'Abl': 'から', 'Gen': 'の', 'Ins': 'で', 'Equ': 'のように'}
PERSONS = {'A1sg': (1, 'sg'), 'A2sg': (2, 'sg'), 'A3sg': (3, 'sg'), 'A1pl': (1, 'pl'), 'A2pl': (2, 'pl'),
           'A3pl': (3, 'pl')}
POSSESSIVES = {'P1sg': '私の', 'P2sg': '君の', 'P3sg': '', 'P1pl': '私たちの', 'P2pl': '君たちの', 'P3pl': '彼らの'}
POSSESSOR_PERSON = {'P1sg': (1, 'sg'), 'P2sg': (2, 'sg'), 'P3sg': (3, 'sg'), 'P1pl': (1, 'pl'), 'P2pl': (2, 'pl'),
                    'P3pl': (3, 'pl')}
TENSES = {'Past': 'perfect', 'Narr': 'perfect', 'Fut': 'future', 'Prog1': 'progressive', 'Prog2': 'progressive',
          'Aor': 'present', 'Pres': 'present'}
# 副動詞・名詞化 (形態素) → (日本語の形の種類, 付ける語, 説明)
CONVERBS = {'AfterDoingSo': ('te', '', '-ıp「〜して」'), 'ByDoingSo': ('te', '', '-arak「〜して」'),
            'When': ('plain', 'と', '-ınca「〜すると」'), 'While': ('te', 'いる間', '-ken「〜している間」'),
            'WithoutHavingDoneSo': ('neg', 'ずに', '-madan「〜せずに」'), 'WithoutBeingAbleToHaveDoneSo': ('neg', 'ずに', '-amadan'),
            'SinceDoingSo': ('te', '以来', '-alı「〜して以来」'), 'AsIf': ('plain', 'かのように', '-casına'),
            'AsLongAs': ('plain', '限り', '-dıkça「〜する限り」'), 'FeelLike': ('masu', 'たそうに', '-ası'),
            'Adamantly': ('plain', 'ばかり', '-asıya'), 'EverSince': ('te', '以来', '-alı')}
NOMINALIZERS = {'Inf1': 'こと', 'Inf2': 'こと', 'Inf3': 'こと', 'PastPart': 'こと', 'FutPart': 'こと',
                'NarrPart': 'こと', 'AorPart': 'こと', 'PresPart': '者'}
PARTICIPLES = {'PastPart': 'past', 'FutPart': 'future', 'PresPart': 'present', 'NarrPart': 'past', 'AorPart': 'present'}

# 代名詞: 見出し → (訳, 人称, 数)
PRONOUNS = {'ben': ('私', 1, 'sg'), 'sen': ('君', 2, 'sg'), 'o': ('彼', 3, 'sg'), 'biz': ('私たち', 1, 'pl'),
            'siz': ('あなた', 2, 'pl'), 'onlar': ('彼ら', 3, 'pl'), 'bu': ('これ', 3, 'sg'), 'şu': ('それ', 3, 'sg'),
            'kendi': ('自分', 3, 'sg'), 'kim': ('誰', 3, 'sg'), 'ne': ('何', 3, 'sg'), 'hepsi': ('すべて', 3, 'pl'),
            'biri': ('誰か', 3, 'sg'), 'birisi': ('誰か', 3, 'sg'), 'hiçbiri': ('誰も', 3, 'sg'), 'burası': ('ここ', 3, 'sg'),
            'orası': ('そこ', 3, 'sg'), 'nere': ('どこ', 3, 'sg')}
DETERMINERS = {'bu': 'この', 'şu': 'その', 'o': 'あの', 'her': '毎〜,どの〜も', 'bir': 'ある', 'hiç': '少しの〜も',
               'bazı': 'いくつかの', 'birkaç': 'いくつかの', 'tüm': 'すべての', 'bütün': 'すべての', 'hangi': 'どの',
               'kaç': 'いくつの', 'çok': '多くの', 'az': '少しの', 'başka': '他の', 'aynı': '同じ'}
# 後置詞: 見出し → (訳, 前の名詞の格)
POSTPOSITIONS = {'için': ('〜のために', None), 'ile': ('〜と,〜で', None), 'gibi': ('〜のように', None),
                 'kadar': ('〜まで,〜ほど', None), 'göre': ('〜によれば,〜に応じて', 'Dat'), 'sonra': ('〜の後で', 'Abl'),
                 'önce': ('〜の前に', 'Abl'), 'beri': ('〜以来', 'Abl'), 'doğru': ('〜へ向かって', 'Dat'),
                 'karşı': ('〜に対して', 'Dat'), 'rağmen': ('〜にもかかわらず', 'Dat'), 'dolayı': ('〜のために', 'Abl'),
                 'başka': ('〜以外に', 'Abl'), 'boyunca': ('〜の間ずっと', None), 'hakkında': ('〜について', None),
                 'üzere': ('〜するために', None), 'ait': ('〜に属する', 'Dat'), 'tarafından': ('〜によって', None)}
CONJUNCTIONS = {'ve': 'そして,〜と', 'veya': 'または', 'ya da': 'または', 'yahut': 'または', 'ama': 'しかし',
                'fakat': 'しかし', 'ancak': 'しかし', 'çünkü': 'なぜなら', 'ki': '〜ということ', 'eğer': 'もし',
                'de': '〜も', 'da': '〜も', 'hem': '〜も', 'ne': '〜も〜ない', 'ise': '〜は', 'yoksa': 'さもなければ',
                'oysa': 'ところが', 'sonra': 'その後'}
# 訳語を決めておく語
GLOSSES = {
    'olmak': 'なる,ある', 'etmek': 'する', 'yapmak': 'する,作る', 'gitmek': '行く', 'gelmek': '来る', 'görmek': '見る',
    'okumak': '読む', 'yazmak': '書く', 'yemek': '食べる', 'içmek': '飲む', 'almak': '取る,買う', 'vermek': '与える',
    'demek': '言う', 'söylemek': '言う', 'konuşmak': '話す', 'bilmek': '知る', 'sevmek': '愛する,好む',
    'istemek': '望む', 'bakmak': '見る', 'çalışmak': '働く,勉強する', 'oturmak': '座る,住む', 'yaşamak': '生きる,住む',
    'uyumak': '眠る', 'koşmak': '走る', 'düşünmek': '考える', 'anlamak': '理解する', 'beklemek': '待つ',
    'sormak': '尋ねる', 'açmak': '開ける', 'kapamak': '閉める', 'kapatmak': '閉める', 'bulmak': '見つける',
    'çıkmak': '出る', 'girmek': '入る', 'dönmek': '戻る', 'kalmak': 'とどまる,残る', 'başlamak': '始める',
    'bitmek': '終わる', 'öğrenmek': '学ぶ', 'öğretmek': '教える', 'satmak': '売る', 'göstermek': '見せる',
    'ev': '家', 'kitap': '本', 'çocuk': '子供', 'adam': '男', 'kadın': '女', 'kız': '娘,少女', 'oğlan': '少年',
    'oğul': '息子', 'anne': '母', 'baba': '父', 'arkadaş': '友達', 'öğretmen': '先生', 'öğrenci': '学生', 'okul': '学校',
    'su': '水', 'ekmek': 'パン', 'yemek_noun': '食事', 'masa': '机', 'kapı': 'ドア', 'pencere': '窓', 'oda': '部屋',
    'şehir': '町', 'köy': '村', 'ülke': '国', 'dünya': '世界', 'gün': '日', 'gece': '夜', 'sabah': '朝', 'akşam': '夕方',
    'yıl': '年', 'zaman': '時', 'saat': '時間,時計', 'yol': '道', 'deniz': '海', 'dağ': '山', 'ağaç': '木', 'çiçek': '花',
    'kedi': '猫', 'köpek': '犬', 'kuş': '鳥', 'para': 'お金', 'iş': '仕事', 'dil': '言語,舌', 'söz': '言葉', 'ad': '名前',
    'isim': '名前', 'el': '手', 'göz': '目', 'kalp': '心', 'gönül': '心', 'aşk': '愛', 'sevgi': '愛', 'hayat': '人生',
    'insan': '人間', 'kişi': '人', 'halk': '人々', 'Türkçe': 'トルコ語', 'Türkiye': 'トルコ', 'İstanbul': 'イスタンブール',
    'Ankara': 'アンカラ', 'güzel': '美しい', 'büyük': '大きい', 'küçük': '小さい', 'iyi': '良い', 'kötü': '悪い',
    'yeni': '新しい', 'eski': '古い', 'uzun': '長い', 'kısa': '短い', 'sıcak': '暑い,熱い', 'soğuk': '寒い,冷たい',
    'mutlu': '幸せな', 'hızlı': '速い', 'yavaş': '遅い', 'çok': 'とても,多い', 'az': '少ない', 'daha': 'もっと',
    'en': '最も', 'şimdi': '今', 'bugün': '今日', 'dün': '昨日', 'yarın': '明日', 'her zaman': 'いつも',
    'hep': 'いつも', 'artık': 'もう', 'hâlâ': 'まだ', 'henüz': 'まだ', 'yine': 'また', 'tekrar': '再び', 'burada': 'ここで',
    'orada': 'そこで', 'mektup': '手紙', 'kardeş': '兄弟', 'içeri': '中へ', 'dışarı': '外へ', 'film': '映画',
    'evet': 'はい', 'hayır': 'いいえ', 'belki': 'たぶん', 'gerçekten': '本当に', 'birlikte': '一緒に',
}
# 助詞の無いときに副詞として読む時の名詞・場所の語
TIME_WORDS = {'dün', 'bugün', 'yarın', 'akşam', 'sabah', 'gece', 'şimdi', 'öğle', 'sonra', 'önce', 'içeri', 'dışarı',
              'yukarı', 'aşağı', 'geri', 'ileri', 'burada', 'orada', 'şurada'}
NUMBERS = {'bir': '一', 'iki': '二', 'üç': '三', 'dört': '四', 'beş': '五', 'altı': '六', 'yedi': '七', 'sekiz': '八',
           'dokuz': '九', 'on': '十', 'yüz': '百', 'bin': '千'}
# 固有名詞の後ろの格の接尾辞 (アポストロフィの後ろ: Ali'nin、İstanbul'da)
NAME_SUFFIXES = [('nın', 'Gen'), ('nin', 'Gen'), ('nun', 'Gen'), ('nün', 'Gen'), ('ın', 'Gen'), ('in', 'Gen'),
                 ('un', 'Gen'), ('ün', 'Gen'), ('dan', 'Abl'), ('den', 'Abl'), ('tan', 'Abl'), ('ten', 'Abl'),
                 ('da', 'Loc'), ('de', 'Loc'), ('ta', 'Loc'), ('te', 'Loc'), ('ya', 'Dat'), ('ye', 'Dat'), ('a', 'Dat'),
                 ('e', 'Dat'), ('yı', 'Acc'), ('yi', 'Acc'), ('yu', 'Acc'), ('yü', 'Acc'), ('ı', 'Acc'), ('i', 'Acc'),
                 ('u', 'Acc'), ('ü', 'Acc'), ('yla', 'Ins'), ('yle', 'Ins'), ('la', 'Ins'), ('le', 'Ins')]


@functools.lru_cache(maxsize=1)
def analyzer():
    logging.getLogger('zeyrek').setLevel(logging.ERROR)
    import zeyrek
    for name in ('zeyrek', 'zeyrek.morphotactics', 'zeyrek.analyzer', 'zeyrek.rulebasedanalyzer'):
        logging.getLogger(name).setLevel(logging.ERROR)
    return zeyrek.MorphAnalyzer()


def available():
    try:
        analyzer()
    except ImportError:
        return False
    return dictionary.available()


@functools.lru_cache(maxsize=100000)
def analyses(word):
    """語 → [(見出し語, 品詞, 形態素のタプル)] (zeyrek の解析。重複を除く)"""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        result = analyzer().analyze(word)
    out = []
    for p in (result[0] if result else []):
        key = (p.lemma, p.pos, tuple(p.morphemes))
        if key not in out:
            out.append(key)
    return out


# ----------------------------------------------------------------------
# 訳語

@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    """見出し語 → (訳, 'ja' / 'en', 辞書の項目)"""
    from dragoman.core import en_ja
    if pos == 'noun' and lemma + '_noun' in GLOSSES:
        return GLOSSES[lemma + '_noun'], 'ja', None
    poses = {'noun': ('noun', 'name', 'pronoun', 'num'), 'name': ('name', 'noun'), 'verb': ('verb',),
             'adj': ('adj', 'noun'), 'adv': ('adv', 'adj', 'particle', 'conj')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if lemma in GLOSSES:
        return GLOSSES[lemma], 'ja', row
    if row is None:
        return None, None, None
    if row['pos'] == 'name':
        name = row['en'].split(',')[0]
        ja = en_ja.translate(name, 'noun')
        return (ja, 'ja', row) if ja else (row['word'], 'en', row)
    ja = en_ja.translate(row['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
    return (ja, 'ja', row) if ja else (row['en'], 'en', row)


def name_suffix(word):
    """固有名詞 + アポストロフィ + 格の接尾辞 → (名前, 格)。違えば None"""
    m = re.match(r"^(.+?)['’](\w+)$", word)
    if not m:
        return None
    for suffix, case in NAME_SUFFIXES:
        if m.group(2) == suffix:
            return m.group(1), case
    return m.group(1), 'Nom'
