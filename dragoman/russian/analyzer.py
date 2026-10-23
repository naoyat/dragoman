#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ロシア語の文の解析
#
# 辞書引き (pymorphy3 の解析、russian/morphology.py) と動詞の読みの選択だけをここで行い、並列・係り先・前置詞句・
# 格の枠・日本語訳はラテン語と共通の解析器 (core/analyzer.py) を、ロシア語の設定 (RUSSIAN) で使う
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '(': 'comma', ')': 'comma', '«': None, '»': None,
               '"': None, '„': None, '“': None}
TOKEN = re.compile(r"[а-яёА-ЯЁ́̀]+(?:-[а-яёА-ЯЁ́̀]+)*|[A-Za-z]+|\d+|[.!?…,;:—–()«»\"„“]")


def _root_items(lemma):
    """見出し語 (動詞の不定形) の訳語 (分詞の元の動詞の訳語に使う)"""
    return [{'pos': 'verb', 'ja': l['ja'], 'gloss_lang': l['gloss_lang']}
            for l in dictionary.lemmas(lemma) if l['pos'] == 'verb']


# 副詞節の従属接続詞 → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py)。いくつかの語のものは1語にまとめる
SUBORDINATORS = {'когда': ('とき', None), 'если': ('なら', None), 'потому что': ('ので', None), 'так как': ('ので', None),
                 'поскольку': ('ので', None), 'хотя': ('けれども', None), 'пока': ('間に', None),
                 'после того как': ('後で', 'perfect'), 'до того как': ('前に', 'present'),
                 'перед тем как': ('前に', 'present'), 'как только': ('とすぐに', None), 'с тех пор как': ('以来', None),
                 'в то время как': ('一方で', None)}


RUSSIAN = language.Language(
    name='ru',
    subordinators=SUBORDINATORS,
    and_words=('и',),
    nor_words=('ни',),
    or_words=('или',),
    copulas=frozenset({'быть'}),
    negations=frozenset({'не', 'нет'}),
    case_particles={'Nom': 'が', 'Gen': 'の', 'Dat': 'に', 'Acc': 'を', 'Ins': 'で', 'Loc': 'で', 'Voc': 'よ'},
    absolute_case=None,  # 独立格の構文は無い (古代ロシア語の独立与格を除く)
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
)


def tokens(text):
    return TOKEN.findall(text)


def sentences(text):
    """テキストを文に分け、各文の語の列を返す"""
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def _word(token):
    if token in PUNCTUATION:
        return Word(token, None)
    return Word(token, morphology.analyze(token))


FINITE_MOODS = ('indicative', 'imperative')


def _finite(item):
    return item.pos == 'verb' and item.attrib('mood') in FINITE_MOODS


def choose_verbs(words):
    """定動詞の読みが一番の語は動詞に絞る (стали: 動詞 стать の過去複数と、名詞 сталь「鋼」の属格)"""
    for word in words:
        if word.items and _finite(word.items[0]):
            word.items = [item for item in word.items if _finite(item)]


def prefer_governed_cases(words):
    """前置詞の後ろの語は、前置詞の支配する格の読みを先にする (из дома: 副詞 дома「家で」より名詞 дом の属格)"""
    for i, word in enumerate(words):
        cases = {item.attrib('dominates') for item in word.items or [] if item.pos == 'preposition'}
        if not cases:
            continue
        for following in words[i + 1:i + 4]:
            if not following.items:
                break
            governed = [item for item in following.items
                        if item._ and any(cng[0] in cases for cng in item._)]
            if not governed:
                break
            following.items = governed + [item for item in following.items if item not in governed]
            if governed[0].pos in ('noun', 'pronoun'):
                break  # 名詞まで (間の形容詞も同じように)


COPULA = {'pos': 'verb', 'pres1sg': 'быть', 'base': 'быть', 'ja': '在る,居る', 'gloss_lang': 'ja', 'aspect': 'impf',
          'voice': 'active', 'mood': 'indicative', 'tense': 'present', 'person': 3, 'number': 'sg',
          'desc': '省略された繋辞'}


