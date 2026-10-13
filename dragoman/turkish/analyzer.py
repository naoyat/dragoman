#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語の文の解析
#
# 語を zeyrek で解析し (turkish/morphology.py)、読みを文脈で選んで記録 (名詞の格・所有、用言の時制・人称 …) に
# まとめてから、並列・係り先・格の枠・日本語訳は共通の解析器 (core/analyzer.py) をトルコ語の設定 (TURKISH) で使う:
#   - 格の接尾辞: 主格 (無標)「が」、対格 -ı「を」、与格 -a「に」、位格 -da「で」、奪格 -dan「から」、属格 -ın「の」
#     (後ろの名詞に掛かる: Ali'nin kitabı「アリの本」)、具格 -la「で,と」。所有の接尾辞 (evim「私の家」)
#   - 用言: 時制 (-dı 過去・-mış 伝聞の過去・-acak 未来・-iyor 進行・-ır 超越 (現在))、人称 (-m 私・-n 君 …。主語を
#     書かなければ人称から補う)、否定 -ma、可能 -abil、受動 -ıl、使役 -dır、命令・願望・条件 -sa、必要 -malı
#   - 名詞・形容詞の述語 (Ali öğretmen(dir)「アリは先生である」、evdeydim「私は家にいた」) は見えない繋辞を補う。
#     var「ある」・yok「ない」は存在、değil は否定の繋辞
#   - 後置詞 (için・ile・gibi・kadar・sonra …) は前の名詞句に掛かる前置詞句にする (名詞句の前に移す)
#   - 分詞 (-an・-dığı・-acağı) は後ろの名詞に掛ける関係節 (kitap okuyan çocuk「本を読む子供」、Ali'nin okuduğu
#     kitap「アリが読んだ本」)。副動詞 (-ıp・-ınca・-ken・-madan …) は節を区切る接続の語にする
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '-': 'comma', '(': 'comma', ')': 'comma', '"': None,
               '“': None, '”': None, '«': None, '»': None}
