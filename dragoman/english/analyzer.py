#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 英語の文の解析
#
# spaCy (en_core_web_sm) の品詞・原形・依存関係で語の項目を作り (english/morphology.py)、助動詞と本動詞を1語に
# まとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器 (core/analyzer.py) を英語の設定 (ENGLISH) で使う:
#   - 名詞に格の形は無いので、格は spaCy の依存関係から: 主語 (nsubj) は主格、目的語 (dobj) は対格、間接目的語
#     (dative) は与格、前置詞の目的語 (pobj) は前置詞の目的語。補語 (attr) は主格。代名詞は形でも (I・me)
#   - 冠詞は名詞に掛けて訳さない。所有格 (John's・my) は後ろの名詞に掛ける「〜の」
#   - 助動詞と本動詞をまとめる: be + 過去分詞 → 受動、have + 過去分詞 → 完了、be + 現在分詞 → 進行「〜している」、
#     will + 原形 → 未来、can・must・should など + 原形、do (否定・疑問の do) は落として時制だけ取る
#   - not・n't・never は否定。there is / are は「〜がある」
#   - 関係代名詞 (who・which・that) は共通の解析器の関係節に
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '(': 'comma', ')': 'comma', '"': None, '“': None, '”': None,
               "'": None, '‘': None, '’': None}


def _particle(case, obj, predicate):
    """自動詞の訳語の目的語は「に」(pass the exam → 試験に受かる。解析器が acc_particle を付けたもの)"""
    if case == 'Acc':
        return predicate.first_item.attrib('acc_particle')
    return None


def _root_items(lemma):
    ja, gloss_lang = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


