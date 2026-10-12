#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語の文の解析
#
# 語節を kiwipiepy で形態素に分け (korean/morphology.py)、内容語と助詞・語尾の記録にまとめてから、並列・係り先・
# 格の枠・日本語訳は共通の解析器 (core/analyzer.py) を韓国語の設定 (KOREAN) で使う:
#   - 格助詞: 이/가 → 主格「が」、을/를 → 対格「を」、에게/한테 → 与格「に」、의 → 属格「の」(後ろの名詞に掛かる)。
#     에・에서・(으)로・와/과・까지・부터 … は後置詞句 (共通の解析器の前置詞句にするため、名詞句の前に移す)
#   - 은/는 は主題「は」、도「も」、만「だけ」: 格は節の中のほかの名詞句から決める (이/가 の句が無ければ主格)
#   - 用言の語尾: 었 → 過去、겠 → 未来・推量、命令・勧誘の終結語尾 → 命令。連結語尾 (-고「そして」・-어서「〜て」・
#     -지만「しかし」・-면「〜なら」…) は節を区切る接続の語にする
#   - 補助用言は本動詞にまとめる: -고 있다「〜ている」、-어 주다「〜てくれる」、-고 싶다「〜たい」、
#     -지 않다 (否定)、-지 못하다・못「〜できない」、-ㄹ 수 있다「〜できる」、-어야 하다「〜なければならない」
#   - 連体形 (-ㄴ/-은・-는・-ㄹ) は後ろの名詞に掛ける: 形容詞だけなら名詞の修飾語 (예쁜 꽃「美しい花」)、
#     前に補語があれば関係節として名詞の訳に組み込む (어머니가 만든 음식「母が作った食べ物」)
#   - 繋辞 이다 (학생입니다「学生です」)・아니다 (否定)、形容詞の述語 (꽃이 예쁘다) は形容詞 + 見えない繋辞
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, script

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', ',': 'comma', ';': 'comma', ':': 'comma',
               '"': None, '“': None, '”': None, "'": None, '‘': None, '’': None, '(': 'comma', ')': 'comma',
               '…': 'comma', '~': None, '-': 'comma', '–': 'comma', '—': 'comma', '「': None, '」': None}
TOKEN = re.compile(r'[^\s.!?,;:"“”\'‘’()…~\-–—「」]+|[.!?,;:"“”\'‘’()…~\-–—「」]')
PUNCT_TAGS = ('SF', 'SP', 'SS', 'SE', 'SO', 'SW')
NOMINAL_TAGS = ('NNG', 'NNP', 'NNB', 'NR', 'NP', 'XPN', 'XR', 'SL', 'SH', 'SN', 'XSN')
PREDICATE_TAGS = ('VV', 'VA', 'VX', 'VCP', 'VCN')
EXISTENTIALS = {'있다': 'ある,いる', '계시다': 'いらっしゃる', '없다': 'ない'}
TENSES = {'past': 'perfect', 'past-perfect': 'pluperfect', 'future': 'future'}


def particle(case, obj, pred):
    """主題「は」・「も」・「だけ」"""
    kind = getattr(obj, 'focus', None) if isinstance(obj, Word) else None
    if kind == 'topic':
        return 'には' if case == 'Dat' and not getattr(obj, 'outer_topic', False) else 'は'
    if kind == 'also':
        return 'にも' if case == 'Dat' else 'も'
    if kind == 'only':
        return 'だけ' + {'Nom': 'が', 'Acc': 'を', 'Dat': 'に'}.get(case, '')
    if case == 'Nom' and isinstance(obj, Word) and set(getattr(obj, 'particles', ())) & {'이', '가', '께서'} and \
            not getattr(obj, 'complement', False):
        return 'が'   # 이/가 の主語は繋辞・形容詞の文でも「が」(꽃이 예쁘다「花が美しい」)
    return None


def predicative_adjective(adj, noun):
    """述語の形容詞 (꽃이 예쁘다・키가 크다) は名詞に掛けない"""
    item = _item(adj)
    return item is not None and bool(item.attrib('predicative'))


def _root_items(lemma):
    return []


