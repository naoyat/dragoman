#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 韓国語の語順のままの日本語訳: 語節ごとに、内容語の訳 + 助詞・語尾の日本語の形を当てて、韓国語と同じ順に並べる
#
#   소년이 학교에서 책을 읽었다.        → 少年が 学校で 本を 読んだ。
#   비가 와서 집에 있었다.              → 雨が 降って 家に いた。
#   나는 어머니가 만든 음식을 먹었다.   → 私は 母が 作った 食べ物を 食べた。
#
# 語節の区切りは韓国語のまま (空白で区切る)。格の枠を組み立てる訳 (共通の解析器) と違い、語順も節のつながり
# (-고「〜て」・-지만「〜が」・-면「〜なら」…) も元の文のまま
#
from dragoman.core import verb_flags as Verb
from dragoman.core.japanese import JaVerb, copula_predicate
from . import analyzer, morphology

PUNCTUATION = {'.': '。', ',': '、', '?': '？', '!': '！'}
# 에서 を「から」と訳す移動の動詞 (일본에서 왔다「日本から来た」)
FROM_VERBS = {'오다', '떠나다', '출발하다', '나오다', '돌아오다', '나가다', '내리다', '도망치다', '오르다'}
CASE_JA = {'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の', 'Voc': 'よ'}
FOCUS_JA = {'topic': 'は', 'also': 'も', 'only': 'だけ'}
# 連結語尾 → (日本語の形の種類, 付ける語)
CONNECTIVE_FORMS = {'고': ('te', ''), '어서': ('te', ''), '서': ('te', ''), '어': ('te', ''), '지만': ('plain', 'が'),
                    '면': ('plain', 'なら'), '으면': ('plain', 'なら'), '니까': ('plain', 'から'), '으니까': ('plain', 'から'),
                    '니': ('plain', 'と'), '으니': ('plain', 'と'), '는데': ('plain', 'が'), '은데': ('plain', 'が'),
                    'ㄴ데': ('plain', 'が'), '면서': ('masu', 'ながら'), '으면서': ('masu', 'ながら'),
                    '려고': ('volitional', 'と'), '으려고': ('volitional', 'と'), '러': ('masu', 'に'), '으러': ('masu', 'に'),
                    '도록': ('plain', 'ように'), '다가': ('te', 'いて'), '거나': ('plain', 'か'), '어도': ('te', 'も'),
                    '더라도': ('te', 'も'), '게': ('plain', 'ように'), '자마자': ('plain', 'とすぐ'), '듯이': ('plain', 'ように')}


def literal(surfaces):
    """語節の列 → 語順のままの日本語 (語節ごとに空白で区切る)"""
    recs = analyzer.merge_auxiliaries(analyzer.apply_collocations(analyzer.records(surfaces)))
    chunks = {}
    order = []
    subject = None   # 節の主語 (있다 の「ある / いる」を選ぶ)
    for k, rec in enumerate(recs):
        nxt = recs[k + 1] if k + 1 < len(recs) else None
        if rec['kind'] == 'noun' and any(f in ('이', '가', '께서', '은', '는') for f, _ in rec['particles']):
            subject = rec
        if rec['kind'] == 'pred':
            rec['pred_after'] = None
            rec['animate_subject'] = subject is None or subject['tag'] == 'NP'
            if rec['ec'] or rec['etm']:
                subject = None
        if rec['kind'] == 'noun':
            rec['pred_after'] = next((r for r in recs[k + 1:] if r['kind'] == 'pred'), None)
        if rec['kind'] == 'negation' and nxt is not None and nxt['kind'] == 'pred':
            nxt['negated'] = True
            if rec['surface'] == '못':
                nxt['aux'] = nxt['aux'] + [('potential', 'ことができる', '못')]
            text = ''
        else:
            text = _chunk(rec, nxt)
        ix = rec['ix']
        if ix not in chunks:
            chunks[ix] = ''
            order.append(ix)
        chunks[ix] += text
    out = ''
    for ix in order:
        text = chunks[ix]
        if not text:
            continue
        if text in PUNCTUATION.values() or text.startswith('では'):
            out += text
        else:
            out += (' ' if out else '') + text
    return out


def _first(ja):
    return (ja or '').split(',')[0]


def _chunk(rec, nxt):
    kind = rec['kind']
    if kind == 'punct':
        return PUNCTUATION.get(rec['surface'], '')
    if kind in ('adv', 'conj', 'intj'):
        ja, _, _ = morphology.gloss(rec['lemma'], 'adv')
        return _first(ja) or rec['lemma']
    if kind == 'det':
        return morphology.DETERMINERS.get(rec['lemma'], rec['lemma'])
    if kind == 'noun':
        return _noun(rec, nxt)
    if kind == 'pred':
        return _predicate(rec)
    return ''