ENGLISH = language.Language(
    name='en',
    and_words=('and',),
    nor_words=('nor',),
    or_words=('or',),
    copulas=frozenset({'be'}),
    negations=frozenset({'not', "n't", 'never', '(not)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    particle=_particle,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    infinitive_objects_follow=True,
    possessor_cases=(),
    question_moods=('indicative',),   # 間接疑問の節の動詞は直説法 (I don't know what you want)
)


# 話し言葉の縮まった形 → 元の語の列 (解析は元の形で、語の表には縮まった形のまま出す)
COLLOQUIAL = {'gonna': ('going', 'to'), 'gotta': ('got', 'to'), 'wanna': ('want', 'to'), 'tryna': ('trying', 'to'),
              'hafta': ('have', 'to'), 'hasta': ('has', 'to'), 'oughta': ('ought', 'to'), 'gimme': ('give', 'me'),
              'lemme': ('let', 'me'), 'outta': ('out', 'of'), 'dunno': ('do', "n't", 'know')}
SPLIT_COLLOQUIAL = {('gon', 'na'): 'gonna', ('got', 'ta'): 'gotta'}   # spaCy が2つに分ける形


def tokens(text):
    out = []
    for token in morphology.tokenize(text.replace('’', "'")):
        joined = SPLIT_COLLOQUIAL.get((out[-1].lower(), token.lower())) if out else None
        if joined:
            out[-1] += token
        else:
            out.append(token)
    return out


def sentences(text):
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


def expand_colloquial(surfaces):
    """縮まった形を元の語の列に (I'm gonna eat → I 'm going to eat)。→ (語の列, {元の語の列の最初の位置: (縮まった形, 元の句)})"""
    out, marks = [], {}
    for surface in surfaces:
        full = COLLOQUIAL.get(surface.lower())
        if not full:
            out.append(surface)
            continue
        if surface[:1].isupper():
            full = (full[0].capitalize(),) + full[1:]
        marks[len(out)] = (surface, ' '.join(full))
        out += full
    return out, marks


def restore_colloquial(words, marks):
    """語の表の形を縮まった形に戻し (going to eat → gonna eat)、語の形の説明に元の形を添える。句が1語にまとまって
    いなければ (gimme → give・me) 最初の語に説明だけ"""
    for short, full in marks.values():
        pattern = r'(?<![\w\'])' + re.escape(full).replace(r'\ ', ' +') + r'(?!\w)'
        word = next((w for w in words if re.search(pattern, w.surface)), None) or \
            next((w for w in words if _item(w) is not None and _item(w).attrib('colloquial') == short), None)
        if word is None:
            continue
        word.surface = re.sub(pattern, short, word.surface, count=1)
        item = _item(word)
        if item is not None:
            form = '%s = %s' % (short, full)
            word.items = [type(item)(dict(item.item, colloquial=short,
                                          form=item.attrib('form') + '・' + form if item.attrib('form') else form))]


def _item(word):
    return word.items[0] if isinstance(word, Word) and word.items else None


def _pos(word):
    item = _item(word)
    return item.pos if item is not None else None


# ----------------------------------------------------------------------
# 語の項目

def _verb_data(token):
    lemma = token.lemma_.lower() if token.lemma_ else token.text.lower()
    if lemma == 'got':
        lemma = 'get'   # spaCy が got を原形のまま返すもの (I got to see …)
    ja, gloss_lang = morphology.gloss(lemma, 'verb')
    tag = token.tag_
    tense = 'perfect' if tag == 'VBD' else 'present'
    mood = 'indicative'
    if tag == 'VBN':
        mood = 'participle'
    elif tag == 'VBG':
        mood = 'participle'
    elif tag == 'VB':
        has_subject = any(c.dep_ in ('nsubj', 'nsubjpass', 'expl') for c in token.children)
        has_aux = any(c.dep_ in ('aux', 'auxpass') for c in token.children)
        mood = 'infinitive' if has_aux or token.dep_ in ('xcomp', 'ccomp', 'advcl') else \
            'imperative' if not has_subject and token.dep_ == 'ROOT' else 'indicative'
    person = 3 if tag == 'VBZ' else None
    number = 'sg' if tag == 'VBZ' else None
    data = {'surface': token.text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': mood, 'tense': tense,
            'person': person, 'number': number, 'main': True, 'progressive': tag == 'VBG'}
    if mood == 'imperative':
        data.update(person=2, number='sg')
    if lemma == 'be':
        data['existential'] = True
    return data


def _case(token):
    """依存関係 → 格"""
    dep = token.dep_
    if dep in ('nsubj', 'nsubjpass', 'attr', 'csubj', 'expl'):
        return ('Nom',)
    if dep == 'dobj' and any(c.dep_ in ('dobj', 'ccomp', 'xcomp') and c.i > token.i for c in token.head.children):
        return ('Dat',)   # 2つ目の目的語・節の前の人は与格 (Tell me where you live、ask him to come)
    if dep in ('dobj', 'oprd'):
        return ('Acc',)
    if dep == 'dative':
        return ('Dat',)
    if dep == 'pobj':
        return ('Acc',) if _prepositional_verb(token.head) else ('Gen',)   # look after her brother の brother
    if dep == 'conj':
        return _case(token.head) if token.head.i != token.i else ('Nom', 'Acc')
    if dep == 'appos':
        return _case(token.head)
    return ('Acc',) if token.head.pos_ in ('VERB', 'AUX') and token.head.i < token.i else ('Nom',)


def _noun_data(token):
    text, lemma = token.text, token.lemma_ or token.text
    proper = token.tag_ in ('NNP', 'NNPS')
    if proper:
        lemma = text
    person = proper and token.ent_type_ == 'PERSON'
    # 地名などは辞書の名前を先に (Japan → 日本。japan「漆」でなく)。人名は英語の読みのカタカナ (John → ジョン。ヨハネでなく)
    ja, gloss_lang = morphology.gloss(lemma, 'name') if proper and not person else (None, None)
    if person:
        from .katakana import katakana
        ja, gloss_lang = katakana(text), 'ja'
    if ja is None:
        ja, gloss_lang = morphology.gloss(lemma, 'noun')
    if ja is None and lemma != text:
        ja, gloss_lang = morphology.gloss(text, 'noun')
    if proper and ja is None:
        from .katakana import katakana
        ja, gloss_lang = katakana(text), 'ja'   # 辞書に無い名前は英語の読みのカタカナ (Jennifer → ジェニファー)
    number = 'pl' if token.tag_ in ('NNS', 'NNPS') else 'sg'
    data = {'surface': text, 'pos': 'noun', 'base': lemma, 'lemma': lemma, 'ja': ja or text,
            'gloss_lang': gloss_lang or 'en', 'main': True, '_': morphology.cngs(_case(token), number)}
    if proper:
        data['proper'] = True
    if token.dep_ == 'attr':
        data['complement'] = True   # 繋辞の補語 (he is a doctor の doctor)
    return data


WEATHER_VERBS = {'rain', 'snow', 'hail', 'thunder', 'drizzle', 'pour', 'freeze'}


PARTICLES = ('up', 'down', 'out', 'off', 'away', 'back', 'in', 'on', 'over', 'around', 'along', 'through', 'forward')


def _phrasal_particle(token):
    """動詞に掛かる副詞のうち、句動詞の表にある組の副詞 (come back の back、run away の away)"""
    from dragoman.core import en_ja
    return token.text.lower() in PARTICLES and token.dep_ in ('advmod', 'prt') and token.head.pos_ in ('VERB', 'AUX') \
        and bool(en_ja.phrasal(token.head.lemma_.lower() + ' ' + token.text.lower()))


VERB_PREPOSITIONS = ('after', 'for', 'at', 'into')


def _prepositional_verb(token):
    """動詞と1つの訳語になる前置詞 (look after「世話をする」・wait for「待つ」)。前置詞の目的語は動詞の目的語に"""
    from dragoman.core import en_ja
    if token.text.lower() not in VERB_PREPOSITIONS or token.dep_ != 'prep' or token.head.pos_ != 'VERB':
        return False
    phrase = token.head.lemma_.lower() + ' ' + token.text.lower()
    return (phrase, 'verb') in morphology.GLOSSES or bool(en_ja.phrasal(phrase))


def _subordinator(text, lower, **extra):
    """副詞節の従属接続詞 (共通の解析器が節を主節の従属節にする: core/Adverbial.py)"""
    suffix, tense = morphology.SUBORDINATORS.get(lower, ('', None))
    data = {'surface': text, 'pos': 'conj', 'base': lower, 'ja': morphology.CONJUNCTIONS.get(lower, lower),
            'gloss_lang': 'ja', 'clause_suffix': suffix, 'clause_tense': tense}
    data.update(extra)
    return data


def _preposition(text, prep):
    ja = morphology.PREPOSITIONS.get(prep) or '〜' + prep
    return {'surface': text, 'pos': 'preposition', 'base': prep, 'dominates': 'Gen', 'ja': ja, 'gloss_lang': 'ja'}


def item_of(token, doc):
    """spaCy の語 → 項目 (dict)。扱わない語は None (句読点)"""
    pos, tag, text = token.pos_, token.tag_, token.text
    lower = text.lower()
    if pos == 'PUNCT' or text in PUNCTUATION:
        return None
    if lower in ('whether', 'if') and (lower == 'whether' or token.dep_ == 'mark' and token.head.dep_ in ('ccomp', 'dobj')):
        return {'surface': text, 'pos': 'adv', 'base': 'whether', 'ja': '', 'gloss_lang': 'ja'}   # 〜かどうか (間接疑問)
    if tag == 'POS':   # 所有格の 's (前の名詞を「〜の」に: possessives)
        return {'surface': text, 'pos': 'particle', 'base': "'s", 'ja': '', 'gloss_lang': 'ja', 'possessive_mark': True}
    if tag == 'EX':    # there is「〜がある」の there
        return {'surface': text, 'pos': 'particle', 'base': 'there', 'ja': '', 'gloss_lang': 'ja', 'expletive': True}
    if tag == 'TO' and token.head.pos_ in ('VERB', 'AUX') and token.dep_ == 'aux':
        return {'surface': text, 'pos': 'particle', 'base': 'to', 'ja': '', 'gloss_lang': 'ja'}   # 不定詞の to
    if lower in morphology.NEGATIONS and (tag == 'RB' or token.dep_ == 'neg'):
        return {'surface': text, 'pos': 'adv', 'base': 'not' if lower == "n't" else lower,
                'ja': morphology.NEGATIONS[lower], 'gloss_lang': 'ja', 'negation': True}
    if tag == 'MD':
        suffix, tense = morphology.MODALS.get(lower, ('', 'present'))
        return {'surface': text, 'pos': 'verb', 'lemma': lower, 'base': lower, 'ja': suffix, 'gloss_lang': 'ja',
                'modal_suffix': suffix, 'tense': tense, 'mood': 'indicative', 'voice': 'active', 'modal_aux': True,
                'person': None, 'number': None}
    if tag in ('PRP$',) or tag == 'WP$':
        ja = morphology.DETERMINERS.get(lower, lower)
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'desc': '不定形容詞',
                '_': morphology.cngs(morphology.ALL_CASES), 'compact': True, 'determiner': True}
    if tag in ('WDT', 'WP') and token.dep_ in ('nsubj', 'dobj', 'nsubjpass', 'pobj') and \
            token.head.dep_ in ('relcl', 'acl'):
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': '〜するところの', 'gloss_lang': 'ja',
                'desc': '関係代名詞', '_': morphology.cngs(_case(token)), 'compact': True}
    if lower == 'how' and token.head.pos_ in ('ADJ', 'ADV') and token.dep_ == 'advmod':
        return {'surface': text, 'pos': 'adv', 'base': 'how', 'ja': 'どれくらい', 'gloss_lang': 'ja', 'interrogative': True}
    if tag == 'WRB' and token.head.dep_ == 'advcl' and lower in morphology.CONJUNCTIONS:
        return _subordinator(text, lower, not_interrogative=True)   # 副詞節の when (I saw her when she came)
    if lower == 'where' and token.head.lemma_ == 'be':
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': 'どこに', 'gloss_lang': 'ja'}   # Where is …?「どこにあるか」
    if tag == 'WRB' and lower in morphology.QUESTION_ADVERBS and token.dep_ != 'advmod' or \
            tag == 'WRB' and lower in morphology.QUESTION_ADVERBS and token.head.dep_ != 'relcl':
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': morphology.QUESTION_ADVERBS[lower], 'gloss_lang': 'ja'}
    if tag == 'WDT' and token.dep_ == 'det':
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': morphology.DETERMINERS.get(lower, lower),
                'gloss_lang': 'ja', 'desc': '不定形容詞', '_': morphology.cngs(morphology.ALL_CASES), 'compact': True,
                'determiner': True, 'interrogative': True}   # which book・what color
    if tag == 'DT' or tag == 'PDT':
        if lower in morphology.DETERMINERS and token.dep_ in ('det', 'predet') or lower in morphology.ARTICLES:
            ja = morphology.DETERMINERS.get(lower, '')
            if lower == 'no':
                return {'surface': text, 'pos': 'adv', 'base': 'no', 'ja': '〜ない', 'gloss_lang': 'ja', 'negation': True}
            if not ja:
                return {'surface': text, 'pos': 'article', 'base': lower, 'ja': '', 'gloss_lang': 'ja',
                        '_': morphology.cngs(morphology.ALL_CASES), 'compact': True}
            return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja',
                    'desc': '指示代名詞' if lower in ('this', 'that', 'these', 'those') else '不定形容詞',
                    '_': morphology.cngs(morphology.ALL_CASES), 'compact': True, 'determiner': True}
    if lower == 'it' and token.dep_ == 'nsubj' and token.head.lemma_ in WEATHER_VERBS:
        return {'surface': text, 'pos': 'particle', 'base': 'it', 'ja': '', 'gloss_lang': 'ja'}   # 天候の it (it rained)
    if pos == 'PRON' or tag in ('PRP', 'WP', 'DT'):
        ja, person, number, cases = morphology.PRONOUNS.get(lower) or (lower, 3, 'sg', morphology.ALL_CASES)
        if len(cases) > 1:
            cases = tuple(c for c in _case(token) if c in cases) or cases
        data = {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(cases, number), 'compact': True}
        if tag == 'WP':
            data['desc'] = '疑問代名詞'   # 直接疑問・間接疑問の who・what (関係代名詞は上で)
        return data
    if pos == 'ADP' or tag == 'IN' and token.dep_ == 'prep' or tag == 'TO':
        if token.dep_ == 'mark' or tag == 'IN' and token.dep_ not in ('prep', 'agent', 'dative', 'prt') and \
                lower in morphology.CONJUNCTIONS:
            if token.dep_ == 'mark' and token.head.dep_ == 'advcl' and lower in morphology.SUBORDINATORS:
                return _subordinator(text, lower)
            return {'surface': text, 'pos': 'conj', 'base': lower, 'ja': morphology.CONJUNCTIONS.get(lower, lower),
                    'gloss_lang': 'ja'}
        if token.dep_ == 'prt' or _phrasal_particle(token) or _prepositional_verb(token):
            # 句動詞の副詞 (give up の up)・前置詞 (look after の after): 動詞に付ける (phrasal_verbs)
            return {'surface': text, 'pos': 'particle', 'base': lower, 'ja': '', 'gloss_lang': 'ja', 'particle_of': token.head.i}
        return _preposition(text, lower)
    if pos == 'SCONJ' and token.dep_ == 'mark' and token.head.dep_ == 'advcl' and lower in morphology.SUBORDINATORS:
        return _subordinator(text, lower)
    if tag in ('CC',) or pos in ('CCONJ', 'SCONJ'):
        return {'surface': text, 'pos': 'conj', 'base': lower, 'ja': morphology.CONJUNCTIONS.get(lower, lower),
                'gloss_lang': 'ja'}
    if pos == 'AUX' and token.dep_ in ('aux', 'auxpass'):
        return dict(_verb_data(token), auxiliary=True)
    if tag.startswith('VB'):
        return _verb_data(token)
    if (tag in ('NN', 'NNS') or pos == 'NOUN') and token.dep_ == 'npadvmod':
        ja, gloss_lang = morphology.gloss(lower, 'noun')   # 副詞の働きの名詞 (tomorrow・last week の week)
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': ja or lower, 'gloss_lang': gloss_lang or 'en'}
    if tag in ('NN', 'NNS', 'NNP', 'NNPS') or pos in ('NOUN', 'PROPN'):
        return _noun_data(token)
    if tag in ('JJ', 'JJR', 'JJS'):
        ja, gloss_lang = morphology.gloss(token.lemma_ or lower, 'adj')
        data = {'surface': text, 'pos': 'adj', 'base': token.lemma_ or lower, 'ja': ja or lower,
                'gloss_lang': gloss_lang or 'en', '_': morphology.cngs(morphology.ALL_CASES), 'main': True}
        if token.dep_ in ('acomp', 'attr') or token.dep_ == 'ROOT':
            data.update(predicative=True, _=morphology.cngs(('Nom',)))
        return data
    if tag == 'CD':
        return {'surface': text, 'pos': 'adj', 'base': text, 'ja': morphology.NUMBERS_JA.get(lower, text),
                'gloss_lang': 'ja', '_': morphology.cngs(morphology.ALL_CASES)}
    if _phrasal_particle(token):   # come back の back (spaCy は副詞と読む)
        return {'surface': text, 'pos': 'particle', 'base': lower, 'ja': '', 'gloss_lang': 'ja', 'particle_of': token.head.i}
    if tag in ('RB', 'RBR', 'RBS', 'WRB', 'UH') or pos in ('ADV', 'INTJ', 'PART'):
        ja, gloss_lang = morphology.gloss(lower, 'adv')
        if ja is None:
            adj, lang = morphology.gloss(re.sub('ly$', '', lower), 'adj')
            if adj and lower.endswith('ly'):
                ja, gloss_lang = morphology.adverbial(adj), lang   # quickly → 速く
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': ja or lower, 'gloss_lang': gloss_lang or 'en'}
    return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': lower, 'gloss_lang': 'en'}


