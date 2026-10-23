#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語 (ハルハ方言・キリル文字) の文の解析
#
# 語を辞書と規則で語幹と接尾辞に分け (mongolian/morphology.py)、読みを文脈で選んで記録にまとめてから、並列・係り先・
# 格の枠・日本語訳は共通の解析器 (core/analyzer.py) をモンゴル語の設定 (MONGOLIAN) で使う:
#   - 格の接尾辞: 主格 (無標)「が」、属格 -ын「の」(後ろの名詞に掛かる)、対格 -ыг「を」、与位格 -д / -т「に,で」、
#     奪格 -аас「から」、造格 -аар「で」、共同格 -тай「と」、方向格 -руу「へ」。再帰所有 -аа「自分の」
#   - 用言: -на (現在・未来)・-лаа / -в / -жээ (過去)・-сан (過去。分詞としても)・-даг (習慣)、否定 -гүй。
#     動詞は人称で変わらない (主語を書かなければ補わない)
#   - 副動詞 (-ж「〜して」・-аад「〜してから」・-вал「〜なら」・-тал「〜まで」…) は節を区切る接続の語。-ж байна は進行
#   - 分詞 (-сан・-х・-даг) は後ろに名詞があれば関係節 (名詞の訳に組み込む)、格が付けば名詞化「〜すること」
#   - 名詞の述語 (Би багш「私は先生だ」) には見えない繋辞を補う。бол・нь は主題「は」、биш は否定の繋辞
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '-': 'comma', '(': 'comma', ')': 'comma', '"': None,
               '“': None, '”': None, '«': None, '»': None}
TOKEN = re.compile(r"[А-Яа-яЁёӨөҮүA-Za-z]+(?:-[А-Яа-яЁёӨөҮү]+)*|\d+(?:[.,]\d+)*|[.!?…,;:—–\-()\"“”«»]")
GENDER = 'c'
ALL_CASES = ('Nom', 'Gen', 'Acc', 'Dat', 'Abl', 'Ins', 'Com', 'Dir')
AUXILIARIES = {'байх', 'болох'}


def particle(case, obj, pred):
    if isinstance(obj, Word) and getattr(obj, 'topic', False) and case == 'Nom':
        return 'は'
    return None


def _root_items(lemma):
    return []


# 副詞節の副動詞の語尾 (切り出した語の見出し) → (節の後ろに付ける形, 節の動詞の時制) (core/Adverbial.py。-ж は
# 助動詞の前 (орж байхад) にも来るので入れない)
SUBORDINATORS = {'-вал': ('なら', None), '-аад': ('て', 'present')}


