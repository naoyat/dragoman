#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語の語形: spaCy の英語モデル (en_core_web_sm) で文脈の中の品詞 (Penn Treebank)・原形・依存関係を付け、語の項目
# (dict) にする。機能語 (代名詞・限定詞・前置詞・接続詞・助動詞) の訳はここの表、内容語の訳は英和の表 (core/en_ja.py。
# 日本語版 Wiktionary の英語の項目から)。基本の語は GLOSSES で決めておく
#
import functools

from dragoman.core import en_ja

NUMBERS = {'Sing': 'sg', 'Plur': 'pl'}
ALL_CASES = ('Nom', 'Acc', 'Dat', 'Gen')

# 人称代名詞: 語形 → (訳, 人称, 数, 格)
PRONOUNS = {
    'i': ('私', 1, 'sg', ('Nom',)), 'me': ('私', 1, 'sg', ('Acc', 'Dat', 'Gen')), 'you': ('あなた', 2, 'sg', ALL_CASES),
    'he': ('彼', 3, 'sg', ('Nom',)), 'him': ('彼', 3, 'sg', ('Acc', 'Dat', 'Gen')), 'she': ('彼女', 3, 'sg', ('Nom',)),
    'her': ('彼女', 3, 'sg', ('Acc', 'Dat', 'Gen')), 'it': ('それ', 3, 'sg', ALL_CASES), 'we': ('私たち', 1, 'pl', ('Nom',)),
    'us': ('私たち', 1, 'pl', ('Acc', 'Dat', 'Gen')), 'they': ('彼ら', 3, 'pl', ('Nom',)),
    'them': ('彼ら', 3, 'pl', ('Acc', 'Dat', 'Gen')), 'myself': ('自分', 1, 'sg', ('Acc', 'Dat', 'Gen')),
    'yourself': ('自分', 2, 'sg', ('Acc', 'Dat', 'Gen')), 'himself': ('自分', 3, 'sg', ('Acc', 'Dat', 'Gen')),
    'herself': ('自分', 3, 'sg', ('Acc', 'Dat', 'Gen')), 'itself': ('それ自身', 3, 'sg', ('Acc', 'Dat', 'Gen')),
    'ourselves': ('自分たち', 1, 'pl', ('Acc', 'Dat', 'Gen')), 'themselves': ('自分たち', 3, 'pl', ('Acc', 'Dat', 'Gen')),
    'this': ('これ', 3, 'sg', ALL_CASES), 'that': ('それ', 3, 'sg', ALL_CASES), 'these': ('これら', 3, 'pl', ALL_CASES),
    'those': ('それら', 3, 'pl', ALL_CASES), 'who': ('誰', 3, 'sg', ALL_CASES), 'whom': ('誰', 3, 'sg', ('Acc', 'Dat', 'Gen')),
    'what': ('何', 3, 'sg', ALL_CASES), 'which': ('どれ', 3, 'sg', ALL_CASES), 'someone': ('誰か', 3, 'sg', ALL_CASES),
    'somebody': ('誰か', 3, 'sg', ALL_CASES), 'something': ('何か', 3, 'sg', ALL_CASES), 'nothing': ('何も', 3, 'sg', ALL_CASES),
    'nobody': ('誰も', 3, 'sg', ALL_CASES), 'everyone': ('みんな', 3, 'sg', ALL_CASES), 'everybody': ('みんな', 3, 'sg', ALL_CASES),
    'everything': ('すべて', 3, 'sg', ALL_CASES), 'anyone': ('誰か', 3, 'sg', ALL_CASES), 'anything': ('何か', 3, 'sg', ALL_CASES),
    'all': ('すべて', 3, 'pl', ALL_CASES), 'one': ('もの', 3, 'sg', ALL_CASES), 'mine': ('私のもの', 3, 'sg', ALL_CASES),
    'yours': ('あなたのもの', 3, 'sg', ALL_CASES), 'his': ('彼のもの', 3, 'sg', ALL_CASES), 'hers': ('彼女のもの', 3, 'sg', ALL_CASES),
    'ours': ('私たちのもの', 3, 'sg', ALL_CASES), 'theirs': ('彼らのもの', 3, 'sg', ALL_CASES),
}
# 限定詞・所有限定詞: 語形 → 訳 (冠詞は訳さない)
DETERMINERS = {'the': '', 'a': '', 'an': '', 'this': 'この', 'that': 'その', 'these': 'これらの', 'those': 'それらの',
               'my': '私の', 'your': 'あなたの', 'his': '彼の', 'her': '彼女の', 'its': 'その', 'our': '私たちの',
               'their': '彼らの', 'every': 'すべての', 'each': 'それぞれの', 'all': 'すべての', 'some': 'いくつかの',
               'any': 'どんな', 'many': '多くの', 'much': '多くの', 'few': 'わずかの', 'several': 'いくつかの',
               'both': '両方の', 'another': '別の', 'other': '他の', 'which': 'どの', 'what': '何の', 'whose': '誰の',
               'such': 'そのような', 'no': ''}