# ----------------------------------------------------------------------
# 動詞の組

def _attach(verb, suffix):
    from dragoman.core.japanese import attach_auxiliary
    return attach_auxiliary(verb, suffix)


def merge_verbs(words, doc):
    """助動詞 (be・have・do・will・can …) を本動詞にまとめる。まとめた動詞は本動詞の位置に"""
    by_i = {w.doc_i: w for w in words}
    removed = set()
    for token in doc:
        main_word = by_i.get(token.i)
        main = _item(main_word) if main_word is not None else None
        if main is None or main.pos != 'verb' or main.attrib('auxiliary') or main.attrib('modal_aux'):
            continue
        auxes = [c for c in token.children if c.dep_ in ('aux', 'auxpass') and c.i in by_i]
        if not auxes:
            continue
        data = dict(main.item)
        forms = []
        finite = None
        for aux in sorted(auxes, key=lambda t: t.i):
            a = _item(by_i[aux.i])
            if a is None:
                continue
            lemma = a.attrib('lemma')
            if a.attrib('modal_aux'):
                finite = finite or a
                suffix = a.attrib('modal_suffix')
                if a.attrib('tense') == 'future' and not suffix:
                    data['tense'] = 'future'
                    forms.append('未来 (%s + 原形)' % aux.text)
                elif suffix:
                    data.update(modal=aux.text.lower(), main_ja=main.ja)
                    if main.attrib('gloss_lang') == 'ja':
                        data['ja'] = ','.join(_attach(j, suffix) for j in (main.ja or '').split(',')[:1])
                    data['tense'] = a.attrib('tense')
                    forms.append('%s + 原形' % aux.text)
            elif lemma == 'be' and aux.dep_ == 'auxpass':
                finite = finite or a
                data['voice'] = 'passive'
                if a.attrib('tense') == 'perfect':
                    data['tense'] = 'perfect'
                forms.append('受動 (be + 過去分詞)')
            elif lemma == 'be' and token.tag_ == 'VBG':
                finite = finite or a
                if main.attrib('gloss_lang') == 'ja':
                    data['ja'] = ','.join(_attach(j, 'ている') for j in (main.ja or '').split(',')[:1])
                data['tense'] = a.attrib('tense')
                forms.append('進行形 (be + 現在分詞)')
            elif lemma == 'have' and token.tag_ == 'VBN':
                finite = finite or a
                if data.get('lemma') == 'be' and any(c.dep_ == 'prep' and c.text.lower() == 'to' for c in token.children):
                    ja, gloss_lang = morphology.gloss('go', 'verb')   # have been to「〜へ行った」
                    data.update(lemma='be (go)', pres1sg='go', base='be (go)', ja=ja, gloss_lang=gloss_lang)
                    data.pop('existential', None)
                data['tense'] = 'pluperfect' if a.attrib('tense') == 'perfect' else 'perfect'
                forms.append('%s (have + 過去分詞)' % ('過去完了' if a.attrib('tense') == 'perfect' else '現在完了'))
            elif lemma == 'do':
                finite = finite or a
                data['tense'] = a.attrib('tense')
            elif lemma == 'be':   # be + 過去分詞を spaCy が aux と読んだもの
                finite = finite or a
                if token.tag_ == 'VBN':
                    data['voice'] = 'passive'
                    forms.append('受動 (be + 過去分詞)')
            removed.add(aux.i)
        if finite is not None:
            data.update(person=finite.attrib('person'), number=finite.attrib('number'))
        data['mood'] = 'indicative' if data.get('mood') in ('participle', 'infinitive') else data.get('mood')
        if data.get('lemma') != 'be':
            data.pop('existential', None)
        if forms:
            data['form'] = '・'.join(forms)
        surfaces = [by_i[a.i].surface for a in sorted(auxes, key=lambda t: t.i) if a.i in by_i] + [main_word.surface]
        data['surface'] = ' '.join(surfaces)
        main_word.items = [type(main)(data)]
        main_word.token_ixs = tuple(by_i[a.i].token_ix for a in auxes if a.i in by_i) + (main_word.token_ix,)
    dropped = {id(by_i[i]) for i in removed if i in by_i}
    for w in words:
        if id(w) in dropped:
            w.merged_into = True
    return [w for w in words if id(w) not in dropped]


