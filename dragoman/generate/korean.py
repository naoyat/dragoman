#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から韓国語の文を作る (한다体: 書き言葉の普通の文体)
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)
#   語順: 主語 - 受け手 - 目的語 - 後置詞句 - 動詞 (SOV)。助詞は前の語の終声 (パッチム) で形を選ぶ: 이 / 가・을 / 를・
#     은 / 는・와 / 과・으로 / 로
#   用言: 現在 -ㄴ다 / -는다 (形容詞は -다)、過去 -았다 / -었다 (母音の縮約: 가 + 았 → 갔、마시 + 었 → 마셨)、
#     未来 -ㄹ 것이다、否定 안 + 用言、命令 -아라 / -어라。繋辞 이다 (否定 아니다)
#   連体形 (関係節・形容詞の修飾): 動詞の過去 -ㄴ / -은・現在 -는、形容詞 -ㄴ / -은 (아름답다 → 아름다운)
#
import dataclasses
import functools
import re

from . import transfer, english
from .frame import NP

PRONOUNS = {('ego', 'sg'): '나', ('ego', 'pl'): '우리', ('tū', 'sg'): '너', ('tū', 'pl'): '너희', ('is', 'sg'): '그',
            ('is', 'pl'): '그들', ('sē', 'sg'): '자기', ('sē', 'pl'): '자기들', ('quis', 'sg'): '누구', ('quid', 'sg'): '무엇',
            ('hic', 'sg'): '이것', ('ille', 'sg'): '그것', ('hic', 'pl'): '이것들', ('ille', 'pl'): '그것들'}
FEMININE_PRONOUNS = {('is', 'sg'): '그녀', ('is', 'pl'): '그녀들'}
DETERMINERS = {'hic': '이', 'hīc': '이', 'iste': '그', 'ille': '그', 'is': '그', 'omnis': '모든', 'alius': '다른',
               'tōtus': '모든'}
POSSESSIVES = {'meus': '나의', 'tuus': '너의', 'suus': '자기의', 'noster': '우리의', 'vester': '너희의'}
NUMERALS = {'ūnus': '한', 'duo': '두', 'trēs': '세', 'quattuor': '네', 'quīnque': '다섯', 'decem': '열', 'centum': '백'}
# ラテン語の前置詞 + 格 → 後置詞 (助詞)。(終声のある語の後ろ, 無い語の後ろ) か1つの形
POSTPOSITIONS = {('in', 'Abl'): '에서', ('in', 'Acc'): '에', ('ad', 'Acc'): '에', ('ex', 'Abl'): '에서',
                 ('ē', 'Abl'): '에서', ('ab', 'Abl'): '에서', ('ā', 'Abl'): '에서', ('cum', 'Abl'): ('과 함께', '와 함께'),
                 ('dē', 'Abl'): '에 대해', ('sine', 'Abl'): ' 없이', ('per', 'Acc'): ('을 통해', '를 통해'),
                 ('propter', 'Acc'): ' 때문에', ('ob', 'Acc'): ' 때문에', ('post', 'Acc'): ' 후에', ('ante', 'Acc'): ' 전에',
                 ('sub', 'Abl'): ' 아래에', ('super', 'Acc'): ' 위에', ('prō', 'Abl'): '을 위해', ('apud', 'Acc'): '에게',
                 ('contrā', 'Acc'): '에 반대해', ('inter', 'Acc'): ' 사이에', ('prope', 'Acc'): ' 근처에'}
CONNECTIVES = {'et': '그리고', 'que': '그리고', 'atque': '그리고', 'ac': '그리고', 'sed': '그러나', 'at': '그러나',
               'autem': '그런데', 'enim': '왜냐하면', 'nam': '왜냐하면', 'igitur': '그래서', 'itaque': '그래서',
               'tamen': '그래도', 'tum': '그때', 'deinde': '그 다음에', 'aut': '또는', 'vel': '또는'}