KOREAN = language.Language(
    name='ko',
    and_words=('와', '과', '하고', '랑', '이랑', '및'),
    or_words=('나', '이나', '또는', '혹은'),
    copulas=frozenset({'이다'}),
    negations=frozenset({'안', '못', '아니', '(안)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の', 'Voc': 'よ', 'Obl': 'に'},
    absolute_case=None,
    lookup=_root_items,
    particle=particle,
    predicative_adjective=predicative_adjective,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_precedes_head=True,
    topic_first=True,
    possessor_cases=('Dat',),
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
# 語節 → 記録 (名詞・用言・副詞 …)

def records(surfaces):
    """語節の列 → 記録 (dict) の列。用言の記録は語尾 (eps・ef・ec・etm・etn) を、名詞の記録は助詞を持つ"""
    morphs = {}
    for ix, t in morphology.tokens(' '.join(surfaces)):
        morphs.setdefault(ix, []).append((t.form, morphology.tag(t), t.lemma if hasattr(t, 'lemma') else t.form))
    out = []
    for ix, surface in enumerate(surfaces):
        if surface in PUNCTUATION:
            out.append({'kind': 'punct', 'surface': surface, 'ix': ix})
            continue
        out += _eojeol(surface, morphs.get(ix, []), ix)
    return out


def _eojeol(surface, morphs, ix):
    out = []
    i = 0
    while i < len(morphs):
        form, tag, lemma = morphs[i]
        if tag in PUNCT_TAGS:
            i += 1
            continue
        if tag in ('MAG', 'MAJ'):
            kind = 'negation' if form in morphology.NEGATIONS else 'conj' if tag == 'MAJ' else 'adv'
            out.append({'kind': kind, 'lemma': form, 'surface': form, 'ix': ix})
            i += 1
            continue
        if tag == 'MM':
            out.append({'kind': 'det', 'lemma': form, 'surface': form, 'ix': ix})
            i += 1
            continue
        if tag == 'IC':
            out.append({'kind': 'intj', 'lemma': form, 'surface': form, 'ix': ix})
            i += 1
            continue
        if tag in NOMINAL_TAGS:
            parts, plural = [], False
            j = i
            while j < len(morphs) and morphs[j][1] in NOMINAL_TAGS:
                if morphs[j][1] == 'XSN' and morphs[j][0] == '들':
                    plural = True
                else:
                    parts.append((morphs[j][0], morphs[j][1]))
                j += 1
            noun = {'kind': 'noun', 'lemma': ''.join(p for p, _ in parts), 'parts': parts, 'plural': plural,
                    'tag': parts[-1][1] if parts else 'NNG', 'particles': [], 'ix': ix, 'surface': surface}
            if j < len(morphs) and morphs[j][1] in ('XSV', 'XSA'):   # 공부 + 하 → 공부하다
                pred, j = _predicate(morphs, j, ix, surface, stem=noun['lemma'])
                out.append(pred)
                i = j
                continue
            if j < len(morphs) and morphs[j][1] == 'VCP':   # 학생 + 이 + ㅂ니다
                out.append(noun)
                pred, j = _predicate(morphs, j, ix, surface)
                out.append(pred)
                i = j
                continue
            while j < len(morphs) and morphs[j][1].startswith('J'):
                noun['particles'].append((morphs[j][0], morphs[j][1]))
                j += 1
            out.append(noun)
            i = j
            continue
        if tag in PREDICATE_TAGS:
            pred, i = _predicate(morphs, i, ix, surface)
            out.append(pred)
            continue
        i += 1   # 語尾だけ・記号など
    return out


def _predicate(morphs, i, ix, surface, stem=''):
    """用言 (と後ろの語尾・名詞化の後の助詞) の記録"""
    form, tag, _ = morphs[i]
    lemma = stem + form + '다'
    pred = {'kind': 'pred', 'lemma': lemma, 'tag': 'VA' if tag == 'XSA' else tag, 'eps': [], 'ef': None, 'ec': None,
            'etm': None, 'etn': None, 'particles': [], 'ix': ix, 'surface': surface, 'aux': [], 'negated': False}
    if tag in ('XSV', 'XSA'):
        pred['tag'] = 'VA' if tag == 'XSA' else 'VV'
    i += 1
    while i < len(morphs):
        form, tag, _ = morphs[i]
        if tag == 'EP':
            pred['eps'].append(morphology.normalize_ending(form))
        elif tag == 'EF':
            pred['ef'] = morphology.normalize_ending(form)
        elif tag == 'EC':
            pred['ec'] = morphology.normalize_ending(form)
            i += 1
            break
        elif tag == 'ETM':
            pred['etm'] = morphology.normalize_ending(form)
        elif tag == 'ETN':
            pred['etn'] = morphology.normalize_ending(form)
        elif tag.startswith('J') and pred['etn']:
            pred['particles'].append((form, tag))
        else:
            break
        i += 1
    return pred, i


# ----------------------------------------------------------------------
# 補助用言をまとめる

def apply_collocations(recs):
    """主語と動詞の決まった組み合わせの訳 (비가 오다「雨が降る」、눈이 오다「雪が降る」): 節の中の名詞と用言の記録に"""
    nouns = []
    for rec in recs:
        if rec['kind'] == 'noun':
            nouns.append(rec)
        elif rec['kind'] == 'pred':
            for n in nouns:
                found = morphology.COLLOCATIONS.get((n['lemma'], rec['lemma']))
                if found:
                    n['ja'], rec['ja'] = found
            nouns = []
        elif rec['kind'] == 'punct':
            nouns = []
    return recs


def merge_auxiliaries(recs):
    out = []
    k = 0
    while k < len(recs):
        rec = recs[k]
        if rec['kind'] != 'pred':
            out.append(rec)
            k += 1
            continue
        while True:
            nxt = recs[k + 1] if k + 1 < len(recs) else None
            nxt2 = recs[k + 2] if k + 2 < len(recs) else None
            key = (rec['ec'], nxt['lemma']) if nxt is not None and nxt['kind'] == 'pred' else None
            if key in morphology.AUXILIARIES:
                suffix, kind = morphology.AUXILIARIES[key]
                rec = _absorb(rec, nxt, suffix, kind)
                k += 1
                continue
            # -ㄹ 수 있다 / 없다「〜できる / できない」、-ㄹ 것이다「〜だろう」
            if rec['etm'] in ('ㄹ', '을') and nxt is not None and nxt['kind'] == 'noun' and nxt2 is not None and \
                    nxt2['kind'] == 'pred':
                if nxt['lemma'] == '수' and nxt2['lemma'] in ('있다', '없다'):
                    rec = _absorb(dict(rec, etm=None), nxt2, 'ことができる', 'potential')
                    rec['negated'] = rec['negated'] or nxt2['lemma'] == '없다'
                    k += 2
                    continue
                if nxt['lemma'] in ('것', '거') and nxt2['lemma'] == '이다':
                    rec = _absorb(dict(rec, etm=None), nxt2, '', 'future')
                    rec['tense_override'] = 'future'
                    k += 2
                    continue
            break
        out.append(rec)
        k += 1
    return out


def _absorb(rec, aux, suffix, kind):
    """本動詞 rec に補助用言 aux をまとめる (語尾は補助用言のものに)"""
    merged = dict(rec, eps=rec['eps'] + aux['eps'], ef=aux['ef'], ec=aux['ec'], etm=aux['etm'], etn=aux['etn'],
                  particles=aux['particles'], aux=rec['aux'] + [(kind, suffix, aux['lemma'])],
                  surface=rec['surface'] if rec['ix'] == aux['ix'] else rec['surface'] + ' ' + aux['surface'],
                  ixs=tuple(dict.fromkeys(rec.get('ixs', (rec['ix'],)) + aux.get('ixs', (aux['ix'],)))))
    if kind in ('negation', 'prohibition'):
        merged['negated'] = True
    elif kind == 'inability':
        merged['negated'] = True
        merged['aux'] = rec['aux'] + [('potential', 'ことができる', aux['lemma'])]
    return merged


# ----------------------------------------------------------------------
# 記録 → 語

def _base_item(surface, pos, lemma, ja, gloss_lang, row=None, **extra):
    data = {'surface': surface, 'pos': pos, 'lemma': lemma, 'base': morphology.describe(lemma, row), 'ja': ja,
            'gloss_lang': gloss_lang, 'roman': morphology.roman(surface), 'compact': True,
            'main': pos in ('noun', 'pronoun', 'verb', 'adj')}   # 語節の本体 (評価で正解の語節に対応させる)
    data.update(extra)
    return data


def _cngs(cases, plural=False):
    return [(c, 'pl' if plural else 'sg', morphology.GENDER) for c in cases]


def _noun_word(rec):
    lemma = rec['lemma']
    if rec['tag'] == 'NP' and lemma in morphology.PRONOUNS:
        ja, person, number = morphology.PRONOUNS[lemma]
        number = 'pl' if rec['plural'] else number
        data = _base_item(rec['surface'], 'pronoun', lemma, ja, 'ja', person=person, number=number,
                          _=_cngs(morphology.CASES, number == 'pl'))
        return Word(lemma, [data])
    ja, gloss_lang, row = morphology.gloss(lemma, 'name' if rec['tag'] == 'NNP' else 'noun')
    if rec.get('ja'):
        ja, gloss_lang = rec['ja'], 'ja'
    if ja is None and len(rec['parts']) > 1:   # 複合語: 部分ごとの訳を並べる (한국 + 어 …)
        pieces = [morphology.gloss(p, 'noun') for p, _ in rec['parts']]
        if all(p[0] for p in pieces):
            ja = ''.join(p[0].split(',')[0] for p in pieces)
            gloss_lang = 'ja' if all(p[1] == 'ja' for p in pieces) else 'en'
    proper = rec['tag'] == 'NNP' or (row or {}).get('pos') == 'name'
    if ja is None:
        romanized = script.romanize(lemma)
        ja, gloss_lang = (romanized[:1].upper() + romanized[1:], 'en') if proper or rec['tag'] in ('NNP', 'SL') \
            else (lemma, 'ja')
    data = _base_item(rec['surface'], 'noun', lemma, ja, gloss_lang, row, _=_cngs(morphology.CASES, rec['plural']))
    if proper:
        data['proper'] = True
    if row and row.get('hanja'):
        data['hanja'] = row['hanja']
    return Word(lemma, [data])


def _japanese_verb(rec):
    """用言の記録 → (訳, gloss_lang, 辞書の項目)。補助用言の形を付ける (読む → 読んでいる)"""
    lemma = rec['lemma']
    pos = 'adj' if rec['tag'] == 'VA' else 'verb'
    if rec.get('ja'):
        ja, gloss_lang, row = rec['ja'], 'ja', (dictionary.lemmas(lemma) or [None])[0]
    elif lemma in EXISTENTIALS:
        ja, gloss_lang, row = EXISTENTIALS[lemma], 'ja', (dictionary.lemmas(lemma) or [None])[0]
    else:
        ja, gloss_lang, row = morphology.gloss(lemma, pos)
    if ja is None:
        ja, gloss_lang = lemma, 'ja'
    if gloss_lang == 'ja':
        for kind, suffix, _ in rec['aux']:
            if suffix:
                ja = ','.join(morphology.attach(j, suffix) for j in ja.split(',')[:1])
    return ja, gloss_lang, row


def _tense(rec):
    if rec.get('tense_override'):
        return rec['tense_override']
    marks = [morphology.PREFINAL.get(e) for e in rec['eps']]
    if 'past-perfect' in marks or marks.count('past') >= 2:
        return 'pluperfect'
    if 'past' in marks or 'honorific-past' in marks:
        return 'perfect'
    if 'future' in marks:
        return 'future'
    return 'present'


def _mood(rec):
    if rec['ef'] in morphology.IMPERATIVE_ENDINGS or rec['ef'] in morphology.HORTATIVE_ENDINGS:
        return 'imperative'
    if any(kind == 'prohibition' for kind, _, _ in rec['aux']):
        return 'imperative'
    return 'indicative'


def _form_notes(rec):
    notes = []
    tense = _tense(rec)
    if tense != 'present':
        notes.append({'perfect': '過去', 'pluperfect': '大過去', 'future': '未来・推量'}[tense])
    if any(morphology.PREFINAL.get(e, '').startswith('honorific') for e in rec['eps']):
        notes.append('尊敬 (-시-)')
    if rec['ef'] in morphology.HORTATIVE_ENDINGS:
        notes.append('勧誘「〜しよう」')
    elif _mood(rec) == 'imperative':
        notes.append('命令')
    if rec['ef'] and re.search('(습|ㅂ)니|요$', rec['ef']):
        notes.append('丁寧')
    notes += [{'progressive': '進行 -고 있다', 'resultative': '結果の状態 -어 있다', 'benefactive': '授受 -어 주다',
               'try': '試み -어 보다', 'completive': '完了 -어 버리다/놓다', 'direction': '方向 -어 가다/오다',
               'desire': '願望 -고 싶다', 'must': '義務 -어야 하다', 'become': '変化 -게 되다', 'negation': '否定 -지 않다',
               'inability': '不可能 -지 못하다', 'prohibition': '禁止 -지 말다', 'passive': '受動 -어지다',
               'potential': '可能 -ㄹ 수 있다', 'future': '未来・推量 -ㄹ 것이다'}.get(kind, kind)
              for kind, _, _ in rec['aux']]
    return notes


def _verb_item(rec, surface=None):
    ja, gloss_lang, row = _japanese_verb(rec)
    lemma = rec['lemma']
    data = _base_item(surface or rec['surface'], 'verb', lemma, ja, gloss_lang, row, pres1sg=lemma, voice='active',
                      mood=_mood(rec), tense=_tense(rec), person=None, number=None, persons=[],
                      form='・'.join(_form_notes(rec)))
    if any(kind == 'passive' for kind, _, _ in rec['aux']):
        data['voice'] = 'passive'
    if lemma in EXISTENTIALS:
        data['existential'] = True
    if rec['ef'] in morphology.HORTATIVE_ENDINGS:
        data['person'] = 1
    return data


def _copula_word(rec, negative=False):
    data = {'surface': '(이다)' if not negative else rec['surface'], 'pos': 'verb', 'lemma': '이다', 'pres1sg': '이다',
            'base': '이다 ida (繋辞)', 'ja': 'である', 'gloss_lang': 'ja', 'copula': True, 'voice': 'active',
            'mood': _mood(rec), 'tense': _tense(rec), 'person': None, 'number': None, 'persons': [],
            'form': '・'.join(_form_notes(rec)), 'compact': True}
    return Word(data['surface'], [data])


def _negation_word(surface='(안)'):
    return Word(surface, [{'surface': surface, 'pos': 'adv', 'base': '안 an (否定)', 'ja': '〜ない', 'gloss_lang': 'ja',
                           'compact': True}])


def _connective_word(rec):
    ja, kind = morphology.CONNECTIVES.get(rec['ec'], ('', 'sub'))
    if not ja:
        return None
    surface = '-' + rec['ec']
    return Word(surface, [{'surface': surface, 'pos': 'conj', 'base': '-%s (連結語尾)' % rec['ec'], 'ja': ja,
                           'gloss_lang': 'ja', 'compact': True, 'connective': kind}])


def _apply_particles(word, particles, out):
    """名詞の語に助詞の働きを付ける。後置詞なら後置詞の語を返す (名詞句の前に移すため)"""
    item = _item(word)
    case, prep, focus = None, None, None
    conj = None
    for form, tag in particles:
        if tag == 'JC':
            conj = form
        elif form in morphology.CASE_PARTICLES and tag in ('JKS', 'JKO', 'JKG', 'JKV', 'JKB', 'JKC'):
            case = morphology.CASE_PARTICLES[form]
        elif form in morphology.POSTPOSITIONS and tag in ('JKB', 'JX'):
            prep = prep or form
        elif form in morphology.FOCUS_PARTICLES:
            focus = morphology.FOCUS_PARTICLES[form] or focus
        elif tag == 'JKC':
            case = 'Nom'
    word.particles = [f for f, _ in particles]
    if any(tag == 'JKC' for _, tag in particles):
        word.complement = True   # 補格 (책이 아니다・학생이 되다): 主語でなく補語
    if focus:
        word.focus = focus
    if case and item._:
        item._ = [(case,) + c[1:] for c in item._[:1]]
    if prep:
        ja = morphology.POSTPOSITIONS[prep]
        if focus in ('topic', 'also'):
            ja = ','.join(j + morphology.FOCUS_JA[focus] for j in ja.split(','))
        item._ = [('Obl',) + c[1:] for c in item._[:1]]
        word.focus = None
        return Word(prep, [{'surface': prep, 'pos': 'preposition', 'base': '%s (助詞)' % prep, 'ja': ja,
                            'gloss_lang': 'ja', 'dominates': 'Obl', 'compact': True}]), conj
    if not case and item._:
        item._ = [c for c in item._ if c[0] in ('Nom', 'Acc')]
        word.open_case = True
    return None, conj


def build_words(recs):
    words = []
    for k, rec in enumerate(recs):
        kind = rec['kind']
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        ix = rec['ix']
        if kind == 'punct':
            word = Word(rec['surface'], None)
        elif kind == 'negation':
            word = Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adv', 'base': '%s (否定)' % rec['surface'],
                                          'ja': morphology.NEGATIONS[rec['surface']], 'gloss_lang': 'ja', 'compact': True}])
            if rec['surface'] == '못' and nxt is not None and nxt['kind'] == 'pred':
                nxt['aux'] = nxt['aux'] + [('potential', 'ことができる', '못')]
        elif kind in ('adv', 'conj', 'intj'):
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'adv')
            pos = {'adv': 'adv', 'conj': 'conj', 'intj': 'intj'}[kind]
            word = Word(rec['surface'], [_base_item(rec['surface'], pos, rec['lemma'], ja or rec['lemma'],
                                                    gloss_lang or 'ja', row)])
        elif kind == 'det':
            ja = morphology.DETERMINERS.get(rec['lemma'], rec['lemma'])
            word = Word(rec['surface'], [_base_item(rec['surface'], 'adj', rec['lemma'], ja, 'ja', demonstrative=True,
                                                    _=_cngs(morphology.CASES) + _cngs(morphology.CASES, True))])
        elif kind == 'noun' and not rec['particles'] and rec['lemma'] in morphology.TIME_NOUNS:
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'noun')   # 助詞の無い時の名詞は副詞 (내일「明日」)
            word = Word(rec['surface'], [_base_item(rec['surface'], 'adv', rec['lemma'], ja or rec['lemma'],
                                                    gloss_lang or 'ja', row)])
        elif kind == 'noun':
            word = _noun_word(rec)
            word.token_ix = ix
            word.eojeol = rec['surface']
            if not rec['particles'] and nxt is not None and nxt['kind'] == 'noun' and nxt['ix'] != ix:
                rec = dict(rec, particles=[('의', 'JKG')])   # 名詞の前の助詞の無い名詞・代名詞は属格 (한국 음식、내 친구)
            prep, conj = _apply_particles(word, rec['particles'], words)
            if prep is not None:
                prep.token_ix = ix
                start = len(words)
                while start > 0 and _np_continues(words[start - 1]):
                    start -= 1
                words.insert(start, prep)
            words.append(word)
            if conj:
                cw = Word(conj, [{'surface': conj, 'pos': 'conj', 'base': '%s (並列の助詞)' % conj, 'ja': 'と',
                                  'gloss_lang': 'ja', 'compact': True}])
                cw.token_ix = ix
                words.append(cw)
                word.coordinated = True
            continue
        elif kind == 'pred':
            words += _pred_words(rec, nxt)
            continue
        else:
            continue
        word.token_ix = ix
        words.append(word)
    return words