# 不定詞を取って1つの述語にする動詞: 原形 → 本動詞に付ける形 (want to go → 行きたい、have to go → 行かなければならない)
CONTROL = {'want': 'たい', 'have': 'なければならない', 'need': 'なければならない', 'try': 'ようとする',
           'begin': '始める', 'start': '始める', 'like': 'たい', 'love': 'たい', 'hope': 'たい', 'would like': 'たい',
           'ought': 'べきだ'}


def control_verbs(words, doc):
    """want to go などの「動詞 + to 不定詞」を不定詞の位置の1語にまとめる (時制・人称は前の動詞から)"""
    by_i = {w.doc_i: w for w in words}
    removed = set()
    for token in doc:
        if token.dep_ != 'xcomp' or token.tag_ != 'VB' or token.head.i not in by_i or token.i not in by_i:
            continue
        head_word, main_word = by_i[token.head.i], by_i[token.i]
        h, m = _item(head_word), _item(main_word)
        if h is None or m is None or h.pos != 'verb' or m.pos != 'verb' or not any(c.tag_ == 'TO' for c in token.children):
            continue
        lemma, tense, form = h.attrib('lemma'), h.attrib('tense'), None
        if lemma == 'go' and token.head.tag_ == 'VBG' and '進行形' in (h.attrib('form') or ''):
            # be going to + 原形: 人が主語なら「〜するつもりだ」、ほか (It's going to rain) は未来「〜だろう」
            suffix = 'つもりだ' if _personal_subject(token.head) else ''
            tense = tense if suffix else 'future'
            form = '未来 (be going to + 原形)'
        elif lemma in ('get', 'got') and token.head.text.lower() == 'got' and \
                (h.attrib('colloquial') == 'gotta' or '現在完了' in (h.attrib('form') or '')):
            suffix, tense, form = 'なければならない', 'present', 'have got to + 原形'   # (have) got to「〜しなければならない」
        elif lemma in CONTROL:
            suffix = CONTROL[lemma]
        else:
            continue
        data = dict(m.item)
        if m.attrib('gloss_lang') == 'ja':
            from dragoman.core.japanese import attach_auxiliary
            first = (m.ja or '').split(',')[0]
            data['ja'] = _masu(first) + '始める' if suffix == '始める' else attach_auxiliary(first, suffix)
        data.update(tense=tense, person=h.attrib('person'), number=h.attrib('number'), mood=h.attrib('mood'),
                    surface=head_word.surface + ' to ' + main_word.surface, main_ja=m.ja,
                    form=form or '%s + to 不定詞' % lemma)
        if h.attrib('form') and not form:
            data['form'] = h.attrib('form') + '・' + data['form']
        if h.attrib('colloquial'):
            data['colloquial'] = h.attrib('colloquial')
        data.pop('existential', None)
        main_word.items = [type(m)(data)]
        main_word.surface = data['surface']
        removed.add(token.head.i)
    dropped = {id(by_i[i]) for i in removed}
    for w in words:
        if id(w) in dropped:
            w.merged_into = True
    return [w for w in words if id(w) not in dropped]