MONGOLIAN = language.Language(
    name='mn',
    subordinators=SUBORDINATORS, subordinators_follow=True,
    and_words=('ба', 'болон'),
    or_words=('буюу', 'эсвэл'),
    copulas=frozenset({'(байх)'}),
    negations=frozenset({'биш', '(биш)', '(-гүй)', 'бүү', 'битгий'}),
    case_particles=dict(morphology.CASE_JA),
    absolute_case=None,
    lookup=_root_items,
    particle=particle,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_precedes_head=True,
    topic_first=True,
    possessor_cases=('Dat', 'Gen'),
    relatives_before_head=True,
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
# 読みの選択と記録

def choose(token, k, surfaces):
    readings = morphology.analyses(token)
    if not readings:
        return None
    nxt = surfaces[k + 1] if k + 1 < len(surfaces) else '.'
    nxt_low = nxt.lower()
    final = nxt in PUNCTUATION or nxt_low in morphology.PARTICLES and morphology.PARTICLES[nxt_low] == 'question'
    nxt_readings = morphology.analyses(nxt) if nxt not in PUNCTUATION else []

    def score(r):
        s = 0
        if final and r['kind'] == 'verb' and r['form'] in ('finite', 'participle') and not r.get('case'):
            s -= 3
        if not final and r['kind'] == 'verb' and r['form'] == 'finite':
            s += 2
        if r['kind'] == 'verb' and r['form'] == 'converb' and r['converb'] == 'manner':
            s += 2   # -н の副動詞 (заан → заа-н) は名詞の読みの後ろに
        if r['kind'] == 'noun' and r.get('case') == 'Nom' and r.get('pos') is None and not r.get('reflexive'):
            s += 0.5
        if r['kind'] == 'det' and nxt_readings and any(x['kind'] in ('noun', 'adj') for x in nxt_readings):
            s -= 2   # 名詞の前の指示詞 (энэ ном「この本」)
        if r['kind'] == 'pronoun' and nxt_readings and any(x['kind'] in ('noun', 'adj') for x in nxt_readings) and \
                r['lemma'] in morphology.DETERMINERS:
            s += 1
        if r.get('pos') == 'name' and not token[:1].isupper():
            s += 1
        if nxt_low in morphology.POSTPOSITIONS and r['kind'] in ('noun', 'pronoun'):
            s += -2 if r.get('case') == 'Gen' else 0   # 後置詞の前は属格 (ширээн дээр「机の上に」)
        if r['kind'] == 'noun' and r.get('case') not in (None, 'Nom') and r.get('pos') is None and \
                not any(x.get('lemma') == token.lower() and x['kind'] in ('adj', 'noun', 'adv') for x in readings):
            s -= 0.3   # 格の接尾辞を分けた読みを、同じ綴りの別の見出しより先に (語そのものが見出しなら見出しを)
        if r.get('lemma') == token.lower() and r['kind'] in ('adj', 'adv'):
            s -= 0.5   # 見出しそのものの形容詞・副詞 (сайхан「美しい」。сайх + 属格でなく)
        return s
    return sorted(readings, key=score)[0]


def records(surfaces):
    out = []
    for k, token in enumerate(surfaces):
        if token in PUNCTUATION:
            out.append({'kind': 'punct', 'surface': token, 'ix': k})
            continue
        r = choose(token, k, surfaces)
        if r is None:
            out.append(_unknown(token, k))
            continue
        if r['kind'] == 'noun' and r.get('case') == 'Nom' and r['lemma'] in morphology.TIME_WORDS:
            r = dict(r, kind='adv')   # 助詞の無い時の名詞は副詞 (өчигдөр「昨日」)
        rec = dict(r, surface=token, ix=k)
        if rec['kind'] == 'noun' and token[:1].isupper() and (k > 0 or rec.get('pos') == 'name'):
            rec['proper'] = True
        out.append(rec)
    return _verb_groups(out)


def _unknown(token, k):
    """辞書に無い語: 大文字なら固有名詞 (格の接尾辞を分ける: Батын → Бат + 属格)"""
    if token[:1].isupper():
        low = token.lower()
        for suffix, case in morphology.CASE_SUFFIXES:
            if len(suffix) >= 2 and low.endswith(suffix) and len(low) - len(suffix) >= 2:   # 1字の接尾辞は分けない (Бат)
                return {'kind': 'noun', 'lemma': token[:len(token) - len(suffix)], 'case': case, 'number': 'sg',
                        'surface': token, 'ix': k, 'proper': True}
        return {'kind': 'noun', 'lemma': token, 'case': 'Nom', 'number': 'sg', 'surface': token, 'ix': k, 'proper': True}
    return {'kind': 'noun', 'lemma': token.lower(), 'case': 'Nom', 'number': 'sg', 'surface': token, 'ix': k,
            'unknown': True}


def _verb_groups(recs):
    """副動詞 -ж + байна「〜している」(進行)、分詞 -сан + байна (結果)、-х гэж байна (〜しようとしている) をまとめる。
    文末・小辞の前の分詞は定形 (өгсөн「与えた」)"""
    out = []
    for k, rec in enumerate(recs):
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        if rec['kind'] == 'verb' and nxt is not None and nxt['kind'] == 'verb' and nxt['lemma'] == 'байх' and \
                not nxt.get('case') and (rec['form'] == 'converb' and rec.get('converb') in ('and', 'manner') or
                                         rec['form'] == 'participle' and not rec.get('case')):
            merged = dict(nxt, lemma=rec['lemma'], surface=rec['surface'] + ' ' + nxt['surface'], ix=rec['ix'],
                          ixs=(rec['ix'], nxt['ix']), aux='progressive' if rec['form'] == 'converb' else 'resultative',
                          negated=rec.get('negated') or nxt.get('negated'))
            recs[k + 1] = dict(merged, absorbed=True)
            out.append(None)
            continue
        if rec.get('absorbed'):
            rec = dict(rec)
            rec.pop('absorbed')
        out.append(rec)
    out = [r for r in out if r is not None]
    for k, rec in enumerate(out):
        nxt = out[k + 1] if k + 1 < len(out) else None
        if rec['kind'] == 'verb' and rec['form'] == 'participle' and not rec.get('case'):
            nxt_kind = nxt['kind'] if nxt is not None else 'punct'
            if nxt_kind in ('noun', 'adj', 'det') and not (nxt.get('case') == 'Nom' and nxt.get('lemma') in morphology.TIME_WORDS):
                rec['attributive'] = True   # 後ろの名詞に掛かる (Бат-ын бичсэн захиа「バトが書いた手紙」)
            elif nxt_kind in ('punct', 'particle', 'conj', 'verb') or nxt is None:
                rec['form'] = 'finite'      # 文末の分詞は定形の過去・習慣・未来
    return out


# ----------------------------------------------------------------------
# 記録 → 語

def _cngs(cases, number='sg'):
    return [(c, number, GENDER) for c in cases]


def _japanese_verb(rec):
    from dragoman.core.japanese import attach_auxiliary
    ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'verb')
    if ja is None:
        return rec['lemma'], 'en', None
    first = ja.split(',')[0]
    if gloss_lang == 'ja' and rec.get('aux') == 'progressive':
        first = attach_auxiliary(first, 'ている')
    return first, gloss_lang, row