def _genitive(word):
    return bool(word.items) and any(cng[0] == 'Gen' for cng in word.items[0]._ or [])


def _nominative(word):
    return bool(word.items) and word.items[0].pos in ('noun', 'pronoun', 'adj') and \
        any(cng[0] == 'Nom' for cng in word.items[0]._ or [])


def supply_copula(words):
    """現在形の繋辞は書かない (Он студент「彼は学生だ」, Москва — столица「モスクワは首都だ」)。
    定動詞が無く、主格の名詞類が2つ以上 (か短語尾形容詞が) あれば、見えない繋辞 быть を補う。
    ダッシュ (—) があればそこに、無ければ最初の主格の名詞類の後ろに"""
    if any(w.items and w.items[0].pos == 'verb' and w.items[0].attrib('mood') in FINITE_MOODS for w in words):
        return words
    noms = [i for i, w in enumerate(words) if _nominative(w)]
    short = [i for i, w in enumerate(words) if w.items and w.items[0].attrib('desc') == '短語尾']
    if len(noms) < 2 and not (noms and short):
        return words
    dash = next((i for i, w in enumerate(words) if w.surface in ('—', '–') and noms[0] < i), None)
    copula = Word('(есть)', [dict(COPULA, surface='(есть)')])
    if dash is not None:
        return words[:dash] + [copula] + words[dash + 1:]
    at = noms[0] + 1
    while at < len(words) and words[at].items and words[at].items[0].pos == 'noun' and \
            any(cng[0] == 'Gen' for cng in words[at].items[0]._ or []):
        at += 1  # 主語に掛かる属格の後ろへ
    return words[:at] + [copula] + words[at:]


def merge_compound_verbs(words):
    """быть と組になる動詞の形を1語にまとめる:
    был напечатан (быть の過去 + 短語尾分詞)「印刷された」、будет читать (быть の未来 + 不定形)「読むだろう」"""
    out = []
    i = 0
    while i < len(words):
        word = words[i]
        nxt = words[i + 1] if i + 1 < len(words) else None
        aux = word.items[0] if word.items and word.items[0].pos == 'verb' and \
            word.items[0].attrib('pres1sg') == 'быть' else None
        if aux is not None and nxt is not None and nxt.items:
            main = nxt.items[0]
            merged = None
            if main.pos == 'verb' and main.attrib('voice') == 'passive' and aux.attrib('tense') in ('imperfect', 'perfect', 'future'):
                tense = 'future' if aux.attrib('tense') == 'future' else 'perfect'
                merged = dict(main.item, tense=tense)
            elif main.pos == 'verb' and main.attrib('mood') == 'infinitive' and aux.attrib('tense') == 'future':
                merged = dict(main.item, mood='indicative', tense='future', person=aux.attrib('person'),
                              number=aux.attrib('number'))
            if merged:
                merged['surface'] = word.surface + ' ' + nxt.surface
                combined = Word(merged['surface'], [merged])
                combined.token_ix = getattr(nxt, 'token_ix', None)  # 本動詞の位置 (UD でも был は助動詞)
                out.append(combined)
                i += 2
                continue
        out.append(word)
        i += 1
    return out


MODALS = {'хотеть', 'надо', 'нужно', 'можно', 'нельзя', 'мочь', 'любить', 'начать', 'начинать', 'стать', 'быть'}


def choose_est(words):
    """есть は быть の現在形「ある」を先に。ただし хочу есть「食べたい」のように動詞・述語副詞の後ろでは「食べる」"""
    for i, word in enumerate(words):
        if word.surface.lower() != 'есть' or not word.items:
            continue
        prev = words[i - 1].items[0] if i > 0 and words[i - 1].items else None
        if prev is not None and (prev.pos == 'verb' or prev.attrib('base') in MODALS):
            word.items = [item for item in word.items if not item.attrib('existential')] + \
                [item for item in word.items if item.attrib('existential')]


