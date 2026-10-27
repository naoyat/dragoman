#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 中国語 (普通話) の文の解析
#
# 語に切り分け (chinese/segment.py)、spaCy (zh_core_web_sm) の品詞 (OntoNotes のタグ)・依存関係で語の項目を作り
# (chinese/morphology.py)、中国語の構文をまとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器
# (core/analyzer.py) を中国語の設定 (CHINESE) で使う:
#   - 格は依存関係から (主語 nsubj → 主格、目的語 dobj → 対格、前置詞 (介詞) の目的語 → 前置詞句)
#   - 数詞・指示詞 + 量詞は名詞に掛かる形容詞 (一本书「一冊の本」、这个问题「この問題」)
#   - 名詞・代名詞 + 的 + 名詞は属格 (妈妈的书「母の本」)。動詞の句 + 的 + 名詞は連体修飾節 (我买的书「私が買った本」)
#   - アスペクト: 動詞 + 了 → 完了「〜した」、+ 过 → 経験「〜したことがある」、+ 着・在 / 正在 + 動詞 → 進行「〜している」
#   - 否定: 不 (現在)、没 / 没有 + 動詞 (過去「〜しなかった」)
#   - 把 + 名詞 (目的語を動詞の前に) は対格、被 (+ 動作主) は受動
#   - 形容詞の述語 (问题很难「問題は 難しい」) は形容詞 + 見えない繋辞、名詞 + 方位詞 (桌子上「机の上」) は1つの名詞
#   - 文末の吗は疑問 (？を補う)、吧・呢・啊は訳さない
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, segment

PUNCTUATION = {'。': 'period', '！': 'period', '？': 'question', '…': 'period', '，': 'comma', '、': 'comma',
               '；': 'comma', '：': 'comma', '.': 'period', '!': 'period', '?': 'question', ',': 'comma',
               '“': None, '”': None, '「': None, '」': None, '《': None, '》': None, '（': 'comma', '）': 'comma',
               '『': None, '』': None, '—': 'comma'}
ALL_CASES = ('Nom', 'Acc', 'Dat', 'Gen')
GENDER = 'c'


def _root_items(lemma):
    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


QUESTION_VERBS = frozenset({'知道', '问', '告诉', '明白', '懂', '清楚', '记得', '忘', '忘记', '看', '想', '说'})
INTERROGATIVES = {'哪儿': 'どこ', '哪里': 'どこ', '什么': None, '谁': None, '怎么': 'どのように', '为什么': 'なぜ',
                  '几': None, '多少': None, '什么时候': 'いつ', '是否': ''}

def _particle(case, obj, predicate):
    """語ごとの助詞: 主語に付けた也・都 (我也去「私も」)"""
    item = obj.items[0] if isinstance(obj, Word) and obj.items else None
    if case == 'Nom' and item is not None and item.attrib('nom_particle'):
        return item.attrib('nom_particle')
    return None


