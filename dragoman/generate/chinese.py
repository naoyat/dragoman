#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から中国語 (普通話・簡体字) の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。zh/en-index.tsv は CC-CEDICT から。解析器の訳語の表 GLOSSES を先に)。
#     語形変化は無い
#   名詞句: 指示詞・数詞 + 量詞 (这本书・两个人。量詞は CC-CEDICT の CL:、無ければ个) + 形容詞 + (的) + 名詞。
#     1字の形容詞は的を付けない (好人)、2字以上は付ける (美丽的花)。属格は 名詞 + 的 (妈妈的书)、人称代名詞の属格も的。
#     関係節は 節 + 的 + 名詞 (我看的书)
#   語順: 主語 - 時の副詞 - 否定 (不 / 没) - 前置詞句 (在花园里・从罗马・和朋友一起・用刀) - 動詞 (+ 了) - 受け手 - 目的語。
#     受け手は 給・送・告诉・教 なら目的語の前 (给女孩一朵花)、ほかの動詞は 给 + 受け手 を動詞の前に
#   時制: 完了は 動詞 + 了、過去完了 已经 + 動詞 + 了、未来 将 + 動詞。否定は 不 (完了なら 没 で 了 を付けない)。
#     受動 被 (+ 動作主) + 動詞
#   繋辞: 名詞の補語は 是、形容詞の補語は 很 + 形容詞、場所は 在、存在の文 (est「ある」) は 有。疑問文は文末に 吗
#   補文: 「言う・知る」の動詞 + 節 (接続詞なし)。話法の動詞 能・想・应该 + 動詞
#
import dataclasses
import functools

from . import transfer, english
from .frame import NP, Lex, Clause

PRONOUNS = {('ego', 'sg'): '我', ('ego', 'pl'): '我们', ('tū', 'sg'): '你', ('tū', 'pl'): '你们',
            ('quis', 'sg'): '谁', ('quis', 'pl'): '谁', ('quid', 'sg'): '什么', ('quid', 'pl'): '什么',
            ('nēmō', 'sg'): '没有人', ('nihil', 'sg'): '什么也', ('ipse', 'sg'): '自己', ('ipse', 'pl'): '自己',
            ('sē', 'sg'): '自己', ('sē', 'pl'): '自己'}
THIRD = {('m', 'sg'): '他', ('f', 'sg'): '她', ('n', 'sg'): '它', ('m', 'pl'): '他们', ('f', 'pl'): '她们',
         ('n', 'pl'): '它们'}
DEMONSTRATIVES = {'hic': '这', 'hīc': '这', 'iste': '那', 'ille': '那', 'is': '那'}
POSSESSIVES = {'meus': '我的', 'tuus': '你的', 'suus': '他的', 'noster': '我们的', 'vester': '你们的'}
NUMERALS = {'ūnus': '一', 'duo': '两', 'trēs': '三', 'quattuor': '四', 'quīnque': '五', 'sex': '六', 'septem': '七',
            'octō': '八', 'novem': '九', 'decem': '十', 'centum': '一百', 'mīlle': '一千'}
QUANTIFIERS = {'omnis': '所有的', 'tōtus': '整个', 'multus': '很多', 'paucī': '很少的', 'alius': '别的', 'cēterī': '其他的'}
# 前置詞 (ラテン語の前置詞, 格) → (中国語の介詞, 方位詞)。動詞の前に置く
PREPOSITIONS = {('in', 'Abl'): ('在', '里'), ('in', 'Acc'): ('到', '里'), ('ad', 'Acc'): ('到', ''),
                ('ex', 'Abl'): ('从', '里'), ('ē', 'Abl'): ('从', ''), ('ab', 'Abl'): ('从', ''), ('ā', 'Abl'): ('从', ''),
                ('cum', 'Abl'): ('和', '一起'), ('dē', 'Abl'): ('关于', ''), ('sine', 'Abl'): ('没有', ''),
                ('per', 'Acc'): ('通过', ''), ('propter', 'Acc'): ('因为', ''), ('ob', 'Acc'): ('因为', ''),
                ('post', 'Acc'): ('在', '后面'), ('ante', 'Acc'): ('在', '前面'), ('sub', 'Abl'): ('在', '下面'),
                ('sub', 'Acc'): ('到', '下面'), ('super', 'Acc'): ('在', '上面'), ('prō', 'Abl'): ('为了', ''),
                ('apud', 'Acc'): ('在', '那里'), ('contrā', 'Acc'): ('反对', ''), ('inter', 'Acc'): ('在', '中间'),
                ('prope', 'Acc'): ('在', '附近'), ('trāns', 'Acc'): ('在', '对面'), ('circum', 'Acc'): ('在', '周围')}