PERSONAL_PRONOUNS = ('i', 'you', 'we', 'he', 'she', 'they')


def _personal_subject(token):
    """主語が人 (人称代名詞・人の名前・人を表す名詞) か"""
    for c in token.children:
        if c.dep_ == 'nsubj':
            return c.text.lower() in PERSONAL_PRONOUNS or c.ent_type_ == 'PERSON' or \
                c.pos_ == 'NOUN' and c.lemma_.lower() in PERSON_NOUNS
    return False


PERSON_NOUNS = {'man', 'woman', 'boy', 'girl', 'child', 'teacher', 'student', 'friend', 'mother', 'father', 'brother',
                'sister', 'people', 'doctor', 'king', 'queen'}


def _masu(verb):
    from dragoman.kobun.modernize import Modern
    try:
        return Modern.masu_stem(verb)
    except Exception:
        return verb


CLAUSE_DEPS = ('ccomp', 'advcl', 'relcl', 'csubj', 'acl')


def clause_starts(words, doc):
    """従属節 (ccomp・advcl・relcl …) の最初の語に節の頭の印 (共通の解析器が動詞の間の語をそこで分ける:
    I don't know | what you're talking about)"""
    by_i = {w.doc_i: w for w in words}
    for token in doc:
        if token.dep_ not in CLAUSE_DEPS:
            continue
        start = min(t.i for t in token.subtree)
        for i in range(start, token.i + 1):
            item = _item(by_i.get(i)) if by_i.get(i) is not None else None
            if item is not None:
                item.item['clause_start'] = True
                break