TOKEN = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû]+(?:['’][A-Za-zÇĞİÖŞÜçğıöşüÂâÎîÛû]+)?|\d+(?:[.,]\d+)*|[.!?…,;:—–\-()\"“”«»]")
GENDER = 'c'
ALL_CASES = ('Nom', 'Acc', 'Dat', 'Loc', 'Abl', 'Gen', 'Ins')
VERB_FEATURES = {'Neg', 'Able', 'Unable', 'Pass', 'Caus', 'Recip', 'Reflex', 'Imp', 'Opt', 'Desr', 'Cond', 'Neces',
                 'Cop', 'Narr', 'Past', 'Fut', 'Prog1', 'Prog2', 'Aor', 'Pres'}


def particle(case, obj, pred):
    """主語の「は」: 文の主題 (文頭の主格) は「は」"""
    if isinstance(obj, Word) and getattr(obj, 'topic', False) and case == 'Nom':
        return 'は'
    return None


def _root_items(lemma):
    return []


TURKISH = language.Language(
    name='tr',
    and_words=('ve',),
    or_words=('veya', 'yahut'),
    copulas=frozenset({'imek'}),
    negations=frozenset({'değil', '(değil)'}),
    case_particles=dict(morphology.CASE_JA),
    absolute_case=None,
    lookup=_root_items,
    particle=particle,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_precedes_head=True,
    possessor_cases=('Gen', 'Dat'),
)


def tokens(text):
    return TOKEN.findall(text)


def sentences(text):
    current = []
    for token in tokens(text):
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


# ----------------------------------------------------------------------
# 読みの選択

def _finite(morphemes):
    """定動詞か (動詞の部分に人称がある。分詞・副動詞・名詞化で終わらない)"""
    last = _last_segment(morphemes)
    return last[:1] == ['Verb'] and any(m in morphology.PERSONS for m in last)


def _last_segment(morphemes):
    """最後の派生の部分 (Verb PastPart Adj P1sg → [Adj, P1sg])。品詞の形態素で区切る"""
    cuts = [i for i, m in enumerate(morphemes) if m in ('Noun', 'Verb', 'Adj', 'Adv', 'Pron', 'Num', 'Det', 'Postp',
                                                       'Conj', 'Ques', 'Interj')]
    return list(morphemes[cuts[-1]:]) if cuts else list(morphemes)


def choose(token, k, surfaces, prev):
    """語の位置の解析 (見出し語, 品詞, 形態素のタプル) を文脈で選ぶ"""
    found = morphology.analyses(token)
    if not found:
        return None
    nxt = surfaces[k + 1] if k + 1 < len(surfaces) else '.'
    final = nxt in PUNCTUATION or nxt.lower() in ('mı', 'mi', 'mu', 'mü', 've', 'ama', 'fakat', 'çünkü', 'ki')
    sentence_initial = k == 0 or surfaces[k - 1] in PUNCTUATION
    lowered = ' '.join(s.lower() for s in surfaces)

    def score(a):
        lemma, pos, morphemes = a
        s = 0
        if lemma[:1].isupper() and (sentence_initial or not token[:1].isupper()):
            s += 4   # 文頭の大文字・小文字の語の固有名詞の読み (Çocuk) は後ろに
        if final and _finite(morphemes):
            s -= 3
        elif not final and _finite(morphemes) and 'Zero' in morphemes:
            s += 2   # 文中の名詞・形容詞の述語の読み (güzel+dir) は後ろに
        if not final and pos == 'Verb' and ('Imp' in morphemes or 'Opt' in morphemes):
            s += 3   # 文中の命令形・願望形 (için → iç-in、bana → ban-a) は後ろに
        if pos == 'Pron' and lemma in morphology.PRONOUNS:
            s -= 2   # 代名詞 (bana「私に」、benim「私の」)
        if lemma in ('var', 'yok') and pos == 'Adj':
            s -= 3   # 存在の var / yok (varmak の命令形でなく)
        if pos == 'Postp' and dictionary.lower(token) not in morphology.POSTPOSITIONS:
            s += 3   # 後置詞の表に無い語の後置詞の読み (çok) は後ろに
        if lemma == dictionary.lower(token) and len(morphemes) <= 2:
            s -= 0.5   # 接尾辞の無い読み (Türkçe「トルコ語」。Türk + 同等格でなく)
        if prev is not None and prev.get('kind') == 'pronoun' and prev.get('case') == 'Gen':
            person = morphology.PRONOUNS.get(prev.get('lemma'), (None, 3, 'sg'))[1:]
            if any(morphology.POSSESSOR_PERSON.get(m) == person for m in morphemes):
                s -= 4   # 属格の代名詞の後ろは同じ人称の所有 (benim kardeşim「私の兄弟」)
        s += morphemes.count('Zero') + 0.1 * len(morphemes)
        if 'P2sg' in morphemes and not re.search(r'\b(sen|senin|seni|sana)\b', lowered):
            s += 1.5   # 2人称の所有 (kitabın「君の本」) は「君」が無ければ後ろに
        bare_noun_before = prev is not None and prev.get('kind') == 'noun' and prev.get('case') == 'Nom' and \
            not prev.get('possessive') and k > 0 and surfaces[k - 1] not in PUNCTUATION
        if morphemes[-1:] == ('P3sg',) and prev is not None and prev.get('case') != 'Gen' and not bare_noun_before:
            s += 1     # 属格の後ろでない -ı は対格を先に (kitabı)
        if morphemes[-1:] == ('Acc',) and 'P3sg' not in morphemes and bare_noun_before and \
                any(m[-1:] == ('P3sg',) for _, _, m in found):
            s += 1.5   # 不定の名詞の後ろの -ı は所有の3人称 (名詞の複合: Yugoslav lideri、Genelkurmay Başkanı)
        if morphemes[-1:] == ('Acc',) and 'P3sg' not in morphemes and prev is not None and prev.get('case') == 'Gen':
            s += 1     # 属格の後ろの -ı は所有 (Ali'nin kitabı)
        if pos == 'Postp' and k == 0:
            s += 2
        if pos == 'Adj' and morphemes == ('Adj',) and not dictionary.lemmas(lemma, ('adj',)) and \
                dictionary.lemmas(lemma, ('noun',)):
            s += 2   # 辞書に名詞しか無い語の形容詞の読み (çocuk) は後ろに
        if lemma in morphology.DETERMINERS and pos == 'Det' and not final and nxt not in PUNCTUATION:
            s -= 2.5   # 名詞の前の指示詞 (bu ev「この家」。代名詞「これ」でなく)
        if lemma in ('çok', 'daha', 'en', 'pek', 'az') and nxt not in PUNCTUATION and \
                any(p == 'Adj' for _, p, _ in morphology.analyses(nxt)):
            s += -4 if pos == 'Adv' else 0   # 形容詞の前の çok は「とても」(çok büyük)
        return s
    return sorted(found, key=score)[0]


# ----------------------------------------------------------------------
# 記録

def record(token, analysis, k, prev_kind=None):
    """語と選んだ解析 → 記録 (dict)"""
    if analysis is None:
        named = morphology.name_suffix(token)
        if named:
            name, case = named
            return {'kind': 'noun', 'lemma': name, 'proper': True, 'case': case, 'number': 'sg', 'possessive': None,
                    'surface': token, 'ix': k, 'morphemes': ('Noun', case)}
        return {'kind': 'noun', 'lemma': token, 'proper': token[:1].isupper(), 'case': None, 'number': 'sg',
                'possessive': None, 'surface': token, 'ix': k, 'morphemes': ()}
    lemma, pos, morphemes = analysis
    ms = list(morphemes)
    rec = {'surface': token, 'ix': k, 'lemma': lemma, 'morphemes': morphemes, 'pos': pos}
    named = morphology.name_suffix(token)
    if named and token[:1].isupper():
        name, case = named
        rec.update(kind='noun', lemma=name, proper=True, case=case, number='sg', possessive=None)
        return rec
    root = ms[0] if ms else pos
    last = _last_segment(ms)
    converb = next((m for m in ms if m in morphology.CONVERBS), None)
    participle = next((m for m in ms if m in morphology.PARTICIPLES), None)
    nominalizer = next((m for m in ms if m in ('Inf1', 'Inf2', 'Inf3')), None)
    verbal = root == 'Verb'
    features = _verb_features(ms)
    low = dictionary.lower(token)
    if low in morphology.POSTPOSITIONS and k > 0 and prev_kind in ('noun', 'pronoun', 'nominalized'):
        rec.update(kind='postposition', lemma=low)
        return rec   # 名詞の後ろの後置詞 (Ali tarafından「アリによって」。taraf の奪格でなく)
    if low == 'bir' and root in ('Det', 'Num', 'Adj', 'Adv'):
        rec.update(kind='article')
        return rec   # 不定の bir「ある、一つの」(訳さない)
    if low in morphology.TIME_WORDS and (ms == ['Noun', 'A3sg'] or root in ('Adv', 'Adj', 'Noun') and len(ms) <= 2):
        rec.update(kind='adv', lemma=low)
        return rec   # 助詞の無い時・場所の語 (dün akşam「昨日の夕方」、içeri「中へ」)
    if lemma == 'değil':   # 否定の繋辞 (değil・değildim)
        rec.update(kind='negcopula', **_verb_features(ms))
        return rec
    if token[:1].isupper() and k > 0 and not lemma[:1].isupper() and root in ('Adj', 'Noun') and \
            dictionary.lemmas(token, ('name',)):
        rec.update(kind='noun', lemma=token, proper=True, case='Nom', number='sg', possessive=None)
        return rec   # 文中の大文字の語は固有名詞 (Ali。形容詞 ali「高い」でなく)
    if pos == 'Ques' or root == 'Ques':
        rec.update(kind='question', person=_person(ms))
        return rec
    if pos == 'Postp' or root == 'Postp':
        rec.update(kind='postposition')
        return rec
    if pos == 'Conj' or root == 'Conj':
        rec.update(kind='conj')
        return rec
    if root in ('Punc',):
        rec.update(kind='punct')
        return rec
    if verbal and converb:
        rec.update(kind='converb', converb=converb, **features)
        return rec
    if verbal and participle and last[:1] == ['Adj']:
        rec.update(kind='participle', participle=participle, subject=_possessive(last), **features)
        return rec
    if verbal and (participle or nominalizer) and last[:1] == ['Noun']:
        rec.update(kind='nominalized', nominalizer=participle or nominalizer, case=_case(last),
                   possessive=_possessive(last), **dict(features, number='sg'))
        return rec
    if verbal and last[:1] == ['Verb']:
        rec.update(kind='verb', **features)
        return rec
    if root in ('Noun', 'Pron', 'Num') or last[:1] == ['Noun'] and root in ('Adj',):
        noun_part = ms[:ms.index('Zero')] if 'Zero' in ms and _finite(ms) else ms
        rec.update(kind='pronoun' if root == 'Pron' else 'noun', case=_case(noun_part),
                   possessive=_possessive(noun_part), number='pl' if 'A3pl' in noun_part else 'sg',
                   proper=lemma[:1].isupper())
        if _finite(ms) and 'Zero' in ms:   # 名詞の述語 (öğretmendir・evdeydim)
            rec['predicate'] = _verb_features(ms[ms.index('Zero'):])
        return rec
    if root == 'Adj':
        rec.update(kind='adj')
        if _finite(ms) and 'Zero' in ms:   # 形容詞の述語 (güzeldi)
            rec['predicate'] = _verb_features(ms[ms.index('Zero'):])
        return rec
    if root == 'Adv':
        rec.update(kind='adv')
        return rec
    if root == 'Det':
        rec.update(kind='det')
        return rec
    rec.update(kind='adv')
    return rec


def _case(ms):
    found = [m for m in ms if m in morphology.CASES]
    return found[-1] if found else 'Nom'


def _possessive(ms):
    return next((m for m in ms if m in morphology.POSSESSIVES), None)


def _person(ms):
    found = [m for m in ms if m in morphology.PERSONS]
    return morphology.PERSONS[found[-1]] if found else (3, 'sg')


def _verb_features(ms):
    tenses = [m for m in ms if m in morphology.TENSES]
    tense = morphology.TENSES[tenses[0]] if tenses else 'present'
    if 'Past' in tenses[1:] and tense != 'perfect':
        tense = 'imperfect' if tense == 'progressive' else 'pluperfect' if tense == 'perfect' else 'perfect'
    person, number = _person(ms)
    mood = 'imperative' if ('Imp' in ms or 'Opt' in ms) else 'indicative'
    return {'tense': tense, 'person': person, 'number': number, 'mood': mood,
            'negated': 'Neg' in ms or 'Unable' in ms, 'able': 'Able' in ms or 'Unable' in ms,
            'passive': 'Pass' in ms, 'causative': 'Caus' in ms, 'conditional': 'Cond' in ms or 'Desr' in ms,
            'necessity': 'Neces' in ms, 'evidential': 'Narr' in ms, 'tense_marks': tuple(tenses)}


# ----------------------------------------------------------------------
# 記録 → 語

def _cngs(cases, number='sg'):
    return [(c, number, GENDER) for c in cases]


def _japanese_verb(rec):
    """用言の訳語 (可能・使役・必要の形を付ける)"""
    from dragoman.core.japanese import attach_auxiliary
    ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'verb')
    if ja is None:
        return rec['lemma'], 'en', None
    if gloss_lang != 'ja':
        return ja, gloss_lang, row
    first = ja.split(',')[0]
    if rec.get('causative'):
        first = attach_auxiliary(first, 'させる')
    if rec.get('passive'):
        first = first   # 受動は態の印で (共通の訳が「〜される」に)
    if rec.get('able'):
        first = attach_auxiliary(first, 'ことができる')
    if rec.get('necessity'):
        first = attach_auxiliary(first, 'なければならない')
    if rec.get('conditional'):
        pass
    return first, 'ja', row


def _form_notes(rec):
    notes = []
    marks = rec.get('tense_marks', ())
    names = {'Past': '過去 -dı', 'Narr': '伝聞の過去 -mış', 'Fut': '未来 -acak', 'Prog1': '進行 -iyor',
             'Prog2': '進行 -makta', 'Aor': '超越 (習慣・一般) -ır'}
    notes += [names[m] for m in marks if m in names]
    for key, name in (('negated', '否定 -ma'), ('able', '可能 -abil'), ('passive', '受動 -ıl'), ('causative', '使役 -dır'),
                      ('conditional', '条件・願望 -sa'), ('necessity', '必要 -malı')):
        if rec.get(key):
            notes.append(name)
    if rec.get('mood') == 'imperative':
        notes.append('命令・願望')
    return '・'.join(notes)


def _base(rec, row=None):
    word = (row or {}).get('word') or rec['lemma']
    return word


def _noun_word(rec):
    lemma = rec['lemma']
    case = rec.get('case') or 'Nom'
    number = rec.get('number', 'sg')
    if rec['kind'] == 'pronoun' or lemma in morphology.PRONOUNS:
        ja, person, pnumber = morphology.PRONOUNS.get(lemma, (lemma, 3, 'sg'))
        data = {'surface': rec['surface'], 'pos': 'pronoun', 'base': lemma, 'ja': ja, 'gloss_lang': 'ja',
                'person': person, 'number': pnumber, '_': _cngs([case], pnumber), 'compact': True, 'main': True}
        return Word(rec['surface'], [data])
    ja, gloss_lang, row = morphology.gloss(lemma, 'name' if rec.get('proper') else 'noun')
    if ja is None:
        ja, gloss_lang = (lemma, 'en') if rec.get('proper') else (lemma, 'ja')
    possessive = morphology.POSSESSIVES.get(rec.get('possessive') or '', '')
    if possessive and gloss_lang == 'ja':
        ja = ','.join(possessive + j for j in ja.split(',')[:2])
    data = {'surface': rec['surface'], 'pos': 'noun', 'base': _base(rec, row), 'lemma': lemma, 'ja': ja,
            'gloss_lang': gloss_lang, '_': _cngs([case], number), 'main': True, 'compact': True}
    if rec.get('proper'):
        data['proper'] = True
    if rec.get('possessive'):
        data['possessive'] = rec['possessive']
    return Word(rec['surface'], [data])


def _verb_item(rec, surface=None):
    ja, gloss_lang, row = _japanese_verb(rec)
    lemma = rec['lemma']
    data = {'surface': surface or rec['surface'], 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja, 'gloss_lang': gloss_lang, 'voice': 'passive' if rec.get('passive') else 'active',
            'mood': rec.get('mood', 'indicative'), 'tense': rec.get('tense', 'present'), 'person': rec.get('person', 3),
            'number': rec.get('number', 'sg'), 'form': _form_notes(rec), 'main': True, 'compact': True}
    return data


def _copula(rec, features, surface='(dir)'):
    data = {'surface': surface, 'pos': 'verb', 'lemma': 'imek', 'pres1sg': 'imek', 'base': 'imek (繋辞)', 'ja': 'である',
            'gloss_lang': 'ja', 'copula': True, 'voice': 'active', 'mood': 'indicative',
            'tense': features.get('tense', 'present'), 'person': features.get('person', 3),
            'number': features.get('number', 'sg'), 'form': _form_notes(features), 'compact': True}
    if features.get('tense') == 'present' and not features.get('tense_marks'):
        data['tense'] = 'present'
    return Word(surface, [data])


def _negation(surface='(değil)'):
    return Word(surface, [{'surface': surface, 'pos': 'adv', 'base': 'değil (否定)', 'ja': '〜ない', 'gloss_lang': 'ja',
                           'compact': True}])


def _np_continues(word):
    item = _item(word)
    if item is None:
        return False
    return item.pos == 'adj' or item.pos in ('noun', 'pronoun') and item._ and all(c[0] == 'Gen' for c in item._)


def build_words(recs):
    words = []
    for k, rec in enumerate(recs):
        kind = rec['kind']
        ix = rec['ix']
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        new = []
        if kind == 'punct':
            new = [Word(rec['surface'], None)]
        elif kind in ('noun', 'pronoun', 'nominalized'):
            if kind == 'nominalized':
                ja, gloss_lang, row = _japanese_verb(rec)
                from dragoman.core.japanese import japanese_plain
                past = rec['nominalizer'] == 'PastPart'
                text = japanese_plain(ja, False, 'perfect' if past else 'present', rec.get('negated')) + \
                    morphology.NOMINALIZERS.get(rec['nominalizer'], 'こと') if gloss_lang == 'ja' else ja
                word = Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'noun', 'base': rec['lemma'], 'ja': text,
                                              'gloss_lang': 'ja', '_': _cngs([rec.get('case') or 'Nom']), 'main': True,
                                              'nominalized': True, 'compact': True}])
            else:
                prev_word = words[-1] if words else None
                if rec.get('possessive') and prev_word is not None and _pos(prev_word) == 'pronoun' and \
                        _item(prev_word)._ and _item(prev_word)._[0][0] == 'Gen':
                    rec = dict(rec, possessive=None)   # benim kardeşim: 「私の」は前の代名詞で (二重にしない)
                    recs[k] = rec
                word = _noun_word(rec)
            new = [word]
            if rec.get('predicate'):   # 名詞の述語 (öğretmendir「先生である」)
                new.append(_copula(rec, rec['predicate']))
            if kind == 'pronoun' and k == 0 or (kind == 'noun' and rec.get('case') == 'Nom' and k == 0):
                word.topic = True
        elif kind == 'adj':
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'adj')
            lemma = rec['lemma']
            if lemma in ('var', 'yok'):   # 存在 (Kitap var「本がある」)
                features = rec.get('predicate') or {'tense': 'present', 'person': 3, 'number': 'sg'}
                data = _verb_item(dict(rec, **features))
                data.update(ja='ある,いる', gloss_lang='ja', existential=True, lemma=lemma)
                if lemma == 'yok':
                    new.append(_negation('(yok)'))
                new.append(Word(rec['surface'], [data]))
            else:
                cases = ['Nom'] if rec.get('predicate') else list(ALL_CASES)
                new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adj', 'base': lemma,
                                              'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                                              '_': _cngs(cases) + _cngs(cases, 'pl'), 'main': True,
                                              'predicative': bool(rec.get('predicate')), 'compact': True}])]
                if rec.get('predicate'):
                    new.append(_copula(rec, rec['predicate']))
        elif kind == 'det':
            lemma = rec['lemma']
            ja = morphology.NUMBERS.get(lemma) if lemma in morphology.NUMBERS and lemma != 'bir' else \
                morphology.DETERMINERS.get(lemma, lemma)
            new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adj', 'base': lemma, 'ja': ja,
                                          'gloss_lang': 'ja', '_': _cngs(ALL_CASES) + _cngs(ALL_CASES, 'pl'),
                                          'demonstrative': True, 'compact': True}])]
        elif kind == 'adv':
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'adv')
            if rec['lemma'] == 'değil':
                new = [_negation(rec['surface']), _copula(rec, {'tense': 'present'}, '(dir)')]
            else:
                new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adv', 'base': rec['lemma'],
                                              'ja': ja or rec['lemma'], 'gloss_lang': gloss_lang or 'en', 'compact': True}])]
        elif kind == 'conj':
            lemma = dictionary.lower(rec['surface'])
            if lemma == 'değil':
                new = [_negation(rec['surface']), _copula(rec, {'tense': 'present'}, '(dir)')]
            else:
                new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'conj', 'base': lemma,
                                              'ja': morphology.CONJUNCTIONS.get(lemma, lemma), 'gloss_lang': 'ja',
                                              'compact': True}])]
        elif kind == 'postposition':
            lemma = dictionary.lower(rec['surface'])
            ja = morphology.POSTPOSITIONS.get(lemma, ('〜' + lemma, None))[0]
            prep = Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'preposition', 'base': lemma, 'ja': ja,
                                          'gloss_lang': 'ja', 'dominates': 'Obl', 'compact': True}])
            prep.token_ix = ix
            # 前の名詞句の前に移す (名詞は後置詞の目的語に)
            start = len(words)
            while start > 0 and _pos(words[start - 1]) is None:
                start -= 1
            if start > 0 and _pos(words[start - 1]) in ('noun', 'pronoun'):
                head = words[start - 1]
                _item(head)._ = [('Obl',) + c[1:] for c in (_item(head)._ or _cngs(['Nom']))[:1]]
                start -= 1
                while start > 0 and _np_continues(words[start - 1]):
                    start -= 1
                words.insert(start, prep)
                continue
            new = [prep]
        elif kind == 'article':
            continue
        elif kind == 'negcopula':
            before = words[-1] if words else None
            if before is not None and _pos(before) in ('noun', 'pronoun') and _item(before)._ and \
                    _item(before)._[0][0] in ('Loc',):   # evde değildim「家にいなかった」
                cop = _copula(rec, rec, '(dir)')
                cop.items[0].item.update(ja='ある,いる', existential=True, copula=False)
                cop.items = [type(cop.items[0])(cop.items[0].item)]
                new = [_negation(), cop]
                rec['existential'] = True
                if getattr(before, 'record', None) is not None:
                    before.record['before_existential'] = True
            else:
                new = [_negation(), _copula(rec, rec, '(dir)')]
        elif kind == 'question':
            if words:
                words[-1].question = True
            continue
        elif kind == 'verb':
            new = [Word(rec['surface'], [_verb_item(rec)])]
        elif kind == 'converb':
            verb = Word(rec['surface'], [_verb_item(dict(rec, mood='indicative', person=None, number=None))])
            form, tail, note = morphology.CONVERBS[rec['converb']]
            conj = Word('-' + rec['converb'], [{'surface': '-' + rec['converb'], 'pos': 'conj', 'base': note,
                                                'ja': {'te': '〜て', 'plain': '〜' + tail, 'neg': '〜' + tail,
                                                       'masu': '〜' + tail}[form] + (tail if form == 'te' else ''),
                                                'gloss_lang': 'ja', 'compact': True}])
            verb.items[0].item['form'] = note
            verb.items = [type(verb.items[0])(verb.items[0].item)]
            new = [verb, conj]
        elif kind == 'participle':
            word = Word(rec['surface'], [_verb_item(rec)])
            word.attributive = rec['participle']
            word.subject_possessive = rec.get('subject')
            new = [word]
        for w in new:
            w.token_ix = ix
            w.record = rec
        words += new
    return words