SUBORDINATORS = {'ubi': '때', 'cum': '때', 'postquam': '후에', 'dum': '동안', 'quod': '때문에', 'quia': '때문에',
                 'sī': '면', 'ut': '도록', 'nē': '지 않도록', 'quamquam': '지만', 'etsī': '지만', 'priusquam': '전에',
                 'antequam': '전에'}
WORDS = {'nōn': '안', 'semper': '항상', 'saepe': '자주', 'iam': '이미', 'nunc': '지금', 'hodiē': '오늘', 'crās': '내일',
         'heri': '어제', 'ibi': '거기서', 'hīc': '여기서', 'etiam': '도', 'quoque': '도', 'valdē': '매우', 'magnopere': '매우',
         'statim': '곧', 'mox': '곧', 'tandem': '마침내', 'iterum': '다시', 'numquam': '결코', 'tum': '그때',
         'posteā': '그 후', 'diū': '오래', 'bene': '잘', 'male': '나쁘게'}


# ----------------------------------------------------------------------
# ハングルの字母

def _jamo(c):
    code = ord(c) - 0xAC00
    if not 0 <= code < 11172:
        return None
    return code // 588, (code % 588) // 28, code % 28


def _compose(initial, vowel, final=0):
    return chr(0xAC00 + initial * 588 + vowel * 28 + final)


def has_final(word):
    """語の最後の音節に終声 (パッチム) があるか (英語・数字は無いものとして)"""
    j = _jamo(word[-1]) if word else None
    return bool(j and j[2])


def final_is_rieul(word):
    j = _jamo(word[-1]) if word else None
    return bool(j and j[2] == 8)


def particle(word, with_final, without_final):
    """終声で助詞を選ぶ: particle('책', '을', '를') → 책을"""
    return word + (with_final if has_final(word) else without_final)


def _add_final(word, final):
    """最後の音節に終声を足す (가 + ㄴ → 간)。終声があれば None"""
    j = _jamo(word[-1])
    if j is None or j[2]:
        return None
    return word[:-1] + _compose(j[0], j[1], final)


FINAL_N, FINAL_L, FINAL_SS, FINAL_B = 4, 8, 20, 17
# 母音: ㅏ0 ㅐ1 ㅑ2 ㅒ3 ㅓ4 ㅔ5 ㅕ6 ㅖ7 ㅗ8 ㅘ9 ㅙ10 ㅚ11 ㅛ12 ㅜ13 ㅝ14 ㅞ15 ㅟ16 ㅠ17 ㅡ18 ㅢ19 ㅣ20
BRIGHT = {0, 2, 8}   # 陽母音 (ㅏ・ㅑ・ㅗ): 았 / 아


def _stem(lemma):
    return lemma[:-1] if lemma.endswith('다') else lemma


def _bright(stem):
    for k, c in enumerate(reversed(stem)):
        j = _jamo(c)
        if j and (j[1] != 18 or j[2] or k > 0 and False):
            # 終声の無い最後の ㅡ は前の音節の母音で決める (예쁘 → 예뻐、아프 → 아파)。만들 の 들 は陰母音
            return j[1] in BRIGHT
    return False