CHINESE = language.Language(
    name='zh',
    particle=_particle,
    question_moods=('indicative',), question_verbs=QUESTION_VERBS, interrogatives=INTERROGATIVES,
    subordinators=morphology.SUBORDINATORS,
    and_words=('和', '跟', '与', '及', '以及'),
    or_words=('或者', '还是', '或'),
    copulas=frozenset({'是', '(是)', '有'}),   # 有 は所有・存在の文 (私には本がある) として繋辞と同じ扱い
    negations=frozenset({'不', '没', '没有', '别', '(不)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_precedes_head=True,
    objects_follow_verb=True,
)


def sentences(text):
    current = []
    for token in segment.segment(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _item(word):
    return word.items[0] if isinstance(word, Word) and word.items else None


def _pos(word):
    item = _item(word)
    return item.pos if item is not None else None


def _cngs(cases):
    return [(c, n, GENDER) for c in cases for n in ('sg', 'pl')]


def _case_of(token):
    dep = token.dep_
    head = token.head
    if head.text in ('有', '没有') and head.tag_ in ('VE', 'VV') and head.i != token.i:
        # 有 の前の所有者・場所と、後ろの有るもの (我有两个朋友「私には 二人の友人が いる」、桌子上有书「机の上に 本が ある」)
        if token.i > head.i and dep in ('dobj', 'obj'):
            return ('Nom',)
        if token.i < head.i and (dep.startswith('nsubj') or dep in ('dep', 'advmod:loc', 'nmod:tmod')):
            place = dep == 'advmod:loc' or token.text in PLACE_PRONOUNS or any(c.tag_ == 'LC' for c in token.children)
            return ('Loc',) if place else ('Dat',)
    if dep in ('nmod:prep', 'pobj') or token.i > 0 and token.doc[token.i - 1].tag_ == 'P':
        return ('Gen',)   # 介詞 (前置詞) の目的語 (在图书馆)
    if token.head.tag_ in ('VV', 'VE') and token.head.text in MOTION_VERBS and dep in ('dobj', 'obj'):
        return ('Dat',)   # 移動の動詞の行き先 (去中国「中国に 行く」)
    if dep.startswith('nsubj'):
        return ('Nom',)
    if dep in ('dobj', 'obj') and any(c.dep_ in ('dobj', 'obj') and c.i > token.i for c in head.children):
        return ('Dat',)   # 二重目的語の前の方は受け手 (给女孩一本书「少女に 本を 与える」)
    if dep in ('dobj', 'obj', 'range'):
        return ('Acc',)
    if dep == 'iobj':
        return ('Dat',)
    if dep == 'compound:nn' and token.head.tag_ in ('NN', 'NR') and token.head.i > token.i:
        return ('Gen',)   # 名詞 + 名詞の複合語 (主体大修工程「本体の 改修の 工事」): 前の名詞は後ろの名詞に掛かる
    if dep in ('nmod:assmod', 'nmod:poss'):
        return ('Gen',)
    if dep == 'ROOT' or any(c.tag_ == 'VC' for c in token.children):
        return ('Nom',)   # 是 の補語 (他是老师)
    return ('Nom', 'Acc')


PLACE_PRONOUNS = {'这里', '那里', '这儿', '那儿', '哪里', '哪儿'}
MOTION_VERBS = {'去', '来', '回', '到', '上', '进', '出', '走'}


def _subject_of_later_clause(token):
    """後ろの節 (補文・並列の動詞) の主語か (我知道 | 他住在哪儿 の 他): 節を分けるとき後ろの動詞に"""
    return token.dep_.startswith('nsubj') and token.head.i > token.i and token.head.dep_ in ('ccomp', 'conj', 'dep', 'xcomp',
                                                                                             'advcl', 'parataxis')


def _verb(text, lemma, tag=None):
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    data = {'surface': text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma, 'ja': ja or lemma,
            'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': 'indicative', 'tense': 'present',
            'person': 3, 'number': 'sg', 'main': True, 'impersonal_person': True}
    if lemma == '是':
        data.update(ja='〜である', gloss_lang='ja', existential=True)
    return data


def item_of(token, doc, text):
    """spaCy の語 → 項目 (dict)。扱わない語は None (句読点)。text は元の字の語 (繁体字のまま)"""
    tag, word = token.tag_, token.text
    if tag == 'PU' or word in PUNCTUATION:
        return None
    if word in morphology.NEGATIONS and tag in ('AD', 'VE', 'VV'):
        if word in ('没', '没有') and token.i + 1 < len(doc) and doc[token.i + 1].tag_ in ('VV', 'VA', 'VE', 'VC') or \
                word not in ('没有',) or tag == 'AD':
            return {'surface': text, 'pos': 'adv', 'base': word, 'ja': morphology.NEGATIONS[word], 'gloss_lang': 'ja',
                    'negation': True, 'neg_past': word in ('没', '没有')}
    if word in ('有人', '有的人'):   # 有人说「ある人が 言う」(節の終わりの 有人 は segment で 有 / 人 に分ける)
        return {'surface': text, 'pos': 'pronoun', 'base': word, 'ja': 'ある人', 'gloss_lang': 'ja', 'person': 3,
                'number': 'sg', '_': _cngs(('Nom',)), 'compact': True}
    if word in morphology.PRONOUNS and tag in ('PN', 'NN', 'DT') and not (tag == 'DT' and word in morphology.DETERMINERS):
        ja, person, number = morphology.PRONOUNS[word]
        gender = morphology.PRONOUN_GENDERS.get(word, GENDER)
        data = {'surface': text, 'pos': 'pronoun', 'base': word, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': [(c, n, gender) for c, n, _ in _cngs(_case_of(token))], 'compact': True}
        if _subject_of_later_clause(token):
            data['clause_start'] = True
        if word in morphology.INTERROGATIVE_PRONOUNS:
            data['desc'] = '疑問代名詞'
        return data
    if tag == 'DT' or word in morphology.DETERMINERS and tag not in ('VV', 'NN'):
        return {'surface': text, 'pos': 'adj', 'base': word, 'ja': morphology.DETERMINERS.get(word, word), 'gloss_lang': 'ja',
                '_': _cngs(ALL_CASES), 'determiner': True}
    if tag in ('CD', 'OD') and word in morphology.DETERMINERS:
        return {'surface': text, 'pos': 'adj', 'base': word, 'ja': morphology.DETERMINERS[word], 'gloss_lang': 'ja',
                '_': _cngs(ALL_CASES), 'determiner': True}   # 很多「たくさんの」
    if tag in ('CD', 'OD'):
        ja = ''.join(morphology.NUMBERS_JA.get(c, c) for c in word)
        return {'surface': text, 'pos': 'adj', 'base': word, 'ja': ja, 'gloss_lang': 'ja', '_': _cngs(ALL_CASES),
                'numeral': True}
    if tag == 'M':
        return {'surface': text, 'pos': 'particle', 'base': word, 'ja': morphology.CLASSIFIERS.get(word, 'つ'),
                'gloss_lang': 'ja', 'classifier': True}
    if tag in ('AS', 'SP', 'DEC', 'DEG', 'DER', 'DEV', 'MSP', 'ETC', 'BA', 'LB', 'SB', 'IJ', 'LC'):
        return {'surface': text, 'pos': 'particle', 'base': word, 'ja': '', 'gloss_lang': 'ja', 'tag': tag}
    if tag == 'P':
        if word == '因为' or word in morphology.SUBORDINATORS and token.head.tag_ in ('VV', 'VA', 'VE', 'VC'):
            return {'surface': text, 'pos': 'conj', 'base': word, 'ja': morphology.CONJUNCTIONS.get(word, word),
                    'gloss_lang': 'ja'}
        if word == '在' and (token.dep_ == 'ROOT' or not any(t.tag_ in ('VV', 'VE', 'VC', 'VA') for t in doc)):
            data = _verb(text, '在')   # 存在の 在 (书在桌子上「本が 机の上に ある」)
            data.update(ja='ある,いる', gloss_lang='ja', existential=True, place_dative=True)
            return data
        ja = morphology.PREPOSITIONS.get(word, '〜' + word)
        if word in ('在', '到', '给') and token.i > 0 and doc[token.i - 1].tag_ == 'VV':
            ja = {'在': '〜に', '到': '〜まで,〜に', '给': '〜に'}[word]   # 動詞の後ろの結果の介詞 (放在桌子上「机の上に 置く」)
        return {'surface': text, 'pos': 'preposition', 'base': word, 'dominates': 'Gen', 'ja': ja, 'gloss_lang': 'ja'}
    if tag in ('CC', 'CS'):
        return {'surface': text, 'pos': 'conj', 'base': word, 'ja': morphology.CONJUNCTIONS.get(word, word),
                'gloss_lang': 'ja'}
    if tag in ('VV', 'VE', 'VC') and word in ('有', '没有'):
        data = _verb(text, '有', tag)   # 所有・存在の 有 (我有两个朋友「私には 二人の友人が いる」)、没有 + 名詞「ない」
        data.update(ja='ある,いる', gloss_lang='ja', existential=True, form='所有・存在 (有)')
        if word == '没有':
            data.update(negative=True, form='所有・存在の否定 (没有 + 名詞)')
        return data
    if tag in ('VV', 'VE', 'VC'):
        data = _verb(text, word, tag)
        if word in ('说', '講', '讲') and any(c.dep_ == 'dobj' and c.text[-1:] in '语文話话' for c in token.children):
            data['ja'] = '話す'   # 言葉を話す (说中文「中国語を 話す」)
        return data
    if tag == 'VA':
        ja, gloss_lang, _ = morphology.gloss(word, 'adj')
        return {'surface': text, 'pos': 'adj', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en',
                '_': _cngs(('Nom',)), 'predicative': True, 'main': True}
    if tag == 'JJ':
        ja, gloss_lang, _ = morphology.gloss(word, 'adj')
        return {'surface': text, 'pos': 'adj', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en',
                '_': _cngs(ALL_CASES), 'main': True}
    if tag == 'AD' or word in morphology.TIME_WORDS or tag == 'NT':
        ja, gloss_lang, _ = morphology.gloss(word, 'adv')
        return {'surface': text, 'pos': 'adv', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en',
                **({'progressive': True} if word in ('正在', '在', '正') else {})}
    if tag in ('NN', 'NR', 'FW'):
        ja, gloss_lang, row = morphology.gloss(word, 'noun')
        # spaCy は 中文 も NR に、CC-CEDICT は言語名 (Zhong1 wen2) も大文字で書く: 手の訳語の表の語・言語名は普通名詞
        proper = (bool(row and row['proper']) or tag == 'NR' and row is None) and word not in morphology.GLOSSES and \
            not (len(word) > 1 and word.endswith(('语', '文', '語')))
        if proper and (ja is None or gloss_lang == 'en'):
            ja, gloss_lang = text, 'ja'   # 中国の地名・人名は日本語でも漢字 (北京・李明)
        if ja is None:
            from .katakana import katakana
            ja, gloss_lang = katakana(word), 'ja'
        return {'surface': text, 'pos': 'noun', 'base': '%s (%s)' % (word, morphology.pinyin(word)), 'lemma': word,
                'ja': ja, 'gloss_lang': gloss_lang or 'en', '_': _cngs(_case_of(token)), 'main': True,
                **({'proper': True} if proper else {}), **({'clause_start': True} if _subject_of_later_clause(token) else {})}
    ja, gloss_lang, _ = morphology.gloss(word, 'adv')
    return {'surface': text, 'pos': 'adv', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en'}


# ----------------------------------------------------------------------

# 補文 (主語のある節) を取る「言う・思う」の動詞 → 節の後ろに付ける形
COMPLEMENT_VERBS = {'说': 'と', '讲': 'と', '告诉': 'と', '觉得': 'と', '认为': 'と', '想': 'と', '以为': 'と', '相信': 'と',
                    '听说': 'と', '表示': 'と', '知道': 'ことを', '希望': 'ことを', '发现': 'ことを', '记得': 'ことを',
                    '忘了': 'ことを', '担心': 'ことを'}


def complement_clauses(words, doc):
    """「言う・思う」の動詞の補文 (他说他是老师「彼は {彼が 先生である}と 言った」) の前に見えない接続詞を入れる。
    中国語には補文の接続詞 (英語の that) が無い。疑問詞のある補文 (我知道他住在哪儿) は間接疑問として共通の解析器で"""
    out = list(words)
    for token in reversed(list(doc)):
        if token.dep_ != 'ccomp' or token.head.text not in COMPLEMENT_VERBS:
            continue
        subtree = sorted(t.i for t in token.subtree)
        if not any(doc[i].dep_.startswith('nsubj') for i in subtree) or \
                any(doc[i].text in INTERROGATIVES for i in subtree):
            continue
        k = next((n for n, w in enumerate(out) if getattr(w, 'doc_i', None) == subtree[0]), None)
        if k is None:
            continue
        conj = Word('(that)', [{'surface': '(that)', 'pos': 'conj', 'base': '(that)', 'ja': '〜ということ', 'gloss_lang': 'ja',
                                'clause_suffix': COMPLEMENT_VERBS[token.head.text], 'clause_start': True,
                                'complement': True, 'desc': '補文 (中国語では接続詞を使わない)'}])
        conj.token_ix = None
        conj.doc_i = None
        out.insert(k, conj)
    return out


def _tag(word):
    item = _item(word)
    return item.attrib('tag') if item is not None else None


def _drop(word):
    word.merged_into = True


PERSON_WORDS = ('person', 'people', 'friend', 'student', 'teacher', 'child', 'man', 'woman', 'boy', 'girl', 'worker',
                'doctor', 'brother', 'sister', 'son', 'daughter', 'colleague', 'classmate', 'guest', 'customer')


def _is_person(noun):
    """人を表す名詞か (CC-CEDICT の英語の語義から: 朋友 friend、学生 student …)"""
    rows = dictionary.lookup(noun.attrib('lemma') or noun.attrib('surface') or '')
    en = (rows[0]['en'] if rows else '') or ''
    return any(re.search(r'\b%s\b' % w, en) for w in PERSON_WORDS)


def classifiers(words):
    """数詞・指示詞 + 量詞 (一本・这个) を名詞に掛かる形容詞1つに (一冊の・この)。量詞だけ (个问题) も"""
    out = []
    for word in words:
        item = _item(word)
        if item is not None and item.attrib('classifier'):
            prev = _item(out[-1]) if out else None
            if prev is not None and prev.attrib('numeral'):
                unit = item.ja
                noun = next((_item(w) for w in words[words.index(word) + 1:words.index(word) + 3]
                             if _pos(w) == 'noun'), None)
                if item.attrib('base') in ('个', '個') and noun is not None and _is_person(noun):
                    unit = '人'   # 人を数える 个 (两个朋友「二人の友人」)
                ja = prev.ja + (unit if unit != 'つ' or len(prev.ja) > 1 else 'つ') + 'の'
                cases = [t for t in prev._ or [] if noun is None or t[0] in {c for c, _, _ in noun._ or []}] or prev._
                out[-1].items = [type(prev)(dict(prev.item, ja=ja, surface=out[-1].surface + word.surface, _=cases))]
                out[-1].surface += word.surface
                _drop(word)
                continue
            if prev is not None and prev.attrib('determiner'):
                out[-1].surface += word.surface
                _drop(word)
                continue
            _drop(word)
            continue
        out.append(word)
    return out


def plurals(words):
    """名詞 + 们 (士兵们「兵士たち」) を複数の名詞1つに"""
    out = []
    for word in words:
        if word.surface == '们' and out and _pos(out[-1]) == 'noun':
            prev = _item(out[-1])
            out[-1].items = [type(prev)(dict(prev.item, ja=prev.ja.split(',')[0] + 'たち', noun_ja=prev.ja, animate=True,
                                             _=[t for t in prev._ or [] if t[1] == 'pl'] or prev._))]
            out[-1].surface += word.surface
            _drop(word)
            continue
        out.append(word)
    return out


def localizers(words):
    """名詞 + 方位詞 (桌子上「机の上」・房间里「部屋の中」) を1つの名詞に"""
    out = []
    for word in words:
        item = _item(word)
        if item is not None and (_tag(word) == 'LC' or len(word.surface) > 1 and word.surface in morphology.LOCALIZERS) and \
                out and _pos(out[-1]) in ('noun', 'pronoun'):
            prev = _item(out[-1])
            place = morphology.LOCALIZERS.get(word.surface, item.attrib('base'))
            out[-1].items = [type(prev)(dict(prev.item, ja=prev.ja.split(',')[0] + 'の' + place, pos='noun',
                                             gloss_lang='ja', localizer=word.surface,
                                             noun_ja=prev.attrib('noun_ja') or prev.ja))]
            out[-1].surface += word.surface
            _drop(word)
            continue
        out.append(word)
    return out


def genitives(words):
    """名詞・代名詞 + 的 (DEG) + 名詞: 前の語を属格に (妈妈的书「母の本」)。的は落とす"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'pronoun' and item._ and all(t[0] == 'Gen' for t in item._) and \
                k + 1 < len(words) and _pos(words[k + 1]) == 'noun':   # 代名詞 + 名詞 (我爸爸「私の父」)
            word.items = [type(item)(dict(item.item, pos='adj', ja=item.ja.split(',')[0] + 'の', _=_cngs(ALL_CASES),
                                          possessive=True))]
            out.append(word)
            continue
        if _tag(word) in ('DEG', 'DEC') and out and _pos(out[-1]) in ('noun', 'pronoun') and k + 1 < len(words) and \
                _pos(words[k + 1]) in ('noun', 'adj'):
            prev = _item(out[-1])
            if prev.pos == 'pronoun':   # 代名詞 + 的 は名詞に掛かる所有「私の」(我的心)
                out[-1].items = [type(prev)(dict(prev.item, pos='adj', ja=prev.ja.split(',')[0] + 'の', _=_cngs(ALL_CASES),
                                                 possessive=True))]
            else:
                out[-1].items = [type(prev)(dict(prev.item, _=_cngs(('Gen',))))]
            _drop(word)
            continue
        out.append(word)
    return out


def _clause_ja(tokens, by_i):
    """連体修飾節の語 (spaCy の語の列) → 日本語 (我买 → 私が買った)"""
    parts, verb, past, negative = [], '', False, False
    for t in tokens:
        w = by_i.get(t.i)
        it = _item(w) if w is not None else None
        if t.tag_ == 'AS' and t.text in ('了', '过'):
            past = True
            continue
        if it is None or it.pos == 'particle':
            continue
        if it.pos == 'verb':
            verb = (it.ja or '').split(',')[0]
        elif it.attrib('negation'):
            negative, past = True, past or it.attrib('neg_past')
        elif it.pos in ('noun', 'pronoun'):
            particle = 'が' if t.dep_.startswith('nsubj') else 'を' if t.dep_ in ('dobj', 'obj') else 'の'
            parts.append(it.ja.split(',')[0] + particle)
        elif it.pos == 'preposition':
            continue
        elif it.pos in ('adv', 'adj'):
            parts.append(it.ja.split(',')[0])
    if verb:
        try:
            from dragoman.core.japanese import JaVerb
            from dragoman.core import verb_flags as V
            verb = JaVerb(verb).form(V.INDICATIVE | (V.PERFECT if past else 0), negative)
        except Exception:
            pass
    return ''.join(parts) + verb


def relative_clauses(words, doc):
    """動詞の句 + 的 (DEC) + 名詞: 連体修飾節を名詞の訳に組み込む (我买的书「私が買った本」)。節の語は除く"""
    by_i = {w.doc_i: w for w in words if getattr(w, 'doc_i', None) is not None}
    for token in doc:
        if token.tag_ != 'DEC' or token.head.dep_ not in ('acl', 'rcmod', 'relcl') and token.head.tag_ not in ('VV', 'VE', 'VA'):
            continue
        verb = token.head
        head = verb.head if verb.head.i != verb.i else None
        if head is None or head.i not in by_i or _pos(by_i[head.i]) not in ('noun', 'pronoun'):
            continue
        sub = sorted((t for t in verb.subtree if t.i != token.i and t.i < token.i), key=lambda t: t.i)
        clause = _clause_ja(sub, by_i)
        noun = by_i[head.i]
        it = _item(noun)
        data = dict(it.item, ja=clause + it.ja.split(',')[0], gloss_lang='ja', noun_ja=it.ja,
                    relative=''.join(t.text for t in sub) + '的')
        adjective = [by_i[t.i] for t in sub if t.i in by_i and _pos(by_i[t.i]) in ('adj', 'verb')]
        if len(sub) == 1 and len(adjective) == 1 and sub[0].tag_ == 'VA':
            data['relative_adj'] = dict(_item(adjective[0]).item, pos='adj')   # 美丽的玫瑰: 文の枠では形容詞に
        noun.items = [type(it)(data)]
        for t in sub + [token]:
            if t.i in by_i:
                _drop(by_i[t.i])
    return [w for w in words if not getattr(w, 'merged_into', False)]


def _experienced(verb):
    """動詞 → 「〜したことがある」(行く → 行ったことがある)"""
    try:
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as V
        return JaVerb(verb).form(V.INDICATIVE | V.PERFECT, False) + 'ことがある'
    except Exception:
        return verb + 'ことがある'


def _with_complement(verb_ja, complement):
    """動詞の訳 + 補語 (看 + 完 → 読み終える、听 + 懂 → 聞いて分かる)"""
    form, suffix = morphology.COMPLEMENTS[complement]
    if not form:
        return verb_ja
    from dragoman.core.japanese import japanese_form
    first = verb_ja.split(',')[:1 if suffix.endswith(('来る', '行く')) else 2]   # 方向の補語は動詞の最初の訳だけ (走 → 歩いて)
    return ','.join(japanese_form(j, False, form, 'present', False) + suffix for j in first)


def complements(words):
    """動詞の後ろの補語を動詞にまとめる:
    結果・方向の補語 (看完「読み終える」、走进来「歩いて入ってくる」)、可能の補語 (听得懂「聞いて分かることができる」、
    看不懂「読んで分かることができない」: 不 は否定として残す)、様態の補語 (跑得很快「とても速く走る」)。
    了 の付いた補語 (看完了) は補語と了に"""
    out = []
    k = 0
    while k < len(words):
        word = words[k]
        item = _item(word)
        nxt_surface = words[k + 1].surface if k + 1 < len(words) else ''
        if item is None or item.pos != 'verb' or item.attrib('lemma') in morphology.MODALS and \
                (item.attrib('lemma'), nxt_surface) not in morphology.COMPLEMENT_GLOSSES:   # 想起来「思い出す」は補語
            out.append(word)
            k += 1
            continue
        j = k + 1
        middle = None
        if j < len(words) and (_tag(words[j]) == 'DER' or words[j].surface == '不' and j + 1 < len(words) and
                               (words[j + 1].surface in morphology.COMPLEMENTS)):
            middle = words[j]
            j += 1
        nxt = words[j] if j < len(words) else None
        surface = nxt.surface if nxt is not None else ''
        complement = surface[:-1] if surface.endswith('了') and surface[:-1] in morphology.COMPLEMENTS else surface
        if nxt is not None and complement in morphology.COMPLEMENTS and (middle is not None or _pos(nxt) == 'verb'):
            ja = morphology.COMPLEMENT_GLOSSES.get((item.attrib('lemma'), complement)) or \
                (_with_complement(item.ja, complement) if item.attrib('gloss_lang') == 'ja' else item.ja)
            form = '補語 %s%s' % ('' if middle is None else middle.surface, complement)
            data = dict(item.item, ja=ja, surface=word.surface + (middle.surface if middle else '') + nxt.surface,
                        form=form)
            if middle is not None and _tag(middle) == 'DER':
                data['ja'] = ','.join(x + 'ことができる' for x in ja.split(','))   # 可能の補語 (听得懂)
                data['form'] = '可能の補語 (動詞 + 得 + 補語「〜できる」)'
                _drop(middle)
            elif middle is not None:
                data['form'] = '可能の補語の否定 (動詞 + 不 + 補語「〜できない」)'
                data['ja'] = ','.join(x + 'ことができる' for x in ja.split(','))
                out.append(middle)   # 不 は否定の副詞として残す
            word.items = [type(item)(data)]
            word.surface = data['surface']
            _drop(nxt)
            out.append(word)
            if surface.endswith('了') and complement != surface:
                le = Word('了', [{'surface': '了', 'pos': 'particle', 'base': '了', 'ja': '', 'gloss_lang': 'ja', 'tag': 'AS'}])
                le.token_ix = getattr(nxt, 'token_ix', None)
                out.append(le)   # 看完了 の 了 (完了「〜した」)
            k = j + 1
            continue
        if middle is not None and _tag(middle) == 'DER' and nxt is not None:
            # 様態の補語 (跑得很快「とても速く走る」): 形容詞を副詞の形にして動詞の前に
            adv, m = '', j
            if nxt.surface in ('很', '非常', '太', '真', '挺', '特别', '比较'):
                adv = (_item(nxt).ja or '').split(',')[0]
                m += 1
            adj = words[m] if m < len(words) else None
            if adj is not None and _pos(adj) == 'adj' and _item(adj).attrib('gloss_lang') == 'ja':
                manner = adv + morphology.adverbial(_item(adj).ja.split(',')[0])
                data = dict(item.item, ja=','.join(manner + x for x in item.ja.split(',')[:2]),
                            surface=word.surface + middle.surface + ''.join(w.surface for w in words[j:m + 1]),
                            form='様態の補語 (動詞 + 得 + 形容詞「〜く …する」)')
                word.items = [type(item)(data)]
                word.surface = data['surface']
                for w in words[j - 1:m + 1]:
                    if w is not word:
                        _drop(w)
                out.append(word)
                k = m + 1
                continue
        out.append(word)
        k += 1
    return out


def aspects(words):
    """動詞の後ろの了・过・着 (と文末の了)、前の在・正在、没 + 動詞を動詞の時制に"""
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb':
            continue
        data = dict(item.item)
        after = [w for w in words[k + 1:k + 4]]
        marks = [w.surface for w in after if _tag(w) in ('AS', 'SP')]
        before = words[max(0, k - 2):k]
        if '过' in marks or '過' in marks:
            data.update(tense='present', form='経験 (动词 + 过「〜したことがある」)', experiential=True)
            if data.get('gloss_lang') == 'ja':
                data['ja'] = ','.join(_experienced(j) for j in data['ja'].split(',')[:2])
        elif '了' in marks:
            data.update(tense='perfect', form='完了 (动词 + 了)')
        elif '着' in marks or '著' in marks or any(_item(w) is not None and _item(w).attrib('progressive') for w in before):
            data.update(tense='progressive', form='進行 (在 / 正在 + 动词、动词 + 着)')
        if any(_item(w) is not None and _item(w).attrib('neg_past') for w in before) and not data.get('experiential'):
            data['tense'] = 'perfect'   # 没 + 動詞「〜しなかった」(没 + 动词 + 过 は「〜したことがない」)
        word.items = [type(item)(data)]
    return [w for w in words if not (_tag(w) in ('AS',) or _tag(w) == 'SP' and w.surface in ('了',)) and
            not (_item(w) is not None and _item(w).attrib('progressive'))]


def modals(words):
    """助動詞 (会・能・想・要 …) + 動詞を1語に (想去「行きたい」)"""
    out = []
    k = 0
    while k < len(words):
        word = words[k]
        item = _item(word)
        nxt = words[k + 1] if k + 1 < len(words) else None
        if item is not None and item.pos == 'verb' and item.attrib('lemma') in morphology.MODALS and nxt is not None and \
                _pos(nxt) == 'verb':
            m = _item(nxt)
            from dragoman.core.japanese import attach_auxiliary
            suffix = morphology.MODALS[item.attrib('lemma')]
            prediction = item.attrib('lemma') == '会' and any(_item(w) is not None and _item(w).attrib('complement')
                                                               for w in out)
            if prediction:
                suffix = 'だろう'   # 補文の 会 は見込み (我觉得他会来「{彼が 来るだろう}と 思う」)。文の枠では未来
            ja = ','.join(attach_auxiliary(j, suffix) for j in m.ja.split(',')[:1]) if m.attrib('gloss_lang') == 'ja' else m.ja
            data = dict(m.item, ja=ja, surface=word.surface + nxt.surface, modal=item.attrib('lemma'), main_ja=m.ja,
                        form='助動詞 %s + 動詞' % item.attrib('lemma'), tense=item.attrib('tense'))
            if prediction:   # 文の枠では未来の時制 (generate/frame.py)
                del data['modal']
                data['prediction'] = True
            word.items = [type(m)(data)]
            word.surface = data['surface']
            _drop(nxt)
            out.append(word)
            k += 2
            continue
        out.append(word)
        k += 1
    return out


def ba_bei(words):
    """把 + 名詞は目的語 (対格)、被 + (動作主) + 動詞は受動 (动作主は「〜によって」)"""
    out = []
    for k, word in enumerate(words):
        tag = _tag(word)
        if tag == 'BA':
            nxt = next((w for w in words[k + 1:] if _pos(w) in ('noun', 'pronoun')), None)
            if nxt is not None:
                it = _item(nxt)
                nxt.items = [type(it)(dict(it.item, _=_cngs(('Acc',)), ba_object=True))]
            verb = next((w for w in words[k + 1:] if _pos(w) == 'verb'), None)
            if verb is not None:   # 把構文 (処置文): 目的語を動詞の前に出して「それをどうするか」。訳でも目的語を先に
                it = _item(verb)
                verb.items = [type(it)(dict(it.item, object_first=True,
                                            form='把構文 (把 + 目的語 + 動詞: 目的語を どうするか (処置))'))]
            _drop(word)
            continue
        if tag in ('LB', 'SB'):
            verb = next((w for w in words[k + 1:] if _pos(w) == 'verb'), None)
            if verb is not None:
                it = _item(verb)
                verb.items = [type(it)(dict(it.item, voice='passive', form='受動 (被)'))]
            agent = words[k + 1] if k + 1 < len(words) and _pos(words[k + 1]) in ('noun', 'pronoun') else None
            if agent is not None:
                word.items = [type(_item(word))({'surface': word.surface, 'pos': 'preposition', 'base': '被',
                                                  'dominates': 'Gen', 'ja': '〜によって', 'gloss_lang': 'ja'})]
                it = _item(agent)
                agent.items = [type(it)(dict(it.item, _=_cngs(('Gen',))))]
                out.append(word)
                continue
            _drop(word)
            continue
        out.append(word)
    return out


COPULA = {'surface': '(是)', 'pos': 'verb', 'lemma': '是', 'pres1sg': '是', 'base': '是', 'ja': '〜である', 'gloss_lang': 'ja',
          'voice': 'active', 'mood': 'indicative', 'tense': 'present', 'person': 3, 'number': 'sg',
          'desc': '省略された繋辞 (形容詞の述語)'}


def hen_adjectives(words):
    """很 + 形容詞の述語は1語に (很难「とても難しい」)。很を先に出さない"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'adj' and out and out[-1].surface in ('很', '非常', '太', '真', '挺', '比较', '最', '更'):
            adv = _item(out[-1])
            together = out[-1].surface + word.surface
            if adv is not None and adv.pos == 'adv' and segment.simplified(together) in morphology.DETERMINERS and \
                    k + 1 < len(words) and _pos(words[k + 1]) == 'noun':
                word.items = [type(item)(dict(item.item, ja=morphology.DETERMINERS[segment.simplified(together)],
                                              surface=together, determiner=True, predicative=False))]   # 很多书「たくさんの本」
                word.surface = together
                _drop(out.pop())
            elif adv is not None and adv.pos == 'adv' and item.attrib('gloss_lang') == 'ja':
                word.items = [type(item)(dict(item.item, ja=','.join(adv.ja.split(',')[0] + j for j in item.ja.split(',')[:2]),
                                              surface=out[-1].surface + word.surface))]
                word.surface = out[-1].surface + word.surface
                _drop(out.pop())
        out.append(word)
    return out


def adjective_predicates(words):
    """形容詞の述語 (VA: 问题很难) の後ろに見えない繋辞を補う (共通の解析器の形容詞の補語「問題は 難しい」)"""
    out = []
    for word in words:
        out.append(word)
        item = _item(word)
        if item is not None and item.pos == 'adj' and item.attrib('predicative'):
            cop = Word('(是)', [dict(COPULA)])
            cop.token_ix = getattr(word, 'token_ix', None)
            cop.doc_i = None
            out.append(cop)
    return out


def place_datives(words):
    """存在の 在 の後ろの場所の名詞は「〜に」(书在桌子上「本が 机の上に ある」)"""
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or not item.attrib('place_dative'):
            continue
        for w in words[k + 1:]:
            it = _item(w)
            if it is not None and it.pos in ('noun', 'pronoun'):
                w.items = [type(it)(dict(it.item, _=_cngs(('Dat',))))]
                break


ALSO = {'也': 'も', '都': 'みな', '还': 'まだ', '就': 'すぐに', '只': 'だけ'}


def subject_adverbs(words):
    """主語の後ろの也「〜も」・都「みな」は主語に付ける (我也去「私も 行く」)。主語の格の助詞の代わり"""
    out = []
    for k, word in enumerate(words):
        if word.surface in ('也', '都') and _pos(word) == 'adv' and out:
            prev = out[-1]
            it = _item(prev)
            if it is not None and it.pos in ('noun', 'pronoun') and it._ and it._[0][0] == 'Nom':
                particle = 'も' if word.surface == '也' else 'はみな'
                prev.items = [type(it)(dict(it.item, nom_particle=particle))]
                _drop(word)
                continue
        out.append(word)
    return out


def question_particles(words, surfaces):
    """文末の吗は疑問: 文末の？が無ければ補う。吧・呢・啊・嘛は訳さない"""
    if any(w.surface in ('吗', '嗎') for w in words) and surfaces and surfaces[-1] not in ('？', '?'):
        surfaces.append('？')
    return [w for w in words if not (_tag(w) == 'SP' and w.surface in ('吗', '嗎', '吧', '呢', '啊', '嘛', '呀', '啦'))]


def lookup_all(surfaces):
    simple = [segment.simplified(s) for s in surfaces]
    doc = morphology.parse(simple)
    words = []
    for token in doc:
        data = item_of(token, doc, surfaces[token.i])
        word = Word(surfaces[token.i], None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    global _display
    _display = list(words)
    words = relative_clauses(words, doc)
    words = complement_clauses(words, doc)
    words = complements(words)
    words = plurals(words)
    words = classifiers(words)
    words = localizers(words)
    words = genitives(words)
    words = ba_bei(words)
    words = aspects(words)
    words = modals(words)
    words = subject_adverbs(words)
    words = hen_adjectives(words)
    words = adjective_predicates(words)
    place_datives(words)
    words = [w for w in words if not getattr(w, 'merged_into', False) and _pos(w) != 'particle']
    for i, word in enumerate(words):
        word.index = i
    return words


_display = []


def analyze_sentence(surfaces):
    surfaces = list(surfaces)
    words = lookup_all(surfaces)
    marks = list(surfaces)
    words = question_particles(words, marks)
    if marks[-1:] == ['？'] and (not words or words[-1].surface not in ('？', '?')):
        q = Word('？', None)
        q.token_ix = None
        words.append(q)
    for i, word in enumerate(words):
        word.index = i
    word_details = [word.detail() for word in words]
    with language.using(CHINESE):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