# ----------------------------------------------------------------------
# 分詞: 後ろの名詞に掛ける関係節

def mark_participles(words):
    """分詞 (-an・-dığı・-acağı) を後ろの名詞に掛け、前の補語と一緒に関係節として名詞の訳に組み込む"""
    from dragoman.core.japanese import japanese_plain
    out = []
    for i, word in enumerate(words):
        if not getattr(word, 'attributive', None):
            out.append(word)
            continue
        head = next((w for w in words[i + 1:i + 3] if _pos(w) in ('noun', 'pronoun')), None)
        start = len(out)
        subject_relative = word.record['participle'] in ('PresPart', 'AorPart', 'NarrPart')
        while start > 0:
            prev = out[start - 1]
            item = _item(prev)
            nominative = item is not None and item.pos in ('noun', 'pronoun') and item._ and item._[0][0] == 'Nom'
            if prev.items is None or _pos(prev) in ('verb', 'conj') or \
                    nominative and not (subject_relative and start == len(out)):
                break   # -an の分詞の直前の主格は不定の目的語 (kitap okuyan「本を読む」)
            if nominative:
                item._ = [('Acc',) + c[1:] for c in item._[:1]]
                if getattr(prev, 'record', None) is not None:
                    prev.record['role_case'] = 'Acc'
            start -= 1
        clause = out[start:]
        item = _item(word)
        if head is None:
            out.append(word)
            continue
        rec = word.record
        ja = (item.ja or '').split(',')[0]
        tense = {'past': 'perfect', 'future': 'future', 'present': 'present'}[morphology.PARTICIPLES[rec['participle']]]
        verb = japanese_plain(ja, False, tense, rec.get('negated')) if item.attrib('gloss_lang') == 'ja' else ja
        if not clause and rec['participle'] in ('PresPart', 'AorPart') and not rec.get('subject'):
            # 補語の無い分詞は形容詞として (okuyan çocuk「読む子供」)
            word.items = [type(item)(dict(item.item, pos='adj', ja=verb, _=_cngs(ALL_CASES) + _cngs(ALL_CASES, 'pl')))]
            out.append(word)
            continue
        parts = []
        pending = None
        for w in clause:
            it = _item(w)
            if it.pos == 'preposition':
                pending = it.ja.split(',')[0].lstrip('〜')
                continue
            text = (it.ja or '').split(',')[0]
            if pending is not None:
                parts.append(text + pending)
                pending = None
            elif it.pos in ('noun', 'pronoun'):
                case = it._[0][0] if it._ else 'Nom'
                parts.append(text + ('が' if case == 'Gen' else morphology.CASE_JA.get(case, '')))
            else:
                parts.append(text)
        subject = morphology.POSSESSIVES.get(rec.get('subject') or '', '')
        if subject and not any(_item(w)._ and _item(w)._[0][0] == 'Gen' for w in clause if _item(w)._):
            parts.insert(0, subject[:-1] + 'が')   # okuduğum kitap「私が読んだ本」
        hitem = _item(head)
        hja = (hitem.ja or '').split(',')[0]
        head.items = [type(hitem)(dict(hitem.item, ja=''.join(parts) + verb + hja, gloss_lang='ja', _=list(hitem._ or []),
                                       relative=' '.join(w.surface for w in clause + [word])))]
        for w in clause + [word]:
            w.relative_of = head
        del out[start:]
    return out