def infinitive(lemma):
    """連用形 (아 / 어 形): 읽 → 읽어、가 → 가、오 → 와、마시 → 마셔、하 → 해、아름답 → 아름다워"""
    stem = _stem(lemma)
    if not stem:
        return lemma
    if stem.endswith('하'):
        return stem[:-1] + '해'
    last = _jamo(stem[-1])
    if last is None:
        return stem + '어'
    initial, vowel, final = last
    bright = _bright(stem)
    head = stem[:-1]
    if final:
        if final == FINAL_B and lemma not in ('입다', '잡다', '좁다', '씹다', '뽑다'):   # ㅂ 不規則 (아름답다 → 아름다워)
            return head + _compose(initial, vowel) + ('와' if lemma in ('돕다', '곱다') else '워')
        if final == 7 and lemma in ('듣다', '걷다', '묻다', '깨닫다', '싣다'):   # ㄷ 不規則 (듣다 → 들어)
            return head + _compose(initial, vowel, FINAL_L) + '어'
        return stem + ('아' if bright else '어')
    if stem.endswith('르') and len(stem) >= 2 and lemma not in ('따르다', '치르다'):   # 르 不規則 (모르다 → 몰라)
        prev = _jamo(stem[-2])
        if prev:
            return stem[:-2] + _compose(prev[0], prev[1], FINAL_L) + ('라' if prev[1] in BRIGHT else '러')
    if vowel in (0, 4, 1, 5):        # ㅏ・ㅓ・ㅐ・ㅔ: そのまま (가 → 가、서 → 서、내 → 내)
        return stem
    if vowel == 8:                    # ㅗ → ㅘ (오 → 와、보 → 봐)
        return head + _compose(initial, 9)
    if vowel == 13:                   # ㅜ → ㅝ (주 → 줘)
        return head + _compose(initial, 14)
    if vowel == 20:                   # ㅣ → ㅕ (마시 → 마셔)
        return head + _compose(initial, 6)
    if vowel == 11:                   # ㅚ → ㅙ (되 → 돼)
        return head + _compose(initial, 10)
    if vowel == 18:                   # ㅡ の脱落 (쓰 → 써、예쁘 → 예뻐)
        return head + _compose(initial, 0 if bright else 4)
    return stem + ('아' if bright else '어')


def past(lemma):
    """過去形 (한다体): 읽었다、갔다、마셨다、했다、아름다웠다"""
    inf = infinitive(lemma)
    with_ss = _add_final(inf, FINAL_SS)
    return (with_ss or inf + '었') + '다'


def present(lemma, adjective=False):
    """現在形 (한다体): 動詞 읽는다・간다・산다 (ㄹ の脱落)、形容詞は辞書形 (예쁘다)"""
    stem = _stem(lemma)
    if adjective or lemma in ('있다', '없다') or not stem:
        return lemma
    if final_is_rieul(stem):   # 살다 → 산다
        j = _jamo(stem[-1])
        return stem[:-1] + _compose(j[0], j[1], FINAL_N) + '다'
    if has_final(stem):
        return stem + '는다'
    return _add_final(stem, FINAL_N) + '다'


IRREGULAR_B = ('입다', '잡다', '좁다', '씹다', '뽑다', '접다', '업다')   # 規則の ㅂ 語幹 (입어・입을)
IRREGULAR_D = ('듣다', '걷다', '묻다', '깨닫다', '싣다')                      # ㄷ 不規則 (들어・들을)


def _eu_stem(lemma):
    """으 で始まる語尾 (-을・-은) の前の語幹: ㅂ 不規則 (아름답 → 아름다우 + ㄹ)、ㄷ 不規則 (듣 → 들 + 을)。
    返り値: (語幹, 終声が残るか)"""
    stem = _stem(lemma)
    j = _jamo(stem[-1]) if stem else None
    if j and j[2] == FINAL_B and lemma not in IRREGULAR_B:
        return stem[:-1] + _compose(j[0], j[1]) + '우', False
    if j and j[2] == 7 and lemma in IRREGULAR_D:
        return stem[:-1] + _compose(j[0], j[1], FINAL_L), True
    return stem, has_final(stem) and not final_is_rieul(stem)


def future(lemma):
    """未来 (推量): 읽을 것이다・갈 것이다・들을 것이다・아름다울 것이다"""
    stem, consonant = _eu_stem(lemma)
    if final_is_rieul(stem) and not consonant:
        return stem + ' 것이다'
    if consonant:
        return stem + '을 것이다'
    return _add_final(stem, FINAL_L) + ' 것이다'