# 方位詞を付けない名詞 (場所そのもの: 国・町の名前、学校・家 …)
PLACE_NOUNS = {'学校', '家', '中国', '城市', '图书馆', '医院', '公园', '商店', '这里', '那里'}
# 中 (里) でなく上 (上) を付ける面の名詞 (在路上・在海上)
ON_NOUNS = ('路', '街', '桥', '山', '船', '床', '桌子', '海', '天空', '天', '地', '岛', '墙')
CONNECTIVES = {'et': '而且', 'que': '而且', 'atque': '而且', 'ac': '而且', 'sed': '但是', 'at': '但是', 'autem': '而',
               'enim': '因为', 'nam': '因为', 'igitur': '所以', 'itaque': '所以', 'tamen': '然而', 'tum': '然后',
               'deinde': '然后', 'aut': '或者', 'vel': '或者'}
# 従属節の接続詞 → (前, 後ろ)
SUBORDINATORS = {'cum': ('当', '的时候'), 'ubi': ('当', '的时候'), 'sī': ('如果', ''), 'quod': ('因为', ''),
                 'quia': ('因为', ''), 'quoniam': ('既然', ''), 'dum': ('当', '的时候'), 'postquam': ('', '以后'),
                 'ut': ('为了', ''), 'quamquam': ('虽然', ''), 'etsī': ('即使', ''), 'priusquam': ('', '以前'),
                 'antequam': ('', '以前'), 'dōnec': ('直到', ''), 'simul': ('一', '就'), 'nisi': ('除非', '')}
WORDS = {'semper': '总是', 'saepe': '常常', 'iam': '已经', 'nunc': '现在', 'hodiē': '今天', 'crās': '明天', 'heri': '昨天',
         'ibi': '在那里', 'hīc': '在这里', 'etiam': '也', 'quoque': '也', 'valdē': '非常', 'magnopere': '非常',
         'statim': '立刻', 'mox': '不久', 'tandem': '终于', 'iterum': '又', 'numquam': '从来不', 'bene': '好好地',
         'male': '不好地', 'posteā': '后来', 'diū': '很久', 'sīc': '这样', 'ita': '这样', 'sōlum': '只', 'paene': '几乎'}
# 前に出す時の副詞 (主語の後ろ・動詞の前)
TIME_WORDS = {'今天', '明天', '昨天', '现在', '已经', '后来', '不久', '终于', '立刻', '总是', '常常', '又', '也', '只'}
# 話法の動詞 (ラテン語の見出し) → 中国語
MODALS = {'possum': '能', 'volō': '想', 'dēbeō': '应该', 'oportet': '必须', 'soleō': '常常', 'incipiō': '开始',
          'coepī': '开始'}
# 受け手を目的語の前に置く動詞 (二重目的語: 给他一本书)
DOUBLE_OBJECT = {'给', '送', '告诉', '教', '问', '还', '借', '交给', '递'}
# 動きの動詞 (in・ad + 対格の行き先を動詞の後ろに: 去罗马)
MOTION = {'去', '来', '回', '到', '走', '跑', '进', '出', '上', '下'}
QUESTION_WORDS = {'cūr': '为什么', 'quārē': '为什么', 'quōmodo': '怎么', 'ubi': '在哪里', 'quō': '到哪里',
                  'unde': '从哪里', 'quandō': '什么时候', 'num': '', 'utrum': ''}


def available():
    return transfer.available('zh')