# ----------------------------------------------------------------------

def mark_topic(words):
    """文の最初の主格の名詞・代名詞 (動詞より前) は主題「は」"""
    for w in words:
        if _pos(w) == 'verb' or w.items is None:
            return
        if _pos(w) in ('noun', 'pronoun') and _item(w)._ and _item(w)._[0][0] == 'Nom':
            w.topic = True
            return
        if _pos(w) in ('noun', 'pronoun'):
            return


def assign_roles(words):
    """節 (接続の語・句読点で区切る) ごとに、主格の名詞の役割を決める: 他動詞の直前の主格は不定の目的語
    (kitap okudu「本を読んだ」)、文頭の主格・代名詞は主題「は」。動詞の無い節には見えない繋辞を補う
    (Kitap masada「本は机にある」、Ali öğretmen「アリは先生である」)"""
    out, clause = [], []
    verbless = not any(_pos(w) == 'verb' for w in words)
    for word in words + [None]:
        if word is None or word.items is None and PUNCTUATION.get(word.surface) in ('period', 'question') or \
                word.items is not None and _pos(word) == 'conj' and word.surface.lower() not in TURKISH.and_words:
            out += _clause_roles(clause, verbless and word is not None and word.items is None or verbless and word is None) + \
                ([word] if word is not None else [])
            clause = []
        else:
            clause.append(word)
    return out