ARTICLES = ('the', 'a', 'an')
PREPOSITIONS = {
    'in': '〜で,〜の中で', 'on': '〜の上で,〜に', 'at': '〜で,〜に', 'to': '〜へ,〜に', 'from': '〜から', 'of': '〜の',
    'with': '〜と,〜で', 'without': '〜なしで', 'for': '〜のために', 'by': '〜によって,〜のそばで', 'about': '〜について',
    'into': '〜の中へ', 'onto': '〜の上へ', 'over': '〜の上に,〜を越えて', 'under': '〜の下で', 'after': '〜の後で',
    'before': '〜の前に', 'behind': '〜の後ろに', 'between': '〜の間に', 'among': '〜の中で', 'through': '〜を通って',
    'during': '〜の間', 'since': '〜以来', 'until': '〜まで', 'till': '〜まで', 'against': '〜に対して',
    'near': '〜の近くに', 'across': '〜を横切って', 'along': '〜に沿って', 'around': '〜の周りに', 'toward': '〜の方へ',
    'towards': '〜の方へ', 'like': '〜のように', 'as': '〜として', 'than': '〜より', 'above': '〜の上に',
    'below': '〜の下に', 'beside': '〜のそばに', 'beyond': '〜の向こうに', 'inside': '〜の中に', 'outside': '〜の外に',
    'within': '〜以内に', 'up': '〜の上へ', 'down': '〜の下へ', 'off': '〜から離れて', 'out': '〜から外へ',
    'per': '〜あたり', 'despite': '〜にもかかわらず', 'except': '〜を除いて', 'upon': '〜の上に',
}
CONJUNCTIONS = {'and': 'そして,〜と', 'or': 'または', 'but': 'しかし', 'so': 'だから', 'nor': '〜も〜ない',
                'yet': 'しかし', 'because': '〜なので', 'if': '〜なら', 'when': '〜するとき', 'while': '〜する間に',
                'although': '〜にもかかわらず', 'though': '〜けれども', 'that': '〜ということ', 'whether': '〜かどうか',
                'before': '〜する前に', 'after': '〜した後で', 'since': '〜して以来', 'until': '〜するまで',
                'unless': '〜でなければ', 'as': '〜なので,〜のように', 'once': 'いったん〜すると', 'than': '〜より'}
# 副詞節の従属接続詞: 語形 → (節の後ろに付ける形, 節の動詞の時制 / None)
SUBORDINATORS = {'when': ('とき', None), 'whenever': ('ときはいつも', None), 'because': ('ので', None),
                 'since': ('ので', None), 'as': ('ので', None), 'if': ('なら', None), 'although': ('けれども', None),
                 'though': ('けれども', None), 'while': ('間に', None), 'before': ('前に', 'present'),
                 'after': ('後で', 'perfect'), 'until': ('まで', 'present'), 'till': ('まで', 'present'),
                 'once': ('と', 'present'), 'so': ('ので', None), 'unless': ('のでなければ', None),
                 'whereas': ('一方で', None), 'wherever': ('ところならどこでも', None)}
NEGATIONS = {'not': '〜ない', "n't": '〜ない', 'never': '決して〜ない', 'no': '〜ない'}
QUESTION_ADVERBS = {'where': 'どこで', 'when': 'いつ', 'why': 'なぜ', 'how': 'どのように'}
# 法の助動詞 (MD): 語形 → (本動詞に付ける形, 時制)
MODALS = {'can': ('ことができる', 'present'), 'could': ('ことができる', 'perfect'), 'must': ('なければならない', 'present'),
          'should': ('べきだ', 'present'), 'may': ('てもよい', 'present'), 'might': ('かもしれない', 'present'),
          'will': ('', 'future'), "'ll": ('', 'future'), 'shall': ('', 'future'), 'would': ('だろう', 'present'),
          "'d": ('だろう', 'present'), 'ca': ('ことができる', 'present'), 'wo': ('', 'future')}