def _np_continues(word):
    item = _item(word)
    if item is None:
        return False
    if item.pos == 'adj':
        return True
    return item.pos in ('noun', 'pronoun') and item._ and all(c[0] == 'Gen' for c in item._)


def _pred_words(rec, nxt):
    ix = rec['ix']
    out = []
    if rec['negated']:
        neg = _negation_word()
        neg.token_ix = ix
        out.append(neg)
    if rec['etn']:   # 名詞化 (읽기「読むこと」)
        ja, gloss_lang, row = _japanese_verb(rec)
        word = Word(rec['surface'], [_base_item(rec['surface'], 'noun', rec['lemma'], ja.split(',')[0] + 'こと', 'ja',
                                                row, _=_cngs(morphology.CASES), nominalized=True)])
        word.token_ix = ix
        out.append(word)
        _apply_particles(word, rec['particles'], out)
        return out
    if rec['etm']:   # 連体形: 後で名詞に掛ける (mark_attributives)
        word = Word(rec['surface'], [_verb_item(rec)])
        word.attributive = rec['etm']
        word.adjective = rec['tag'] == 'VA' and rec['lemma'] not in EXISTENTIALS
        word.token_ix = ix
        word.eojeol = rec['surface']
        out.append(word)
        return out
    if rec['lemma'] == '이다' or rec['tag'] == 'VCN':
        if rec['tag'] == 'VCN':
            neg = _negation_word('아니')
            neg.token_ix = ix
            out.append(neg)
        word = _copula_word(rec)
    elif rec['tag'] == 'VA' and rec['lemma'] not in EXISTENTIALS:   # 形容詞の述語: 形容詞 + 見えない繋辞
        ja, gloss_lang, row = _japanese_verb(rec)
        adj = Word(rec['surface'], [_base_item(rec['surface'], 'adj', rec['lemma'], ja, gloss_lang, row,
                                               _=_cngs(('Nom',)) + _cngs(('Nom',), True), predicative=True)])
        adj.token_ix = ix
        out.append(adj)
        word = _copula_word(rec)
    else:
        word = Word(rec['surface'], [_verb_item(rec)])
    word.token_ix = ix
    if len(rec.get('ixs', ())) > 1:
        word.token_ixs = rec['ixs']   # 補助用言をまとめた動詞 (읽고 있다)
    out.append(word)
    if rec['ec']:
        conj = _connective_word(rec)
        if conj is not None:
            conj.token_ix = ix
            out.append(conj)
    return out


