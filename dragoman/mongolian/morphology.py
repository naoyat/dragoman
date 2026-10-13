#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語 (ハルハ方言・キリル文字) の語形: 辞書 (Wiktionary の見出しと名詞の変化表) と規則で、語を語幹と接尾辞に分ける
#
#   номыг → ном + 対格「本を」        охинд → охин + 与位格「少女に」      Монголд → Монгол + 与位格
#   өгсөн → өг- (өгөх) + 過去          уншиж → унш- (унших) + 副動詞 -ж「読んで」
#   явсангүй → яв- (явах) + 過去 + 否定 -гүй「行かなかった」
#
# 接尾辞は母音調和で4通りに変わる (男性母音 а・о・у、女性母音 э・ө・ү。о・ө の語は -оо / -өө 系): 奪格 -аас / -ээс /
# -оос / -өөс。規則で語幹を切り出し、語幹 (+ 母音) + х が辞書の動詞の見出しなら動詞、語幹が名詞の見出しなら名詞
#
import functools
import re

from . import dictionary

VOWELS = 'аэиоуөүяеёюы'
# 名詞の格の接尾辞: 形 → 格 (長いものから試す)
CASE_SUFFIXES = [
    ('ийн', 'Gen'), ('ын', 'Gen'), ('ний', 'Gen'), ('ны', 'Gen'), ('ы', 'Gen'), ('н', 'Gen'),
    ('ийг', 'Acc'), ('ыг', 'Acc'), ('г', 'Acc'),
    ('наас', 'Abl'), ('нээс', 'Abl'), ('ноос', 'Abl'), ('нөөс', 'Abl'),
    ('гаас', 'Abl'), ('гээс', 'Abl'), ('гоос', 'Abl'), ('гөөс', 'Abl'), ('аас', 'Abl'), ('ээс', 'Abl'), ('оос', 'Abl'),
    ('өөс', 'Abl'), ('иас', 'Abl'), ('иос', 'Abl'),
    ('гаар', 'Ins'), ('гээр', 'Ins'), ('гоор', 'Ins'), ('гөөр', 'Ins'), ('аар', 'Ins'), ('ээр', 'Ins'), ('оор', 'Ins'),
    ('өөр', 'Ins'), ('иар', 'Ins'), ('иор', 'Ins'),
    ('тай', 'Com'), ('тэй', 'Com'), ('той', 'Com'),
    ('руу', 'Dir'), ('рүү', 'Dir'), ('луу', 'Dir'), ('лүү', 'Dir'),
    ('нд', 'Dat'), ('д', 'Dat'), ('т', 'Dat'),
]
REFLEXIVE = ('гаа', 'гээ', 'гоо', 'гөө', 'аа', 'ээ', 'оо', 'өө', 'яа', 'ёо', 'еэ')
PLURALS = ('нууд', 'нүүд', 'чууд', 'чүүд', 'ууд', 'үүд', 'нар')
CASE_JA = {'Nom': 'が', 'Gen': 'の', 'Acc': 'を', 'Dat': 'に', 'Abl': 'から', 'Ins': 'で', 'Com': 'と', 'Dir': 'へ'}

