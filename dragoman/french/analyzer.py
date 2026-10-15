#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# フランス語の文の解析
#
# spaCy (fr_core_news_sm) の品詞・原形・性・数・人称・時制・依存関係で語の項目を作り (french/morphology.py)、
# 動詞の組を1語にまとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器 (core/analyzer.py) を
# フランス語の設定 (FRENCH) で使う:
#   - 名詞に格の形は無いので、格は文の中の役割から: 前置詞の後ろは前置詞の目的語、それ以外は spaCy の依存関係
#     (主語・目的語) か、動詞の前なら主語・後ろなら目的語 (繋辞 être の後ろは補語)。代名詞は形で (je・me・le・lui)
#   - 冠詞は名詞に掛けて訳さない。前置詞と冠詞の縮約形 (au・du・aux・des) は前置詞
#   - 動詞の組を本動詞にまとめる: avoir / être + 過去分詞 → 複合過去「〜した」(être を取るのは移動・変化の動詞)、
#     être + 過去分詞 (ほかの動詞) → 受動、話法の助動詞 + 不定詞 (pouvoir「〜できる」、vouloir「〜したい」、
#     devoir「〜なければならない」)、aller + 不定詞 → 近い未来
#   - ne … pas・ne … jamais は否定。il y a は「〜がある」
#   - 関係代名詞 (qui・que) は共通の解析器の関係節に
#   - spaCy の小さいモデルの読み誤りを辞書の語形の表で直す: 主語の後ろの動詞の形 (Le garçon lit … の lit を前置詞と
#     読む)、動詞の前の接語の代名詞 (Je le lui ai donné の le・lui を冠詞・名詞と読む)
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '(': 'comma', ')': 'comma', '"': None, '«': None, '»': None,
               '“': None, '”': None}
LETTERS = "A-Za-zÀ-ÖØ-öø-ÿœŒæÆ"
ELISIONS = ("l'", "d'", "j'", "m'", "t'", "s'", "n'", "c'", "qu'", "jusqu'", "lorsqu'", "puisqu'", "quoiqu'", "presqu'")
KEEP_APOSTROPHE = {"aujourd'hui", "quelqu'un", "quelqu'une", "prud'homme"}
TOKEN = re.compile(r"[%s]+(?:['-][%s]+)*'?|\d+(?:[.,]\d+)*|[.!?…,;:—–()\"«»“”]" % (LETTERS, LETTERS))
INVERSION = re.compile(r"^(.+?)(-t)?-(je|tu|il|elle|on|nous|vous|ils|elles|ce|moi|toi|le|la|les|lui|leur|y|en)$", re.I)
FINITE = ('first-person', 'second-person', 'third-person')


def _root_items(lemma):
    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


def _particle(case, obj, predicate):
    """manquer à・plaire à の人は主題「は」(Tu me manques「私は 君が いなくて寂しい」)、s'appeler の名前は「と」(ジャンと呼ばれている)"""
    if case == 'Dat' and predicate.first_item.attrib('experiencer'):
        return 'は'
    if case == 'Acc' and predicate.first_item.attrib('lemma') == 'se appeler':
        return 'と'
    if isinstance(obj, Word) and obj.items and obj.items[0].pos == 'pronoun' and \
            obj.items[0].attrib('base') in ('rien', 'personne'):
        return 'も'   # ne … rien「何も〜ない」、personne ne …「誰も〜ない」
    return None