def adnominal(lemma, tense='present', adjective=False):
    """連体形: 動詞の過去 읽은・간、現在 읽는・가는、形容詞 예쁜・좋은・아름다운"""
    stem = _stem(lemma)
    if not stem:
        return lemma
    if lemma in ('있다', '없다') or (not adjective and tense not in ('perfect', 'past-perfect')):
        if final_is_rieul(stem):   # 살다 → 사는
            j = _jamo(stem[-1])
            return stem[:-1] + _compose(j[0], j[1]) + '는'
        return stem + '는'
    j = _jamo(stem[-1])
    if final_is_rieul(stem):   # 길다 → 긴、만들다 → 만든
        return stem[:-1] + _compose(j[0], j[1], FINAL_N)
    stem, consonant = _eu_stem(lemma)   # 아름답다 → 아름다운、듣다 → 들은
    if consonant:
        return stem + '은'
    return _add_final(stem, FINAL_N)


def imperative(lemma):
    return infinitive(lemma) + '라'


# ----------------------------------------------------------------------
# 語

def available():
    return transfer.available('ko')


def _adjective_lemma(word):
    from dragoman.korean import morphology
    try:
        return morphology.is_adjective(word)
    except Exception:
        return False


def to_korean(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'ko':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'ko')
        if found:
            return found[0]
        from .name_script import to_script
        return to_script('ko', lex.lemma) or lex.lemma
    target = transfer.best(lex, 'ko', pos)
    if target is None and pos == 'adj':
        target = transfer.best(lex, 'ko', 'verb')
    return target.lemma if target else None


