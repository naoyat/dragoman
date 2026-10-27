#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ポルトガル語の文の解析 (ブラジルとポルトガルの両方)
#
# spaCy (pt_core_news_sm) の品詞・原形・性・数・人称・時制・依存関係で語の項目を作り (portuguese/morphology.py)、
# 動詞の組を1語にまとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器 (core/analyzer.py) を
# ポルトガル語の設定 (PORTUGUESE) で使う:
#   - 格は依存関係から (主語 nsubj → 主格、目的語 obj → 対格、間接目的語 iobj → 与格、前置詞の後ろ → 前置詞の目的語)。
#     冠詞は名詞に掛けて訳さない。前置詞と冠詞の縮約形 (do・na・pelo・ao …) は前置詞、前置詞と代名詞の縮約形
#     (dele「彼の」・nele) は前置詞 + 代名詞の2語に
#   - 接語の代名詞: 動詞の前 (me deu「私に与えた」。ブラジルに多い) も、ハイフンで動詞の後ろ (deu-me。ポルトガルに多い) も。
#     動詞の中に入る接語 (dar-te-ei「君に与えるだろう」) は動詞の未来・過去未来の形に戻す
#   - 動詞の組を本動詞にまとめる: ter / haver + 過去分詞 → 完了、ser + 過去分詞 → 受動、estar + 現在分詞 (ブラジル)・
#     estar a + 不定詞 (ポルトガル) → 進行「〜している」、ir + 不定詞 → 未来、話法の動詞 + 不定詞 (poder「〜できる」、
#     querer「〜したい」、dever・ter que / de「〜なければならない」)
#   - não・nunca は否定。há + 名詞「〜がある」(ブラジルの口語の tem + 名詞も)
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '(': 'comma', ')': 'comma', '"': None, '“': None, '”': None,
               '«': None, '»': None, "'": None}
LETTERS = 'A-Za-zÀ-ÖØ-öø-ÿ'
TOKEN = re.compile(r"[%s]+(?:-[%s]+)*|\d+(?:[.,]\d+)*|[.!?…,;:—–()\"“”«»']" % (LETTERS, LETTERS))
# ハイフンの後ろの接語 (deu-me・vê-lo・dá-lhes)。-lo・-la は r・s・z で終わる形の後ろ (vê-lo = ver + o)、-no・-na は鼻音の後ろ
ENCLITICS = {'me', 'te', 'se', 'nos', 'vos', 'lhe', 'lhes', 'o', 'a', 'os', 'as', 'lo', 'la', 'los', 'las', 'no', 'na',
             'nas'}
# 動詞の中に入る接語 (未来・過去未来の語幹 + 接語 + 語尾: dar-te-ei → darei + te)
MESOCLITIC_ENDINGS = ('ei', 'ás', 'á', 'emos', 'eis', 'ão', 'ia', 'ias', 'íamos', 'íeis', 'iam')


def _root_items(lemma):
    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


# 間接疑問: 節の動詞の法、疑問詞を取る動詞、疑問詞 (core/analyzer.detect_indirect_questions)
QUESTION_MOODS = ('indicative', 'subjunctive')
QUESTION_VERBS = frozenset({'saber', 'perguntar', 'entender', 'compreender', 'dizer', 'ver', 'explicar', 'mostrar',
                            'esquecer', 'lembrar', 'descobrir', 'imaginar', 'contar', 'perceber'})
INTERROGATIVES = {'onde': 'どこで', 'aonde': 'どこへ', 'quando': 'いつ', 'como': 'どのように', 'porque': 'なぜ',
                  'por que': 'なぜ', 'quanto': 'どれだけ', 'se': '', 'quem': None, 'qual': None}   # que は補文の「〜ということ」