# ----------------------------------------------------------------------
# 連体形

def mark_attributives(words):
    """連体形の用言を後ろの名詞に掛ける。補語の無い形容詞は修飾語 (예쁜 꽃)、ほかは関係節を名詞の訳に組み込む"""
    out = []
    for i, word in enumerate(words):
        if not getattr(word, 'attributive', None):
            out.append(word)
            continue
        head = next((w for w in words[i + 1:i + 3] if _pos(w) in ('noun', 'pronoun')), None)
        # 関係節の補語: 直前の、主題でない名詞句 (と後置詞・否定・副詞)
        start = len(out)
        while start > 0:
            prev = out[start - 1]
            if prev.items is None or _pos(prev) in ('verb', 'conj') or getattr(prev, 'attributive', None) or \
                    getattr(prev, 'focus', None) == 'topic':
                break
            start -= 1
        clause = out[start:]
        item = _item(word)
        if head is None:
            out.append(word)
            continue
        if getattr(word, 'adjective', False) and not [w for w in clause if _pos(w) in ('noun', 'pronoun')]:
            ja = item.ja
            word.items = [type(item)(dict(item.item, pos='adj', _=_cngs(morphology.CASES) +
                                          _cngs(morphology.CASES, True)))]
            out.append(word)
            continue
        text = _relative_text(clause, word)
        hitem = _item(head)
        hja = (hitem.ja or '').split(',')[0]
        head.items = [type(hitem)(dict(hitem.item, ja=text + hja, gloss_lang='ja', _=list(hitem._ or []),
                                       relative=' '.join(dict.fromkeys(getattr(w, 'eojeol', w.surface)
                                                                       for w in clause + [word]))))]
        for w in clause + [word]:
            w.relative_of = head
        del out[start:]
    return out