def _clause_roles(clause, supply=True):
    verbs = [w for w in clause if _pos(w) == 'verb']
    nominals = [w for w in clause if _pos(w) in ('noun', 'pronoun')]
    if verbs:
        verb = verbs[-1]
        vi = clause.index(verb)
        noms = [w for w in nominals if _item(w)._ and _item(w)._[0][0] == 'Nom' and clause.index(w) < vi]
        if len(noms) >= 2 or noms and _item(verb).attrib('person') in (1, 2):
            last = noms[-1]
            if clause.index(last) == vi - 1 and not _item(verb).attrib('copula') and \
                    not _item(verb).attrib('existential') and _item(verb).attrib('voice') != 'passive':
                it = _item(last)
                it._ = [('Acc',) + c[1:] for c in it._[:1]]   # 不定の目的語
        return clause
    if not nominals or not supply:
        return clause   # 動詞の無い文の最後の区切りにだけ繋辞を補う (読点で並べた名詞の一つ一つにではなく)
    last = nominals[-1]
    case = _item(last)._[0][0] if _item(last)._ else 'Nom'
    copula = _copula({}, {'tense': 'present'})
    if case in ('Loc', 'Dat', 'Abl'):
        copula.items[0].item.update(ja='ある,いる', existential=True, copula=False)
        copula.items = [type(copula.items[0])(copula.items[0].item)]
    copula.token_ix = getattr(last, 'token_ix', None)
    rec = getattr(last, 'record', None)
    if rec is not None:
        rec['supplied'] = 'existential' if case in ('Loc', 'Dat', 'Abl') else 'copula'   # 語順のままの訳にも
    k = clause.index(last) + 1
    return clause[:k] + [copula] + clause[k:]


def lookup_all(surfaces):
    recs = []
    prev = None
    for k, token in enumerate(surfaces):
        if token in PUNCTUATION:
            recs.append({'kind': 'punct', 'surface': token, 'ix': k})
            prev = None
            continue
        rec = record(token, choose(token, k, surfaces, prev), k, prev['kind'] if prev else None)
        recs.append(rec)
        prev = rec
    words = build_words(recs)
    for w in words:   # 語順のままの訳のため、記録に最終的な格・主題を
        rec = getattr(w, 'record', None)
        if rec is not None and _item(w) is not None and _item(w)._:
            rec['role_case'] = _item(w)._[0][0]
    global _display
    _display = list(words)
    words = mark_participles(words)
    words = assign_roles(words)
    mark_topic(words)
    for w in words:
        rec = getattr(w, 'record', None)
        if rec is not None and _item(w) is not None and _item(w)._ and _item(w).pos in ('noun', 'pronoun'):
            rec['role_case'] = _item(w)._[0][0]
            rec['topic'] = getattr(w, 'topic', False)
    for i, word in enumerate(words):
        word.index = i
    return words, recs


_display = []


def analyze_sentence(surfaces):
    words, recs = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(TURKISH):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    from .literal import literal
    analysis.literal = literal(recs)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