PORTUGUESE = language.Language(
    name='pt',
    question_moods=QUESTION_MOODS, question_verbs=QUESTION_VERBS, interrogatives=INTERROGATIVES,
    subordinators=morphology.SUBORDINATORS,
    and_words=('e',),
    nor_words=('nem',),
    or_words=('ou',),
    copulas=frozenset({'ser', 'estar'}),
    negations=frozenset({'não', 'nunca', 'jamais'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
)


def _split(token):
    """ハイフンの接語を分ける: deu-me → [deu, -me]、dar-te-ei → [darei, -te]。複合語 (guarda-chuva) はそのまま"""
    parts = token.split('-')
    if len(parts) == 3 and parts[1].lower() in ENCLITICS and parts[2].lower() in MESOCLITIC_ENDINGS:
        stem = parts[0]
        if parts[1].lower().startswith('l'):   # -lo・-la の前では語幹の r が落ちる (vê-lo-ei = verei + o)
            stem = _unaccent(stem) + 'r'
        return [stem + parts[2], '-' + parts[1]]
    if len(parts) >= 2 and all(p.lower() in ENCLITICS for p in parts[1:]) and parts[0]:
        return [parts[0]] + ['-' + p for p in parts[1:]]
    return [token]


def _unaccent(word):
    return word[:-1] + {'á': 'a', 'â': 'a', 'ê': 'e', 'é': 'e', 'í': 'i', 'ô': 'o', 'ó': 'o'}.get(word[-1:], word[-1:])


def tokens(text):
    return [piece for token in TOKEN.findall(text) for piece in _split(token)]


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
# 語の項目

def _base(lemma, row=None):
    gender = (row or {}).get('gender')
    article = {'m': 'o', 'f': 'a', 'mf': 'o / a'}.get(gender)
    return '%s%s' % (lemma, ' (%s)' % article if article else '')


TENSES = {'Pres': 'present', 'Imp': 'imperfect', 'Past': 'perfect', 'Pqp': 'pluperfect', 'Fut': 'future'}
TABLE_TENSES = {'present': 'present', 'perfect': 'preterite', 'imperfect': 'imperfect', 'pluperfect': 'pluperfect',
                'future': 'future'}   # 時制 → 語形の表の印
MOODS = {'Ind': 'indicative', 'Sub': 'subjunctive', 'Cnd': 'subjunctive', 'Imp': 'imperative'}


def _verb_data(token, feats, lemma=None):
    lemma = lemma or token.lemma_.lower()
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    if ja is None:   # spaCy が原形に戻せない形 (Vou の Vou) は語形の表から
        better = next((l for l, tags in morphology.verb_forms(token.text.lower())), None)
        if better:
            lemma = better
            ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    tense = TENSES.get(feats.get('Tense'), 'present')
    mood = MOODS.get(feats.get('Mood'), 'indicative')
    if feats.get('Mood') == 'Cnd':
        tense = 'future'   # 過去未来 (条件法)「〜だろう」
    form = feats.get('VerbForm')
    if form == 'Inf':
        mood = 'infinitive'
    elif form == 'Part':
        mood = 'participle'
    elif form == 'Ger':
        mood = 'participle'
        tense = 'present'
    person = int(feats['Person']) if feats.get('Person', '').isdigit() else 3
    if form == 'Fin' or form is None and mood == 'indicative':
        # spaCy の時制が語形の表のどの読みにも無ければ表から (sei を過去と読む)。現在・直説法を先に
        readings = [t for l, t in morphology.verb_forms(token.text.lower()) if l == lemma and
                    t & {'present', 'preterite', 'imperfect', 'pluperfect', 'future', 'conditional'}]
        wanted = TABLE_TENSES.get(tense)
        if readings and wanted and not any(wanted in t for t in readings):
            best = sorted(readings, key=lambda t: ('present' not in t, 'indicative' not in t))[0]
            tense = next((k for k, v in TABLE_TENSES.items() if v in best), tense)
            mood = 'subjunctive' if 'subjunctive' in best and 'indicative' not in best else mood
    if mood in ('infinitive', 'participle'):
        person = None
    data = {'surface': token.text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': mood, 'tense': tense,
            'person': person, 'number': morphology.NUMBERS.get(feats.get('Number'), 'sg'), 'main': True}
    if form == 'Ger':
        data['gerund'] = True
    if lemma in ('ser', 'estar'):
        data['existential'] = True
    return data


PARTICIPLE = re.compile(r'^(.+)([aií])d[oa]s?$')


def _participle_gloss(word):
    """辞書に無い過去分詞の形容詞 (trancados) → 動詞 (trancar「閉じる」) の受動「閉じられた」。動詞も無ければ (None, None)"""
    m = PARTICIPLE.match(word)
    if not m:
        return None, None
    stem, vowel = m.group(1), {'a': 'ar', 'i': 'ir', 'í': 'ir'}[m.group(2)]
    for verb in ((stem + vowel,) if vowel == 'ar' else (stem + 'er', stem + 'ir')):
        ja, gloss_lang, _ = morphology.gloss(verb, 'verb')
        if ja and gloss_lang == 'ja':
            from dragoman.core.japanese import JaVerb
            return ','.join(JaVerb(j).attributive_form('passive') for j in ja.split(',')[:2]), 'ja'
    return None, None


def _relative_cases(token, lower):
    """関係代名詞の格: que・qual は節の中の働き (spaCy の依存関係) で主格か対格に絞る (seis homens que moram aqui の que は主格)"""
    cases = morphology.RELATIVES.get(lower, ('Nom', 'Acc'))
    if cases == ('Nom', 'Acc'):
        if token.dep_.startswith('nsubj') and token.head.morph.get('Person') in ([], ['3']) and \
                not any(c.dep_.startswith('nsubj') and c.i != token.i for c in token.head.children):
            return ('Nom',)   # 1・2人称の動詞 (o homem que vi) の que は主語でない (spaCy が nsubj にすることがある)
        if token.dep_ in ('obj', 'dobj'):
            return ('Acc',)
    return cases


def _case_of(token):
    """依存関係から名詞・代名詞の格"""
    dep = token.dep_
    if any(c.dep_ == 'case' for c in token.children) or token.i > 0 and token.doc[token.i - 1].pos_ == 'ADP':
        return ('Gen',)   # 前置詞の目的語
    if dep.startswith('nsubj'):
        return ('Nom',)
    if dep == 'obj':
        return ('Acc',)
    if dep == 'iobj':
        return ('Dat',)
    if dep == 'ROOT' or any(c.dep_ == 'cop' for c in token.children):
        return ('Nom',)   # 繋辞の補語 (Ela é professora)
    return ('Nom', 'Acc')


ADVERB_SUBORDINATORS = {'enquanto', 'quando', 'embora', 'caso'}


def _noun_data(token, feats, proper=False):
    text, lemma = token.text, token.lemma_ or token.text
    if proper:
        lemma = text
    ja, gloss_lang, row = morphology.gloss(lemma, 'name' if proper else 'noun')
    if ja is None and lemma != text:
        ja, gloss_lang, row = morphology.gloss(text.lower(), 'noun')
        if ja is not None and not proper:
            lemma = text.lower()   # spaCy の原形の誤り (rosa → roso): 辞書で引けた語形を見出しに
    given = proper and row is not None and re.search(r'given name|surname', row.get('en') or '')
    if proper and (ja is None or given or gloss_lang == 'en' and ja.split(',')[0] in (lemma, text)):
        from .katakana import katakana   # 辞書に無い名前・人名はカタカナ (João → ジョアオン)
        ja, gloss_lang = katakana(lemma), 'ja'
    gender = dictionary.gender(lemma) or (row or {}).get('gender')
    data = {'surface': text, 'pos': 'noun', 'base': _base(lemma, row), 'lemma': lemma, 'ja': ja or text,
            'gloss_lang': gloss_lang or 'en', 'main': True,
            '_': morphology.cngs(_case_of(token), dict(feats, Gender=None) if gender in ('m', 'f') else feats, gender)}
    if proper:
        data['proper'] = True
    return data


def _preposition(text, prep):
    return {'surface': text, 'pos': 'preposition', 'base': prep, 'dominates': 'Gen',
            'ja': morphology.PREPOSITIONS.get(prep, '〜' + prep), 'gloss_lang': 'ja'}


_ENCLITIC_SURFACES = {}   # spaCy の語の番号 → 表層形が - で始まる接語か (lookup_all が入れる)


def _enclitic_after(token):
    return _ENCLITIC_SURFACES.get(token.i + 1, False)


def item_of(token, doc):
    """spaCy の語 → 項目 (dict)。扱わない語は None (句読点)"""
    pos, lemma, text = token.pos_, token.lemma_, token.text
    feats = morphology.morph(token)
    lower = text.lower().lstrip('-')
    if pos == 'PUNCT' or lower in PUNCTUATION:
        return None
    enclitic = text.startswith('-')
    if enclitic or (lower in morphology.CLITICS and pos == 'PRON'):
        ja, person, number, cases = morphology.PRONOUNS.get(lower, (lower, 3, 'sg', ('Acc',)))
        if lower in ('me', 'te', 'nos', 'vos', 'se'):
            # 人の接語の格は動詞で決める (目的語の名詞があれば与格: dative_clitics。与格を取る動詞の表 DATIVE_VERBS)。
            # spaCy の obj / iobj は揺れる (me viu を iobj と読む)
            head = token.head.lemma_.lower() if token.head is not None else ''
            cases = ('Dat',) if head in morphology.DATIVE_VERBS else ('Acc',)
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(cases, feats), 'compact': True, 'clitic': True,
                **({'enclitic': True} if enclitic else {})}
    host = token.i + 1 < len(doc) and _enclitic_after(token)
    if host and pos not in ('VERB', 'AUX'):
        readings = morphology.verb_forms(lower)   # 接語の付いた語は動詞 (文頭の Dei-lhe を名詞と読む誤り)
        if readings:
            lemma, tags = sorted(readings, key=lambda r: ('indicative' not in r[1], 'present' not in r[1]))[0]
            person = next((k + 1 for k, p in enumerate(('first-person', 'second-person', 'third-person')) if p in tags), 3)
            tense = next((k for k, v in TABLE_TENSES.items() if v in tags), 'present')
            return _verb_data(token, {'VerbForm': 'Fin', 'Person': str(person),
                                      'Number': 'Plur' if 'plural' in tags else 'Sing',
                                      'Tense': {v: k for k, v in TENSES.items()}.get(tense, 'Pres')}, lemma)
    if pos == 'ADP' or (pos == 'DET' and ' ' in lemma and lemma.split()[0] in morphology.PREPOSITIONS):
        prep = lemma.split()[0] if ' ' in lemma else lower
        return _preposition(text, prep if prep in morphology.PREPOSITIONS else lower)
    if pos == 'DET' or lower in morphology.ARTICLES and pos not in ('PRON', 'NOUN', 'VERB'):
        if lower in morphology.DETERMINERS:
            ja = morphology.DETERMINERS[lower]
            if lower in ('nenhum', 'nenhuma'):
                return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': '〜ない', 'gloss_lang': 'ja', 'negation': True}
            data = {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja',
                    'desc': '指示代名詞' if lower.startswith(('est', 'ess', 'aquel')) else '不定形容詞',
                    '_': morphology.cngs(morphology.CASES + ('Gen',), dict(feats, Number=None)),
                    'compact': True, 'determiner': True}
            if lower in morphology.POSSESSIVES:
                data['possessive'] = morphology.POSSESSIVES[lower]
            return data
        if pos != 'NUM' and lower not in morphology.NUMBERS_JA or lower in ('um', 'uma'):
            return {'surface': text, 'pos': 'article', 'base': lower, 'ja': '', 'gloss_lang': 'ja',
                    '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'compact': True}
    if pos == 'PRON':
        if feats.get('PronType') == 'Rel' or lower in morphology.RELATIVES and token.head.dep_ == 'acl:relcl':
            return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': '〜するところの', 'gloss_lang': 'ja',
                    'desc': '関係代名詞', '_': morphology.cngs(_relative_cases(token, lower)),
                    'compact': True}
        ja, person, number, cases = morphology.PRONOUNS.get(lower) or \
            (lemma, 3, morphology.NUMBERS.get(feats.get('Number'), 'sg'), morphology.CASES)
        if lower not in morphology.CLITICS:
            cases = _case_of(token) if lower in morphology.SUBJECT_PRONOUNS or len(cases) > 1 else cases
        data = {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(cases, feats), 'compact': True}
        if feats.get('PronType') == 'Int' or lower in ('quem', 'que', 'qual', 'quais') and token.dep_ != 'mark':
            data['desc'] = '疑問代名詞'
        return data
    if pos == 'NUM' or lower in morphology.NUMBERS_JA and lower not in ('um', 'uma'):
        ja = morphology.NUMBERS_JA.get(lower, text)
        return {'surface': text, 'pos': 'adj', 'base': text, 'ja': ja + 'つの' if len(ja) <= 2 and lower in
                morphology.NUMBERS_JA else ja, 'gloss_lang': 'ja', '_': morphology.cngs(morphology.CASES + ('Gen',))}
    if lower in morphology.LANGUAGE_NOUNS and pos in ('NOUN', 'ADJ', 'PROPN') and token.dep_ in ('obj', 'nsubj', 'obl'):
        data = _noun_data(token, feats)   # falar português「ポルトガル語」
        data.update(ja=morphology.LANGUAGE_NOUNS[lower], gloss_lang='ja', lemma=lower, base=lower + ' (o)')
        return data
    if pos in ('NOUN', 'PROPN'):
        return _noun_data(token, feats, proper=pos == 'PROPN' and text[:1].isupper())   # spaCy は小文字の rosa も PROPN に
    if pos == 'ADJ':
        ja, gloss_lang, row = morphology.gloss(lemma, 'adj')
        if ja is None and lemma != lower:
            ja, gloss_lang, row = morphology.gloss(lower, 'adj')
        if ja is None:
            ja, gloss_lang = _participle_gloss(lower)
        data = {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'main': True}
        if token.dep_ == 'ROOT' or any(c.dep_ == 'cop' for c in token.children):
            data.update(predicative=True, _=morphology.cngs(('Nom',), feats))   # 述語 (A casa é bonita)
        return data
    if pos == 'VERB' and feats.get('VerbForm') == 'Part' and token.dep_ in ('acl', 'amod') and \
            not any(c.dep_ in ('obj', 'nsubj', 'aux', 'aux:pass') for c in token.children):
        ja, gloss_lang = _participle_gloss(lower)   # 名詞に掛かる過去分詞 (os livros vendidos「売られた本」)
        if ja:
            return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja, 'gloss_lang': gloss_lang,
                    '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'main': True, 'desc': '過去分詞'}
    if pos in ('VERB', 'AUX'):
        return _verb_data(token, feats)
    if lower in morphology.NEGATIONS and pos in ('ADV', 'PRON', 'DET', 'CCONJ'):
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': morphology.NEGATIONS[lower], 'gloss_lang': 'ja',
                'negation': True}
    if lower == 'que' and pos in ('SCONJ', 'PRON') and token.dep_ == 'mark' and token.head.dep_ in ('ccomp', 'xcomp'):
        # 補文の que (Ela disse que me ama「{…}と 言った」): 共通の解析器が節を前の動詞の従属節にする (core/Adverbial.py)
        say = token.head.head.lemma_.lower() in morphology.SAY_VERBS
        return {'surface': text, 'pos': 'conj', 'base': lower, 'ja': '〜ということ', 'gloss_lang': 'ja',
                'clause_suffix': 'と' if say else 'ことを', 'clause_start': True, 'complement': True}
    if lower in INTERROGATIVES and INTERROGATIVES[lower] and token.i == 0 and token.doc[-1].text == '?':
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': INTERROGATIVES[lower], 'gloss_lang': 'ja'}   # Quando vens?
    if pos == 'ADV' and lower in ADVERB_SUBORDINATORS and (token.i > 0 or token.dep_ == 'mark') and \
            token.doc[-1].text != '?' and \
            any(t.pos_ in ('VERB', 'AUX') for t in token.doc[token.i + 1:]):
        pos = 'SCONJ'   # spaCy が副詞と読む従属接続詞 (A menina canta enquanto o menino lê)
    if pos in ('CCONJ', 'SCONJ'):
        return {'surface': text, 'pos': 'conj', 'base': lower, 'ja': morphology.CONJUNCTIONS.get(lower, lemma),
                'gloss_lang': 'ja'}
    if lower in INTERROGATIVES and INTERROGATIVES[lower]:
        return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': INTERROGATIVES[lower], 'gloss_lang': 'ja'}
    ja, gloss_lang, row = morphology.gloss(lower if lower in morphology.GLOSSES else lemma, 'adv')
    if gloss_lang == 'ja' and row is not None and row['pos'] == 'adj':
        ja = morphology.adverbial(ja)
    return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en'}