# 動詞の語尾: 形 → (種類, 時制 / 働き)。種類: finite (定形)・participle (分詞。連体・名詞化にも)・converb (副動詞)・
# imperative
VERB_ENDINGS = [
    ('аарай', 'imperative', 'polite'), ('ээрэй', 'imperative', 'polite'), ('оорой', 'imperative', 'polite'),
    ('өөрэй', 'imperative', 'polite'),
    ('цгаая', 'imperative', 'hortative'), ('цгээе', 'imperative', 'hortative'), ('ъя', 'imperative', 'hortative'),
    ('ая', 'imperative', 'hortative'), ('ъё', 'imperative', 'hortative'), ('ье', 'imperative', 'hortative'),
    ('лаа', 'finite', 'perfect'), ('лээ', 'finite', 'perfect'), ('лоо', 'finite', 'perfect'), ('лөө', 'finite', 'perfect'),
    ('жээ', 'finite', 'perfect'), ('чээ', 'finite', 'perfect'),
    ('на', 'finite', 'present'), ('нэ', 'finite', 'present'), ('но', 'finite', 'present'), ('нө', 'finite', 'present'),
    ('в', 'finite', 'perfect'),
    ('сан', 'participle', 'perfect'), ('сэн', 'participle', 'perfect'), ('сон', 'participle', 'perfect'),
    ('сөн', 'participle', 'perfect'),
    ('даг', 'participle', 'habitual'), ('дэг', 'participle', 'habitual'), ('дог', 'participle', 'habitual'),
    ('дөг', 'participle', 'habitual'),
    ('х', 'participle', 'future'),
    ('аа', 'participle', 'imperfective'), ('ээ', 'participle', 'imperfective'), ('оо', 'participle', 'imperfective'),
    ('өө', 'participle', 'imperfective'),
    ('гч', 'participle', 'agent'),
    ('аад', 'converb', 'after'), ('ээд', 'converb', 'after'), ('оод', 'converb', 'after'), ('өөд', 'converb', 'after'),
    ('гаад', 'converb', 'after'), ('гээд', 'converb', 'after'), ('гоод', 'converb', 'after'), ('гөөд', 'converb', 'after'),
    ('бал', 'converb', 'if'), ('бэл', 'converb', 'if'), ('бол', 'converb', 'if'), ('бөл', 'converb', 'if'),
    ('вал', 'converb', 'if'), ('вэл', 'converb', 'if'), ('вол', 'converb', 'if'), ('вөл', 'converb', 'if'),
    ('тал', 'converb', 'until'), ('тэл', 'converb', 'until'), ('тол', 'converb', 'until'), ('төл', 'converb', 'until'),
    ('хаар', 'converb', 'purpose'), ('хээр', 'converb', 'purpose'), ('хоор', 'converb', 'purpose'),
    ('хөөр', 'converb', 'purpose'),
    ('саар', 'converb', 'while'), ('сээр', 'converb', 'while'), ('соор', 'converb', 'while'), ('сөөр', 'converb', 'while'),
    ('магц', 'converb', 'as_soon'), ('мэгц', 'converb', 'as_soon'),
    ('ж', 'converb', 'and'), ('ч', 'converb', 'and'), ('н', 'converb', 'manner'),
]
NEGATION_SUFFIX = 'гүй'
# 副動詞 → (日本語の形の種類, 付ける語, 説明)
CONVERBS = {'and': ('te', '', '-ж / -ч「〜して」'), 'after': ('te', '', '-аад「〜してから」'), 'if': ('plain', 'なら', '-вал「〜なら」'),
            'until': ('plain', 'まで', '-тал「〜するまで」'), 'purpose': ('masu', 'に', '-хаар「〜しに」'),
            'while': ('te', 'いて', '-саар「〜しながら」'), 'as_soon': ('plain', 'とすぐ', '-магц「〜するとすぐ」'),
            'manner': ('te', '', '-н「〜して」')}