TENSES = {'present': 'present', 'perfect': 'perfect', 'habitual': 'present', 'future': 'future',
          'imperfective': 'present', 'agent': 'present'}


def _form_notes(rec):
    names = {'present': '現在・未来 -на', 'perfect': '過去', 'habitual': '習慣 -даг', 'future': '未来 -х',
             'imperfective': '未完了 -аа'}
    notes = [names.get(rec.get('tense'), '')] if rec.get('form') in ('finite', 'participle') else []
    if rec.get('form') == 'converb':
        notes.append(morphology.CONVERBS.get(rec.get('converb'), ('', '', ''))[2])
    if rec.get('aux') == 'progressive':
        notes.append('進行 -ж байна')
    if rec.get('negated'):
        notes.append('否定 -гүй')
    if rec.get('form') == 'imperative':
        notes.append('命令・勧誘')
    return '・'.join(n for n in notes if n)


def _verb_item(rec, person=None):
    ja, gloss_lang, row = _japanese_verb(rec)
    tense = TENSES.get(rec.get('tense'), 'present')
    if rec.get('aux') == 'progressive':
        tense = 'perfect' if rec.get('tense') == 'perfect' else 'present'
    mood = 'imperative' if rec.get('form') == 'imperative' else 'indicative'
    return {'surface': rec['surface'], 'pos': 'verb', 'lemma': rec['lemma'], 'pres1sg': rec['lemma'],
            'base': '%s %s' % (rec['lemma'], (row or {}).get('roman') or ''), 'ja': ja, 'gloss_lang': gloss_lang,
            'voice': 'active', 'mood': mood, 'tense': tense, 'person': person, 'number': None, 'persons': [],
            'form': _form_notes(rec), 'main': True, 'compact': True,
            'existential': rec['lemma'] == 'байх' and not rec.get('aux')}


def _negation(surface='(-гүй)'):
    return Word(surface, [{'surface': surface, 'pos': 'adv', 'base': '-гүй (否定)', 'ja': '〜ない', 'gloss_lang': 'ja',
                           'compact': True}])


def _copula(tense='present', surface='(байх)'):
    return Word(surface, [{'surface': surface, 'pos': 'verb', 'lemma': '(байх)', 'pres1sg': '(байх)',
                           'base': '(繋辞なし)', 'ja': 'である', 'gloss_lang': 'ja', 'copula': True, 'voice': 'active',
                           'mood': 'indicative', 'tense': tense, 'person': None, 'number': None, 'persons': [],
                           'compact': True}])