# ----------------------------------------------------------------------
# 動詞の組

def _attach(verb, suffix):
    from dragoman.core.japanese import attach_auxiliary
    return attach_auxiliary(verb, suffix)


def _merge(aux_word, main_word, kind, aux_lemma=None):
    """aux_word の位置に、本動詞の訳・時制・態をまとめた動詞を作る。kind: perfect / passive / progressive / future / modal"""
    a, m = _item(aux_word), _item(main_word)
    data = dict(m.item)
    data.update(person=a.attrib('person'), number=a.attrib('number'), mood=a.attrib('mood'),
                surface=aux_word.surface + ' … ' + main_word.surface)
    data.pop('existential', None)
    data.pop('gerund', None)
    aux_tense = a.attrib('tense')
    past = aux_tense in ('perfect', 'imperfect', 'pluperfect')
    if kind == 'perfect':
        data['tense'] = 'pluperfect' if past else 'perfect'
        data['form'] = '%s (%s + 過去分詞)' % ('過去完了' if past else '複合完了', aux_lemma)
    elif kind == 'passive':
        data.update(voice='passive', tense=aux_tense)
        data['form'] = '受動 (%s + 過去分詞)' % aux_lemma
    elif kind == 'progressive':
        data['tense'] = 'imperfect' if past else 'progressive'
        data['form'] = '進行 (%s + %s)' % (aux_lemma, '現在分詞' if m.attrib('mood') == 'participle' else 'a + 不定詞')
    elif kind == 'future':
        data['tense'] = 'future'
        data['form'] = '近い未来 (ir + 不定詞)'
    elif kind == 'modal':
        suffix = morphology.MODALS[aux_lemma]
        data['ja'] = ','.join(_attach(j, suffix) for j in (m.ja or '').split(',')[:1]) if m.attrib('gloss_lang') == 'ja' \
            else m.ja
        data['tense'] = aux_tense
        data.update(modal=aux_lemma, main_ja=m.ja, form='%s + 不定詞' % aux_lemma)
    data['mood'] = 'indicative' if data.get('mood') in ('participle', 'infinitive') else data.get('mood')
    data['main'] = True
    aux_word.items = [type(m)(data)]
    aux_word.surface = data['surface']
    aux_word.token_ixs = (aux_word.token_ix, main_word.token_ix)
    aux_word.token_ix = main_word.token_ix


