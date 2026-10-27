#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から古英語の文を作る
#
#   語: 英語を仲立ちにした置き換え (transfer。解析器の訳語の表 GLOSSES を先に)。名詞の性と、名詞・形容詞・動詞の語形は
#     辞書 (ang/wiktionary.sqlite の語形の表。Wiktionary の変化表) から。綴りは長音符・口蓋音の点の付いた標準の綴り
#   名詞句: 冠詞 sē・sēo・þæt (性・数・格) + 形容詞 (冠詞の後ろは弱変化、冠詞が無ければ強変化) + 名詞。固有名詞・代名詞は冠詞なし。
#     属格の名詞句は名詞の前 (þæs cyninges sunu)
#   語順: 主文は動詞が2番目 (主語 - 定動詞 - 与格 - 対格 - 前置詞句 - 過去分詞・不定詞)、関係節 (þe) と従属節は動詞を最後に。
#     否定は定動詞の前の ne (ne + is → nis、ne + wæs → næs …)
#   時制: 現在 (未来も現在の形)、過去 (完了・未完了も過去の形)、過去完了 (hæfde / wæs + 過去分詞)、受動 (wæs / is + 過去分詞)、
#     話法の動詞 + 不定詞 (mæġ・wile・sceal)
#
import dataclasses

from . import transfer, english
from .frame import NP

ARTICLES = {  # (格, 性 / 複数) → 冠詞 sē
    ('Nom', 'm'): 'sē', ('Nom', 'f'): 'sēo', ('Nom', 'n'): 'þæt', ('Nom', 'p'): 'þā',
    ('Acc', 'm'): 'þone', ('Acc', 'f'): 'þā', ('Acc', 'n'): 'þæt', ('Acc', 'p'): 'þā',
    ('Dat', 'm'): 'þǣm', ('Dat', 'f'): 'þǣre', ('Dat', 'n'): 'þǣm', ('Dat', 'p'): 'þǣm',
    ('Gen', 'm'): 'þæs', ('Gen', 'f'): 'þǣre', ('Gen', 'n'): 'þæs', ('Gen', 'p'): 'þāra'}
THES = {  # この (þes)
    ('Nom', 'm'): 'þes', ('Nom', 'f'): 'þēos', ('Nom', 'n'): 'þis', ('Nom', 'p'): 'þās',
    ('Acc', 'm'): 'þisne', ('Acc', 'f'): 'þās', ('Acc', 'n'): 'þis', ('Acc', 'p'): 'þās',
    ('Dat', 'm'): 'þissum', ('Dat', 'f'): 'þisse', ('Dat', 'n'): 'þissum', ('Dat', 'p'): 'þissum',
    ('Gen', 'm'): 'þisses', ('Gen', 'f'): 'þisse', ('Gen', 'n'): 'þisses', ('Gen', 'p'): 'þissa'}
PRONOUNS = {  # (ラテン語の代名詞, 数) → {格: 形}
    ('ego', 'sg'): {'Nom': 'iċ', 'Acc': 'mē', 'Dat': 'mē', 'Gen': 'mīn'},
    ('tū', 'sg'): {'Nom': 'þū', 'Acc': 'þē', 'Dat': 'þē', 'Gen': 'þīn'},
    ('ego', 'pl'): {'Nom': 'wē', 'Acc': 'ūs', 'Dat': 'ūs', 'Gen': 'ūre'},
    ('tū', 'pl'): {'Nom': 'ġē', 'Acc': 'ēow', 'Dat': 'ēow', 'Gen': 'ēower'},
    ('is', 'pl'): {'Nom': 'hīe', 'Acc': 'hīe', 'Dat': 'him', 'Gen': 'hiera'},
    ('sē', 'sg'): {'Nom': 'hē', 'Acc': 'hine', 'Dat': 'him', 'Gen': 'his'},
    ('quis', 'sg'): {'Nom': 'hwā', 'Acc': 'hwone', 'Dat': 'hwǣm', 'Gen': 'hwæs'},
    ('quid', 'sg'): {'Nom': 'hwæt', 'Acc': 'hwæt', 'Dat': 'hwǣm', 'Gen': 'hwæs'}}