def _noun_word(rec):
    lemma = rec['lemma']
    case = rec.get('case') or 'Nom'
    number = rec.get('number', 'sg')
    if rec['kind'] == 'pronoun':
        data = {'surface': rec['surface'], 'pos': 'pronoun', 'base': lemma, 'ja': rec['ja'], 'gloss_lang': 'ja',
                'person': rec['person'], 'number': rec['number'], '_': _cngs([case], rec['number']), 'compact': True,
                'main': True}
        return Word(rec['surface'], [data])
    ja, gloss_lang, row = morphology.gloss(lemma, 'noun')
    if rec.get('proper') and (ja is None or gloss_lang == 'en'):
        from .katakana import katakana
        ja, gloss_lang = katakana(lemma), 'ja'   # 辞書に無い名前はカタカナ (Бат → バト)
    if ja is None:
        ja, gloss_lang = lemma, 'ja'
    if rec.get('reflexive') and gloss_lang == 'ja':
        ja = ','.join('自分の' + j for j in ja.split(',')[:1])
    data = {'surface': rec['surface'], 'pos': 'noun', 'base': '%s %s' % (lemma, (row or {}).get('roman') or ''),
            'lemma': lemma, 'ja': ja, 'gloss_lang': gloss_lang, '_': _cngs([case], number), 'main': True, 'compact': True}
    if rec.get('proper'):
        data['proper'] = True
    if row and row.get('script'):
        data['script'] = row['script']
    return Word(rec['surface'], [data])


def _np_continues(word):
    item = _item(word)
    if item is None:
        return False
    return item.pos == 'adj' or item.pos in ('noun', 'pronoun') and item._ and all(c[0] == 'Gen' for c in item._)


def build_words(recs):
    from dragoman.core.japanese import japanese_plain
    words = []
    for k, rec in enumerate(recs):
        kind = rec['kind']
        new = []
        if kind == 'punct':
            new = [Word(rec['surface'], None)]
        elif kind in ('noun', 'pronoun'):
            new = [_noun_word(rec)]
        elif kind == 'adj':
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'adj')
            new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adj', 'base': rec['lemma'], 'ja': ja or rec['lemma'],
                                          'gloss_lang': gloss_lang or 'en', '_': _cngs(ALL_CASES) + _cngs(ALL_CASES, 'pl'),
                                          'main': True, 'compact': True}])]
        elif kind == 'det':
            lemma = rec['lemma']
            ja = morphology.DETERMINERS.get(lemma, lemma)
            new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adj', 'base': lemma, 'ja': ja, 'gloss_lang': 'ja',
                                          '_': _cngs(ALL_CASES) + _cngs(ALL_CASES, 'pl'), 'demonstrative': True,
                                          'compact': True}])]
        elif kind == 'adv':
            ja, gloss_lang, row = morphology.gloss(rec['lemma'], 'adv')
            new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'adv', 'base': rec['lemma'],
                                          'ja': ja or rec['lemma'], 'gloss_lang': gloss_lang or 'en', 'compact': True}])]
        elif kind == 'conj':
            new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'conj', 'base': rec['lemma'],
                                          'ja': morphology.CONJUNCTIONS.get(rec['lemma'], rec['lemma']), 'gloss_lang': 'ja',
                                          'compact': True}])]
        elif kind == 'negation':
            if rec['lemma'] == 'биш':   # 否定の繋辞 (Энэ ном биш「これは本ではない」)
                new = [_negation('биш'), _copula()]
            else:
                new = [_negation(rec['surface'])]
        elif kind == 'particle':
            p = rec.get('particle') or morphology.PARTICLES.get(rec['lemma'])
            prev = next((w for w in reversed(words) if w.items is not None), None)
            if p == 'topic' and prev is not None and _pos(prev) in ('noun', 'pronoun'):
                prev.topic = True   # бол・нь「〜は」
            elif p == 'question' and prev is not None:
                prev.question = True
            elif p == 'copula':
                new = [_copula('present', rec['surface'])]
            if not new:
                continue
        elif kind == 'postposition':
            ja = morphology.POSTPOSITIONS.get(rec['lemma'], '〜' + rec['lemma'])
            prep = Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'preposition', 'base': rec['lemma'], 'ja': ja,
                                          'gloss_lang': 'ja', 'dominates': 'Obl', 'compact': True}])
            prep.token_ix = rec['ix']
            start = len(words)
            if start > 0 and _pos(words[start - 1]) in ('noun', 'pronoun'):
                head = words[start - 1]
                _item(head)._ = [('Obl',) + c[1:] for c in (_item(head)._ or _cngs(['Nom']))[:1]]
                start -= 1
                while start > 0 and _np_continues(words[start - 1]):
                    start -= 1
                words.insert(start, prep)
                continue
            new = [prep]
        elif kind == 'verb':
            if rec.get('case'):   # 名詞化 (байхдаа「いる時に」、уншихыг「読むことを」)
                ja, gloss_lang, row = _japanese_verb(rec)
                tense = 'perfect' if rec.get('tense') == 'perfect' else 'present'
                text = japanese_plain(ja, False, tense, rec.get('negated')) if gloss_lang == 'ja' else ja
                tail = '時' if rec['case'] == 'Dat' else 'こと'
                new = [Word(rec['surface'], [{'surface': rec['surface'], 'pos': 'noun', 'base': rec['lemma'],
                                              'ja': text + tail, 'gloss_lang': 'ja', '_': _cngs([rec['case']]),
                                              'nominalized': True, 'main': True, 'compact': True}])]
            elif rec.get('attributive'):
                word = Word(rec['surface'], [_verb_item(rec)])
                word.attributive = True
                new = [word]
            elif rec['form'] == 'converb':
                verb = Word(rec['surface'], [_verb_item(rec)])
                form, tail, note = morphology.CONVERBS.get(rec['converb'], ('te', '', ''))
                conj = Word('-' + rec.get('ending', ''), [{'surface': '-' + rec.get('ending', ''), 'pos': 'conj',
                                                           'base': note, 'ja': '〜て' if form == 'te' and not tail else '〜' + tail,
                                                           'gloss_lang': 'ja', 'compact': True}])
                new = ([_negation()] if rec.get('negated') else []) + [verb, conj]
            else:
                new = ([_negation()] if rec.get('negated') else []) + [Word(rec['surface'], [_verb_item(rec)])]
        for w in new:
            w.token_ix = rec['ix']
            w.record = rec
            if len(rec.get('ixs', ())) > 1 and _pos(w) == 'verb':
                w.token_ixs = rec['ixs']
        words += new
    return words