def merge_verbs(words, doc):
    """助動詞と本動詞 (過去分詞・現在分詞・不定詞) を、助動詞の位置の1語にまとめる"""
    by_i = {w.doc_i: w for w in words}
    removed = set()
    for token in doc:
        main_word = by_i.get(token.i)
        if main_word is None or _pos(main_word) != 'verb':
            continue
        main = _item(main_word)
        auxes = [c for c in token.children if c.dep_ in ('aux', 'aux:pass') and c.i in by_i and c.i < token.i]
        xcomp_head = token.head if token.dep_ == 'xcomp' and token.head.i in by_i and token.head.i < token.i else None
        for aux in auxes:
            lemma = _item(by_i[aux.i]).attrib('lemma') if _item(by_i[aux.i]) else aux.lemma_
            mood = main.attrib('mood')
            if lemma in ('ter', 'haver') and mood == 'participle' and not main.attrib('gerund'):
                kind = 'perfect'
            elif lemma in ('ser',) and mood == 'participle':
                kind = 'passive'
            elif lemma in morphology.PROGRESSIVE and (main.attrib('gerund') or mood == 'infinitive'):
                kind = 'progressive'
            elif lemma == 'ir' and mood == 'infinitive':
                kind = 'future'
            elif lemma in morphology.MODALS and mood == 'infinitive':
                kind = 'modal'
            else:
                continue
            _merge(by_i[aux.i], main_word, kind, lemma)
            removed.add(token.i)
            break
        else:
            if xcomp_head is not None and main.attrib('mood') == 'infinitive':
                head_word = by_i[xcomp_head.i]
                lemma = _item(head_word).attrib('lemma') if _item(head_word) else None
                if lemma == 'ir':
                    _merge(head_word, main_word, 'future', lemma)
                    removed.add(token.i)
                elif lemma in morphology.MODALS:
                    _merge(head_word, main_word, 'modal', lemma)
                    removed.add(token.i)
                elif lemma in morphology.PROGRESSIVE and any(c.text.lower() == 'a' for c in token.children):
                    _merge(head_word, main_word, 'progressive', lemma)   # estar a fazer (ポルトガル)
                    removed.add(token.i)
    # 動詞の組の前置詞・que (ter que fazer・estar a fazer・gostar de cantar) は落とす
    for token in doc:
        if token.i in removed:
            for c in token.children:
                if c.dep_ in ('mark', 'case') and c.text.lower() in ('a', 'de', 'que') and c.i in by_i:
                    removed.add(c.i)
    dropped = {id(by_i[i]) for i in removed if i in by_i}
    for w in words:
        if id(w) in dropped:
            w.merged_into = True
    return [w for w in words if id(w) not in dropped]