def stranded_prepositions(words, doc):
    """取り残された前置詞 (what are you talking about の about): 目的語 (前にある疑問詞・関係詞) の直前に移す"""
    by_i = {w.doc_i: w for w in words}
    for token in doc:
        if token.dep_ != 'pobj' or token.head.i <= token.i or token.head.i not in by_i or token.i not in by_i:
            continue
        prep, obj = by_i[token.head.i], by_i[token.i]
        if _pos(prep) != 'preposition':
            continue
        words.remove(prep)
        words.insert(words.index(obj), prep)
        if _item(obj) is not None and _item(obj).attrib('clause_start'):
            _item(prep).item['clause_start'] = True
    return words


def phrasal_verbs(words, doc):
    """句動詞 (give up・look after の副詞の部分): 英和の表に句動詞があれば動詞の訳に、無ければ副詞は落とす"""
    by_i = {w.doc_i: w for w in words}
    for w in words:
        item = _item(w)
        if item is None or item.attrib('particle_of') is None:
            continue
        verb = by_i.get(item.attrib('particle_of'))
        v = _item(verb) if verb is not None else None
        if v is None or v.pos != 'verb':
            continue
        phrase = '%s %s' % (v.attrib('lemma'), item.attrib('base'))
        from dragoman.core import en_ja
        found = en_ja.phrasal(phrase)   # JMdict の英訳の句動詞を先に (give up → 諦める)
        ja, gloss_lang = (','.join(found[:2]), 'ja') if found else (None, None)
        if (phrase, 'verb') in morphology.GLOSSES or not ja:
            ja, gloss_lang = morphology.gloss(phrase, 'verb')
        if ja:
            verb.items = [type(v)(dict(v.item, lemma=phrase, base=phrase, ja=ja, gloss_lang=gloss_lang))]