def _relative_text(clause, verb):
    """関係節の日本語 (母が作った)"""
    from dragoman.kobun.modernize import Modern
    parts = []
    pending_prep = None
    negated = False
    for w in clause:
        item = _item(w)
        if item.pos == 'preposition':
            pending_prep = item.ja.split(',')[0].lstrip('〜')
            continue
        if item.pos == 'adv' and w.surface in KOREAN.negations:
            negated = True
            continue
        ja = (item.ja or '').split(',')[0]
        if pending_prep is not None:
            parts.append(ja + pending_prep)
            pending_prep = None
        elif item.pos in ('noun', 'pronoun'):
            case = item._[0][0] if item._ else 'Nom'
            parts.append(ja + {'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'}.get(case, 'が'))
        else:
            parts.append(ja)
    vitem = _item(verb)
    v = (vitem.ja or '').split(',')[0]
    past = verb.attributive in ('ㄴ', '은') and not getattr(verb, 'adjective', False) or vitem.attrib('tense') == 'perfect'
    try:
        if negated or vitem.item.get('negated'):
            v = Modern.neg_stem(v) + 'ない'
        if past and vitem.attrib('gloss_lang') == 'ja':
            v = Modern.past_form(v)
    except Exception:
        pass
    return ''.join(parts) + v