def attach_articles(words):
    """冠詞 (o / um …) を後ろの名詞 (間に形容詞・数詞があってもよい) に掛け、語の列から除く (訳さない)"""
    out = []
    for i, word in enumerate(words):
        if _pos(word) != 'article':
            out.append(word)
            continue
        j = i + 1
        while j < len(words) and _pos(words[j]) == 'adj':
            j += 1
        if j < len(words) and _pos(words[j]) in ('noun', 'pronoun'):
            words[j].add_modifier(word)
            word.article_of = words[j]
            continue
        out.append(word)
    return out


NAME_LINKS = {'de', 'do', 'da', 'dos', 'das', 'e'}   # いくつかの語の固有名詞の中の語 (Rio de Janeiro)


FINITE_TAGS = {'first-person', 'second-person', 'third-person'}


def supply_verb(words):
    """動詞の無い文: 語形の表で定動詞の読みのある語を動詞に (Eu moro em São Paulo の moro を spaCy は代名詞と読む)"""
    if any(_pos(w) == 'verb' for w in words):
        return
    for w in words:
        item = _item(w)
        if item is None or item.pos in ('preposition', 'article') or w.surface.lower() in morphology.PRONOUNS or \
                w.surface.lower() in morphology.DETERMINERS:
            continue
        readings = [(l, t) for l, t in morphology.verb_forms(w.surface.lower()) if t & FINITE_TAGS]
        if not readings:
            continue
        lemma, tags = sorted(readings, key=lambda r: ('indicative' not in r[1], 'present' not in r[1]))[0]
        person = next((k + 1 for k, p in enumerate(('first-person', 'second-person', 'third-person')) if p in tags), 3)
        tense = next((k for k, v in TABLE_TENSES.items() if v in tags), 'present')
        ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
        w.items = [type(item)({'surface': w.surface, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
                               'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'active',
                               'mood': 'subjunctive' if 'subjunctive' in tags and 'indicative' not in tags else 'indicative',
                               'tense': tense, 'person': person, 'number': 'pl' if 'plural' in tags else 'sg',
                               'main': True})]
        return