def mark_participles(words):
    """連体の分詞の節を共通の解析器の関係節にする: 節の頭に見えない関係代名詞を補い (空所の格: 節に属格の主語
    (Батын бичсэн) があれば対格、無ければ主格)、分詞を節の定動詞にする。先行詞は節の後ろの名詞
    (relatives_before_head)。関係節より前の同じ節の語は関係節の後ろへ"""
    out = []
    for i, word in enumerate(words):
        if not getattr(word, 'attributive', False):
            out.append(word)
            continue
        head = next((w for w in words[i + 1:i + 3] if _pos(w) in ('noun', 'pronoun')), None)
        if head is None:
            out.append(word)
            continue
        start = len(out)
        while start > 0:
            prev = out[start - 1]
            item = _item(prev)
            nominative = item is not None and item.pos in ('noun', 'pronoun') and item._ and item._[0][0] == 'Nom'
            if prev.items is None or _pos(prev) in ('verb', 'conj') or getattr(prev, 'topic', False) or \
                    nominative and start < len(out) or getattr(prev, 'relative_participle', False):
                break
            start -= 1
        clause = out[start:]
        subject = [w for w in clause if _pos(w) in ('noun', 'pronoun') and _item(w)._ and _item(w)._[0][0] == 'Gen']
        for w in subject[:1]:
            _item(w)._ = [('Nom',) + c[1:] for c in _item(w)._[:1]]   # 関係節の主語 (Батын бичсэн → Бат が)
        gap = 'Acc' if subject else 'Nom'
        item = _item(word)
        word.items = [type(item)(dict(item.item, mood='indicative', form=(item.attrib('form') or '') + '・分詞 (関係節)'))]
        word.attributive = False
        word.relative_participle = True
        pronoun = Word('(харьц)', [{'surface': '(харьц)', 'pos': 'pronoun', 'base': '(関係節の空所)', 'ja': '〜するところの',
                                    'gloss_lang': 'ja', 'desc': '関係代名詞', '_': _cngs((gap,)) + _cngs((gap,), 'pl'),
                                    'compact': True}])
        pronoun.token_ix = None
        before, after = Word(',', None), Word(',', None)
        before.token_ix = after.token_ix = None
        lead = start
        while lead > 0 and out[lead - 1].items is not None and _pos(out[lead - 1]) not in ('verb', 'conj') and \
                not getattr(out[lead - 1], 'relative_participle', False):
            lead -= 1
        moved = out[lead:start]
        del out[lead:start]
        out[lead:lead] = [before, pronoun]
        out.append(word)
        out.append(after)
        out += moved
    return out