def to_chinese(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'zh':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    if lex.proper:   # 漢字の名前の表は無いので、ラテン文字のまま (長音符は除く: Mārcus → Marcus)
        from .names import localized
        import unicodedata
        found = localized(lex, 'zh')
        return found[0] if found else ''.join(c for c in unicodedata.normalize('NFD', lex.lemma)
                                              if not unicodedata.combining(c))
    target = transfer.best(lex, 'zh', pos)
    return target.lemma if target else None


def word(lex, pos=None):
    found = to_chinese(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


@functools.lru_cache(maxsize=20000)
def classifier(noun):
    """名詞の量詞 (CC-CEDICT の CL:。無ければ个)"""
    from dragoman.chinese import dictionary
    for row in dictionary.lookup(noun):
        if row.get('classifiers'):
            return row['classifiers'].split(',')[0]
    return '个'


# ----------------------------------------------------------------------
# 名詞句

def _pronoun(np):
    head = np.head
    number = 'pl' if np.number == 'pl' else 'sg'
    if head.lemma in ('is', 'ille') and not np.modifiers:
        g = 'f' if np.gender == 'f' else 'n' if np.gender == 'n' and not np.animate else 'm'
        return THIRD[(g, number)]
    return PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg'))


def _adjective(lex):
    form = word(lex, 'adj')
    if not form or form.startswith('['):
        return form
    if lex.degree == '+':
        return '更' + form
    if lex.degree == '++':
        return '最' + form
    return form


def _attributive(adj):
    """名詞の前の形容詞: 1字なら的なし (好人)、2字以上は的 (美丽的花)"""
    if not adj or adj.endswith('的') or adj.startswith('['):
        return adj
    return adj if len(adj) == 1 else adj + '的'


def noun_phrase(np):
    if np.members:
        parts = [noun_phrase(m) for m in np.members]
        conj = '或者' if np.conj in ('aut', 'vel') else '和'
        return '、'.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        found = _pronoun(np)
        if found:
            return found
        if head.lemma in DEMONSTRATIVES:
            return DEMONSTRATIVES[head.lemma] + ('些' if np.number == 'pl' else '个')
        return word(head)
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    if head.pos in ('adj', 'participle'):
        noun = _attributive(noun) + ('人' if np.animate else '东西')   # 形容詞の名詞的用法 (bonī → 好人)
    determiner, number_word, quantifier, possessive = '', '', '', ''
    adjectives = []
    for m in np.modifiers:
        if isinstance(m, NP):   # 形容詞の並列 (又好又勇敢的)
            forms = [_adjective(x.head) for x in m.members if x.head is not None]
            adjectives.append(''.join('又' + f for f in forms) + '的' if len(forms) > 1 else ''.join(forms))
            continue
        latin = m.lang in ('', 'la')
        if m.lemma in DEMONSTRATIVES and latin:
            determiner = DEMONSTRATIVES[m.lemma]
        elif m.lemma in POSSESSIVES and latin:
            possessive = POSSESSIVES[m.lemma]
        elif m.lemma in NUMERALS and latin:
            number_word = NUMERALS[m.lemma]
        elif m.lemma in QUANTIFIERS and latin:
            quantifier = QUANTIFIERS[m.lemma]
        else:
            adjectives.append(_adjective(m))
    counted = ''
    if not (number_word or determiner or quantifier) and np.definite is False and np.number == 'sg' and \
            head.pos == 'noun' and not head.proper:
        number_word = '一'   # 不定冠詞のある言語の不定の名詞 (uma rosa・一本书) は 一 + 量詞
    if number_word or determiner:
        cl = classifier(noun) if not noun.startswith('[') else '个'
        counted = determiner + number_word + (cl if not (determiner and np.number == 'pl' and not number_word) else '些')
    adjective_text = ''.join(_attributive(a) for a in adjectives if a)
    genitive = ''.join(noun_phrase(g) + '的' for g in np.genitives)
    relative = ''.join(relative_clause(r) + '的' for r in np.relatives) + \
        ''.join(_attributive_participle(p) + '的' for p in np.participles)   # 逃跑的敌人
    if possessive and not (genitive or relative or counted or quantifier or adjective_text) and noun in KIN_NOUNS:
        possessive = possessive[:-1]   # 親族は 的 なしで (我爸爸)
    if np.number == 'pl' and np.animate and not (counted or quantifier) and head.pos == 'noun' and not head.proper and \
            not noun.endswith('们') and np.head.lang == 'zh':
        noun += '们'   # 人の複数 (士兵们)。元が中国語の文のときだけ (ほかの言語からは数を書かない)
    return possessive + genitive + relative + counted + quantifier + adjective_text + noun


# 所有の代名詞を 的 なしで付ける親族の名詞 (我爸爸・你妈妈)
KIN_NOUNS = {'爸爸', '妈妈', '哥哥', '姐姐', '弟弟', '妹妹', '爷爷', '奶奶', '儿子', '女儿', '丈夫', '妻子', '家'}


def _indefinite(np):
    """存在・所有の文の名詞は「一 + 量詞」を付ける (有一本书)。複数・修飾語のあるものはそのまま"""
    text = noun_phrase(np)
    if np.definite is False or np.members or np.number == 'pl' or np.modifiers or np.genitives or np.relatives or np.head is None or \
            np.head.pos != 'noun' or np.head.proper:
        return text
    return '一' + classifier(text) + text


def relative_clause(r):
    """関係節: 空所を除いた節 (我看的 + 书)"""
    return ''.join(realize(r, gap=r.gap or 'subject'))


def _place(np, prep, localizer):
    inner = noun_phrase(np)
    if not inner:
        return ''
    if localizer == '里' and inner.endswith(tuple(ON_NOUNS)):
        localizer = '上'   # 面の名詞は 上 (在路上・在天上)
    if localizer and np.head is not None and not np.head.proper and inner not in PLACE_NOUNS and \
            not inner.endswith(tuple(PLACE_NOUNS)):
        inner += localizer
    return prep + inner


def prepositional(np, passive=False):
    """前置詞句 → (動詞の前に置く句, 動詞の後ろに置く行き先)"""
    import dataclasses
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        return '被' + noun_phrase(inner), ''
    if np.prep is not None and np.prep.lang == 'zh' and np.prep.surface:   # 元の介詞と方位詞 (在花园里)
        localizer = np.prep.desc[len('localizer:'):] if np.prep.desc.startswith('localizer:') else ''
        if np.prep.surface == '到':   # 跑到家里: 行き先は動詞の後ろ
            return '', noun_phrase(inner) + localizer
        return np.prep.surface + noun_phrase(inner) + localizer, ''
    prep, localizer = PREPOSITIONS.get((np.prep.lemma, np.case), ('在', '里')) if np.prep is not None else ('在', '里')
    if prep == '到':
        return '', _place(inner, '', localizer)   # 行き先は動詞の後ろ (去罗马・走到花园里)
    text = _place(inner, prep, localizer)
    return text, ''


# ----------------------------------------------------------------------
# 節

def _verb(clause):
    found = word(clause.verb, 'verb')
    return found or '[%s]' % english.word(clause.verb)


# 場所の 在 + 名詞を動詞の後ろに置く動詞 (住在北京「北京に住む」)
POSTVERBAL_ZAI = {'住', '坐', '站', '躺', '停', '留', '放', '生', '活', '掉', '落'}


SOURCE_MODALS = ('可以', '应该', '必须', '愿意', '会', '能', '想', '要', '得')


def realize(clause, gap=None, infinitive=False):
    """節 → 語の列 (中国語は空白なしでつなぐ)"""
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    from .frame import dative_as_object
    clause = dative_as_object(clause, 'zh')   # grātiās agit magistrō → 感谢老师 (受け手を目的語に)
    if clause.question and clause.question_word and clause.mood == 'indicative' and gap is None and not infinitive:
        return [_question(clause)]   # 直接の疑問文 (疑問詞はその場に)
    subject = (clause.role('subject') or [None])[0]
    out = []
    if subject is not None and gap != 'subject' and not infinitive:
        out.append(noun_phrase(subject))
    elif subject is None and gap is None and clause.mood not in ('imperative', 'infinitive') and not infinitive:
        out.append({(1, 'sg'): '我', (1, 'pl'): '我们', (2, 'sg'): '你', (2, 'pl'): '你们', (3, 'sg'): '他',
                    (3, 'pl'): '他们'}.get((clause.person or 3, clause.number or 'sg'), '他'))
    adverbs = [word(a, 'adv') for a in clause.adverbs if a.lemma != 'nōn']
    out += [a for a in adverbs if a in TIME_WORDS]
    rest = [a for a in adverbs if a not in TIME_WORDS]
    before, after = [], []
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            b, a = prepositional(np, clause.voice == 'passive')
            before += [b] if b else []
            after += [a] if a else []
            continue
        if np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            before.append(WORDS[np.head.lemma])
            continue
        text = noun_phrase(np)
        if not text:
            continue
        if role == 'means':   # 受動の動作主 (人) は 被、ほかは手段 用
            before.append(('被' if np.animate and clause.voice == 'passive' else '用') + text)
        elif role == 'possessor':
            before.append('为' + text)
        else:
            before.append('在' + text)
    perfect = clause.tense in ('perfect', 'past-perfect', 'future-perfect')
    negation = ''
    if clause.negated:
        negation = '别' if clause.mood == 'imperative' else '没' if perfect and not clause.copula else '不'
    if clause.copula:
        complements = clause.role('complement')
        owner = (clause.role('recipient') or [None])[0]
        have = ('没' if clause.negated else '') + '有'
        if not complements and subject is not None and owner is not None and gap is None:
            return [noun_phrase(owner)] + rest + [have, _indefinite(subject)]   # 所有の与格 (Mihi est liber「我有一本书」)
        if not complements and subject is not None and gap is None:
            if before and subject.definite is False and before[0].startswith('在'):
                return [before[0][1:]] + rest + [have, _indefinite(subject)]   # 不定の主語は存在の文 (桌子上有一本书)
            if before:   # 場所の繋辞: 主語 + 在 + 場所 (他在花园里)
                return out + rest + [negation] + before
            return rest + [have, _indefinite(subject)]   # 存在の文 (有 + 名詞)
        comp = complements[0] if complements else None
        adjectival = comp is not None and (all(m.head is not None and m.head.pos in ('adj', 'participle')
                                               for m in comp.members) if comp.members else
                                           comp.head is not None and comp.head.pos in ('adj', 'participle'))
        if adjectival:   # 形容詞の述語は 很 + 形容詞 (玫瑰很美)
            forms = [_adjective(m.head) for m in comp.members] if comp.members else [_adjective(comp.head)]
            text = '又'.join(forms) if len(forms) > 1 else forms[0]
            return out + rest + before + ([negation] if negation else ['很'] if len(forms) == 1 else []) + [text]
        return out + rest + before + [negation, '是', noun_phrase(comp) if comp is not None else '']
    verb = _verb(clause)
    if clause.mood == 'infinitive' or infinitive:
        pass
    modal = MODALS.get(clause.verb.lemma) if clause.verb.lang in ('', 'la') else None
    if modal:   # 元が中国語の文なら元の助動詞 (会说 の 会。possum は 能 にする)
        modal = next((m for m in SOURCE_MODALS if (clause.verb.surface or '').startswith(m)), modal)
    if modal and len(clause.infinitives) == 1 and not clause.infinitives[0].role('subject'):
        inner = clause.infinitives[0]
        inner_words = realize(inner, gap='subject', infinitive=True)
        return out + rest + [negation, modal] + inner_words
    obj = (clause.role('object') or [None])[0]
    recipients = clause.role('recipient')
    objects = []
    if obj is not None and gap != 'object':
        objects.append(noun_phrase(obj))
    tense_before = '已经' if clause.tense == 'past-perfect' else '会' if clause.tense in ('future', 'future-perfect') \
        else ''
    passive = clause.voice == 'passive'
    if passive and not any(b.startswith('被') for b in before):
        before.insert(0, '被')
    for np in recipients:
        if verb in DOUBLE_OBJECT:
            objects.insert(0, noun_phrase(np))
        else:
            before.append('给' + noun_phrase(np))
    aspect = '了' if perfect and not clause.negated and gap is None else ''   # 関係節には付けない (我买的书)
    if after and verb in ('去', '回'):   # 去罗马・回家 (行き先をそのまま)
        verb_words = [verb + aspect] + after + objects
    elif after:   # 走到城镇・来到别墅 (到 + 行き先)
        verb_words = [verb + '到' + aspect] + after + objects
    elif verb in POSTVERBAL_ZAI and any(b.startswith('在') for b in before):   # 住在北京・坐在椅子上
        place = next(b for b in before if b.startswith('在'))
        before = [b for b in before if b is not place]
        verb_words = [verb + place + aspect] + objects
    else:
        verb_words = [verb + aspect] + objects
    complements = []
    for inner in clause.infinitives:
        if inner.role('subject'):   # 補文 (我知道你来)・知覚 (我看见女孩唱歌): 接続詞なし
            complements.append(''.join(realize(dataclasses.replace(inner, mood='indicative'))))
        else:
            complements.append(''.join(realize(inner, gap='subject', infinitive=True)))
    before = [_adverbial_participle(p) for p in clause.adjuncts if p.kind != 'absolute'] + before
    for inner in clause.questions:
        complements.append(_question(inner))
    if clause.mood == 'imperative':
        return [negation] + rest + before + verb_words + complements
    return out + [tense_before] + rest + [negation] + before + verb_words + complements


def _participle_verb(p):
    return Lex(p.verb.verb, 'verb', p.verb.verb_ja, lang=p.verb.lang) if p.verb.verb else None


def _attributive_participle(p):
    """名詞に掛かる分詞 (的 は呼ぶ側で): 動詞句 (逃跑)、過去の受動は 被 + 動詞 (被写)"""
    lex = _participle_verb(p)
    if lex is None:
        return word(p.verb, 'adj')
    voice = 'passive' if p.voice == 'passive' and p.tense != 'present' else 'active'
    args = [(r, np) for r, np in p.args if r != 'subject']
    return ''.join(realize(Clause(lex, voice=voice, args=args), gap='subject', infinitive=True))


def _adverbial_participle(p):
    """述語的な分詞句: 現在は 動詞 + 着 (摘着花)、過去は 動詞 + 了 + 以后、過去の受動は 被 + 動詞 (被使者的话感动)"""
    lex = _participle_verb(p)
    if lex is None:
        return word(p.verb, 'adj')
    args = [(r, np) for r, np in p.args if r != 'subject']
    if p.voice == 'passive' and p.tense != 'present':
        agents = [np for r, np in args if r in ('means', 'prep')]
        others = [(r, np) for r, np in args if r not in ('means', 'prep')]
        verb = word(lex, 'verb')
        return '被' + ''.join(noun_phrase(np) for np in agents[:1]) + ''.join(
            realize(Clause(lex, args=others), gap='subject', infinitive=True)) if verb else ''
    text = ''.join(realize(Clause(lex, args=args), gap='subject', infinitive=True))
    verb = word(lex, 'verb')
    if p.tense == 'present':
        return text.replace(verb, verb + '着', 1) if verb and verb in text else text
    return text + '以后'


def absolute(p):
    """独立奪格: 現在は 節 + 的时候 (女孩唱歌的时候)、過去は 節 + 以后 (国王死了以后)"""
    lex = _participle_verb(p)
    if lex is None or p.subject is None:
        return ''
    args = [('subject', p.subject)] + [(r, np) for r, np in p.args if r != 'subject']
    if p.tense == 'present':
        return ''.join(realize(Clause(lex, args=args))) + '的时候'
    voice = 'passive' if p.voice == 'passive' else 'active'
    return ''.join(realize(Clause(lex, tense='perfect', voice=voice, args=args))) + '以后'


PRONOUN_WORDS = {'我', '你', '他', '她', '它', '我们', '你们', '他们', '她们', '它们'}


def _question(inner):
    """間接疑問・直接の疑問文: 節のまま (疑問詞は元の位置: 我不知道他住在哪里、他什么时候来、女孩在哪里)。
    疑問の副詞は主語の後ろ、疑問詞の無い間接疑問は 是否"""
    import dataclasses
    from .frame import where_is
    word_ = QUESTION_WORDS.get(inner.question_word)
    finite = dataclasses.replace(inner, mood='indicative', question_word='', question=False)
    if word_ and where_is(inner) is not None:
        return noun_phrase(where_is(inner)) + word_   # 女孩在哪里 (有 の存在の文にしない)
    words = [w for w in realize(finite) if w]
    text = ''.join(words)
    if word_ is None:
        return text
    if not word_:
        return '是否' + text
    if word_.startswith(('在', '到', '从')) and words[-1:] and words[-1] in POSTVERBAL_ZAI:
        return text + word_   # 住在哪里
    subject = 1 if words and (inner.role('subject') and not inner.role('subject')[0].interrogative or
                              words[0] in PRONOUN_WORDS) else 0
    return ''.join(words[:subject]) + word_ + ''.join(words[subject:])


def wrap(text, clause, last):
    sub = SUBORDINATORS.get(clause.subordinator) if not last else None
    if sub:
        text = sub[0] + text + sub[1]
    words = [CONNECTIVES[k] for k in clause.connectives if k in CONNECTIVES]
    return ''.join(words) + text


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address, subordinate_first
    clauses = subordinate_first(clauses)
    parts = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        address = '，'.join(''.join(noun_phrase(np) for np in group) for group in groups)
        text = wrap(''.join(w for w in realize(rest) if w), rest, k + 1 == len(clauses))
        absolutes = [absolute(p) for p in rest.adjuncts if p.kind == 'absolute']
        parts.append((address + '，' if address else '') + ''.join(a + '，' for a in absolutes if a) + text)
    text = '，'.join(parts)
    if any(c.question for c in clauses) and not any(c.question_word or _has_interrogative(c) for c in clauses):
        return text + '吗。'   # 文末の印は frame.punctuate で？に
    return text + '。'


def _has_interrogative(clause):
    return any(np.head is not None and np.head.lemma in ('quis', 'quid') for _, np in clause.args) or \
        any(a.lemma in QUESTION_WORDS for a in clause.adverbs)


# ----------------------------------------------------------------------
# 比較の表

PRO_DROP_HOW = '代名詞を補う (我・他 …)'
PREDICATE_HOW = '語形は変えない。完了は 動詞 + 了、未来 会、否定 不 / 没、受動 被'
COPULA_HOW = '名詞は 是 + 補語、形容詞は 很 + 形容詞 (繋辞なし)、場所は 在、存在は 有'
ADDRESS_HOW = 'そのまま'


def compare_np(role, np, clause):
    if role == 'prep' and np.prep is not None:
        before, after = prepositional(np, clause.voice == 'passive')
        return (before or '到' + after), ('動詞の前の介詞 %s' % before[:1] if before else '動詞の後ろの行き先')
    if role == 'address':
        return noun_phrase(np), ADDRESS_HOW
    if role == 'subject':
        return noun_phrase(np), '動詞の前 (格の印なし)'
    if role == 'object':
        return noun_phrase(np), '動詞の後ろ (格の印なし)'
    if role == 'recipient':
        return ('给' + noun_phrase(np)), '介詞 给 (動詞の前。给・送・告诉 は目的語の前)'
    if role == 'possessor':
        return noun_phrase(np) + '的', '的 (名詞の前)'
    if role == 'means':
        return '用' + noun_phrase(np), '介詞 用 (動詞の前)'
    return '在' + noun_phrase(np), '介詞 在 (動詞の前)'


def compare_predicate(clause, reduced):
    if clause.copula:
        words = realize(reduced)
        subject = (clause.role('subject') or [None])[0]
        head = noun_phrase(subject) if subject is not None else ''
        text = ''.join(w for w in words if w)
        return (text[len(head):] if head and text.startswith(head) else text), COPULA_HOW
    perfect = clause.tense in ('perfect', 'past-perfect', 'future-perfect')
    verb = _verb(clause)
    negation = ('没' if perfect else '不') if clause.negated else ''
    return negation + ('被' if clause.voice == 'passive' else '') + verb + ('了' if perfect and not clause.negated else ''), \
        PREDICATE_HOW