def proper_names(words):
    """いくつかの語の固有名詞 (Rio de Janeiro・São Paulo) を辞書の見出しで1語の名詞に"""
    out, k = [], 0
    while k < len(words):
        found = None
        if words[k].surface[:1].isupper():
            for n in (4, 3, 2):
                span = words[k:k + n]
                if len(span) < n or not span[-1].surface[:1].isupper() or \
                        any(not (w.surface[:1].isupper() or w.surface.lower() in NAME_LINKS) for w in span):
                    continue
                name = ' '.join(w.surface for w in span)
                if dictionary.lemmas(name, 'name'):
                    found = (n, name)
                    break
        if found is None:
            out.append(words[k])
            k += 1
            continue
        n, name = found
        ja, gloss_lang, row = morphology.gloss(name, 'name')
        if ja is None or gloss_lang == 'en':
            from .katakana import katakana
            ja, gloss_lang = katakana(name), 'ja'   # 名前は続けて (ヒウジジャネイル)
        first = words[k]
        cases = (_item(words[k]) or _item(words[k + n - 1]))._ if (_item(words[k]) or _item(words[k + n - 1])) else None
        first.items = [type(_item(first))({'surface': name, 'pos': 'noun', 'base': name, 'lemma': name, 'ja': ja,
                                           'gloss_lang': gloss_lang, 'proper': True, 'main': True,
                                           '_': cases or morphology.cngs(morphology.CASES + ('Gen',))})]
        first.surface = name
        out.append(first)
        k += n
    return out