THIRD = {'m': {'Nom': 'hē', 'Acc': 'hine', 'Dat': 'him', 'Gen': 'his'},
         'f': {'Nom': 'hēo', 'Acc': 'hīe', 'Dat': 'hire', 'Gen': 'hire'},
         'n': {'Nom': 'hit', 'Acc': 'hit', 'Dat': 'him', 'Gen': 'his'}}
DEMONSTRATIVES = {'hic': THES, 'hīc': THES, 'iste': THES, 'ille': ARTICLES, 'is': ARTICLES}
POSSESSIVES = {'meus': 'mīn', 'tuus': 'þīn', 'suus': 'his', 'noster': 'ūre', 'vester': 'ēower'}   # his は変化しない
NUMERALS = {'ūnus': 'ān', 'duo': 'twēġen', 'trēs': 'þrīe', 'quattuor': 'fēower', 'quīnque': 'fīf', 'decem': 'tīen',
            'centum': 'hund', 'mīlle': 'þūsend'}
QUANTIFIERS = {'omnis': 'eall', 'multus': 'maniġ', 'tōtus': 'eall', 'alius': 'ōþer'}
PREPOSITIONS = {('in', 'Abl'): ('on', 'Dat'), ('in', 'Acc'): ('on', 'Acc'), ('ad', 'Acc'): ('tō', 'Dat'),
                ('ex', 'Abl'): ('of', 'Dat'), ('ē', 'Abl'): ('of', 'Dat'), ('ab', 'Abl'): ('fram', 'Dat'),
                ('ā', 'Abl'): ('fram', 'Dat'), ('cum', 'Abl'): ('mid', 'Dat'), ('dē', 'Abl'): ('be', 'Dat'),
                ('sine', 'Abl'): ('būtan', 'Dat'), ('per', 'Acc'): ('þurh', 'Acc'), ('propter', 'Acc'): ('for', 'Dat'),
                ('ob', 'Acc'): ('for', 'Dat'), ('post', 'Acc'): ('æfter', 'Dat'), ('ante', 'Acc'): ('beforan', 'Dat'),
                ('sub', 'Abl'): ('under', 'Dat'), ('super', 'Acc'): ('ofer', 'Dat'), ('prō', 'Abl'): ('for', 'Dat'),
                ('apud', 'Acc'): ('mid', 'Dat'), ('contrā', 'Acc'): ('wiþ', 'Acc'), ('inter', 'Acc'): ('betwux', 'Dat'),
                ('prope', 'Acc'): ('nēah', 'Dat')}
CONNECTIVES = {'et': 'and', 'que': 'and', 'atque': 'and', 'ac': 'and', 'sed': 'ac', 'at': 'ac', 'autem': 'sōþlīċe',
               'enim': 'for þǣm', 'nam': 'for þǣm', 'igitur': 'for þǣm', 'itaque': 'for þǣm', 'tamen': 'swā þēah',
               'tum': 'þā', 'deinde': 'þā', 'aut': 'oþþe', 'vel': 'oþþe'}
WORDS = {'semper': 'simle', 'saepe': 'oft', 'iam': 'ǣr', 'nunc': 'nū', 'hodiē': 'tōdæġ', 'crās': 'tōmorgen',
         'heri': 'ġiestrandæġ', 'ibi': 'þǣr', 'hīc': 'hēr', 'etiam': 'ēac', 'quoque': 'ēac', 'valdē': 'swīþe',
         'magnopere': 'swīþe', 'statim': 'sōna', 'mox': 'sōna', 'tandem': 'æt nīehstan', 'iterum': 'eft',
         'numquam': 'nǣfre', 'bene': 'wel', 'posteā': 'siþþan', 'diū': 'lange'}
# 不定詞を支配する話法の動詞 (ラテン語の見出し) → 古英語の話法の動詞
MODALS = {'possum': 'magan', 'volō': 'willan', 'dēbeō': 'sculan', 'oportet': 'sculan', 'faciō': 'lǣtan',
          'sinō': 'lǣtan'}