# 代名詞: 形 → (訳, 人称, 数, 格)
PRONOUNS = {
    'би': ('私', 1, 'sg', 'Nom'), 'намайг': ('私', 1, 'sg', 'Acc'), 'надад': ('私', 1, 'sg', 'Dat'), 'над': ('私', 1, 'sg', 'Dat'),
    'миний': ('私', 1, 'sg', 'Gen'), 'надаас': ('私', 1, 'sg', 'Abl'), 'надтай': ('私', 1, 'sg', 'Com'),
    'чи': ('君', 2, 'sg', 'Nom'), 'чамайг': ('君', 2, 'sg', 'Acc'), 'чамд': ('君', 2, 'sg', 'Dat'), 'чиний': ('君', 2, 'sg', 'Gen'),
    'чамаас': ('君', 2, 'sg', 'Abl'), 'чамтай': ('君', 2, 'sg', 'Com'),
    'та': ('あなた', 2, 'sg', 'Nom'), 'таныг': ('あなた', 2, 'sg', 'Acc'), 'танд': ('あなた', 2, 'sg', 'Dat'),
    'таны': ('あなた', 2, 'sg', 'Gen'), 'танаас': ('あなた', 2, 'sg', 'Abl'), 'тантай': ('あなた', 2, 'sg', 'Com'),
    'тэр': ('彼', 3, 'sg', 'Nom'), 'түүнийг': ('彼', 3, 'sg', 'Acc'), 'түүнд': ('彼', 3, 'sg', 'Dat'),
    'түүний': ('彼', 3, 'sg', 'Gen'), 'түүнээс': ('彼', 3, 'sg', 'Abl'), 'түүнтэй': ('彼', 3, 'sg', 'Com'),
    'бид': ('私たち', 1, 'pl', 'Nom'), 'биднийг': ('私たち', 1, 'pl', 'Acc'), 'бидэнд': ('私たち', 1, 'pl', 'Dat'),
    'бидний': ('私たち', 1, 'pl', 'Gen'), 'биднээс': ('私たち', 1, 'pl', 'Abl'), 'бидэнтэй': ('私たち', 1, 'pl', 'Com'),
    'манай': ('私たち', 1, 'pl', 'Gen'), 'та нар': ('あなたたち', 2, 'pl', 'Nom'),
    'тэд': ('彼ら', 3, 'pl', 'Nom'), 'тэднийг': ('彼ら', 3, 'pl', 'Acc'), 'тэдэнд': ('彼ら', 3, 'pl', 'Dat'),
    'тэдний': ('彼ら', 3, 'pl', 'Gen'),
    'энэ': ('これ', 3, 'sg', 'Nom'), 'үүнийг': ('これ', 3, 'sg', 'Acc'), 'үүнд': ('これ', 3, 'sg', 'Dat'), 'үүний': ('これ', 3, 'sg', 'Gen'),
    'үүнээс': ('これ', 3, 'sg', 'Abl'), 'энийг': ('これ', 3, 'sg', 'Acc'), 'юу': ('何', 3, 'sg', 'Nom'), 'юуг': ('何', 3, 'sg', 'Acc'),
    'хэн': ('誰', 3, 'sg', 'Nom'), 'хэнийг': ('誰', 3, 'sg', 'Acc'), 'хэнд': ('誰', 3, 'sg', 'Dat'), 'хэний': ('誰', 3, 'sg', 'Gen'),
    'хаана': ('どこ', 3, 'sg', 'Dat'), 'өөрөө': ('自分', 3, 'sg', 'Nom'), 'өөрийн': ('自分', 3, 'sg', 'Gen'),
}
DETERMINERS = {'энэ': 'この', 'тэр': 'その', 'ямар': 'どんな', 'бүх': 'すべての', 'зарим': 'いくつかの', 'нэг': 'ある',
               'өөр': '他の', 'олон': '多くの', 'хоёр': '二つの', 'гурав': '三つの', 'гурван': '三つの', 'дөрвөн': '四つの',
               'таван': '五つの', 'хэдэн': 'いくつかの', 'тэдгээр': 'それらの', 'эдгээр': 'これらの', 'миний': '私の',
               'чиний': '君の', 'түүний': '彼の', 'манай': '私たちの', 'таны': 'あなたの'}
# 後置詞: 形 → 訳
POSTPOSITIONS = {'дээр': '〜の上で', 'доор': '〜の下で', 'дотор': '〜の中で', 'өмнө': '〜の前に', 'хойно': '〜の後で',
                 'дараа': '〜の後で', 'тухай': '〜について', 'төлөө': '〜のために', 'хамт': '〜と一緒に', 'шиг': '〜のように',
                 'хүртэл': '〜まで', 'хооронд': '〜の間に', 'дунд': '〜の中で', 'орчим': '〜ごろ', 'гадна': '〜の外で',
                 'дэргэд': '〜のそばで', 'тул': '〜なので', 'учир': '〜なので', 'болохоор': '〜なので', 'үед': '〜の時に',
                 'хойш': '〜以来', 'руу': '〜へ', 'рүү': '〜へ', 'ард': '〜の後ろで', 'урд': '〜の前で', 'дээрээс': '〜の上から'}
CONJUNCTIONS = {'ба': 'そして,〜と', 'болон': '〜と', 'бөгөөд': 'そして', 'буюу': 'または', 'эсвэл': 'または',
                'гэхдээ': 'しかし', 'харин': 'しかし', 'гэвч': 'しかし', 'тэгээд': 'それから', 'учир нь': 'なぜなら',
                'хэрэв': 'もし', 'гэж': '〜と'}
# 小辞: 形 → 働き
PARTICLES = {'уу': 'question', 'үү': 'question', 'юу': 'question', 'юү': 'question', 'вэ': 'question', 'бэ': 'question',
             'нь': 'topic', 'бол': 'topic', 'л': 'emphasis', 'ч': 'also', 'ч гэсэн': 'also', 'юм': 'copula',
             'минь': 'possessive', 'чинь': 'possessive', 'шүү': 'emphasis', 'даа': 'emphasis', 'дээ': 'emphasis',
             'биз': 'question'}