def mark_proclitics(words):
    """動詞の前の接語 (me viu・lhe deu) は後ろの動詞のもの: 節を分けるとき後ろの動詞に (O homem que veio | me viu)"""
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or not item.attrib('clitic') or item.attrib('enclitic'):
            continue
        j = k + 1
        while j < len(words) and _item(words[j]) is not None and _item(words[j]).attrib('clitic'):
            j += 1
        if j < len(words) and _pos(words[j]) == 'verb':
            word.items = [type(item)(dict(item.item, proclitic=True))]


def genitive_de(words):
    """名詞 + de (do・da …) + 名詞・代名詞: de を落として後ろの語を属格に (o livro da professora「先生の本」、
    o livro dele「彼の本」)。動詞の後ろの de (gostar de …) は前置詞のまま"""
    out = []
    for i, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'de' and out:
            k = len(out) - 1
            while k >= 0 and _pos(out[k]) == 'adj' and not _item(out[k]).attrib('predicative'):
                k -= 1
            j = i + 1
            while j < len(words) and (_pos(words[j]) in ('article', 'adj') or
                                      _item(words[j]) is not None and _item(words[j]).attrib('determiner')):
                j += 1
            if k >= 0 and _pos(out[k]) == 'noun' and j < len(words) and _pos(words[j]) in ('noun', 'pronoun'):
                it = _item(words[j])
                words[j].items = [type(it)(dict(it.item, _=[('Gen',) + c[1:] for c in it._ or [('Gen', 'sg', 'm')]]))]
                words[j].genitive_of_de = True
                word.merged_into = True
                continue
        out.append(word)
    return out


def dative_clitics(words):
    """名詞の目的語 (対格) のある文の人の接語 (me・te・nos・vos) は与格「〜に」(Você me deu o livro「私に本を」)"""
    if not any(_pos(w) == 'noun' and _item(w)._ and _item(w)._[0][0] == 'Acc' for w in words):
        return
    for w in words:
        it = _item(w)
        if it is not None and it.attrib('clitic') and it.attrib('base') in ('me', 'te', 'nos', 'vos') and it._ and \
                it._[0][0] == 'Acc':
            w.items = [type(it)(dict(it.item, _=[('Dat',) + c[1:] for c in it._]))]


def objects_after_first_person(words):
    """1・2人称の定動詞の後ろの、主格と読んだ名詞は目的語 (Dei-lhe o livro「本を」。名詞は1・2人称の主語にならない)"""
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('person') not in (1, 2) or item.attrib('lemma') in ('ser', 'estar'):
            continue
        for w in words[k + 1:]:
            it = _item(w)
            if it is None or it.pos in ('verb', 'conj', 'preposition'):
                break
            if it.pos == 'noun' and it._ and all(c[0] == 'Nom' for c in it._):
                w.items = [type(it)(dict(it.item, _=[('Acc',) + c[1:] for c in it._]))]