# 話法の動詞・助動詞の形 (辞書に表が無い・不規則なもの): (人称, 数) → 現在 / 過去
AUX = {
    'wesan': {(1, 'sg'): 'eom', (2, 'sg'): 'eart', (3, 'sg'): 'is', 'pl': 'sindon'},
    'wesan_past': {(1, 'sg'): 'wæs', (2, 'sg'): 'wǣre', (3, 'sg'): 'wæs', 'pl': 'wǣron'},
    'habban': {(1, 'sg'): 'hæbbe', (2, 'sg'): 'hæfst', (3, 'sg'): 'hæfþ', 'pl': 'habbaþ'},
    'habban_past': {(1, 'sg'): 'hæfde', (2, 'sg'): 'hæfdest', (3, 'sg'): 'hæfde', 'pl': 'hæfdon'},
    'magan': {(1, 'sg'): 'mæġ', (2, 'sg'): 'meaht', (3, 'sg'): 'mæġ', 'pl': 'magon'},
    'magan_past': {(1, 'sg'): 'meahte', (2, 'sg'): 'meahtest', (3, 'sg'): 'meahte', 'pl': 'meahton'},
    'willan': {(1, 'sg'): 'wille', (2, 'sg'): 'wilt', (3, 'sg'): 'wile', 'pl': 'willaþ'},
    'willan_past': {(1, 'sg'): 'wolde', (2, 'sg'): 'woldest', (3, 'sg'): 'wolde', 'pl': 'woldon'},
    'sculan': {(1, 'sg'): 'sceal', (2, 'sg'): 'scealt', (3, 'sg'): 'sceal', 'pl': 'sculon'},
    'sculan_past': {(1, 'sg'): 'sceolde', (2, 'sg'): 'sceoldest', (3, 'sg'): 'sceolde', 'pl': 'sceoldon'},
}
# 否定の縮約 (ne + is → nis …)
NEGATIVE_CONTRACTIONS = {'is': 'nis', 'eom': 'neom', 'eart': 'neart', 'wæs': 'næs', 'wǣre': 'nǣre', 'wǣron': 'nǣron',
                         'hæfþ': 'næfþ', 'hæfde': 'næfde', 'hæfdon': 'næfdon', 'hæbbe': 'næbbe', 'wile': 'nyle',
                         'wille': 'nylle', 'wolde': 'nolde', 'woldon': 'noldon', 'wāt': 'nāt'}
# bēon / wesan で完了を作る移動・変化の自動詞
BE_PERFECT = ('cuman', 'gān', 'faran', 'fēran', 'weorþan', 'feallan', 'becuman')


def _dictionary():
    from dragoman.oldenglish import dictionary
    return dictionary


def available():
    return transfer.available('ang') and _dictionary().available()


_ENGLISH = {}   # 選んだ見出し → 英語の訳語 (同じ綴りの見出しの表を選ぶのに: sēon「見る」の seah、「漉す」の sāh)


def _forms(lemma, pos):
    return _dictionary().lemma_forms(lemma, pos, _ENGLISH.get((lemma, pos), ()))


def _number(n):
    return 'pl' if n == 'pl' else 'sg'


def _closeness(lemma):
    """見出しに近い形を先に: 頭から同じ字の長いもの (表には異綴りの形も入っている: cyning の cening・wīf の wīb)"""
    from dragoman.oldenglish import orthography
    k = orthography.key(lemma)

    def score(surface):
        s = orthography.key(surface)
        common = next((i for i, (a, b) in enumerate(zip(k, s)) if a != b), min(len(k), len(s)))
        return (-common, surface.startswith('ġe') and not lemma.startswith('ġe'), len(s))
    return score