NEGATIONS = {'биш': '〜ではない', 'үгүй': 'いいえ', 'бүү': '〜するな', 'битгий': '〜するな', 'огт': 'まったく'}
GLOSSES = {
    'байх': 'ある,いる', 'болох': 'なる', 'гэх': '言う', 'хийх': 'する,作る', 'явах': '行く', 'ирэх': '来る', 'очих': '行く',
    'үзэх': '見る', 'харах': '見る', 'унших': '読む', 'бичих': '書く', 'идэх': '食べる', 'уух': '飲む', 'өгөх': '与える',
    'авах': '取る,買う', 'мэдэх': '知る', 'хэлэх': '言う', 'ярих': '話す', 'сурах': '学ぶ', 'заах': '教える',
    'амьдрах': '住む,生きる', 'унтах': '眠る', 'суух': '座る,住む', 'босох': '起きる', 'хүлээх': '待つ', 'хайх': '探す',
    'олох': '見つける', 'мартах': '忘れる', 'санах': '思い出す,思う', 'асуух': '尋ねる', 'хариулах': '答える',
    'ажиллах': '働く', 'тоглох': '遊ぶ', 'дуулах': '歌う', 'хайрлах': '愛する', 'дурлах': '恋する', 'гарах': '出る',
    'орох': '入る', 'буцах': '帰る', 'зарах': '売る', 'худалдах': '売る', 'нээх': '開ける', 'хаах': '閉める',
    'хүү': '少年,息子', 'охин': '少女,娘', 'ном': '本', 'гэр': '家', 'хүн': '人', 'эх': '母', 'ээж': '母', 'аав': '父',
    'эцэг': '父', 'ах': '兄', 'эгч': '姉', 'дүү': '弟,妹', 'найз': '友達', 'багш': '先生', 'сурагч': '生徒', 'оюутан': '学生',
    'сургууль': '学校', 'ус': '水', 'хоол': '食事', 'талх': 'パン', 'цай': 'お茶', 'сүү': '牛乳', 'мах': '肉', 'морь': '馬',
    'нохой': '犬', 'муур': '猫', 'заан': '象', 'соёо': '牙', 'хот': '町', 'улс': '国', 'газар': '土地,所', 'тэнгэр': '空',
    'нар': '太陽', 'сар': '月', 'од': '星', 'уул': '山', 'гол': '川', 'нуур': '湖', 'тал': '草原', 'өдөр': '日',
    'шөнө': '夜', 'өглөө': '朝', 'орой': '夕方', 'цаг': '時間', 'жил': '年', 'хэл': '言語', 'үг': '言葉', 'нэр': '名前',
    'захиа': '手紙', 'дэлгүүр': '店', 'шуудан': '郵便局', 'сандал': '椅子', 'ширээ': '机', 'савх': '箸', 'шөл': 'スープ',
    'бэлэг': '贈り物', 'мөнгө': 'お金', 'ажил': '仕事', 'дуу': '歌', 'хайр': '愛', 'зүрх': '心', 'сэтгэл': '心',
    'нүд': '目', 'гар': '手', 'толгой': '頭', 'хүйтэн': '冷たい,寒い', 'халуун': '暑い,熱い', 'сайн': '良い', 'муу': '悪い',
    'том': '大きい', 'жижиг': '小さい', 'шинэ': '新しい', 'хуучин': '古い', 'сайхан': '美しい,素晴らしい', 'гоё': '美しい',
    'хөөрхөн': 'かわいい', 'хурдан': '速い', 'удаан': '遅い', 'өндөр': '高い', 'урт': '長い', 'хэцүү': '難しい',
    'амархан': '易しい', 'их': 'とても,大きい', 'маш': 'とても', 'бага': '少し', 'одоо': '今', 'өнөөдөр': '今日',
    'өчигдөр': '昨日', 'маргааш': '明日', 'үргэлж': 'いつも', 'дахиад': 'また', 'хамт': '一緒に', 'энд': 'ここで',
    'тэнд': 'そこで', 'тийм': 'はい,そのような', 'хэрэгтэй': '必要な', 'Монгол': 'モンゴル', 'Улаанбаатар': 'ウランバートル',
}
NUMBERS = {'нэг': '一', 'хоёр': '二', 'гурав': '三', 'гурван': '三', 'дөрөв': '四', 'дөрвөн': '四', 'тав': '五',
           'таван': '五', 'зургаа': '六', 'долоо': '七', 'найм': '八', 'ес': '九', 'арав': '十', 'зуу': '百', 'мянга': '千'}