FRENCH = language.Language(
    name='fr',
    and_words=('et',),
    nor_words=('ni',),
    or_words=('ou',),
    copulas=frozenset({'être'}),
    negations=frozenset({'ne', "n'", '(ne)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    particle=_particle,
    topic_first=True,   # 主題「は」の句を先頭に (私は / 君が / いなくて寂しい)
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    infinitive_objects_follow=True,
    possessor_cases=(),
)


def tokens(text):
    out = []
    for token in TOKEN.findall(text.replace('’', "'")):
        lower = token.lower()
        if lower in KEEP_APOSTROPHE:
            out.append(token)
            continue
        m = INVERSION.match(token)
        if m and not dictionary.lemmas(lower) and len(m.group(1)) > 1:   # 倒置 (dit-il → dit il、a-t-il → a il)
            out += [m.group(1), m.group(3)]
            continue
        elision = next((e for e in ELISIONS if lower.startswith(e) and len(lower) > len(e)), None)
        if elision:   # l'école → l' école、qu'il → qu' il
            out += [token[:len(elision)], token[len(elision):]]
            continue
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


def _item(word):
    return word.items[0] if isinstance(word, Word) and word.items else None


def _pos(word):
    item = _item(word)
    return item.pos if item is not None else None


# ----------------------------------------------------------------------
# spaCy の読みを直す

def _finite_forms(text):
    """語形の表で定形の動詞として引ける見出しと印 (lit → lire、chante → chanter)"""
    return [(lemma, tags) for lemma, tags in morphology.verb_forms(text) if tags & set(FINITE) or 'imperative' in tags]


SUBJECTS = {'je', "j'", 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils', 'elles'}


def corrections(doc):
    """語の番号 → 直した品詞 ('VERB' / 'CLITIC')"""
    fixed = {}
    words = [t for t in doc]
    for t in words:
        lower = t.text.lower()
        if t.pos_ in ('VERB', 'AUX', 'PUNCT', 'DET', 'CCONJ', 'SCONJ') or lower in morphology.ARTICLES:
            continue
        if t.pos_ == 'PRON' and (lower in morphology.PRONOUNS or lower in morphology.RELATIVES or
                                 lower in morphology.DETERMINERS):
            continue   # 本当の代名詞 (代名詞と読まれた動詞の形 aimez は直す)
        if lower in morphology.PREPOSITIONS or lower in morphology.CONJUNCTIONS:
            continue
        if not _finite_forms(lower):
            continue
        clitic_det = t.i > 1 and words[t.i - 1].text.lower() in ('le', 'la', "l'", 'les') and \
            words[t.i - 2].text.lower() in SUBJECTS | {'ne', "n'"}   # 主語の代名詞の後ろの le・la・les は接語 (Je les vois)
        clitic_en = t.i > 1 and words[t.i - 1].text.lower() in ('en', 'y') and \
            words[t.i - 2].text.lower() in morphology.CLITICS | SUBJECTS | {'ne', "n'"}   # s'en・n'en・m'y は接語
        if t.pos_ in ('NOUN', 'PROPN') and t.i > 0 and words[t.i - 1].pos_ in ('DET', 'ADJ', 'ADP', 'NUM') and \
                not clitic_det and not clitic_en and words[t.i - 1].text.lower() not in SUBJECTS:   # Tu lis を冠詞 + 名詞と読む誤りは直す
            continue   # 冠詞・形容詞・前置詞の後ろの名詞はそのまま (la crise)
        if t.i == 0 and any('imperative' in tags for _, tags in _finite_forms(lower)) and len(words) > 1 and \
                words[1].pos_ in ('DET', 'PRON', 'ADP'):
            fixed[t.i] = 'VERB'   # 文頭の命令形 (Arrêtez la lecture)
            continue
        k = t.i - 1
        while k >= 0 and words[k].text.lower() in morphology.CLITICS | {'ne', "n'"} and \
                (words[k].pos_ != 'DET' or words[k].text.lower() in ('lui', 'leur', 'y', 'en', 'me', 'te', 'se') or
                 clitic_det):
            k -= 1
        if k + 1 < t.i and words[k + 1].text.lower() in ('nous', 'vous') and \
                (k < 0 or words[k].pos_ not in ('VERB', 'AUX')):
            fixed[t.i] = 'VERB'   # 主語の nous・vous (接語の表にもある) の後ろ (Nous chanterons)
            continue
        prev = words[k] if k >= 0 else None
        if prev is None:
            continue
        p = prev.text.lower()
        if prev.pos_ in ('NOUN', 'PROPN') or p in ('qui', 'je', "j'", 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils',
                                                  'elles', 'ce', "c'", 'cela', 'ça') or k < t.i - 1:
            fixed[t.i] = 'VERB'   # 主語・関係代名詞 qui・接語の後ろの動詞の形 (Le garçon lit、qui chante)
    for t in words:
        lower = t.text.lower()
        if lower not in morphology.CLITICS or t.i in fixed:
            continue
        k = t.i + 1
        while k < len(words) and words[k].text.lower() in morphology.CLITICS | {'ne', "n'"}:
            k += 1
        if k < len(words) and (words[k].pos_ in ('VERB', 'AUX') or fixed.get(words[k].i) == 'VERB'):
            fixed[t.i] = 'CLITIC'   # 動詞の前の接語の代名詞 (Je le lui ai donné)
    return fixed


# ----------------------------------------------------------------------
# 語の項目

def _base(lemma, row=None):
    gender = (row or {}).get('gender')
    article = {'m': 'le', 'f': 'la', 'mf': 'le / la'}.get(gender)
    return '%s%s' % (lemma, ' (%s)' % article if article else '')


def _verb_feats(feats, tags=None):
    """spaCy の素性 (か語形の表の印) → (時制, 法, 人称, 数)"""
    if tags:
        tense = 'perfect' if 'historic' in tags else 'imperfect' if 'imperfect' in tags else \
            'future' if 'future' in tags else 'present'
        # 語義からの印は複数の読みが混ざる (first/third-person singular present indicative/subjunctive): 直説法・3人称を先に
        mood = 'indicative' if 'indicative' in tags else 'imperative' if 'imperative' in tags else \
            'subjunctive' if 'subjunctive' in tags or 'conditional' in tags else 'indicative'
        person = 3 if 'third-person' in tags else next((k + 1 for k, p in enumerate(FINITE) if p in tags), 3)
        return tense, mood, person, 'pl' if 'plural' in tags else 'sg'
    tense = {'Pres': 'present', 'Imp': 'imperfect', 'Past': 'perfect', 'Fut': 'future'}.get(feats.get('Tense'), 'present')
    mood = {'Ind': 'indicative', 'Sub': 'subjunctive', 'Cnd': 'subjunctive', 'Imp': 'imperative'}.get(
        feats.get('Mood'), 'indicative')
    if feats.get('VerbForm') == 'Inf':
        mood = 'infinitive'
    elif feats.get('VerbForm') == 'Part':
        mood = 'participle'
    person = int(feats['Person']) if feats.get('Person', '').isdigit() else 3
    return tense, mood, person, morphology.NUMBERS.get(feats.get('Number'), 'sg')


def _verb_data(token, feats, lemma=None, tags=None):
    lemma = lemma or token.lemma_
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    if ja is None or gloss_lang == 'en' and lemma not in morphology.GLOSSES:
        better = _finite_forms(token.text.lower()) or \
            [(l, t) for l, t in morphology.verb_forms(token.text.lower())]
        for candidate, candidate_tags in better:
            if candidate != lemma and morphology.gloss(candidate, 'verb')[0]:
                lemma, tags = candidate, tags or candidate_tags
                ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
                break
    tense, mood, person, number = _verb_feats(feats, tags if tags and set(tags) & set(FINITE) else None)
    if not tags and feats.get('VerbForm') in ('Part', 'Inf'):
        # spaCy が分詞・不定詞と読んでも、語形の表に定形の読みしか無ければ定形 (Tu me plais の plais を過去分詞と読む)
        readings = [t for l, t in morphology.verb_forms(token.text.lower()) if l == lemma]
        if readings and not any({'participle', 'infinitive'} & t for t in readings) and \
                any(t & set(FINITE) for t in readings):
            best = sorted([t for t in readings if t & set(FINITE)], key=lambda t: ('present' not in t, 'indicative' not in t))[0]
            tense, mood, person, number = _verb_feats({}, best)
            feats = dict(feats, VerbForm='Fin')
    if not tags and feats.get('VerbForm') == 'Fin':
        # spaCy の時制が語形の表のどの読みにも無ければ表から (chantent を半過去と読む)。現在を先に
        readings = [t for l, t in morphology.verb_forms(token.text.lower()) if l == lemma and t & set(FINITE)]
        wanted = {'present': 'present', 'imperfect': 'imperfect', 'future': 'future', 'perfect': 'historic'}[tense] \
            if tense in ('present', 'imperfect', 'future', 'perfect') else None
        if readings and wanted and not any(wanted in t for t in readings):
            best = sorted(readings, key=lambda t: ('present' not in t, 'indicative' not in t))[0]
            tense = _verb_feats({}, best)[0]
    if tags and 'participle' in tags:
        mood = 'participle'
    if mood in ('infinitive', 'participle'):
        person = None   # 不定詞・分詞に人称は無い (主語の代名詞を補わない)
    data = {'surface': token.text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': mood, 'tense': tense,
            'person': person, 'number': number, 'main': True}
    if lemma == 'être':
        data['existential'] = True
    return data


def _noun_data(token, feats, proper=False):
    text, lemma = token.text, token.lemma_ or token.text
    if proper:
        lemma = text
    ja, gloss_lang, row = morphology.gloss(lemma, 'name' if proper else 'noun')
    if ja is None and lemma != text:
        ja, gloss_lang, row = morphology.gloss(text, 'name' if proper else 'noun')
    if ja is None and not proper:
        ja, gloss_lang, row = morphology.gloss(text.lower(), 'noun')
    given = proper and row is not None and re.search(r'given name|surname', row.get('en') or '')
    if proper and (ja is None or given or gloss_lang == 'en' and ja.split(',')[0] in (lemma, text)):
        # 人名はフランス語の読みのカタカナ (Jean → ジャン。英語の名前 John の訳にしない)。地名は辞書の訳 (Londres → ロンドン)
        from dragoman.core.katakana_names import latin as katakana
        ja, gloss_lang = katakana(lemma, 'fr'), 'ja'   # 辞書に無い名前はカタカナ (Jean → ジャン)
    data = {'surface': text, 'pos': 'noun', 'base': _base(lemma, row), 'lemma': lemma, 'ja': ja or text,
            'gloss_lang': gloss_lang or 'en', 'main': True, 'feats': feats,
            'gender': dictionary.gender(lemma) or (row or {}).get('gender')}
    if proper:
        data['proper'] = True
    return data


def item_of(token, doc, fixed):
    """spaCy の語 → 項目 (dict)。扱わない語は None (句読点)"""
    pos, lemma, text = token.pos_, token.lemma_, token.text
    feats = morphology.morph(token)
    lower = text.lower()
    if pos == 'PUNCT' or lower in PUNCTUATION:
        return None
    if fixed.get(token.i) == 'VERB':   # 3人称の読みを先に (qui chante・le garçon lit。je・tu の後ろは subject_persons で)
        forms = sorted(_finite_forms(lower), key=lambda f: 'third-person' not in f[1])
        return _verb_data(token, {}, forms[0][0], forms[0][1])
    starts = token.i == 0 or doc[token.i - 1].pos_ in ('PUNCT', 'CCONJ', 'SCONJ') or \
        doc[token.i - 1].text.lower() in ('que', "qu'", 'si', 'quand')
    if lower in ('nous', 'vous') and starts:   # 文頭・節の頭の nous・vous は主語 (Nous vous parlons)
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': morphology.PRONOUNS[lower][0], 'gloss_lang': 'ja',
                'person': morphology.PRONOUNS[lower][1], 'number': 'pl', '_': morphology.cngs(('Nom',), feats),
                'compact': True}
    after_prep = token.i > 0 and (doc[token.i - 1].pos_ == 'ADP' or doc[token.i - 1].text.lower() in morphology.PREPOSITIONS)
    if lower in morphology.CLITICS and after_prep and lower in ('lui', 'nous', 'vous', 'elle', 'eux', 'elles'):
        ja, person, number, _ = morphology.PRONOUNS[lower]   # 前置詞の後ろの強勢形 (de lui・avec nous) は接語でない
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(('Gen',), feats), 'compact': True}
    if fixed.get(token.i) == 'CLITIC' or (lower in morphology.CLITICS and pos == 'PRON'):
        ja, person, number, cases = morphology.PRONOUNS[lower]
        if lower in ('se', "s'"):
            ja = '自分'
        if lower == 'lui':
            cases = ('Dat',)   # 接語の lui は与格だけ (le lui「それを彼に」)
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(cases, feats), 'compact': True, 'clitic': True}
    if lower in SUBJECTS and pos != 'PRON':   # 主語の代名詞を冠詞・名詞と読む誤り (Tu me manques の Tu を冠詞)
        ja, person, number, cases = morphology.PRONOUNS[lower]
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(('Nom',), feats), 'compact': True}
    if lower in ('ne', "n'"):
        return {'surface': text, 'pos': 'adv', 'base': 'ne', 'ja': '〜ない', 'gloss_lang': 'ja', 'negation': True}
    after_verb = token.i > 0 and (doc[token.i - 1].pos_ in ('VERB', 'AUX') or fixed.get(token.i - 1) == 'VERB' or
                                  doc[token.i - 1].text.lower() in ('pas', 'jamais', 'plus'))
    prev_lemma = doc[token.i - 1].lemma_ if token.i > 0 else ''
    if lower in ('du', 'des', 'de', "d'") and prev_lemma in DE_VERBS:
        return _preposition(text, 'de', DE_VERBS[prev_lemma])   # parler du film「映画について話す」
    if lower in ('du', 'des') and after_verb and token.i + 1 < len(doc) and doc[token.i + 1].pos_ in ('NOUN', 'ADJ'):
        return {'surface': text, 'pos': 'article', 'base': lower, 'ja': '', 'gloss_lang': 'ja',
                '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'compact': True}   # 部分冠詞 (manger du pain)
    if lower in morphology.CONTRACTIONS and pos in ('ADP', 'DET') and \
            (pos == 'ADP' and token.dep_ != 'det' or token.dep_ == 'case' or lower in ('au', 'aux')):
        return _preposition(text, morphology.CONTRACTIONS[lower])
    if pos == 'ADP' or lower in morphology.PREPOSITIONS and pos not in ('ADV', 'SCONJ', 'CCONJ', 'PRON', 'DET'):
        return _preposition(text, lower if lower in morphology.PREPOSITIONS else lemma)
    if pos == 'DET' or lower in morphology.ARTICLES and pos not in ('PRON',):
        if lower in morphology.DETERMINERS or lemma in morphology.DETERMINERS:
            ja = morphology.DETERMINERS.get(lower) or morphology.DETERMINERS.get(lemma, '')
            if lower in ('aucun', 'aucune'):
                return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': '〜ない', 'gloss_lang': 'ja', 'negation': True}
            # 限定詞は共通の解析器の指示詞と同じく、すぐ後ろの名詞に掛ける (ma sœur、tous les enfants)
            data = {'surface': text, 'pos': 'pronoun' if ja else 'article', 'base': lower, 'ja': ja, 'gloss_lang': 'ja',
                    'desc': '指示代名詞' if lower in ('ce', 'cet', 'cette', 'ces') else '不定形容詞',
                    '_': morphology.cngs(morphology.CASES + ('Gen',), dict(feats, Number=None), _determiner_gender(lower)),
                    'compact': True, 'determiner': True}
            if lower in morphology.POSSESSIVES:
                data['possessive'] = morphology.POSSESSIVES[lower]
            return data
        if pos == 'NUM' or lower in morphology.NUMBERS_JA and lower not in ('un', 'une'):
            pass
        else:
            return {'surface': text, 'pos': 'article', 'base': lower, 'ja': '', 'gloss_lang': 'ja',
                    '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'compact': True}
    if pos == 'PRON':
        if lower in morphology.RELATIVES and (feats.get('PronType') == 'Rel' or token.dep_ != 'ROOT' and
                                              token.head.dep_ == 'acl:relcl'):
            return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': '〜するところの', 'gloss_lang': 'ja',
                    'desc': '関係代名詞', '_': morphology.cngs(morphology.RELATIVES[lower]), 'compact': True}
        ja, person, number, cases = morphology.PRONOUNS.get(lower) or morphology.PRONOUNS.get(lemma) or \
            (lemma, 3, morphology.NUMBERS.get(feats.get('Number'), 'sg'), morphology.CASES)
        if token.i > 0 and doc[token.i - 1].pos_ == 'ADP':
            cases = ('Gen',)   # 前置詞の後ろ (avec moi・pour lui)
        return {'surface': text, 'pos': 'pronoun', 'base': lower, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(cases, feats), 'compact': True}
    if pos == 'NUM' or lower in morphology.NUMBERS_JA and lower not in ('un', 'une'):
        ja = morphology.NUMBERS_JA.get(lower, text)
        return {'surface': text, 'pos': 'adj', 'base': text, 'ja': ja + 'つの' if lower in morphology.NUMBERS_JA and
                len(ja) <= 2 else ja,
                'gloss_lang': 'ja', '_': morphology.cngs(morphology.CASES + ('Gen',))}
    if lower in ('personne', 'rien') and (token.i == 0 or doc[token.i - 1].pos_ != 'DET') and \
            any(t.text.lower() in ('ne', "n'", 'sans') for t in doc):
        # ne … personne「誰も〜ない」、sans que personne「誰にも〜されずに」(冠詞の無い personne は否定の代名詞)
        return {'surface': text, 'pos': 'particle', 'base': lower, 'ja': morphology.NEGATIONS[lower], 'gloss_lang': 'ja',
                'negative_word': True}
    if pos in ('NOUN', 'PROPN') or pos == 'X' and text[:1].isupper():
        named = text[:1].isupper() and token.i > 0 and bool(dictionary.lemmas(text, 'name'))   # 文中の大文字の名前 (Marie)
        return _noun_data(token, feats, proper=pos in ('PROPN', 'X') or named)
    if pos == 'ADJ' and token.dep_ in ('obj', 'nsubj', 'nsubj:pass', 'obl', 'obl:arg', 'obl:mod', 'nmod') and \
            dictionary.lemmas(lower, 'noun'):
        return _noun_data(token, feats)   # 名詞として使った形容詞の形 (a trouvé preneur の preneur)
    if pos == 'ADJ':
        ja, gloss_lang, row = morphology.gloss(lemma, 'adj')
        if ja is None and lemma != lower:
            ja, gloss_lang, row = morphology.gloss(lower, 'adj')
        data = {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                '_': morphology.cngs(morphology.CASES + ('Gen',), feats), 'main': True}
        if token.dep_ == 'ROOT' or token.head.lemma_ == 'être' or any(c.dep_ == 'cop' for c in token.children):
            data['predicative'] = True   # 述語 (La maison est belle)
        return data
    if pos in ('VERB', 'AUX'):
        return _verb_data(token, feats)
    if lower in morphology.NEGATIONS and pos in ('ADV', 'PRON', 'NOUN', 'X'):
        return {'surface': text, 'pos': 'particle', 'base': lower, 'ja': morphology.NEGATIONS[lower], 'gloss_lang': 'ja',
                'negative_word': True}
    if pos in ('CCONJ', 'SCONJ'):
        return {'surface': text, 'pos': 'conj', 'base': lower, 'ja': morphology.CONJUNCTIONS.get(lower, lemma),
                'gloss_lang': 'ja'}
    if pos in ('ADV', 'INTJ', 'PART') or True:
        ja, gloss_lang, row = morphology.gloss(lower if lower in morphology.GLOSSES else lemma, 'adv')
        if gloss_lang == 'ja' and row is not None and row['pos'] == 'adj':
            ja = morphology.adverbial(ja)
        return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en'}


def _determiner_gender(word):
    """限定詞の形の性 (ma・ta・sa・cette は女性、mon・ce・cet は男性。ma sœur の ma を maison に掛けない)"""
    if word in ('ma', 'ta', 'sa', 'cette', 'toute', 'quelle'):
        return 'f'
    if word in ('ce', 'cet', 'tout', 'quel'):
        return 'm'
    return None


# de を取る動詞 → de の訳 (parler de「〜について話す」、avoir besoin de は名詞の後ろなので属格に)
DE_VERBS = {'parler': '〜について', 'rêver': '〜を', 'souvenir': '〜を', 'occuper': '〜を', 'discuter': '〜について',
            'douter': '〜を', 'profiter': '〜を', 'manquer': '〜が', 'dépendre': '〜に', 'changer': '〜を',
            'sortir': '〜から', 'venir': '〜から', 'partir': '〜から', 'revenir': '〜から', 'arriver': '〜から'}


def _preposition(text, prep, ja=None):
    ja = ja or morphology.PREPOSITIONS.get(prep) or '〜' + prep
    return {'surface': text, 'pos': 'preposition', 'base': prep, 'dominates': 'Gen', 'ja': ja, 'gloss_lang': 'ja'}


# ----------------------------------------------------------------------
# 動詞の組

def _determiner(word):
    item = _item(word)
    return item is not None and bool(item.attrib('determiner'))


def _participle(word):
    item = _item(word)
    return item is not None and item.pos == 'verb' and item.attrib('mood') == 'participle'


def _infinitive(word):
    item = _item(word)
    return item is not None and item.pos == 'verb' and item.attrib('mood') == 'infinitive'


def _skippable(word):
    """助動詞と本動詞の間に入る語 (否定 pas・副詞・接語)"""
    item = _item(word)
    return item is not None and (item.pos == 'adv' or item.attrib('negative_word') or item.attrib('clitic'))


def merge_verbs(words):
    """助動詞・話法の助動詞と本動詞 (過去分詞・不定詞) を、助動詞の位置の1語にまとめる"""
    changed = True
    while changed:
        changed = False
        for i, word in enumerate(words):
            item = _item(word)
            if item is None or item.pos != 'verb' or item.attrib('mood') in ('participle', 'infinitive'):
                continue
            lemma = item.attrib('lemma')
            j = i + 1
            while j < len(words) and _skippable(words[j]):
                j += 1
            if j >= len(words):
                continue
            main = words[j]
            if lemma in ('avoir', 'être') and _participle(main):
                _merge(word, main, lemma, reflexive=_reflexive_before(words, i))
            elif lemma in morphology.MODALS and _infinitive(main):
                _merge(word, main, lemma)
            else:
                continue
            main.merged_into = True
            del words[j]
            changed = True
            break
    return words


def _reflexive_before(words, i):
    """動詞の前の再帰の接語 (se・s'、主語と同じ人称の me・te・nous・vous: je me lève)。あればその語"""
    k = i - 1
    while k >= 0 and _item(words[k]) is not None and (_item(words[k]).attrib('clitic') or
                                                       _item(words[k]).attrib('base') == 'ne'):
        k -= 1
    subject = words[k].surface.lower() if k >= 0 else ''
    match = {'me': ('je', "j'"), "m'": ('je', "j'"), 'te': ('tu',), "t'": ('tu',), 'nous': ('nous',), 'vous': ('vous',)}
    for w in words[k + 1:i]:
        base = _item(w).attrib('base') if _item(w) is not None else ''
        if base in ('se', "s'") or subject in match.get(base, ()):
            return w
    return None


def pronominal_verbs(words):
    """代名動詞: 再帰の接語 + 動詞を辞書の「se + 動詞」の見出しで引き、接語は訳に出さない (Il se lève「起きる」、
    Je m'appelle Jean「〜という名前である」)。見出しが無ければ接語は再帰の目的語のまま (自分を)"""
    out = list(words)
    for i, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('mood') in ('infinitive', 'participle'):
            continue
        clitic = _reflexive_before(words, i)
        if clitic is None:
            continue
        lemma = 'se ' + item.attrib('lemma')
        ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
        if not ja:
            continue
        if item.attrib('voice') == 'passive':   # se + être + 過去分詞は複合過去 (s'est levé)
            item.item.update(voice='active')
        word.items = [type(item)(dict(item.item, lemma=lemma, pres1sg=lemma, base=lemma, ja=ja,
                                      gloss_lang=gloss_lang, pronominal=True,
                                      form=(item.attrib('form') + '・' if item.attrib('form') else '') + '代名動詞'))]
        clitic.merged_into = True
        out = [w for w in out if w is not clitic]
    return out


def _merge(aux_word, main_word, aux_lemma, reflexive=None):
    a, m = _item(aux_word), _item(main_word)
    data = dict(m.item)
    data.update(person=a.attrib('person'), number=a.attrib('number'), mood=a.attrib('mood'),
                surface=aux_word.surface + ' … ' + main_word.surface)
    data.pop('existential', None)
    tense = a.attrib('tense')
    form = ''
    main_lemma = m.attrib('lemma')
    if aux_lemma == 'avoir' and m.attrib('mood') == 'participle':
        if m.attrib('lemma') == 'être' and m.attrib('voice') != 'passive':
            data.update(tense='perfect' if tense == 'present' else 'pluperfect', existential=True)
            form = '複合過去 (avoir + été)'
        elif a.attrib('voice') == 'passive':
            data.update(voice='passive', tense='perfect')
        else:
            data['tense'] = 'perfect' if tense == 'present' else 'pluperfect' if tense == 'imperfect' else \
                'future-perfect' if tense == 'future' else 'perfect'
            form = '%s (avoir + 過去分詞)' % ('複合過去' if tense == 'present' else '大過去' if tense == 'imperfect' else '複合時制')
    elif aux_lemma == 'être' and m.attrib('mood') == 'participle':
        if main_lemma in morphology.ETRE_VERBS or reflexive is not None:   # 再帰の接語 + être は複合過去 (s'est levé)
            data['tense'] = 'perfect' if tense == 'present' else 'pluperfect' if tense == 'imperfect' else 'perfect'
            form = '複合過去 (être + 過去分詞)'
        elif main_lemma == 'être':
            data.update(existential=True, tense=tense)
        else:
            data.update(voice='passive', tense=tense if tense != 'perfect' else 'perfect')
            form = '受動 (être + 過去分詞)'
    elif aux_lemma == 'aller' and m.attrib('mood') == 'infinitive':
        data['tense'] = 'future'
        form = '近い未来 (aller + 不定詞)'
    elif aux_lemma in morphology.MODALS:
        suffix = morphology.MODALS[aux_lemma]
        data['ja'] = ','.join(_attach(j, suffix) for j in (m.ja or '').split(',')[:1]) if m.attrib('gloss_lang') == 'ja' \
            else m.ja
        data['tense'] = tense
        form = '%s + 不定詞' % aux_lemma
    data['mood'] = 'indicative' if data.get('mood') in ('participle', 'infinitive') else data.get('mood')
    data['form'] = form
    data['main'] = True
    aux_word.items = [type(m)(data)]
    aux_word.surface = data['surface']
    aux_word.token_ixs = (aux_word.token_ix, main_word.token_ix)
    aux_word.token_ix = main_word.token_ix   # 評価では本動詞 (UD でも助動詞は aux)


def _attach(verb, suffix):
    from dragoman.core.japanese import attach_auxiliary
    return attach_auxiliary(verb, suffix)


# ----------------------------------------------------------------------

def attach_articles(words):
    """冠詞 (le / un / des …) を後ろの名詞 (間に形容詞・数詞があってもよい) に掛け、語の列から除く (訳さない)"""
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


SUBJECT_PERSONS = {'je': (1, 'sg'), "j'": (1, 'sg'), 'tu': (2, 'sg'), 'il': (3, 'sg'), 'elle': (3, 'sg'), 'on': (3, 'sg'),
                   'nous': (1, 'pl'), 'vous': (2, 'pl'), 'ils': (3, 'pl'), 'elles': (3, 'pl')}


def subject_persons(words):
    """動詞の人称・数を直前の主語の代名詞から (間は接語・ne だけ。spaCy は Je le lui ai の ai を3人称と読む)"""
    for i, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('mood') in ('infinitive', 'participle'):
            continue
        k = i - 1
        while k >= 0 and _item(words[k]) is not None and (_item(words[k]).attrib('clitic') or
                                                           _item(words[k]).attrib('base') == 'ne'):
            k -= 1
        lower = words[k].surface.lower() if k >= 0 else ''
        if lower in SUBJECT_PERSONS and not (_item(words[k]) is not None and _item(words[k]).attrib('clitic')):
            person, number = SUBJECT_PERSONS[lower]
            mood = 'indicative' if item.attrib('mood') == 'imperative' else item.attrib('mood')   # 主語があれば命令形でない
            if (item.attrib('person'), item.attrib('number'), item.attrib('mood')) != (person, number, mood):
                word.items = [type(item)(dict(item.item, person=person, number=number, mood=mood))]


def clitic_cases(words):
    """接語が2つ並ぶとき (me le・le lui・me l'): 3人称の le・la・les は対格、ほか (me・te・nous・vous・lui・leur) は与格。
    主語の代名詞の後ろの nous・vous は目的語 (Je vous aime)"""
    for i in range(1, len(words)):
        item = _item(words[i])
        if item is not None and item.attrib('base') in ('nous', 'vous') and \
                words[i - 1].surface.lower() in set(SUBJECT_PERSONS) | {'ne', "n'"}:
            item.item['_'] = [c for c in item._ if c[0] != 'Nom'] or item._
            item.item['clitic'] = True
            words[i].items = [type(item)(item.item)]
    for i in range(len(words) - 1):
        a, b = _item(words[i]), _item(words[i + 1])
        if a is None or b is None or not a.attrib('clitic') or not b.attrib('clitic'):
            continue
        for item, word in ((a, words[i]), (b, words[i + 1])):
            base = item.attrib('base')
            if base in ('y', 'en'):
                continue
            case = 'Acc' if base in ('le', 'la', "l'", 'les') else 'Dat'
            item.item['_'] = [c for c in item._ if c[0] == case] or item._
            word.items = [type(item)(item.item)]


PERSONAL_CLITICS = ('me', "m'", 'te', "t'", 'se', "s'", 'nous', 'vous')


def clitic_valency(words):
    """人を表す接語 (me・te・se・nous・vous) の格を動詞から: 間接他動詞・二重目的語の動詞なら与格 (Il me parle「私に話す」、
    Il me donne le livre「私に本を与える」)、ほかは対格 (Il me voit「私を見る」)。2つ並ぶときは clitic_cases で決めてある"""
    for i, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb':
            continue
        lemma = item.attrib('lemma')
        run = []
        k = i - 1
        while k >= 0 and _item(words[k]) is not None and (_item(words[k]).attrib('clitic') or
                                                           _item(words[k]).attrib('base') == 'ne'):
            if _item(words[k]).attrib('clitic'):
                run.append(words[k])
            k -= 1
        personal = [w for w in run if _item(w).attrib('base') in PERSONAL_CLITICS]
        if len(run) != 1 or not personal:
            continue
        clitic = _item(personal[0])
        reflexive = clitic.attrib('base') in ('se', "s'")
        tags = dictionary.valency(lemma)
        # 辞書の語義の印: à を取る・物を人に (to grant something to someone)・自動詞だけの語義なら人は与格
        dative = lemma in morphology.INDIRECT_VERBS or lemma in morphology.DITRANSITIVE_VERBS and not reflexive or \
            not reflexive and ('à' in tags or 'to-someone' in tags or 'intransitive' in tags and 'transitive' not in tags)
        if lemma in morphology.EXPERIENCER_VERBS and dative:   # Tu me manques「私は 君が いなくて寂しい」(人を主題に)
            word.items = [type(item)(dict(item.item, ja=morphology.EXPERIENCER_VERBS[lemma], gloss_lang='ja',
                                          experiencer=True))]
        case = 'Dat' if dative else 'Acc'
        cases = [c for c in clitic._ if c[0] == case] or [(case,) + c[1:] for c in clitic._[:1]]
        personal[0].items = [type(clitic)(dict(clitic.item, _=cases))]
    for i, word in enumerate(words):   # manquer à + 名詞 (Tu manques à ta mère「君の母は 君が いなくて寂しい」)
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('lemma') not in morphology.EXPERIENCER_VERBS or \
                item.attrib('experiencer'):
            continue
        prep = next((w for w in words[i + 1:i + 3] if _pos(w) == 'preposition'), None)
        if prep is not None and _item(prep).attrib('base') == 'à':
            word.items = [type(item)(dict(item.item, ja=morphology.EXPERIENCER_VERBS[item.attrib('lemma')],
                                          gloss_lang='ja', experiencer=True))]
            prep.items = [type(_item(prep))(dict(_item(prep).item, ja='〜は'))]


def negation(words):
    """ne … pas: ne を否定の副詞に、pas は落とす (jamais・plus・rien は意味を残す)。ne の無い pas も否定"""
    has_ne = any(_item(w) is not None and _item(w).attrib('base') == 'ne' for w in words)
    out = []
    verb_seen = False   # 同じ節の前に動詞があるか (Personne ne vient は主語、Il ne voit personne は目的語)
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'verb':
            verb_seen = True
        elif item is not None and item.pos == 'conj' or PUNCTUATION.get(w.surface):
            verb_seen = False
        if item is not None and item.pos == 'pronoun' and item.attrib('base') in ('rien', 'personne'):
            w.items = [type(item)(dict(item.item, _=morphology.cngs(('Acc',) if verb_seen else ('Nom',))))]
            out.append(w)
            continue
        if item is not None and item.attrib('negative_word'):
            base = item.attrib('base')
            if base in ('pas', 'point'):
                if not has_ne:   # 話し言葉の pas だけの否定
                    w.items = [type(item)(dict(item.item, pos='adv', base='ne', ja='〜ない', negation=True))]
                    out.append(w)
                continue
            if base in ('rien', 'personne'):
                ja = '何' if base == 'rien' else '誰'   # 助詞は「も」(_particle)
                w.items = [type(item)(dict(item.item, pos='pronoun', ja=ja, person=3, number='sg',
                                           _=morphology.cngs(('Acc',) if verb_seen else ('Nom',))))]
            else:
                ja = {'jamais': '決して', 'plus': 'もう', 'guère': 'ほとんど'}.get(base, '')
                w.items = [type(item)(dict(item.item, pos='adv', ja=ja))]
            if not has_ne and base in ('jamais', 'rien', 'personne', 'plus'):
                pass
        out.append(w)
    return out


def existential_il_y_a(words):
    """il y a + 名詞「〜がある」: il・y を除き、名詞を主語に"""
    for i, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('lemma') != 'avoir' or i < 2:
            continue
        if words[i - 1].surface.lower() == 'y' and words[i - 2].surface.lower() == 'il':
            item.item.update(ja='ある,いる', gloss_lang='ja', existential=True, lemma='être', pres1sg='être',
                             base='il y a', person=3, number='sg')
            word.items = [type(item)(item.item)]
            for w in (words[i - 1], words[i - 2]):
                w.items = [type(_item(w))(dict(_item(w).item, pos='particle', ja='', _=None))]
            return True
    return False


COPULA_LIKE = {'être', 'devenir', 'sembler', 'paraître', 'rester'}
BOUNDARY = {'qui', 'que', "qu'", 'dont', 'où', 'et', 'mais', 'ou', 'si', 'quand', 'lorsque', 'parce', 'car',
            'comme', 'puisque'}


def assign_cases(words, doc, existential=False):
    """名詞の格: 前置詞の後ろは前置詞の目的語 (Gen)。ほかは動詞の前なら主語、後ろなら目的語 (繋辞の後ろは補語)"""
    verb_before = None   # 同じ節の前の動詞
    after_prep = False
    for word in words:
        item = _item(word)
        lower = word.surface.lower()
        if PUNCTUATION.get(word.surface) and word.surface != '(' or item is not None and (lower in BOUNDARY or
                                                                                    item.pos == 'conj'):
            verb_before = None
            after_prep = False
            continue
        if item is None:
            continue
        if item.pos == 'preposition':
            after_prep = True
            continue
        if item.pos == 'verb':
            verb_before = item
            after_prep = False
            continue
        if item.pos != 'noun':
            if item.pos not in ('adj', 'article', 'adv') and not item.attrib('determiner'):
                after_prep = False
            continue
        feats = item.attrib('feats') or {}
        if after_prep or getattr(word, 'genitive_of_de', False):
            cases = ('Gen',)
        elif existential and verb_before is not None and verb_before.attrib('base') == 'il y a':
            cases = ('Nom',)
        elif verb_before is None:
            cases = ('Nom',)
        elif verb_before.attrib('lemma') in COPULA_LIKE and verb_before.attrib('voice') != 'passive':
            cases = ('Nom',)   # 補語 (Elle est ma sœur)
        else:
            cases = ('Acc',)
        after_prep = False
        item.item['_'] = morphology.cngs(cases, feats, item.attrib('gender'))
        word.items = [type(item)(item.item)]


def genitive_de(words):
    """名詞 + de + 名詞: de を落として後ろの名詞を属格に (la présidence de l'Organisation「組織の主宰」)。
    動詞の後ろの de (parler de …) は前置詞のまま"""
    out = []
    for i, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'de' and out:
            k = len(out) - 1
            while k >= 0 and _pos(out[k]) in ('adj',) and not _item(out[k]).attrib('predicative'):
                k -= 1
            j = i + 1
            while j < len(words) and (_pos(words[j]) in ('article', 'adj') or _determiner(words[j])):
                j += 1
            if k >= 0 and _pos(out[k]) == 'noun' and j < len(words) and _pos(words[j]) == 'noun':
                words[j].genitive_of_de = True
                word.merged_into = True
                continue
        out.append(word)
    return out


# 前置詞 + 不定詞 → 従属節の接続詞 (pour voir「見るために」)。de・à は落とす (essayer de lire、commencer à lire)
INFINITIVE_PREPOSITIONS = {'pour': '〜するために', 'sans': '〜せずに', 'avant': '〜する前に', 'après': '〜した後で',
                           'afin': '〜するために', 'par': '〜することによって'}


def infinitive_prepositions(words):
    out = []
    for i, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'preposition':
            j = i + 1
            while j < len(words) and (_item(words[j]) is not None and _item(words[j]).attrib('clitic') or
                                      _pos(words[j]) == 'preposition' and _item(words[j]).attrib('base') == 'de'):
                j += 1
            if j < len(words) and _infinitive(words[j]):
                base = item.attrib('base')
                if base in INFINITIVE_PREPOSITIONS:
                    word.items = [type(item)(dict(item.item, pos='conj', ja=INFINITIVE_PREPOSITIONS[base]))]
                elif base in ('de', 'à'):
                    word.merged_into = True
                    continue
        out.append(word)
    return out


# 前置詞・副詞 + que の接続詞 (sans que「〜することなく」、avant que「〜する前に」…)
COMPOUND_CONJUNCTIONS = {'sans': '〜することなく', 'avant': '〜する前に', 'pour': '〜するように', 'afin': '〜するように',
                         'bien': '〜にもかかわらず', 'parce': '〜なので', 'après': '〜した後で', 'alors': '〜である一方',
                         'pendant': '〜する間', 'dès': '〜するとすぐ', 'depuis': '〜して以来', 'tandis': '〜する一方',
                         'malgré': '〜にもかかわらず', 'à condition': '〜という条件で', 'de sorte': '〜するように'}


def compound_conjunctions(words):
    """sans que・bien que … を1つの接続詞に (que は落とす)"""
    out = []
    for i, word in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if out and _item(word) is not None and word.surface.lower() in ('que', "qu'") and \
                getattr(out[-1], 'compound_que', False):
            word.merged_into = True
            continue
        if nxt is not None and nxt.surface.lower() in ('que', "qu'") and word.surface.lower() in COMPOUND_CONJUNCTIONS \
                and _item(word) is not None:
            item = _item(word)
            word.items = [type(item)(dict(item.item, pos='conj', ja=COMPOUND_CONJUNCTIONS[word.surface.lower()],
                                          base=word.surface.lower() + ' que', _=None))]
            word.compound_que = True
        out.append(word)
    return out


def passive_agents(words):
    """受動の文の par + 名詞は動作主「〜によって」"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('voice') == 'passive' for w in words):
        return
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'par':
            w.items = [type(item)(dict(item.item, ja='〜によって', agent=True))]


def lookup_all(surfaces):
    doc = morphology.parse(surfaces)
    fixed = corrections(doc)
    words = []
    for token in doc:
        data = item_of(token, doc, fixed)
        if data is not None and data.get('pos') in ('verb', 'noun', 'adj', 'adv'):
            note = morphology.reform_note(token.text, data.get('lemma') or data.get('base'))
            if note:
                data['reform'] = note   # 1990年の綴りの改革で変わった語 (plaît / plait)
        word = Word(token.text, None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    global _display
    _display = list(words)
    clitic_cases(words)
    subject_persons(words)
    words = negation(words)
    words = merge_verbs(words)
    words = pronominal_verbs(words)
    clitic_valency(words)   # 動詞の組をまとめてから (Il m'a parlé は parler で決める)
    existential = existential_il_y_a(words)
    words = [w for w in words if _pos(w) != 'particle']
    words = compound_conjunctions(words)
    words = infinitive_prepositions(words)
    words = genitive_de(words)
    assign_cases(words, doc, existential)
    words = attach_articles(words)
    passive_agents(words)
    for i, word in enumerate(words):
        word.index = i
    return words


_display = []


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(FRENCH):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