def find_nominal(lemma, pos, case, number, gender=None, decl=None):
    """語形の表から格・数 (・性・強変化 / 弱変化) の合う形。無ければ None"""
    matched, other_decl = [], []
    for surface, feats in _forms(lemma, pos):
        if feats.get('rank'):
            continue
        cng = [tuple(x) for x in feats.get('_', [])]
        if not any(c == case and n == number and (gender is None or g in (gender, None)) for c, n, g in cng):
            continue
        if feats.get('alt'):
            other_decl.append(surface)   # 異綴りの形は後に
            continue
        (other_decl if decl and decl not in (feats.get('decl') or decl) else matched).append(surface)
    found = matched or other_decl
    return _marked(min(found, key=_closeness(lemma)), lemma) if found else None


def _marked(surface, lemma):
    """長音符の無い語形 (変化形だけの項目から取った godan) に、見出し語 (gōd) の頭から同じ字の長音符・点を写す
    (名詞・形容詞だけ。動詞は語幹の母音が変わる: sēon の seah)"""
    from dragoman.oldenglish.analyzer import _overlay_prefix
    return _overlay_prefix(surface, lemma)


def gender(noun):
    rows = _dictionary().lemmas(noun, 'noun')
    g = (rows[0].get('gender') or 'n').split(',')[0] if rows else 'n'
    return g if g in ('m', 'f', 'n') else 'n'


# ----------------------------------------------------------------------
# 語