ANIMATE = {'хүн', 'хүү', 'охин', 'ах', 'эгч', 'дүү', 'найз', 'багш', 'ээж', 'аав', 'эх', 'эцэг', 'нохой', 'муур', 'морь',
           'заан', 'сурагч', 'оюутан'}
TIME_WORDS = {'өчигдөр', 'өнөөдөр', 'маргааш', 'одоо', 'өглөө', 'орой', 'шөнө', 'үргэлж', 'энд', 'тэнд', 'хаана'}


def lower(word):
    return word.lower()


@functools.lru_cache(maxsize=100000)
def verb_lemma(stem):
    """動詞の語幹 → 辞書の見出し (өг → өгөх、унш → унших、ир → ирэх)。無ければ None"""
    if not stem:
        return None
    candidates = [stem + 'х'] + [stem + v + 'х' for v in 'аэоөиу']
    if stem.endswith('ь'):
        candidates.append(stem[:-1] + 'их')
    if len(stem) > 3 and stem[-2] in 'аэоөу' and stem[-1] not in VOWELS:
        # 語幹の母音の挿入 (амьдар-даг → амьдрах、санаа → …): 挿入された母音を除いて試す
        squeezed = stem[:-2] + stem[-1]
        candidates += [squeezed + v + 'х' for v in 'аэоө']
    for c in candidates:
        if dictionary.lemmas(c, ('verb',)) or c in GLOSSES:
            return c
    return None


@functools.lru_cache(maxsize=100000)
def noun_lemma(stem):
    """名詞の語幹 → 辞書の見出し (охин → охин、гэр → гэр。語幹の脱落母音・н を戻す)"""
    if not stem:
        return None
    candidates = [stem]
    if len(stem) > 2 and stem[-1] not in VOWELS:
        # 脱落した母音を戻す (номын は ном。охины → охин、морины → морь)
        candidates += [stem[:-1] + v + stem[-1] for v in 'аэоөиуү']
    if stem.endswith('и'):
        candidates.append(stem[:-1] + 'ь')
    candidates += [stem + 'н', stem + 'ь']
    for c in candidates:
        if dictionary.lemmas(c, ('noun', 'name', 'adj', 'pronoun', 'num')) or c in GLOSSES or c.capitalize() in GLOSSES:
            return c
    return None


@functools.lru_cache(maxsize=100000)
def analyses(word):
    """語 → [読み (dict)]。読みは kind (noun / verb / pronoun / adj / adv / det / postposition / conj / particle /
    negation)、lemma、名詞なら case・number・reflexive、動詞なら form (finite / participle / converb / imperative)・
    tense・negated・converb・case (名詞化の格)"""
    low = word.lower()
    out = []
    if low in PRONOUNS:
        ja, person, number, case = PRONOUNS[low]
        out.append({'kind': 'pronoun', 'lemma': low, 'ja': ja, 'person': person, 'number': number, 'case': case})
    if low in DETERMINERS:
        out.append({'kind': 'det', 'lemma': low})
    if low in POSTPOSITIONS:
        out.append({'kind': 'postposition', 'lemma': low})
    if low in CONJUNCTIONS:
        out.append({'kind': 'conj', 'lemma': low})
    if low in PARTICLES:
        out.append({'kind': 'particle', 'lemma': low, 'particle': PARTICLES[low]})
    if low in NEGATIONS:
        out.append({'kind': 'negation', 'lemma': low})
    if out:
        return out
    # 辞書の名詞の変化表 (動詞の見出しの形は、名詞化した分詞の格の形: байхдаа「いる時に」、байгааг「いることを」)
    for lemma, pos, case, number, tags in dictionary.forms(low):
        if pos == 'verb':
            reading = {'kind': 'verb', 'lemma': lemma, 'form': 'participle', 'tense': 'future' if 'х' in low[len(lemma) - 2:len(lemma) + 1] else 'imperfective',
                       'negated': False, 'case': case, 'reflexive': 'possessive' in tags, 'ending': ''}
        else:
            reading = {'kind': 'noun', 'lemma': lemma, 'case': case, 'number': number,
                       'reflexive': 'possessive' in tags, 'pos': pos}
        if reading not in out:
            out.append(reading)
    # 見出し語そのもの
    for row in dictionary.lemmas(low):
        kind = {'noun': 'noun', 'name': 'noun', 'pronoun': 'noun', 'num': 'noun', 'adj': 'adj', 'adv': 'adv',
                'verb': None, 'postposition': 'postposition', 'conj': 'conj', 'particle': 'particle'}.get(row['pos'], 'adv')
        if kind is None:
            continue
        reading = {'kind': kind, 'lemma': row['key'], 'case': 'Nom', 'number': 'sg', 'pos': row['pos']}
        if reading not in out:
            out.append(reading)
    if low in GLOSSES and not out and not (low.endswith('х') and verb_lemma(low[:-1])):
        out.append({'kind': 'noun', 'lemma': low, 'case': 'Nom', 'number': 'sg'})
    out += _verb_readings(low)
    if not any(r['kind'] == 'noun' for r in out):
        out += _noun_readings(low)
    return out


