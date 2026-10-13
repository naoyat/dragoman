#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# モンゴル語の語順のままの日本語訳: 語ごとに、内容語の訳 + 格の接尾辞の助詞 + 用言の語尾の日本語の形を当てて、
# モンゴル語と同じ順に並べる (韓国語・トルコ語と同じ考え方)
#
#   Хүү өчигдөр охинд ном өгсөн.      → 少年は 昨日 少女に 本を 与えた。
#   Би чамайг иртэл хүлээнэ.          → 私は 君を 来るまで 待つ。
#
from dragoman.core.japanese import japanese_form, japanese_plain
from . import analyzer, morphology

PUNCTUATION = {'.': '。', ',': '、', '?': '？', '!': '！', ';': '、', ':': '：'}


def _first(ja):
    return (ja or '').split(',')[0]


def literal(recs):
    out = ''
    subject = None
    for k, rec in enumerate(recs):
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        if rec['kind'] in ('noun', 'pronoun') and (rec.get('role_case') or rec.get('case')) == 'Nom':
            subject = rec
        if rec['kind'] == 'verb':
            rec['animate_subject'] = subject is None or subject['kind'] == 'pronoun' or subject['lemma'] in morphology.ANIMATE
        if rec['kind'] == 'verb' and k > 0 and recs[k - 1]['kind'] == 'adj':
            rec['after_adjective'] = True
        text = _chunk(rec, nxt)
        if not text:
            continue
        if text in PUNCTUATION.values() or text == 'か' or text.startswith(('ではな', 'こと', '時に', 'の')):
            out += text
        else:
            out += (' ' if out else '') + text
    return out


def _chunk(rec, nxt):
    kind = rec['kind']
    if kind == 'punct':
        return PUNCTUATION.get(rec['surface'], '')
    if kind in ('noun', 'pronoun'):
        return _noun(rec, nxt)
    if kind == 'adj':
        ja, _, _ = morphology.gloss(rec['lemma'], 'adj')
        ja = _first(ja) or rec['lemma']
        if rec.get('supplied') == 'copula':
            return ja if ja.endswith('い') else ja + 'だ'
        return ja
    if kind == 'det':
        return _first(morphology.DETERMINERS.get(rec['lemma'], rec['lemma']))
    if kind == 'adv':
        ja, _, _ = morphology.gloss(rec['lemma'], 'adv')
        return _first(ja) or rec['surface']
    if kind == 'conj':
        return _first(morphology.CONJUNCTIONS.get(rec['lemma'], rec['lemma'])).lstrip('〜')
    if kind == 'postposition':
        text = _first(morphology.POSTPOSITIONS.get(rec['lemma'], rec['lemma'])).lstrip('〜')
        if nxt is not None and nxt['kind'] == 'verb' and nxt['lemma'] == 'байх' and not nxt.get('aux') and text.endswith('で'):
            text = text[:-1] + 'に'   # 存在の場所 (ширээн дээр байна「机の上に ある」)
        return text
    if kind == 'negation':
        return 'ではない' if rec['lemma'] == 'биш' else _first(morphology.NEGATIONS.get(rec['lemma'], ''))
    if kind == 'particle':
        return 'か' if (rec.get('particle') or morphology.PARTICLES.get(rec['lemma'])) == 'question' else ''
    if kind == 'verb':
        return _verb(rec)
    return rec['surface']


def _noun(rec, nxt):
    word = analyzer._noun_word(rec)
    ja = _first(word.items[0].ja)
    case = rec.get('role_case') or rec.get('case') or 'Nom'
    if rec.get('supplied') == 'existential':
        return ja + 'に ある'
    if rec.get('supplied') == 'copula':
        return ja + 'だ'
    if nxt is not None and nxt['kind'] == 'postposition':
        return ja   # 後置詞の側で「の上で」…
    if nxt is not None and nxt['kind'] == 'negation' and nxt['lemma'] == 'биш':
        return ja
    if nxt is not None and nxt['kind'] == 'particle' and (nxt.get('particle') or morphology.PARTICLES.get(nxt['lemma'])) == 'topic':
        return ja + 'は'
    if rec.get('bare_object'):
        return ja + 'を'
    if case == 'Nom':
        if nxt is not None and nxt['kind'] == 'adj':
            return ja + 'が'
        return ja + ('は' if rec.get('topic') else 'が')
    if case == 'Gen' and nxt is not None and nxt['kind'] == 'verb' and nxt.get('attributive'):
        return ja + 'が'   # 関係節の主語 (Батын бичсэн「バトが 書いた」)
    return ja + morphology.CASE_JA.get(case, '')


def _verb(rec):
    ja, gloss_lang, _ = analyzer._japanese_verb(rec)
    if gloss_lang != 'ja':
        return '[%s]' % ja
    negated = rec.get('negated')
    tense = analyzer.TENSES.get(rec.get('tense'), 'present')
    if rec['lemma'] == 'байх' and not rec.get('aux'):
        ja = 'いる' if rec.get('animate_subject', True) else 'ある'
    if rec.get('case') and rec['lemma'] == 'байх' and rec.get('after_adjective'):
        return {'Acc': 'ことを', 'Dat': '時に', 'Abl': 'ことから'}.get(rec['case'], 'こと')   # хүйтэн байгааг「冷たいことを」
    if rec.get('case'):
        text = japanese_plain(ja, False, 'perfect' if rec.get('tense') == 'perfect' else 'present', negated)
        return text + ('時に' if rec['case'] == 'Dat' else 'ことを' if rec['case'] == 'Acc' else 'ことから'
                       if rec['case'] == 'Abl' else 'ことの' if rec['case'] == 'Gen' else 'こと')
    if rec.get('attributive'):
        return japanese_plain(ja, False, 'perfect' if rec.get('tense') == 'perfect' else 'present', negated)
    if rec['form'] == 'converb':
        form, tail, _ = morphology.CONVERBS.get(rec['converb'], ('te', '', ''))
        return japanese_form(ja, False, form, 'present', negated) + tail
    if rec['form'] == 'imperative':
        if rec.get('tense') == 'hortative':
            return japanese_form(ja, False, 'volitional', 'present', False)
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as Verb
        return JaVerb(ja).form(Verb.IMPERATIVE, False)
    if rec.get('aux') == 'progressive':
        return japanese_plain(ja, False, 'perfect' if rec.get('tense') == 'perfect' else 'present', negated)
    return japanese_plain(ja, False, tense, negated)