def _noun(rec, nxt):
    if not rec['particles'] and rec['lemma'] in morphology.TIME_NOUNS:
        ja, _, _ = morphology.gloss(rec['lemma'], 'noun')
        return _first(ja) or rec['lemma']
    word = analyzer._noun_word(rec)
    ja = _first(word.items[0].ja)
    case, prep, focus, conj, complement = None, None, None, None, False
    for form, tag in rec['particles']:
        if tag == 'JC':
            conj = form
        elif tag == 'JKC':
            complement = True
        elif form in morphology.CASE_PARTICLES and tag in ('JKS', 'JKO', 'JKG', 'JKV', 'JKB'):
            case = morphology.CASE_PARTICLES[form]
        elif form in morphology.POSTPOSITIONS and tag in ('JKB', 'JX'):
            prep = prep or form
        elif form in morphology.FOCUS_PARTICLES:
            focus = morphology.FOCUS_PARTICLES[form] or focus
    if conj:
        return ja + 'と'
    if complement:
        if nxt is not None and nxt['kind'] == 'pred' and nxt['tag'] == 'VCN':
            return ja   # 〜ではない (아니다 の側で)
        return ja + 'に'   # 되다「〜になる」
    if nxt is not None and nxt['kind'] == 'pred' and nxt['lemma'] == '이다' and nxt['ix'] == rec['ix']:
        return ja   # 학생입니다: 繋辞は後ろで (学生だ)
    particle = ''
    if prep:
        particle = _first(morphology.POSTPOSITIONS[prep]).lstrip('〜')
        pred = rec.get('pred_after')
        if prep == '에서' and pred is not None and pred['lemma'] in FROM_VERBS:
            particle = 'から'
    elif case:
        particle = CASE_JA.get(case, '')
    if focus:
        if particle in ('が', 'を'):
            particle = ''
        particle += FOCUS_JA[focus]
    if not particle and not rec['particles'] and nxt is not None and nxt['kind'] == 'noun' and nxt['ix'] != rec['ix']:
        particle = 'の'   # 한국 음식「韓国の食べ物」
    return ja + particle


def _tense(rec):
    return analyzer._tense(rec)


def _predicate(rec):
    tense = _tense(rec)
    negated = rec['negated']
    if rec['lemma'] == '이다' or rec['tag'] == 'VCN':
        base = _copula(tense, negated or rec['tag'] == 'VCN')
        return base + _ending_tail(rec, None)
    ja, gloss_lang, _ = analyzer._japanese_verb(rec)
    ja = _first(ja)
    if rec['lemma'] == '있다' and not rec['aux'] and ja == 'ある' and rec.get('animate_subject'):
        ja = 'いる'
    if gloss_lang != 'ja':
        return '[%s]' % ja
    adjective = rec['tag'] == 'VA' and rec['lemma'] not in analyzer.EXISTENTIALS or rec['lemma'] == '없다'
    if rec['etn']:
        return _plain(ja, adjective, 'present', negated) + 'こと' + _particles_after_nominal(rec)
    if rec['etm']:
        past = rec['etm'] in ('ㄴ', '은') and not adjective
        return _plain(ja, adjective, 'perfect' if past or tense == 'perfect' else 'present', negated)
    if rec['ec'] and rec['ec'] in CONNECTIVE_FORMS:
        form, tail = CONNECTIVE_FORMS[rec['ec']]
        return _form(ja, adjective, form, tense, negated) + tail
    if analyzer._mood(rec) == 'imperative':
        if rec['ef'] in morphology.HORTATIVE_ENDINGS:
            return _form(ja, adjective, 'volitional', tense, negated)
        if negated:
            return ja + 'な'
        return JaVerb(ja).form(Verb.IMPERATIVE, False)
    return _plain(ja, adjective, tense, negated)


def _copula(tense, negated):
    past = tense in ('perfect', 'pluperfect')
    if negated:
        return 'ではなかった' if past else 'ではない'
    return 'だった' if past else 'だろう' if tense == 'future' else 'だ'


def _ending_tail(rec, _):
    if rec['ec'] in CONNECTIVE_FORMS:
        return CONNECTIVE_FORMS[rec['ec']][1] if CONNECTIVE_FORMS[rec['ec']][0] != 'te' else ''
    return ''


def _plain(ja, adjective, tense, negated):
    if adjective:
        return copula_predicate(ja, True, 'past' if tense in ('perfect', 'pluperfect') else 'present', negated)
    flag = Verb.INDICATIVE
    if tense in ('perfect', 'pluperfect'):
        flag |= Verb.PERFECT
    elif tense == 'future':
        flag |= Verb.FUTURE
    try:
        return JaVerb(ja).form(flag, negated)
    except Exception:
        return ja


def _form(ja, adjective, form, tense, negated):
    from dragoman.kobun.modernize import Modern
    try:
        if form == 'plain':
            return _plain(ja, adjective, tense, negated)
        if form == 'te':
            if adjective:
                return ja[:-1] + ('くなくて' if negated else 'くて') if ja.endswith('い') else ja + 'で'
            return Modern.neg_stem(ja) + 'ないで' if negated else Modern.te(ja)
        if form == 'masu':
            return Modern.masu_stem(ja)
        if form == 'volitional':
            return Modern.volitional(ja)
    except Exception:
        pass
    return ja


def _particles_after_nominal(rec):
    out = ''
    for form, tag in rec['particles']:
        if form in morphology.CASE_PARTICLES:
            out += CASE_JA.get(morphology.CASE_PARTICLES[form], '')
        elif form in morphology.FOCUS_PARTICLES and morphology.FOCUS_PARTICLES[form]:
            out += FOCUS_JA[morphology.FOCUS_PARTICLES[form]]
    return out