# ----------------------------------------------------------------------
# 主題・とりたての句の格

def copy_coordinated_cases(words):
    """並列の助詞 (와/과・하고) の前の名詞は、後ろの名詞の格と主題の印に合わせる (고양이와 개가「猫と犬が」)"""
    for i in range(len(words) - 1, -1, -1):
        word = words[i]
        if not getattr(word, 'coordinated', False):
            continue
        nxt = next((w for w in words[i + 1:] if _pos(w) in ('noun', 'pronoun')), None)
        if nxt is None:
            continue
        _item(word)._ = [c[:1] + _item(word)._[0][1:] for c in (_item(nxt)._ or [])[:1]] or _item(word)._
        word.open_case = getattr(nxt, 'open_case', False)
        word.focus = getattr(nxt, 'focus', None)


def assign_cases(words):
    """節 (接続の語・句読点で区切る) ごとに、助詞の無い名詞・主題「は」・「も」の名詞の格を決める:
    이/가 の主語が無ければ主格、あれば (他動詞で을/를 の句が無ければ) 対格"""
    clause = []
    for word in words + [None]:
        if word is None or word.items is None or _pos(word) == 'conj':
            _assign_clause(clause)
            clause = []
        else:
            clause.append(word)


def _assign_clause(clause):
    nominals = [w for w in clause if _pos(w) in ('noun', 'pronoun')]
    verb = next((_item(w) for w in clause if _pos(w) == 'verb'), None)
    if verb is not None and verb.attrib('lemma') in ('되다', '변하다'):
        for w in nominals:   # 補格の 되다 (선생님이 되다「先生になる」): 補語は「に」
            if getattr(w, 'complement', False):
                _item(w)._ = [('Dat',) + c[1:] for c in _item(w)._[:1]]
    open_ = [w for w in nominals if getattr(w, 'open_case', False)]
    if not open_:
        return
    fixed = {c[0] for w in nominals if not getattr(w, 'open_case', False) and not getattr(w, 'complement', False)
             for c in (_item(w)._ or [])[:1]}
    verb = next((_item(w) for w in clause if _pos(w) == 'verb'), None)
    copula = verb is not None and (verb.attrib('copula') or verb.attrib('existential'))
    has_nom = 'Nom' in fixed
    has_acc = 'Acc' in fixed
    for k, w in enumerate(open_):
        item = _item(w)
        if has_nom and copula and getattr(w, 'focus', None) == 'topic':
            # 二重主語 (그 사람은 키가 크다「その人は背が高い」): 主題は格の枠の外の「は」
            item._ = [('Dat',) + c[1:] for c in item._[:1]]
            w.outer_topic = True
            continue
        if not has_nom:
            case = 'Nom'
            has_nom = True
        elif not has_acc and not copula:
            case = 'Acc'
            has_acc = True
        else:
            case = 'Nom'
        if getattr(w, 'focus', None) is None and k == len(open_) - 1 and has_nom and not copula and not has_acc:
            case = 'Acc'
        item._ = [(case,) + c[1:] for c in item._[:1]]


# ----------------------------------------------------------------------

def lookup_all(surfaces):
    recs = merge_auxiliaries(apply_collocations(records(surfaces)))
    words = build_words(recs)
    global _display
    _display = list(words)
    words = mark_attributives(words)
    copy_coordinated_cases(words)
    assign_cases(words)
    for i, word in enumerate(words):
        word.index = i
    return words


_display = []


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(KOREAN):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    analysis.display = _display
    from .literal import literal
    analysis.literal = literal(surfaces)   # 語順のままの日本語訳
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