def existential(words):
    """há + 名詞「〜がある」(haver の3人称単数)。ブラジルの口語の tem + 名詞 (主語の無い ter) も。名詞は主語に"""
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('lemma') not in ('haver', 'ter') or item.attrib('person') != 3:
            continue
        if item.attrib('lemma') == 'ter' and any(_pos(w) in ('noun', 'pronoun') and _item(w)._ and
                                                 _item(w)._[0][0] == 'Nom' for w in words[:k]):
            continue   # 主語のある ter は「持つ」
        if item.attrib('form'):
            continue   # 動詞の組 (tinha comido)
        word.items = [type(item)(dict(item.item, ja='ある,いる', gloss_lang='ja', existential=True, person=None))]
        for w in words[k + 1:]:
            it = _item(w)
            if it is not None and it.pos == 'noun' and it._:
                w.items = [type(it)(dict(it.item, _=[('Nom',) + c[1:] for c in it._]))]
                break


def passive_agents(words):
    """受動の文の por (pelo・pela) + 名詞は動作主「〜によって」"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('voice') == 'passive' for w in words):
        return
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'por':
            w.items = [type(item)(dict(item.item, ja='〜によって', agent=True))]


def compound_conjunctions(words):
    """いくつかの語の接続詞 (ainda que・depois que・a fim de que …) を1語の接続詞に"""
    compounds = sorted((k.split() for k in morphology.SUBORDINATORS if ' ' in k), key=len, reverse=True)
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
        word.items = [type(item)(dict(item.item, pos='conj', base=' '.join(parts), ja='', dominates=None, _=None))]
        word.surface = ' '.join(w.surface for w in words[k:k + len(parts)])
        out.append(word)
        k += len(parts)
    return out


def lookup_all(surfaces):
    plain = [s.lstrip('-') if s.startswith('-') and s.lstrip('-').isalpha() else s for s in surfaces]   # spaCy には - の無い接語で
    doc = morphology.parse(plain)
    _ENCLITIC_SURFACES.clear()
    _ENCLITIC_SURFACES.update({k: True for k, x in enumerate(surfaces) if x.startswith('-') and len(x) > 1})
    words = []
    for token in doc:
        surface = surfaces[token.i]
        data = item_of(token, doc) if not surface.startswith('-') or len(surface) == 1 else \
            item_of(_Enclitic(token, surface), doc)
        word = Word(surface, None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    words = _split_pronoun_contractions(words)
    words = proper_names(words)
    supply_verb(words)
    global _display
    _display = list(words)
    mark_proclitics(words)
    words = merge_verbs(words, doc)
    words = genitive_de(words)
    words = attach_articles(words)
    dative_clitics(words)
    existential(words)
    objects_after_first_person(words)
    passive_agents(words)
    words = compound_conjunctions(words)
    for i, word in enumerate(words):
        word.index = i
    return words


class _Enclitic:
    """ハイフンで動詞の後ろに付いた接語: spaCy の語に、表層形 (-me) を持たせる"""
    def __init__(self, token, surface):
        self._token, self.text = token, surface

    def __getattr__(self, name):
        return getattr(self._token, name)


def Item_like(word, data):
    """語の今の項目と同じ型の項目 (縮約形を作り直すとき)"""
    from dragoman.core.Item import Item
    return Item(data)


def _split_pronoun_contractions(words):
    """前置詞と代名詞の縮約形 (dele「彼の」・nele・disso) を前置詞 + 代名詞の2語に"""
    out = []
    for word in words:
        key = word.surface.lower()
        if key not in morphology.PRONOUN_CONTRACTIONS or _pos(word) not in ('preposition', 'pronoun', 'adp', None, 'adv'):
            out.append(word)
            continue
        prep, pronoun = morphology.PRONOUN_CONTRACTIONS[key]
        ja, person, number, _ = morphology.PRONOUNS[pronoun]
        if prep == 'de' and pronoun in ('ele', 'ela', 'eles', 'elas') and out and _pos(out[-1]) == 'noun':
            # 名詞の後ろの dele・dela は所有「彼の」(o livro dele): 名詞に掛かる形容詞に
            word.items = [Item_like(word, {'surface': word.surface, 'pos': 'adj', 'base': key,
                                           'ja': ja.split(',')[0] + 'の', 'gloss_lang': 'ja', 'possessive_pronoun': True,
                                           '_': morphology.cngs(morphology.CASES + ('Gen',))})]
            out.append(word)
            continue
        p = Word(word.surface, [_preposition(word.surface, prep)])
        q = Word('(' + pronoun + ')', [{'surface': pronoun, 'pos': 'pronoun', 'base': pronoun, 'ja': ja, 'gloss_lang': 'ja',
                                        'person': person, 'number': number, '_': morphology.cngs(('Gen',)),
                                        'compact': True}])
        for w in (p, q):
            w.token_ix = word.token_ix
            w.doc_i = word.doc_i
        q.doc_i = None
        out += [p, q]
    return out


_display = []


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(PORTUGUESE):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