def _verb_readings(low):
    out = []
    negated = low.endswith(NEGATION_SUFFIX)
    core = low[:-len(NEGATION_SUFFIX)] if negated else low
    for case_suffix, case in [('', None)] + [(s, c) for s, c in CASE_SUFFIXES if c in ('Acc', 'Dat', 'Abl', 'Gen', 'Ins')]:
        if case_suffix and not core.endswith(case_suffix):
            continue
        body = core[:-len(case_suffix)] if case_suffix else core
        for reflexive in ('',) + REFLEXIVE:
            if reflexive and not body.endswith(reflexive):
                continue
            base = body[:-len(reflexive)] if reflexive else body
            for ending, form, tense in VERB_ENDINGS:
                if not base.endswith(ending) or len(base) - len(ending) < 1:
                    continue
                if case_suffix and form != 'participle':
                    continue   # 名詞化の格の接尾辞は分詞の後ろだけ (уншихыг「読むことを」、байхдаа「いる時に」)
                stem = base[:-len(ending)]
                lemma = verb_lemma(stem) or (verb_lemma(stem[:-1]) if stem and stem[-1] in 'иы' else None)
                if lemma:
                    reading = {'kind': 'verb', 'lemma': lemma, 'form': form, 'tense': tense, 'negated': negated,
                               'case': case, 'reflexive': bool(reflexive), 'ending': ending}
                    if form == 'converb':
                        reading['converb'] = tense
                    if reading not in out:
                        out.append(reading)
    return out


def _noun_readings(low):
    out = []
    for reflexive in ('',) + REFLEXIVE:
        body = low[:-len(reflexive)] if reflexive and low.endswith(reflexive) else (low if not reflexive else None)
        if body is None:
            continue
        for suffix, case in CASE_SUFFIXES + [('', 'Nom')]:
            if suffix and not body.endswith(suffix):
                continue
            stem = body[:-len(suffix)] if suffix else body
            number = 'sg'
            for p in PLURALS:
                if stem.endswith(p) and noun_lemma(stem[:-len(p)]):
                    stem, number = stem[:-len(p)], 'pl'
                    break
            lemma = noun_lemma(stem)
            if lemma and lemma.endswith('х') and (dictionary.lemmas(lemma, ('verb',)) or verb_lemma(lemma[:-1]) == lemma):
                # 未来分詞 -х の名詞化 + 格 (байхдаа「いる時に」、уншихыг「読むことを」)
                out.append({'kind': 'verb', 'lemma': lemma, 'form': 'participle', 'tense': 'future', 'negated': False,
                            'case': case, 'reflexive': bool(reflexive), 'ending': 'х'})
            elif lemma and (suffix or reflexive or number == 'pl'):
                out.append({'kind': 'noun', 'lemma': lemma, 'case': case, 'number': number, 'reflexive': bool(reflexive)})
        if out:
            break
    return out


# ----------------------------------------------------------------------
# 訳語

@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    from dragoman.core import en_ja
    if lemma in GLOSSES:
        return GLOSSES[lemma], 'ja', (dictionary.lemmas(lemma) or [None])[0]
    if lemma.capitalize() in GLOSSES:
        return GLOSSES[lemma.capitalize()], 'ja', None
    poses = {'noun': ('noun', 'name', 'pronoun', 'num'), 'verb': ('verb',), 'adj': ('adj', 'noun'),
             'adv': ('adv', 'adj', 'particle', 'noun')}.get(pos, (pos,))
    rows = dictionary.lemmas(lemma, poses)
    row = rows[0] if rows else None
    if row is None:
        return None, None, None
    if row['pos'] == 'name':
        name = row['en'].split(',')[0].split(':')[0]
        ja = en_ja.translate(name, 'noun')
        return (ja, 'ja', row) if ja else (name, 'en', row)
    ja = en_ja.translate(row['en'], pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2)
    return (ja, 'ja', row) if ja else (row['en'], 'en', row)