def _possessive_preposition(words):
    """存在・所有の文の у + 生格 (у меня есть книга「私には本がある」) は「〜には」と訳す"""
    for word in words:
        if word.surface.lower() == 'у' and word.items:
            for item in word.items:
                if item.pos == 'preposition':
                    item.ja = '〜には'
                    item.item['ja'] = '〜には'


def negative_existence(words):
    """нет / не было / не будет + 生格「〜が無い」: 主格の名詞類が無ければ、生格の名詞を主語として読む
    (У меня нет книги「私には本が無い」)。нет だけなら見えない繋辞を補う"""
    surfaces = [w.surface.lower() for w in words]
    has_net = 'нет' in surfaces
    negated_byt = any(s == 'не' and i + 1 < len(words) and words[i + 1].items and
                      words[i + 1].items[0].attrib('pres1sg') == 'быть' for i, s in enumerate(surfaces))
    # 生格とも読める主格 (книги: 生格単数 / 主格複数) は主語の候補に数えない
    if not (has_net or negated_byt) or any(_nominative(w) and not _genitive(w) for w in words):
        return words
    for i, word in enumerate(words):
        if not word.items or word.items[0].pos not in ('noun', 'pronoun') or common._after_genitive_preposition(words, i):
            continue
        item = word.items[0]
        gen = [c for c in item._ or [] if c[0] == 'Gen']
        if gen:
            item._ = gen + [c for c in item._ if c[0] != 'Gen']  # 生格の読みを先に
        if item._ and item._[0][0] == 'Gen':
            item._ = [('Nom',) + tuple(item._[0][1:])] + item._  # 存在の否定の主語
            for adj in words[max(0, i - 3):i]:
                if adj.items and adj.items[0].pos == 'adj' and adj.items[0]._ and adj.items[0]._[0][0] == 'Gen':
                    adj.items[0]._ = [('Nom',) + tuple(c[1:]) for c in adj.items[0]._ if c[0] == 'Gen'] + adj.items[0]._
    if has_net:
        at = surfaces.index('нет')
        copula = Word('(есть)', [dict(COPULA, surface='(есть)', existential=True)])
        words = words[:at + 1] + [copula] + words[at + 1:]
    else:
        for word in words:
            if word.items and word.items[0].attrib('pres1sg') == 'быть':
                word.items[0].item['existential'] = True
    _possessive_preposition(words)
    return words


def mark_existential(words):
    """есть / был があって у + 生格がある文 (所有) は у を「〜には」と訳す"""
    if any(w.items and w.items[0].attrib('pres1sg') == 'быть' for w in words) and \
            any(w.surface.lower() == 'у' for w in words):
        _possessive_preposition(words)


# 譲歩の構文「疑問詞 + бы … ни + 動詞」(Сколько бы нитей ни плёл обман「嘘が どれほど 糸を 紡いでも」) の疑問詞の訳
CONCESSIVE_WORDS = {'сколько': 'どれほど', 'что': '何を', 'как': 'どんなに', 'где': 'どこで', 'куда': 'どこへ',
                    'когда': 'いつ', 'кто': '誰が', 'какой': 'どんな', 'какая': 'どんな', 'какое': 'どんな',
                    'какие': 'どんな', 'откуда': 'どこから', 'чей': '誰の'}