CONTENT_POS = ('noun', 'verb', 'adj')


def corpus_glosses(words, doc):
    """訳語の候補を対訳文 (Tatoeba) で文の語の文脈から選ぶ (take this medicine → 薬、write a letter → 手紙、
    wash your hands → 手)。決めておいた訳語 (GLOSSES)・名前は変えない"""
    from dragoman.core import en_ja
    context = [t.lemma_.lower() for t in doc if t.pos_ in ('NOUN', 'VERB', 'ADJ', 'PROPN')]
    for word in words:
        item = _item(word)
        if item is None or item.pos not in CONTENT_POS or item.attrib('gloss_lang') != 'ja' or item.attrib('proper') or \
                item.attrib('context_gloss') or item.attrib('modal_aux'):
            continue
        lemma = item.attrib('lemma') or item.attrib('base')
        if not lemma or ' ' in lemma or (lemma.lower(), item.pos) in morphology.GLOSSES:
            continue
        candidates = [c for c in en_ja.lookup(lemma, item.pos) if 'を' not in c]   # 目的語まで入った訳語 (手紙を書く) は除く
        if len(candidates) < 2:
            continue
        ranked = en_ja.corpus_ranked(lemma, candidates, context, prune=True)
        ja = ','.join(ranked[:2])
        if ja != item.ja:
            word.items = [type(item)(dict(item.item, ja=ja))]


def verbs_in_context(words, doc):
    """目的語・主語の語で動詞の訳語を選ぶ (pass the exam → 受かる、take medicine → 飲む、time passes → 経つ)"""
    from dragoman.core import en_ja
    by_i = {w.doc_i: w for w in words}
    for token in doc:
        word = by_i.get(token.i)
        item = _item(word) if word is not None else None
        if item is None or item.pos != 'verb' or ' ' in (item.attrib('lemma') or '') or item.attrib('modal_aux'):
            continue
        objects = [c.lemma_ for c in token.children if c.dep_ in ('dobj', 'nsubjpass')] + \
            [c.lemma_ for c in token.children if c.dep_ == 'nsubj']
        found = en_ja.verb_in_context(item.attrib('lemma'), objects) if objects else []
        if found:
            ja = ','.join(found[:2])
            data = dict(item.item, ja=ja, gloss_lang='ja', context_gloss=True)
            if _intransitive(found[0]) and any(c.dep_ == 'dobj' for c in token.children):
                data['acc_particle'] = 'に'   # 試験に受かる (自動詞の訳語)
            word.items = [type(item)(data)]