def to_oldenglish(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.lang == 'ang':
        return lex.lemma
    if lex.lemma in WORDS and lex.lang in ('', 'la'):
        return WORDS[lex.lemma]
    if lex.proper:
        from .names import localized
        found = localized(lex, 'ang')
        return found[0] if found else _latin_name(lex.lemma)
    target = transfer.best(lex, 'ang', pos)
    if target is None:
        return None
    rows = _dictionary().lemmas(target.lemma, pos)
    base = rows[0]['base'] if rows else target.lemma   # 手の表の見出し (giefan) は辞書の綴り (ġiefan) に
    _ENGLISH[(base, pos)] = tuple(target.english)
    return base


def _latin_name(lemma):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', lemma) if not unicodedata.combining(c))


def word(lex, pos=None):
    found = to_oldenglish(lex, pos)
    if found:
        return found
    en = english.word(lex)
    return '[%s]' % en if en and en != '[]' else ''


# ----------------------------------------------------------------------
# 名詞句

def noun_form(noun, case, number):
    return find_nominal(noun, 'noun', case, number) or (noun if number == 'sg' else noun)


def adjective_form(adj, case, number, g, weak):
    form = find_nominal(adj, 'adj', case, number, g, 'weak' if weak else 'strong')
    return form or adj


def noun_phrase(np, case='Nom'):
    if np.members:
        parts = [noun_phrase(m, case) for m in np.members]
        conj = ' oþþe ' if np.conj in ('aut', 'vel') else ' and '
        return ', '.join(parts[:-1]) + conj + parts[-1] if len(parts) > 2 else conj.join(parts)
    head = np.head
    if head is None:
        return ''
    number = _number(np.number)
    if head.pos == 'pronoun':
        if head.lemma == 'is' and number == 'sg':
            return THIRD.get(np.gender if np.gender in THIRD else 'm')[case]
        forms = PRONOUNS.get((head.lemma, number)) or PRONOUNS.get((head.lemma, 'sg'))
        if forms:
            return forms[case]
        if head.lemma in DEMONSTRATIVES:
            g = np.gender if np.gender in ('m', 'f', 'n') else 'n'
            return DEMONSTRATIVES[head.lemma][(case, 'p' if number == 'pl' else g)]
        return word(head)
    noun = word(head, 'adj' if head.pos in ('adj', 'participle') else 'noun')
    if not noun:
        return ''
    g = gender(noun)
    key = 'p' if number == 'pl' else g
    determiner = None
    adjectives = []
    for m in np.modifiers:
        if isinstance(m, NP):
            adjectives += [x.head for x in m.members]
            continue
        if m.lemma in DEMONSTRATIVES and m.lang in ('', 'la'):
            determiner = DEMONSTRATIVES[m.lemma][(case, key)]
        elif m.lemma in POSSESSIVES and m.lang in ('', 'la'):
            base = POSSESSIVES[m.lemma]
            determiner = adjective_form(base, case, number, g, False) if base in ('mīn', 'þīn') else base
        elif m.lemma in NUMERALS and m.lang in ('', 'la'):
            determiner = adjective_form(NUMERALS[m.lemma], case, number, g, False)
        else:
            adjectives.append(m)
    # 冠詞: 固有名詞と、冠詞の無い名詞 (元の文に冠詞の無いもの: gold「金」) には付けない
    bare = np.definite is False or head.lang == 'ang' and not np.definite   # 古英語の文の冠詞の無い名詞はそのまま
    article = determiner if determiner is not None else ('' if head.proper or bare else ARTICLES[(case, key)])
    weak = bool(article) and article in ARTICLES.values() or article in THES.values()
    adjs = []
    for a in adjectives:
        if a.lemma in QUANTIFIERS and a.lang in ('', 'la'):
            adjs.append(adjective_form(QUANTIFIERS[a.lemma], case, number, g, False))
            continue
        form = word(a, 'adj')
        adjs.append(adjective_form(form, case, number, g, weak) if form and not form.startswith('[') else form)
    genitives = [noun_phrase(gen, 'Gen') for gen in np.genitives]
    if genitives and article in ARTICLES.values():
        article = ''   # 前に置いた属格が冠詞の代わり (þæs flotan mæġeþ「水夫の娘」)
    text = ' '.join(x for x in genitives + [article] + adjs + [noun_form(noun, case, number)] if x)
    for r in np.relatives:
        text += ', ' + relative_clause(r) + ','
    return text


def relative_clause(r):
    """関係節: 関係の小辞 þe + 動詞を最後に (sē cyning, þe þone mann lufode,)"""
    return ' '.join(['þe'] + realize(r, gap=r.gap or 'subject', subordinate=True))


def prepositional(np, passive=False):
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep is not None and np.prep.lemma in ('ā', 'ab', 'abs'):
        text = noun_phrase(inner, 'Dat')
        return 'fram ' + text if text else ''
    prep, case = PREPOSITIONS.get((np.prep.lemma, np.case), ('on', 'Dat')) if np.prep is not None else ('on', 'Dat')
    text = noun_phrase(inner, case)
    return prep + ' ' + text if text else ''


# ----------------------------------------------------------------------
# 動詞

def _aux(name, person, number):
    table = AUX[name]
    return table['pl'] if number == 'pl' else table[(person, 'sg')]


def finite(lemma, tense, person, number, mood='indicative'):
    """定形 (現在・過去)。辞書の語形の表から (話法の動詞・bēon / wesan・habban は表 AUX から)"""
    past = tense == 'past'
    base = {'bēon': 'wesan'}.get(lemma, lemma)
    if base in ('wesan', 'habban', 'magan', 'willan', 'sculan'):
        return _aux(base + ('_past' if past else ''), person, number)
    want_tense = 'perfect' if past else 'present'
    candidates, alternatives = [], []
    for surface, feats in _forms(lemma, 'verb'):
        if feats.get('mood') != mood or feats.get('tense') != want_tense or feats.get('number') != number:
            continue
        if number == 'sg' and feats.get('person') not in (person, None):
            continue
        (alternatives if feats.get('alt') else candidates).append(surface)
    if candidates or alternatives:
        # 見出しの変化表と変化形だけの項目の両方にある形 (標準の siehþ・bireþ。表だけの sē̆eþ・方言の項目だけの sēh より)、
        # 次に表の形、見出しに近い形
        both = [c for c in candidates if c in alternatives]
        close = _closeness(lemma)
        return min(both or candidates or alternatives, key=close)
    return _regular(lemma, past, person, number)


def _regular(lemma, past, person, number):
    stem = lemma[:-3] if lemma.endswith('ian') else lemma[:-2] if lemma.endswith('an') else lemma
    if past:
        return stem + ('odon' if lemma.endswith('ian') else 'don') if number == 'pl' else \
            stem + ('ode' if lemma.endswith('ian') else 'de') + ('st' if person == 2 else '')
    if number == 'pl':
        return stem + ('iaþ' if lemma.endswith('ian') else 'aþ')
    return stem + {1: 'e', 2: 'est', 3: 'eþ'}[person]


def participle_form(lemma):
    forms = [s for s, f in _forms(lemma, 'verb') if f.get('mood') == 'participle' and f.get('tense') == 'past']
    if forms:
        return max(forms, key=lambda f: f.startswith('ġe'))   # ġe- の付いた形を先に (ġesewen)
    stem = lemma[:-3] if lemma.endswith('ian') else lemma[:-2] if lemma.endswith('an') else lemma
    return 'ġe' + stem + ('od' if lemma.endswith('ian') else 'ed')


def imperative_form(lemma, number):
    forms = [s for s, f in _forms(lemma, 'verb') if f.get('mood') == 'imperative' and f.get('number') == number]
    return forms[0] if forms else (lemma[:-2] if lemma.endswith('an') else lemma)


def _negate(form):
    return NEGATIVE_CONTRACTIONS.get(form) or 'ne ' + form


def verb_parts(clause, person, number, infinitive=False):
    """(定形, 文末の語の列)"""
    lemma = word(clause.verb, 'verb')
    if not lemma or lemma.startswith('['):
        return lemma, []
    if infinitive:   # 話法の動詞の後ろの不定詞
        return '', [lemma]
    past = clause.tense in ('perfect', 'imperfect', 'past-perfect')
    mood = 'subjunctive' if clause.mood == 'subjunctive' else 'indicative'
    if clause.voice == 'passive':
        return _aux('wesan_past' if past else 'wesan', person, number), [participle_form(lemma)]
    if clause.tense == 'past-perfect':
        aux = 'wesan_past' if lemma in BE_PERFECT else 'habban_past'
        return _aux(aux, person, number), [participle_form(lemma)]
    return finite(lemma, 'past' if past else 'present', person, number, mood), []


def _person(clause):
    subject = (clause.role('subject') or [None])[0]
    if subject is not None and subject.head is not None and subject.head.pos == 'pronoun' and \
            subject.head.lemma in ('ego', 'tū'):
        return {'ego': 1, 'tū': 2}[subject.head.lemma], _number(subject.number)
    if subject is not None:
        return 3, 'pl' if subject.members or subject.number == 'pl' else 'sg'
    return clause.person, _number(clause.number)


def _modal(clause, gap, subordinate):
    """話法の動詞 + 不定詞 (Iċ mæġ þā bōc rǣdan)。当てはまらなければ None"""
    from .frame import Lex
    if clause.copula or len(clause.infinitives) != 1 or clause.verb is None:
        return None
    modal = MODALS.get(clause.verb.lemma) if clause.verb.lang in ('', 'la') else None
    if modal is None:
        return None
    inner = clause.infinitives[0]
    if inner.role('subject') and modal != 'lǣtan' and clause.verb.lemma != 'oportet':
        return None
    args = list(clause.args)
    if clause.verb.lemma == 'oportet' and not clause.role('subject') and inner.role('subject'):
        args = [('subject', inner.role('subject')[0])]
    inner_words = realize(dataclasses.replace(inner, mood='indicative',
                                              args=[(r, np) for r, np in inner.args if r != 'subject']),
                          gap='subject', subordinate=True, infinitive=True)
    outer = dataclasses.replace(clause, verb=Lex(modal, 'verb', lang='ang'), infinitives=[], args=args)
    words = realize(outer, gap, subordinate)
    if subordinate:
        return words[:-1] + inner_words + words[-1:]
    return words + inner_words


# 直接の疑問文の疑問の副詞
QUESTION_WORDS = {'quandō': 'hwonne', 'ubi': 'hwǣr', 'cūr': 'hwȳ', 'quārē': 'hwȳ', 'quōmodo': 'hū', 'unde': 'hwanon',
                  'quō': 'hwider', 'quotiēns': 'hū oft'}


def direct_question(clause):
    """疑問詞のある直接の疑問文: 疑問詞 + 定動詞 + 主語 … (Hwonne cymþ hē?・Hwǣr is sēo mæġeþ?)。
    疑問代名詞が主語なら語順はそのまま (Hwā cymþ?)"""
    from .frame import interrogative_np, without_interrogative
    owner, role, wh = interrogative_np(clause)
    plain = dataclasses.replace(clause, question_word='', question=False, invert=True)
    if wh is None:
        return [QUESTION_WORDS.get(clause.question_word, clause.question_word)] + realize(plain)
    if owner is clause and role == 'subject':
        return realize(dataclasses.replace(plain, invert=False))
    first = prepositional(wh) if role == 'prep' else noun_phrase(wh, {'recipient': 'Dat', 'possessor': 'Gen'}.get(role, 'Acc'))
    return [first] + realize(without_interrogative(plain))


def realize(clause, gap=None, subordinate=False, infinitive=False):
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    if clause.question and clause.question_word and clause.mood == 'indicative' and gap is None and not subordinate:
        return direct_question(clause)
    modal = _modal(clause, gap, subordinate)
    if modal is not None:
        return modal
    complements = [inner for inner in clause.infinitives if inner.infinitive_kind in ('saying', 'command', 'emotion')
                   and inner.role('subject')]
    if complements:   # 補文は þæt 節 (Iċ wāt þæt þū cymst。動詞は最後)
        from .frame import reflexive_subject
        main = realize(dataclasses.replace(clause, infinitives=[i for i in clause.infinitives if i not in complements]),
                       gap, subordinate)
        for inner in complements:
            mood = 'subjunctive' if inner.infinitive_kind == 'command' else 'indicative'
            main += [',', 'þæt'] + realize(dataclasses.replace(reflexive_subject(inner, clause), mood=mood,
                                                                infinitive_kind=''), subordinate=True)
        return main
    person, number = _person(clause)
    subject = (clause.role('subject') or [None])[0]
    head_words = []
    if subject is not None and gap != 'subject':
        head_words.append(noun_phrase(subject, 'Nom'))
    elif subject is None and gap != 'subject' and clause.mood != 'imperative':   # 主語は省かない (þe þū ġesihst)
        head_words.append({(1, 'sg'): 'iċ', (2, 'sg'): 'þū', (3, 'sg'): 'hē', (1, 'pl'): 'wē', (2, 'pl'): 'ġē',
                           (3, 'pl'): 'hīe'}[(person, number)])
    middle, tail = [], []
    for adv in clause.adverbs:
        if adv.lemma != 'nōn':
            middle.append(word(adv, 'adv'))
    if clause.copula:
        complements = clause.role('complement')
        for role, np in clause.args:
            if role == 'prep':
                middle.append(prepositional(np))
        past = clause.tense in ('perfect', 'imperfect', 'past-perfect')
        verb = _aux('wesan_past' if past else 'wesan', person, number)
        if complements:
            comp = complements[0]
            if comp.head is not None and comp.head.pos in ('adj', 'participle') and not comp.members:
                tail.append(word(comp.head, 'adj'))
            elif comp.members and all(m.head is not None and m.head.pos in ('adj', 'participle') for m in comp.members):
                tail.append(' and '.join(word(m.head, 'adj') for m in comp.members))   # langsum and wīd (冠詞なし)
            else:
                tail.append(noun_phrase(comp, 'Nom'))
        elif not clause.role('prep') and subject is not None and not clause.invert:   # 存在の文: þǣr is + 主格
            head_words = ['þǣr']
            tail.append(noun_phrase(subject, 'Nom'))
    else:
        for np in clause.role('recipient'):
            middle.append(noun_phrase(np, 'Dat'))
        obj = (clause.role('object') or [None])[0]
        if obj is not None and gap != 'object':
            middle.append(noun_phrase(obj, 'Acc'))
        for role, np in clause.args:
            if role in ('subject', 'object', 'recipient', 'complement', 'address'):
                continue
            if role == 'prep':
                middle.append(prepositional(np, clause.voice == 'passive'))
            elif np.head is not None and np.head.lemma in WORDS and np.head.lang in ('', 'la'):
                middle.append(WORDS[np.head.lemma])
            elif role == 'means' and np.animate:
                middle.append(noun_phrase(np, 'Dat'))
            elif role == 'means':
                middle.append('mid ' + noun_phrase(np, 'Dat'))
            elif role == 'possessor':
                middle.append(noun_phrase(np, 'Gen'))
            else:
                middle.append('on ' + noun_phrase(np, 'Dat'))
        verb, tail = verb_parts(clause, person, number, infinitive)
    if clause.negated and verb:
        verb = _negate(verb)
    if clause.mood == 'imperative' and not clause.copula:
        lemma = word(clause.verb, 'verb')
        form = imperative_form(lemma, number)
        return [w for w in [('ne ' if clause.negated else '') + form] + middle if w]
    if subordinate or infinitive:   # 関係節・従属節: 動詞を最後に
        return [w for w in head_words + middle + tail + [verb] if w]
    if clause.invert:   # 疑問詞の後ろは定動詞 + 主語 (Hwonne cymþ hē?)
        return [w for w in [verb] + head_words + middle + tail if w]
    return [w for w in head_words + [verb] + middle + tail if w]


def vocative(np):
    text = noun_phrase(np, 'Nom')
    article = text.split(' ')[0]
    return text[len(article) + 1:] if article in ('sē', 'sēo', 'þæt', 'þā') else text


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address
    parts = []
    for k, c in enumerate(clauses):
        groups, rest = split_address(c)
        words = [', '.join(vocative(np) for np in group) + ',' for group in groups]
        for key in rest.connectives:
            if key in CONNECTIVES and k > 0:
                words.append(CONNECTIVES[key])
        words += realize(rest)
        parts.append(' '.join(w for w in words if w))
    text = ', '.join(parts).replace(' ,', ',').replace(',,', ',').rstrip(',')
    return text[:1].upper() + text[1:] + '.'


# ----------------------------------------------------------------------
# 比較の表

CASE_HOW = {'Nom': '主格 (sē / sēo / þæt)', 'Acc': '対格 (þone / þā / þæt)', 'Dat': '与格 (þǣm / þǣre)',
            'Gen': '属格 (þæs / þǣre、名詞の -es。名詞の前)'}
PRO_DROP_HOW = '代名詞を補う'
PREDICATE_HOW = '人称・数・時制の語形 (singþ・sang)、過去完了 hæfde + 過去分詞、受動 wæs + 過去分詞。主文は2番目'
COPULA_HOW = 'wesan + 補語'
ADDRESS_HOW = '冠詞なし'


def compare_np(role, np, clause):
    passive = clause.voice == 'passive'
    if role == 'prep' and np.prep is not None:
        text = prepositional(np, passive)
        if passive and np.prep.lemma in ('ā', 'ab', 'abs'):
            return text, '前置詞 fram + 与格 (受動の動作主)'
        prep, case = PREPOSITIONS.get((np.prep.lemma, np.case), ('on', 'Dat'))
        return text, '%s + %s' % (prep, {'Dat': '与格', 'Acc': '対格', 'Gen': '属格'}[case])
    if role == 'address':
        return vocative(np), ADDRESS_HOW
    case = {'subject': 'Nom', 'object': 'Acc', 'recipient': 'Dat', 'means': 'Dat', 'possessor': 'Gen'}.get(role, 'Dat')
    text = noun_phrase(np, case)
    if role == 'means' and not np.animate:
        return 'mid ' + text, 'mid + 与格'
    if role in ('place', 'source'):
        return 'on ' + text, 'on + 与格'
    return text, CASE_HOW.get(case, case)


def compare_predicate(clause, reduced):
    person, number = _person(clause)
    if clause.copula:
        words = realize(reduced)
        subject = (clause.role('subject') or [None])[0]
        head = noun_phrase(subject, 'Nom') if subject is not None else ''
        text = ' '.join(words)
        return (text[len(head):].strip() if head and text.startswith(head) else text), COPULA_HOW
    verb, tail = verb_parts(clause, person, number)
    if clause.negated and verb:
        verb = _negate(verb)
    return ' '.join(x for x in [verb] + tail if x), PREDICATE_HOW