# 訳語を決めておく語 (英和の表の最初の訳語が外れるもの)
GLOSSES = {
    ('be', 'verb'): 'ある,いる', ('have', 'verb'): '持つ', ('do', 'verb'): 'する', ('go', 'verb'): '行く',
    ('get', 'verb'): '得る', ('make', 'verb'): '作る', ('take', 'verb'): '取る', ('see', 'verb'): '見る',
    ('come', 'verb'): '来る', ('know', 'verb'): '知っている', ('give', 'verb'): '与える', ('like', 'verb'): '好む',
    ('love', 'verb'): '愛する', ('want', 'verb'): '欲しい', ('live', 'verb'): '住む', ('play', 'verb'): '遊ぶ,演奏する',
    ('study', 'verb'): '勉強する', ('speak', 'verb'): '話す', ('talk', 'verb'): '話す', ('think', 'verb'): '思う,考える',
    ('look', 'verb'): '見る', ('say', 'verb'): '言う', ('tell', 'verb'): '話す,伝える', ('put', 'verb'): '置く',
    ('leave', 'verb'): '去る', ('find', 'verb'): '見つける', ('show', 'verb'): '見せる', ('meet', 'verb'): '会う',
    ('man', 'noun'): '男', ('woman', 'noun'): '女', ('boy', 'noun'): '少年', ('girl', 'noun'): '少女',
    ('cat', 'noun'): '猫', ('dog', 'noun'): '犬', ('day', 'noun'): '日', ('time', 'noun'): '時間',
    ('people', 'noun'): '人々', ('station', 'noun'): '駅', ('garden', 'noun'): '庭',
    ('very', 'adv'): 'とても', ('ever', 'adv'): '今までに', ('here', 'adv'): 'ここで', ('here', 'adv'): 'ここで', ('there', 'adv'): 'そこで', ('now', 'adv'): '今',
    ('today', 'noun'): '今日', ('tomorrow', 'noun'): '明日', ('yesterday', 'noun'): '昨日', ('also', 'adv'): '〜も',
    ('always', 'adv'): 'いつも', ('often', 'adv'): 'しばしば', ('again', 'adv'): '再び', ('only', 'adv'): '〜だけ',
    ('well', 'adv'): '上手に', ('yes', 'adv'): 'はい', ('home', 'adv'): '家に', ('together', 'adv'): '一緒に',
    ('good', 'adj'): '良い', ('new', 'adj'): '新しい', ('old', 'adj'): '古い,年老いた', ('big', 'adj'): '大きい',
    ('small', 'adj'): '小さい', ('happy', 'adj'): '幸せな', ('beautiful', 'adj'): '美しい',
}
NUMBERS_JA = {'one': '一', 'two': '二', 'three': '三', 'four': '四', 'five': '五', 'six': '六', 'seven': '七',
              'eight': '八', 'nine': '九', 'ten': '十', 'hundred': '百', 'thousand': '千'}


@functools.lru_cache(maxsize=1)
def nlp():
    import spacy
    return spacy.load('en_core_web_sm')


def available():
    try:
        nlp()
    except (ImportError, OSError):
        return False
    return en_ja.available()


def tokenize(text):
    return [t.text for t in nlp().tokenizer(text) if not t.is_space]


def parse(surfaces):
    """語の列 → spaCy の Doc (語の切れ目はそのまま)"""
    from spacy.tokens import Doc
    model = nlp()
    return model(Doc(model.vocab, words=list(surfaces)))


def morph(token):
    return {k: v for f in str(token.morph).split('|') if '=' in f for k, v in [f.split('=', 1)]}


def cngs(cases, number=None):
    """[(格, 数, 性)]。英語に文法上の性は無いので性はすべての値"""
    numbers = [number] if number in ('sg', 'pl') else ['sg', 'pl']
    return [(c, n, g) for c in cases for n in numbers for g in ('m', 'f', 'n')]


@functools.lru_cache(maxsize=50000)
def gloss(lemma, pos):
    """見出し語 → (訳, 'ja' / 'en')。英和の表に無ければ英語のまま"""
    key = (lemma.lower(), pos)
    if key in GLOSSES:
        return GLOSSES[key], 'ja'
    for p in ((pos, 'name') if pos == 'noun' else ('name', 'noun') if pos == 'name' else (pos,)):
        found = en_ja.lookup(lemma, p) or (en_ja.lookup(lemma.lower(), p) if lemma != lemma.lower() else [])
        if found:
            return ','.join(found[:2]), 'ja'
    return None, None


def adverbial(ja):
    """形容詞の訳 → 副詞の形 (速い → 速く、静かな → 静かに)"""
    out = []
    for j in ja.split(','):
        if j.endswith('い') and not j.endswith(('きれい', 'きらい')):
            out.append(j[:-1] + 'く')
        elif j.endswith(('な', 'の')):
            out.append(j[:-1] + 'に')
        else:
            out.append(j)
    return ','.join(out)
