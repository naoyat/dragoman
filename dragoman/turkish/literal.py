#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# トルコ語の語順のままの日本語訳: 語ごとに、内容語の訳 + 格・所有の接尾辞の助詞 + 用言の語尾の日本語の形を当てて、
# トルコ語と同じ順に並べる (韓国語の korean/literal.py と同じ考え方)
#
#   Çocuk okulda kitap okudu.            → 子供が 学校で 本 読んだ。
#   Ali'nin okuduğu kitap güzeldi.       → アリが 読んだ 本が 美しかった。
#   Eve gelince yemek yedik.             → 家に 来ると 食事 食べた。
#
from dragoman.core.japanese import japanese_form, japanese_plain
from . import analyzer, morphology

PUNCTUATION = {'.': '。', ',': '、', '?': '？', '!': '！', ';': '、', ':': '：'}


def _first(ja):
    return (ja or '').split(',')[0]


def literal(recs):
    out = ''
    for k, rec in enumerate(recs):
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        text = _chunk(rec, nxt, recs[k - 1] if k else None)
        if not text:
            continue
        if text.startswith('ではな') and out.endswith('い') and prev_adjective(recs, k):
            out = out[:-1] + 'く' + text[2:]   # büyük değil「大きくない」
            continue
        if text in PUNCTUATION.values() or text in ('か', 'か？'):
            out += text
        else:
            out += (' ' if out else '') + text
    return out


def prev_adjective(recs, k):
    return k > 0 and recs[k - 1]['kind'] == 'adj' and recs[k - 1]['lemma'] not in ('var', 'yok')


def _chunk(rec, nxt, prev):
    kind = rec['kind']
    if kind == 'punct':
        return PUNCTUATION.get(rec['surface'], '')
    if kind == 'question':
        return 'か'
    if kind in ('noun', 'pronoun', 'nominalized'):
        return _noun(rec, nxt)
    if kind == 'adj':
        return _adjective(rec)
    if kind == 'det':
        lemma = rec['lemma']
        return morphology.NUMBERS.get(lemma, '') if lemma in morphology.NUMBERS and lemma != 'bir' else \
            _first(morphology.DETERMINERS.get(lemma, lemma))
    if kind == 'adv':
        if rec['lemma'] == 'değil':
            return 'ではない'
        ja, _, _ = morphology.gloss(rec['lemma'], 'adv')
        return _first(ja) or rec['surface']
    if kind == 'conj':
        lemma = rec['surface'].lower()
        if lemma == 'değil':
            return 'ではない'
        return _first(morphology.CONJUNCTIONS.get(lemma, lemma)).lstrip('〜')
    if kind == 'postposition':
        lemma = rec['surface'].lower()
        return _first(morphology.POSTPOSITIONS.get(lemma, ('〜' + lemma, None))[0]).lstrip('〜')
    if kind in ('verb', 'converb', 'participle'):
        return _verb(rec)
    if kind == 'article':
        return ''
    if kind == 'negcopula':
        past = rec.get('tense') in ('perfect', 'pluperfect')
        if rec.get('existential'):
            return 'いなかった' if past else 'いない'
        return 'ではなかった' if past else 'ではない'
    return rec['surface']


def _noun(rec, nxt):
    word = analyzer._noun_word(rec) if rec['kind'] != 'nominalized' else None
    if word is not None:
        ja = _first(word.items[0].ja)
    else:
        ja, gloss_lang, _ = analyzer._japanese_verb(rec)
        ja = japanese_plain(_first(ja), False, 'perfect' if rec['nominalizer'] == 'PastPart' else 'present',
                            rec.get('negated')) + morphology.NOMINALIZERS.get(rec['nominalizer'], 'こと')
    case = rec.get('role_case') or rec.get('case') or 'Nom'
    if rec.get('supplied') == 'existential':
        return ja + morphology.CASE_JA.get(case, '').replace('で', 'に') + ' ある'   # Kitap masada「本は 机に ある」
    if rec.get('supplied') == 'copula':
        return ja + 'だ'
    if rec.get('before_existential') and case == 'Loc':
        return ja + 'に'   # evde değildim「家に いなかった」
    if nxt is not None and nxt['kind'] == 'postposition':
        particle = ''   # 後置詞が後ろに (okul için「学校のために」)
        if nxt['surface'].lower() in ('için', 'gibi', 'kadar', 'hakkında') and case in ('Nom', 'Gen'):
            particle = 'の'
    elif case == 'Nom':
        particle = 'は' if rec.get('topic') else 'が'
    elif case == 'Gen' and nxt is not None and nxt['kind'] == 'participle':
        particle = 'が'   # 関係節の主語 (Ali'nin okuduğu「アリが 読んだ」)
    else:
        particle = morphology.CASE_JA.get(case, '')
    text = ja + particle
    if rec.get('predicate'):
        text = ja + _copula(rec['predicate'])
    return text


def _copula(features):
    past = features.get('tense') in ('perfect', 'pluperfect', 'imperfect')
    if features.get('negated'):
        return 'ではなかった' if past else 'ではない'
    return 'だった' if past else 'だ'


def _adjective(rec):
    lemma = rec['lemma']
    if lemma in ('var', 'yok'):
        features = rec.get('predicate') or {'tense': 'present'}
        past = features.get('tense') in ('perfect', 'pluperfect')
        if lemma == 'var':
            return 'あった' if past else 'ある'
        return 'なかった' if past else 'ない'
    ja, gloss_lang, _ = morphology.gloss(lemma, 'adj')
    ja = _first(ja) or lemma
    if rec.get('predicate'):
        features = rec['predicate']
        if ja.endswith('い') and gloss_lang == 'ja':
            return japanese_plain(ja, True, features.get('tense'), features.get('negated'))
        return ja + _copula(features)
    return ja


def _verb(rec):
    ja, gloss_lang, _ = analyzer._japanese_verb(rec)
    ja = _first(ja)
    if gloss_lang != 'ja':
        return '[%s]' % ja
    negated = rec.get('negated')
    tense = rec.get('tense', 'present')
    if rec.get('passive'):
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as Verb
        flag = Verb.INDICATIVE | Verb.PASSIVE | (Verb.PERFECT if tense in ('perfect', 'pluperfect') else 0)
        try:
            return JaVerb(ja).form(flag, negated)
        except Exception:
            return ja
    if rec['kind'] == 'converb':
        form, tail, _ = morphology.CONVERBS[rec['converb']]
        return japanese_form(ja, False, form, 'present', negated if form != 'neg' else False) + tail
    if rec['kind'] == 'participle':
        past = morphology.PARTICIPLES[rec['participle']] == 'past'
        return japanese_plain(ja, False, 'perfect' if past else 'present', negated)
    if rec.get('mood') == 'imperative':
        if rec.get('person') == 1:
            return japanese_form(ja, False, 'volitional', tense, negated)
        if negated:
            return ja + 'な'
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as Verb
        return JaVerb(ja).form(Verb.IMPERATIVE, False)
    if rec.get('conditional'):
        return japanese_plain(ja, False, tense, negated) + 'なら'
    if tense == 'progressive':
        return japanese_plain(japanese_form(ja, False, 'te', tense, negated) + 'いる', False, 'present', False)
    if tense == 'imperfect':
        return japanese_plain(japanese_form(ja, False, 'te', tense, negated) + 'いる', False, 'perfect', False)
    text = japanese_plain(ja, False, tense, negated)
    if rec.get('evidential') and tense == 'perfect':
        text += 'そうだ'
    return text