def _intransitive(ja):
    from dragoman.kobun.modernize import _transitivity
    return _transitivity().get(ja) == {'vi'}


def possessives(words):
    """所有格の 's: 前の名詞を後ろの名詞に掛ける「〜の」(限定詞と同じく)"""
    out = []
    for k, w in enumerate(words):
        item = _item(w)
        if item is not None and item.attrib('possessive_mark'):
            if out and _pos(out[-1]) == 'noun':
                owner = out[-1]
                o = _item(owner)
                ja = (o.ja or owner.surface).split(',')[0]
                owner.items = [type(o)(dict(o.item, pos='pronoun', ja=ja + 'の', determiner=True, desc='不定形容詞',
                                            _=morphology.cngs(morphology.ALL_CASES), compact=True))]
                owner.surface += w.surface
            w.merged_into = True
            continue
        out.append(w)
    return out


HOW_ADJECTIVES = {'old': '何歳', 'many': 'いくつ', 'much': 'いくら', 'long': 'どれくらいの長さ', 'far': 'どれくらいの距離'}


def how_adjectives(words):
    """how old「何歳」・how many「いくつ」など: how を落とし、形容詞を疑問詞の補語に (How old are you? → あなたは何歳であるか)"""
    out = []
    for k, w in enumerate(words):
        item = _item(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        n = _item(nxt) if nxt is not None else None
        if item is not None and item.attrib('base') == 'how' and n is not None and n.attrib('base') in HOW_ADJECTIVES and \
                n.attrib('predicative'):
            nxt.items = [type(n)(dict(n.item, pos='pronoun', ja=HOW_ADJECTIVES[n.attrib('base')], desc='疑問代名詞',
                                      complement=True, gloss_lang='ja', _=morphology.cngs(('Nom',))))]
            nxt.surface = w.surface + ' ' + nxt.surface
            w.merged_into = True
            continue
        if item is not None and item.attrib('base') == 'how' and n is not None and n.attrib('base') in ('many', 'much'):
            nxt.items = [type(n)(dict(n.item, ja='いくつの' if n.attrib('base') == 'many' else 'どれくらいの',
                                      gloss_lang='ja', interrogative=True))]   # how many books「いくつの本」
            nxt.surface = w.surface + ' ' + nxt.surface
            w.merged_into = True
            continue
        out.append(w)
    return out


def existential_there(words):
    """there is / are「〜がある」: there を落とし、be の後ろの名詞を主語に"""
    for k, w in enumerate(words):
        item = _item(w)
        if item is None or not item.attrib('expletive'):
            continue
        for v in words[k + 1:k + 4]:
            vi = _item(v)
            if vi is not None and vi.pos == 'verb' and vi.attrib('lemma') == 'be':
                v.items = [type(vi)(dict(vi.item, ja='ある,いる', gloss_lang='ja', existential=True,
                                         lemma='there be', base='there be'))]
                break
        return


def attach_articles(words):
    """冠詞 (the / a) を後ろの名詞 (間に形容詞・数詞があってもよい) に掛け、語の列から除く (訳さない)"""
    out = []
    for i, word in enumerate(words):
        if _pos(word) != 'article':
            out.append(word)
            continue
        j = i + 1
        while j < len(words) and _pos(words[j]) in ('adj',) and not _item(words[j]).attrib('predicative'):
            j += 1
        if j < len(words) and _pos(words[j]) in ('noun', 'pronoun'):
            words[j].add_modifier(word)
            word.article_of = words[j]
            continue
        out.append(word)
    return out


def passive_agents(words):
    """受動の文の by は動作主「〜によって」"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('voice') == 'passive' for w in words):
        return
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'by':
            w.items = [type(item)(dict(item.item, ja='〜によって'))]


def lookup_all(surfaces):
    surfaces, colloquial = expand_colloquial(surfaces)
    doc = morphology.parse(surfaces)
    words = []
    for token in doc:
        data = item_of(token, doc)
        if data is not None and token.i in colloquial:
            data['colloquial'] = colloquial[token.i][0]   # gotta の got (have got to と同じく「〜しなければならない」)
        word = Word(token.text, None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    global _display
    _display = list(words)
    clause_starts(words, doc)
    words = stranded_prepositions(words, doc)
    corpus_glosses(words, doc)     # 訳語を決めてから助動詞とまとめる (can give up → 諦めることができる)
    phrasal_verbs(words, doc)
    verbs_in_context(words, doc)
    words = merge_verbs(words, doc)
    words = control_verbs(words, doc)
    words = possessives(words)
    words = how_adjectives(words)
    existential_there(words)
    words = [w for w in words if _pos(w) != 'particle']
    words = attach_articles(words)
    passive_agents(words)
    restore_colloquial(words, colloquial)
    for i, word in enumerate(words):
        word.index = i
    return words


_display = []


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(ENGLISH):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