def particle_by(words):
    """бы (縮めた形 б) の構文:
    疑問詞 + бы … ни (не と書かれても) + 動詞 → 譲歩「どれほど〜しても」(ни・бы は落とし、сколько の後ろの属格は目的語に)、
    ほかは過去形 + бы → 条件法「〜するだろう」(Я бы пошёл「私は 行くだろう」)"""
    out = list(words)
    for k, w in enumerate(words):
        if w.surface.lower() not in ('бы', 'б') or w not in out:
            continue
        clause_start = k
        while clause_start > 0 and words[clause_start - 1].items is not None:
            clause_start -= 1
        question = next((q for q in reversed(words[clause_start:k]) if q.surface.lower() in CONCESSIVE_WORDS), None)
        verb_ix = next((j for j in range(k + 1, len(words)) if words[j].items and words[j].items[0].pos == 'verb'), None)
        negator = next((x for x in words[k + 1:verb_ix] if x.surface.lower() in ('ни', 'не')), None) \
            if verb_ix is not None else None
        out.remove(w)
        w.merged_into = True
        if verb_ix is None:
            continue
        verb = words[verb_ix]
        dropped = [w] + ([negator] if question is not None and negator is not None else [])
        if question is not None and negator is not None:
            out.remove(negator)
            negator.merged_into = True
            verb.items = [type(i)(dict(i.item, concessive=True, form='譲歩 (疑問詞 + бы … %s + 動詞「〜しても」)'
                                       % negator.surface.lower())) for i in verb.items]
            q = question.items[0] if question.items else None
            if q is not None:
                question.items = [type(q)(dict(q.item, pos='adv', ja=CONCESSIVE_WORDS[question.surface.lower()],
                                               gloss_lang='ja', _=None))]
            if question.surface.lower() == 'сколько':   # сколько + 属格 (сколько нитей「どれほど 糸を」)
                for x in words[words.index(question) + 1:verb_ix]:
                    if x.items and x.items[0].pos == 'noun' and any(c == 'Gen' for c, _, _ in x.items[0]._ or []):
                        x.items = [type(i)(dict(i.item, _=[('Acc',) + t[1:] for t in i._ if t[0] == 'Gen']))
                                   for i in x.items if i._ and any(t[0] == 'Gen' for t in i._)] or x.items
                        break
        elif any(i.attrib('tense') in ('perfect', 'imperfect', 'past') for i in verb.items):
            verb.items = [type(i)(dict(i.item, tense='future', conditional=True, form='条件法 (бы + 過去形)'))
                          for i in verb.items]   # 条件法
        else:
            continue
        verb.surface = ' … '.join(x.surface for x in dropped) + ' ' + verb.surface   # 語の表に落とした語も (б … ни плёл)
    return out



def compound_conjunctions(words):
    """いくつかの語の接続詞 (потому что・после того как …) を1語の接続詞に (後ろの語は落とす。表示は全部の語で)"""
    compounds = sorted((k.split() for k in SUBORDINATORS if ' ' in k), key=len, reverse=True)
    out, k = [], 0
    while k < len(words):
        lower = [w.surface.lower() for w in words[k:k + 4]]
        parts = next((c for c in compounds if lower[:len(c)] == c), None)
        word = words[k]
        if parts is None or not word.items:
            out.append(word)
            k += 1
            continue
        item = word.items[0]
        base = ' '.join(parts)
        word.items = [type(item)(dict(item.item, pos='conj', base=base, ja='', _=None))]
        word.surface = ' '.join(w.surface for w in words[k:k + len(parts)])
        out.append(word)
        k += len(parts)
    return out


def question_when(words):
    """疑問文の頭の когда は疑問詞「いつ」(Когда он пришёл?。接続詞「〜するとき」でなく)"""
    marks = [w.surface for w in words if w.surface.strip()]
    if not marks or marks[-1] != '?' or ',' in marks:
        return
    first = words[0]
    if first.surface.lower() == 'когда' and first.items:
        item = first.items[0]
        first.items = [type(item)(dict(item.item, pos='adv', ja='いつ', gloss_lang='ja', _=None))]


def lookup_all(surfaces):
    words = [_word(s) for s in surfaces]
    choose_est(words)
    for ix, word in enumerate(words):
        word.token_ix = ix  # 元の語の位置 (補った繋辞には無い)
    choose_verbs(words)
    words = merge_compound_verbs(words)
    prefer_governed_cases(words)
    words = particle_by(words)
    words = negative_existence(words)
    words = supply_copula(words)
    mark_existential(words)
    words = compound_conjunctions(words)
    question_when(words)
    for i, word in enumerate(words):
        word.index = i
    return words


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(RUSSIAN):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)   # 元の文の語の列 (見出し・音読・カタカナ読み: 解析で落とした б・ни も)
    return analysis


def analyze_text(text):
    from .script import from_latin
    text = from_latin(text)   # ラテン文字の転写の入力はキリル文字に直して読む (Ja ljubljú tebjá → Я люблю тебя)
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