def word(lex, pos=None):
    found = to_korean(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


def _pronoun(np):
    key = (np.head.lemma, 'pl' if np.number == 'pl' else 'sg')
    if np.gender == 'f' and key in FEMININE_PRONOUNS:
        return FEMININE_PRONOUNS[key]
    return PRONOUNS.get(key) or PRONOUNS.get((np.head.lemma, 'sg')) or word(np.head)


def noun_phrase(np):
    if np.members:
        parts = [noun_phrase(m) for m in np.members]
        if np.conj in ('aut', 'vel'):
            return ' 또는 '.join(parts)
        return ''.join(particle(p, '과 ', '와 ') for p in parts[:-1]) + parts[-1]
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        return _pronoun(np)
    before = []
    for g in np.genitives:
        before.append(noun_phrase(g) + '의')
    for r in np.relatives:
        before.append(relative_clause(r))
    for m in np.modifiers:
        if isinstance(m, NP):
            before.append(' '.join(_modifier(x.head) for x in m.members))
            continue
        before.append(_modifier(m))
    text = word(head, 'noun')
    counted = any(not isinstance(m, NP) and m.lemma in NUMERALS and m.lemma != 'ūnus' for m in np.modifiers)
    if np.number == 'pl' and np.animate and not counted:   # 数詞の後ろは 들 を付けない (두 고양이)
        text += '들'
    return ' '.join(x for x in before + [text] if x)


def _modifier(lex):
    if lex.lemma in DETERMINERS and lex.lang in ('', 'la'):
        return DETERMINERS[lex.lemma]
    if lex.lemma in POSSESSIVES and lex.lang in ('', 'la'):
        return POSSESSIVES[lex.lemma]
    if lex.lemma in NUMERALS and lex.lang in ('', 'la'):
        return NUMERALS[lex.lemma]
    found = to_korean(lex, 'adj')
    if not found:
        return '[%s]' % english.word(lex)
    if found.endswith('다'):
        return adnominal(found, adjective=True)
    return found + '의'   # 名詞の修飾 (한국의)


def relative_clause(r):
    """関係節は名詞の前の連体形の節 (소녀가 본 장미)"""
    words = realize(r, gap=r.gap, final=False)
    return ' '.join(words)


def prepositional(np, passive=False):
    inner = noun_phrase(dataclasses.replace(np, prep=None))
    if not inner:
        return ''
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        return particle(inner, '에 의해', '에 의해')
    post = POSTPOSITIONS.get((np.prep.lemma, np.case), '에서') if np.prep is not None else '에서'
    if isinstance(post, tuple):
        return particle(inner, post[0], post[1])
    if post.startswith(' '):
        return inner + post
    if post.startswith('을'):
        return particle(inner, post, '를' + post[1:])
    return inner + post


SUBJECT_FORMS = {'나': '내가', '저': '제가', '너': '네가', '누구': '누가'}   # 主格の 가 で形が変わる代名詞


def _subject_particle(text):
    return SUBJECT_FORMS.get(text) or particle(text, '이', '가')


def _object_particle(text):
    return particle(text, '을', '를')


def verb_form(clause, final=True, adnominal_tense=None):
    """述語の用言の形"""
    if clause.copula:
        return None
    lemma = word(clause.verb, 'verb')
    if lemma.startswith('['):
        return lemma
    adjective = _adjective_lemma(lemma)
    if clause.voice == 'passive' and not adjective:
        # 受動: 하다 動詞は 되다 (칭찬하다 → 칭찬되다)、ほかは -어지다 (읽어지다)
        lemma = lemma[:-2] + '되다' if lemma.endswith('하다') else infinitive(lemma) + '지다'
    if adnominal_tense is not None:
        return adnominal(lemma, adnominal_tense, adjective)
    if clause.mood == 'imperative':
        form = imperative(lemma)
        return ('하지 마라' if False else lemma[:-1] + '지 마라') if clause.negated else form
    if clause.tense in ('perfect', 'past-perfect', 'imperfect'):
        form = past(lemma)
    elif clause.tense in ('future', 'future-perfect'):
        form = future(lemma)
    else:
        form = present(lemma, adjective)
    return ('안 ' + form) if clause.negated else form


def _copula(complement, clause):
    """繋辞の述語 (학생이다・아니다)。形容詞の補語は形容詞の述語 (예쁘다)"""
    head = complement.head
    if complement.members and all(m.head is not None and m.head.pos in ('adj', 'participle') for m in complement.members):
        # 並列の形容詞の述語 (longa et lāta → 길고 넓다): 前の形容詞は -고
        lemmas = [(to_korean(m.head, 'adj') or '[%s]' % english.word(m.head)) for m in complement.members]
        lemmas = [l if l.endswith('다') or l.startswith('[') else l + '하다' for l in lemmas]
        last = _copula(dataclasses.replace(complement, members=[], head=complement.members[-1].head), clause)
        return ' '.join([_stem(l) + '고' for l in lemmas[:-1]] + [last])
    if head is not None and head.pos in ('adj', 'participle') and not complement.members:
        lemma = to_korean(head, 'adj') or '[%s]' % english.word(head)
        if not lemma.endswith('다'):
            lemma += '하다'
        if clause.tense in ('perfect', 'past-perfect', 'imperfect'):
            form = past(lemma)
        elif clause.tense == 'future':
            form = future(lemma)
        else:
            form = lemma
        return ('안 ' + form) if clause.negated else form
    text = noun_phrase(complement)
    past_tense = clause.tense in ('perfect', 'past-perfect', 'imperfect')
    if clause.negated:
        return _subject_particle(text) + (' 아니었다' if past_tense else ' 아니다')
    if past_tense:
        return text + ('이었다' if has_final(text) else '였다')
    if clause.tense == 'future':
        return text + '일 것이다'
    return text + ('이다' if has_final(text) else '다')


def realize(clause, gap=None, final=True):
    """節の語の列 (gap: 関係節の空所の役割。関係節なら用言は連体形)"""
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    subject = (clause.role('subject') or [None])[0]
    out = []
    for adv in clause.adverbs:
        if adv.lemma not in ('nōn',):
            out.append(word(adv, 'adv'))
    if subject is not None and gap != 'subject':
        out.append(_subject_particle(noun_phrase(subject)))
    if clause.copula:
        complements = clause.role('complement')
        for role, np in clause.args:
            if role == 'prep':
                text = prepositional(np)
                if not complements and text.endswith('에서') and np.prep is not None and np.prep.lemma == 'in':
                    text = text[:-2] + '에'   # 存在の場所 (정원에 있다)
                out.append(text)
        if complements:
            if gap is not None:   # 関係節の繋辞 (美しい少女): 補語の連体形
                head = complements[0].head
                lemma = to_korean(head, 'adj') or '[%s]' % english.word(head)
                out.append(adnominal(lemma, adjective=True) if lemma.endswith('다') else lemma + '인')
            else:
                out.append(_copula(complements[0], clause))
        else:
            out.append('있었다' if clause.tense in ('perfect', 'imperfect') else '있다')   # 存在 (정원에 있다)
        return out
    for np in clause.role('recipient'):
        out.append(noun_phrase(np) + '에게')
    obj = (clause.role('object') or [None])[0]
    if obj is not None and gap != 'object':
        out.append(_object_particle(noun_phrase(obj)))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement', 'address'):
            continue
        if role == 'prep':
            out.append(prepositional(np, clause.voice == 'passive'))
            continue
        if np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
            out.append(WORDS[np.head.lemma])   # 副詞の場所 (hīc → 여기서)
            continue
        if not noun_phrase(np):
            continue
        if role == 'means' and np.animate:
            out.append(noun_phrase(np) + '에게')
        elif role == 'means':
            out.append(particle(noun_phrase(np), '으로', '로'))
        elif role == 'possessor':
            out.append(noun_phrase(np) + '의')
        else:
            out.append(noun_phrase(np) + '에서')
    out.append(verb_form(clause, final, adnominal_tense=clause.tense if gap is not None else None))
    return out


def vocative(np):
    text = noun_phrase(np)
    return particle(text, '아', '야') if np.head is not None and np.head.proper else text + '여'


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address
    parts = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        words = []
        for group in groups:
            words.append(', '.join(vocative(np) for np in group) + ',')
        for key in rest.connectives:
            if key in CONNECTIVES and k > 0:
                words.append(CONNECTIVES[key])
        words += realize(rest)
        text = ' '.join(w for w in words if w)
        if rest.subordinator in SUBORDINATORS and k + 1 < len(clauses):
            text = _subordinate(text, rest.subordinator)
        parts.append(text)
    return ', '.join(parts) + '.'


def _subordinate(text, key):
    """従属節: 文末の用言を接続の形に (〜할 때・〜하면)。作れなければ接続の語を後ろに"""
    tail = SUBORDINATORS[key]
    return text + ' ' + tail


# ----------------------------------------------------------------------
# 比較の表

AGENT_HOW = '에 의해 (受動の動作主)'


def compare_np(role, np, clause):
    """(形, 手段)"""
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, AGENT_HOW
        post = POSTPOSITIONS.get((np.prep.lemma, np.case), '에서')
        post = post[1] if isinstance(post, tuple) else post
        return text, '後置詞 %s' % post.strip()
    text = noun_phrase(np)
    if role == 'subject':
        return _subject_particle(text), '助詞 이/가 (終声で交替)'
    if role == 'object':
        return _object_particle(text), '助詞 을/를'
    if role == 'recipient' or (role == 'means' and np.animate):
        return text + '에게', '助詞 에게'
    if role == 'means':
        return particle(text, '으로', '로'), '助詞 (으)로'
    if role == 'address':
        return vocative(np), '呼格の助詞 아/야 (名前)・여'
    if role == 'possessor':
        return text + '의', '助詞 의'
    return text + '에서', '助詞 에서'


PREDICATE_HOW = '語幹 + 先語末語尾 (過去 -었-) + 終結語尾 (-다)、否定 안、未来 -ㄹ 것이다'
COPULA_HOW = '補語 + 이다 (否定 아니다)。形容詞は用言としてそのまま述語'
PRO_DROP_HOW = '書かない (文脈で分かる)'
ADDRESS_HOW = '呼格の助詞 아/야 (名前)・여'


def compare_predicate(clause, reduced):
    """述語の形 (繋辞の文は補語 + 이다 / 形容詞の述語)"""
    if clause.copula:
        complements = clause.role('complement')
        if complements:
            return _copula(complements[0], clause), COPULA_HOW
        return ' '.join(realize(reduced)[-1:]), COPULA_HOW
    return verb_form(clause), PREDICATE_HOW