def supply_copula(words):
    """動詞の無い文には、最後の名詞類の後ろに見えない繋辞を補う (Би багш「私は先生だ」)。与位格なら存在「ある」"""
    if any(_pos(w) == 'verb' and not getattr(w, 'relative_participle', False) for w in words):
        return words
    last_relative = max([k for k, w in enumerate(words) if getattr(w, 'relative_participle', False)], default=-1)
    nominals = [i for i, w in enumerate(words) if _pos(w) in ('noun', 'pronoun', 'adj') and i > last_relative]
    if len(nominals) < 1:
        return words
    k = nominals[-1]
    last = words[k]
    case = _item(last)._[0][0] if _item(last)._ else 'Nom'
    cop = _copula()
    if case == 'Dat':
        cop.items[0].item.update(ja='ある,いる', existential=True, copula=False)
        cop.items = [type(cop.items[0])(cop.items[0].item)]
    cop.token_ix = getattr(last, 'token_ix', None)
    if getattr(last, 'record', None) is not None:
        last.record['supplied'] = 'existential' if case == 'Dat' else 'copula'
    first = words[nominals[0]]
    if len(nominals) > 1 and _item(first)._ and _item(first)._[0][0] == 'Nom':
        first.topic = True
    return words[:k + 1] + [cop] + words[k + 1:]


def bare_objects(words):
    """動詞の直前の、格の接尾辞の無い名詞 (文の最初の名詞類でないもの) は不定の目的語 (ном өгсөн「本を与えた」)"""
    first = next((w for w in words if _pos(w) in ('noun', 'pronoun')), None)
    for i, w in enumerate(words[:-1]):
        nxt = next((x for x in words[i + 1:] if x.surface not in MONGOLIAN.negations), words[i + 1])
        item = _item(w)
        if item is None or item.pos != 'noun' or w is first or not item._ or item._[0][0] != 'Nom':
            continue
        if _pos(nxt) == 'verb' and not _item(nxt).attrib('copula') and not _item(nxt).attrib('existential') or \
                getattr(nxt, 'attributive', False):
            item._ = [('Acc',) + c[1:] for c in item._[:1]]
            if getattr(w, 'record', None) is not None:
                w.record['bare_object'] = True


def mark_topic(words):
    relatives = [k for k, w in enumerate(words) if getattr(w, 'relative_participle', False)]
    first_verb = next((k for k, w in enumerate(words) if _pos(w) == 'verb' and
                       not getattr(w, 'relative_participle', False)), len(words))
    start = max([k + 1 for k in relatives if k < first_verb], default=0)   # 名詞の前の関係節は飛ばす
    for w in words[start:]:
        if w.items is None and getattr(w, 'token_ix', 0) is None:
            continue
        if _pos(w) == 'verb' or w.items is None:
            return
        if _pos(w) in ('noun', 'pronoun'):
            if _item(w)._ and _item(w)._[0][0] == 'Nom':
                w.topic = True
            return


def lookup_all(surfaces):
    recs = records(surfaces)
    words = build_words(recs)
    global _display
    _display = list(words)
    bare_objects(words)
    words = mark_participles(words)
    words = supply_copula(words)
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
    with language.using(MONGOLIAN):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    from .literal import literal
    analysis.literal = literal(recs)
    return analysis


def analyze_text(text):
    from .script import from_latin
    text = from_latin(text)
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
