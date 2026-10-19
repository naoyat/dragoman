#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の文の解析
#
# 品詞を決める解析器 (spaCy など) は無いので、ラテン語・ギリシア語と同じく語ごとに辞書のすべての読み (格・数・性、
# 法・時制・人称・数) を並べ、並列・係り先・格の枠・日本語訳は共通の解析器 (core/analyzer.py) を古英語の設定
# (OLD_ENGLISH) で使う:
#   - 語形は Wiktionary の変化表 (oldenglish/dictionary.py)。綴りは長音符・点を除き ð = þ で引き、辞書に無い綴りは
#     綴りの揺れ (hyran = hieran、mon = man …。oldenglish/orthography.py) で引き直す
#   - 格は主格「が」・対格「を」・属格「の」・与格「に」・具格「で」。前置詞は後ろの語の格で訳を選ぶ (on + 与格
#     「〜で」、on + 対格「〜へ」)
#   - sē・sēo・þæt (冠詞「その」) は後ろの一致する名詞に掛けて訳さず、名詞の格を絞る。名詞が無ければ指示代名詞
#     「その人・それ」。þes「この」も同じ
#   - 話法の動詞 (sculan・magan・cunnan・willan・mōtan) + 不定詞「〜なければならない・〜できる・〜たい」、habban +
#     過去分詞は完了、bēon / wesan / weorþan + 過去分詞は受動 (移動・変化の動詞は完了)。間に語があってもよい
#     (Hē hæfde þone cyning ġesewen)
#   - 否定は ne (と縮約: nis = ne is、nolde = ne wolde)、nā・nǣfre、否定の代名詞 nān
#   - 関係の小辞 þe と、se þe「〜する人」は関係代名詞
#
import re
import unicodedata

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, orthography

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', ';': 'comma', ',': 'comma', ':': 'comma', '·': 'comma',
               '—': 'comma', '–': 'comma', '(': 'comma', ')': 'comma', '"': None, '“': None, '”': None, "'": None}
LETTER = "A-Za-zÀ-ÿĀ-žǢǣǼǽȲȳĠġĊċÞþÐðƿǷꝥ̀-ͯ"
TOKEN = re.compile(r"[%s]+(?:-[%s]+)*|[⁊&]|\d+|[.!?;,:·—–()\"“”']" % (LETTER, LETTER))
ARTICLE_WINDOW = 3   # 冠詞と名詞の間に入りうる語の数 (se gōda cyning、þæs ēadigan cyninges)
CLAUSE_WINDOW = 8    # 助動詞と本動詞の間に入りうる語の数


def _root_items(lemma):
    rows = dictionary.lemmas(lemma, 'verb')
    if not rows:
        return []
    ja, gloss_lang = _gloss(rows[0], 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}]


OLD_ENGLISH = language.Language(
    name='ang',
    and_words=('and',),
    or_words=('oþþe',),
    copulas=frozenset({'wesan', 'bēon'}),
    negations=frozenset({'ne', 'na', 'no', 'næfre', 'nā', 'nō', 'nǣfre', '(ne)'}),
    vocative_particles=frozenset({'eala', 'ēalā'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Gen': 'の', 'Dat': 'に', 'Ins': 'で', 'Voc': 'よ'},
    absolute_case=None,   # 独立与格はまれ (ラテン語の独立奪格の訳)
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    objects_follow_verb=True,
    genitive_precedes_head=True,   # 属格はふつう名詞の前 (þæs cyninges sunu「王の息子」)
)


def tokens(text):
    return TOKEN.findall(unicodedata.normalize('NFC', text))


def sentences(text):
    current = []
    for token in tokens(text):
        current.append(token)
        if PUNCTUATION.get(token) in ('period', 'question'):
            yield current
            current = []
    if current:
        yield current


# ----------------------------------------------------------------------
# 語の読み

def _gloss(info, pos):
    from dragoman.core import en_ja
    hand = morphology.gloss(info['base'], pos)
    if hand:
        return hand, 'ja'
    en = info.get('en') or ''
    if info.get('proper'):
        return _katakana(info['base']), 'ja'
    ja = en_ja.translate(en, pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2) if en else None
    return (ja, 'ja') if ja else (en or info['base'], 'en')


def _katakana(name):
    """古英語の名前をカタカナに (発音から: Ælfrēd → アルフレード、Ēadweard → エーアドウェアルド)"""
    from .phonology import katakana
    return katakana(name)


def _signature(item):
    return tuple(sorted((k, str(v)) for k, v in item.items() if k not in ('surface', 'en', 'senses', 'id')))


def _item(info, feats, surface):
    pos = info['pos']
    item = {'surface': surface, 'pos': pos, 'base': info['base'], 'lemma': info['base'],
            'spelling': feats.get('surface') or surface}   # 辞書の綴り (長音符付き。音読で母音の長さに)
    if pos in ('adv', 'conj', 'indecl'):
        item['compact'] = True
    if pos == 'verb':
        item.update(pres1sg=info['base'], voice='active', mood=feats.get('mood', 'indicative'),
                    tense=feats.get('tense', 'present'))
        if 'person' in feats:
            item.update(person=feats['person'], number=feats['number'])
        if item['mood'] == 'participle':
            item.update(pos='participle', _=[(c, n, g) for c in ('Nom', 'Acc') for n in ('sg', 'pl')
                                              for g in morphology.ALL_GENDERS])
        if base_key(info) in morphology.COPULAS:
            item['existential'] = True
    elif pos in ('noun', 'adj', 'pronoun', 'article'):
        item['_'] = [tuple(x) for x in feats.get('_', [])]
        if info.get('proper'):
            item['proper'] = True
        if pos == 'article':
            item.update(ja='', gloss_lang='ja', compact=True)
            return item
    elif pos == 'preposition':
        return None   # 前置詞は手で書いた表 (morphology.PREPOSITIONS) から
    rank = feats.get('rank') or info.get('rank')
    if pos == 'adj' and rank:
        # 比較級・最上級「より〜・最も〜」(strengra ← strang、betera ← gōd)。訳は原級の訳から
        positive = info.get('positive')
        source = (dictionary.lemmas(positive, 'adj') or [info])[0] if positive else info
        ja, gloss_lang = _gloss(source, 'adj')
        if gloss_lang == 'ja':
            ja = ','.join(('より' if rank == '+' else '最も') + j for j in ja.split(',')[:2])
        item.update(ja=ja, gloss_lang=gloss_lang, rank=rank,
                    form='%s (%s)' % ('比較級' if rank == '+' else '最上級', source['base']))
        return item
    if pos == 'adj' and feats.get('decl'):
        item['form'] = '・'.join({'strong': '強変化', 'weak': '弱変化'}[d] for d in feats['decl'].split(','))
    ja, gloss_lang = _gloss(info, 'verb' if pos in ('verb', 'participle') else pos)
    item.update(ja=ja, gloss_lang=gloss_lang)
    if item['pos'] == 'participle':
        item['ja'] = ja if item['tense'] == 'present' else ja   # 分詞の訳は共通の解析器が時制で直す
    return item


def base_key(info):
    return orthography.key(info.get('base') or '')


MAX_LEMMAS_PER_POS = 2


def dictionary_items(surface):
    """辞書の読み → 項目のリスト (同じ品詞の見出しは語義の多い2つまで。手で訳を決めた見出しを先に)"""
    pairs = dictionary.forms(surface)
    variant = None
    if not pairs:
        variant, pairs = dictionary.variant_forms(surface)
    by_pos = {}
    for info, feats in pairs:
        by_pos.setdefault(info['pos'], []).append((info, feats))
    items, seen = [], set()
    for pos, group in by_pos.items():
        ids = []
        for info, _ in sorted(group, key=lambda p: (morphology.gloss(p[0]['base'], _gloss_pos(pos)) is None,
                                                       -(p[0].get('senses') or 0))):
            if info['id'] not in ids:
                ids.append(info['id'])
        keep = ids[:MAX_LEMMAS_PER_POS]
        for info, feats in sorted(group, key=lambda p: keep.index(p[0]['id']) if p[0]['id'] in keep else 99):
            if info['id'] not in keep:
                continue
            item = _item(info, feats, surface)
            if item is None or _signature(item) in seen:
                continue
            seen.add(_signature(item))
            if variant:
                item['variant'] = variant
            items.append(item)
    if surface[:1].isupper():   # 大文字の語は固有名詞の読みを先に (God「神」を gōd「良い・財産」より)
        items.sort(key=lambda i: not i.get('proper'))
    else:   # 小文字の語は固有名詞の読みを後に (gold「金」を Gold より)
        items.sort(key=lambda i: bool(i.get('proper')))
    return sorted(items, key=_reading_order)


def _reading_order(item):
    """動詞の読みは直説法・3人称を先に (主語が名詞の文の既定)"""
    if item['pos'] != 'verb':
        return (0, 0)
    return (('indicative', 'subjunctive', 'imperative', 'infinitive').index(item['mood'])
            if item['mood'] in ('indicative', 'subjunctive', 'imperative', 'infinitive') else 4,
            {3: 0, 1: 1, 2: 2}.get(item.get('person'), 3))


def _gloss_pos(pos):
    return 'verb' if pos in ('verb', 'participle') else pos


# 語尾 → (不定詞の語尾の候補, 法, 時制, 人称, 数)。辞書に無い動詞の形を、語尾を外して不定詞で引き直す
VERB_ENDINGS = (
    ('odon', ('ian',), 'indicative', 'perfect', None, 'pl'), ('edon', ('an', 'ian'), 'indicative', 'perfect', None, 'pl'),
    ('don', ('an',), 'indicative', 'perfect', None, 'pl'), ('ton', ('an',), 'indicative', 'perfect', None, 'pl'),
    ('ode', ('ian',), 'indicative', 'perfect', 3, 'sg'), ('ede', ('an', 'ian'), 'indicative', 'perfect', 3, 'sg'),
    ('de', ('an',), 'indicative', 'perfect', 3, 'sg'), ('te', ('an',), 'indicative', 'perfect', 3, 'sg'),
    ('iaþ', ('ian',), 'indicative', 'present', None, 'pl'), ('aþ', ('ian', 'an'), 'indicative', 'present', 3, 'sg'),
    ('eþ', ('an',), 'indicative', 'present', 3, 'sg'), ('þ', ('an',), 'indicative', 'present', 3, 'sg'),
    ('ian', ('ian',), 'infinitive', 'present', None, None), ('an', ('an',), 'infinitive', 'present', None, None),
    ('od', ('ian',), 'participle', 'past', None, None), ('ed', ('an',), 'participle', 'past', None, None),
    ('e', ('an',), 'subjunctive', 'present', None, 'sg'),   # 接続法単数 (tōbecume「来ますように」)
)


def guess_compound(surface):
    """辞書に無い語を複合語と推定する (leorningcnihtas → leorning + cnihtas、ceasterwaru → ceaster + waru):
    後ろの要素 (3字以上で、名詞・形容詞の読みのあるもの) の格・数・性を使う。長い後ろの要素から"""
    k = orthography.key(surface)
    for cut in range(3, len(k) - 3):   # 前の要素は3字以上、後ろの要素は4字以上
        head = k[cut:]
        items = [i for i in dictionary_items(head) if i['pos'] in ('noun', 'adj')]
        if items:
            first = k[:cut]
            out = []
            for i in items:
                out.append(dict(i, surface=surface, base='%s-%s' % (first, i['base']), lemma='%s-%s' % (first, i['base']),
                                guessed='複合語 %s + %s' % (first, i['base'])))
            return out
    return []


# 動詞の接頭辞 (辞書に無い動詞を、接頭辞を外して引き直す: tōbecuman → becuman)
VERB_PREFIXES = ('to', 'be', 'bi', 'a', 'for', 'of', 'on', 'ofer', 'under', 'wiþ', 'ymb', 'ut', 'up', 'forþ', 'æt',
                 'geond', 'þurh', 'mis', 'oþ', 'ed', 'ge')


def guess_verb(surface):
    """辞書に無い語を動詞の形と推定する (gyrnde → girnan の過去、oferhogodon → oferhogian の過去複数)。
    語尾を外し、不定詞 (〜an・〜ian) を辞書で (綴りの揺れも) 引く。ge- の有無も試す"""
    k = orthography.key(surface)
    for ending, infinitives, mood, tense, person, number in VERB_ENDINGS:
        if not k.endswith(ending) or len(k) - len(ending) < 2:
            continue
        stem = k[:-len(ending)]
        stems = [stem, stem[2:] if stem.startswith('ge') else 'ge' + stem]
        stems += [stem[len(p):] for p in VERB_PREFIXES if stem.startswith(p) and len(stem) - len(p) >= 3]
        for st in dict.fromkeys(stems):
            prefix = stem[:len(stem) - len(st)] if stem.endswith(st) and st != stem else ''
            for inf in infinitives:
                rows = dictionary.lemmas(st + inf, 'verb')
                if not rows:
                    v, found = dictionary.variant_forms(st + inf)
                    rows = [info for info, feats in found if info['pos'] == 'verb' and feats.get('mood') == 'infinitive']
                if not rows:
                    continue
                info = rows[0]
                feats = {'mood': mood, 'tense': tense}
                persons = [person] if person else ([1, 2, 3] if number else [None])
                items = []
                for p in persons:
                    f = dict(feats, person=p, number=number) if number else feats
                    item = dict(_item(info, f, surface), guessed='%s の %s' % (info['base'], ending))
                    if prefix and not prefix.startswith('ge'):   # 接頭辞を外して引いた語 (tō + becuman): 訳は外した語の
                        item.update(base=prefix + '-' + info['base'], lemma=prefix + '-' + info['base'],
                                    pres1sg=prefix + '-' + info['base'])
                    items.append(item)
                return sorted(items, key=_reading_order)
    return []


# 人称代名詞の主格の鍵 (文の枠の見出し: frame.SOURCE_PRONOUNS['ang'])
NOMINATIVE = {'私': 'ic', '君': 'þu', '彼': 'he', '彼女': 'heo', 'それ': 'hit', '私たち': 'we', '君たち': 'ge', '彼ら': 'hie',
              '誰': 'hwa', '何': 'hwæt'}


def _pronoun_items(k, surface):
    return [{'surface': surface, 'pos': 'pronoun', 'base': surface, 'lemma': NOMINATIVE.get(ja, k), 'ja': ja,
             'gloss_lang': 'ja', 'person': person, 'number': number, '_': list(cng), 'compact': True}
            for ja, person, number, cng in morphology.PRONOUNS[k]]


def _demonstrative_items(k, surface):
    """sē・þes の形: 冠詞 (訳さない) / 「この」と、指示代名詞「その人・それ」/「これ」"""
    if k in morphology.SE_FORMS:
        cng = morphology.SE_FORMS[k]
        items = [{'surface': surface, 'pos': 'article', 'base': 'sē', 'ja': '', 'gloss_lang': 'ja', '_': list(cng),
                  'compact': True}]
        ja, base = 'それ', 'sē'
    else:
        cng = morphology.THES_FORMS[k]
        items = [{'surface': surface, 'pos': 'adj', 'base': 'þes', 'ja': 'この', 'gloss_lang': 'ja', '_': list(cng),
                  'demonstrative': True}]
        ja, base = 'これ', 'þes'
    if k == 'þæt':
        items.append({'surface': surface, 'pos': 'conj', 'base': 'þæt', 'ja': '〜ということ', 'gloss_lang': 'ja',
                      'complementizer': True})
    for c, n, g in cng:
        person_ja = ja if g == 'n' else ('彼ら' if n == 'pl' else '彼女' if g == 'f' else '彼')
        items.append({'surface': surface, 'pos': 'pronoun', 'base': base, 'ja': person_ja, 'gloss_lang': 'ja',
                      'person': 3, 'number': n, '_': [(c, n, g)], 'desc': '指示代名詞', 'compact': True})
    return items


VERB_FUNCTION_WORDS = {'for'}
# 冠詞を掛けない語: よく使う動詞の形 (þæt is「それは〜である」の is を īs「氷」と読まない)
COMMON_VERBS = {'wesan', 'beon', 'habban', 'weorþan', 'cweþan', 'secgan', 'don', 'gan', 'cuman'} | set(morphology.MODALS)


LATE_ENDINGS = re.compile('(?:ie|ien|iende)$')


def word_items(surface, first=False, following=None):
    """表層形 → 項目のリスト"""
    k = orthography.key(surface)
    items = []
    if k in morphology.NEGATIVE_CONTRACTIONS:   # nis = ne is
        inner = [dict(i, surface=surface, negated=True) for i in word_items(morphology.NEGATIVE_CONTRACTIONS[k])
                 if i['pos'] in ('verb', 'adj', 'pronoun')]
        if inner:
            return inner
    if k == 'hwæt' and following in PUNCTUATION:   # Hwæt!「さあ聞け」(ベーオウルフの冒頭)
        return [{'surface': surface, 'pos': 'adv', 'base': 'hwæt', 'ja': 'さあ聞け', 'gloss_lang': 'ja'}]
    if k in morphology.NEGATIONS:
        return [{'surface': surface, 'pos': 'adv', 'base': surface, 'ja': morphology.ADVERBS[k], 'gloss_lang': 'ja',
                 'negation': True}]
    if k in morphology.PREPOSITIONS:
        items += [{'surface': surface, 'pos': 'preposition', 'base': surface, 'dominates': case, 'ja': ja,
                   'gloss_lang': 'ja'} for case, ja in morphology.PREPOSITIONS[k]]
    if k in morphology.PRONOUNS:
        items += _pronoun_items(k, surface)
    if k in morphology.POSSESSIVE_GENITIVES:
        items.append({'surface': surface, 'pos': 'adj', 'base': surface, 'lemma': k, 'ja': morphology.POSSESSIVE_GENITIVES[k],
                      'gloss_lang': 'ja', '_': [(c, n, g) for c in ('Nom', 'Acc', 'Gen', 'Dat', 'Ins')
                                                 for n in ('sg', 'pl') for g in morphology.ALL_GENDERS],
                      'possessive': True})
    if k in morphology.POSSESSIVES:   # 所有の形容詞の基本の形 (ūre・þīn。変化した形は辞書から)
        items.append({'surface': surface, 'pos': 'adj', 'base': surface, 'lemma': k, 'ja': morphology.POSSESSIVES[k],
                      'gloss_lang': 'ja', '_': [(c, n, g) for c in ('Nom', 'Acc') for n in ('sg', 'pl')
                                                 for g in morphology.ALL_GENDERS], 'possessive': True})
    if k in morphology.SE_FORMS or k in morphology.THES_FORMS:
        items += _demonstrative_items(k, surface)
    if k in morphology.CONJUNCTIONS and k not in ('þa', 'þonne', 'nu', 'eac'):
        items.append({'surface': surface, 'pos': 'conj', 'base': surface, 'ja': morphology.CONJUNCTIONS[k],
                      'gloss_lang': 'ja'})
    if k in morphology.ADVERBS:
        items.append({'surface': surface, 'pos': 'adv', 'base': surface, 'ja': morphology.ADVERBS[k],
                      'gloss_lang': 'ja'})
    if k in morphology.NEGATIVE_WORDS:
        items.append({'surface': surface, 'pos': 'adj', 'base': surface, 'ja': morphology.NEGATIVE_WORDS[k],
                      'gloss_lang': 'ja', 'negation': True,
                      '_': [(c, n, g) for c in ('Nom', 'Acc', 'Dat') for n in ('sg',) for g in morphology.ALL_GENDERS]})
    if k in VERB_FUNCTION_WORDS:   # fōr「行った」(faran の過去) は前置詞 for と同じ綴り (Hēr fōr se here)
        items += [i for i in dictionary_items(surface) if i['pos'] == 'verb']
    if items:
        return items   # 機能語は辞書の読み (まれな名詞・動詞の読み) を足さない
    if ROMAN_NUMERAL.match(k) and len(k) > 1 or k.isdigit():   # 数詞 (dccc monna「800人」)
        return [{'surface': surface, 'pos': 'adj', 'base': surface, 'ja': surface.upper() if not k.isdigit() else k,
                 'gloss_lang': 'ja', '_': [(c, n, g) for c in ('Nom', 'Acc', 'Gen', 'Dat') for n in ('pl',)
                                            for g in morphology.ALL_GENDERS], 'numeral': True}]
    late = LATE_ENDINGS.sub(lambda m: {'ie': 'ige', 'ien': 'igen', 'iende': 'igende'}[m.group(0)], k)
    if late != k:   # 後期の綴り -ie = -iġe (lufie = lufiġe「私は愛する」。lufu「愛」の形でもある)
        extra = [i for i in dictionary_items(late) if i['pos'] == 'verb']
        if extra:
            return sorted(dictionary_items(surface) + [dict(i, surface=surface) for i in extra], key=_reading_order)
    items = dictionary_items(surface) or guess_verb(surface) or \
        (guess_compound(surface) if not surface[:1].isupper() else [])
    if k in morphology.SPELLINGS:
        items = dictionary_items(morphology.SPELLINGS[k]) + items
    for item in items:
        if item['pos'] in ('pronoun', 'adj') and orthography.key(item['base']) in morphology.POSSESSIVES:
            item.update(ja=morphology.POSSESSIVES[orthography.key(item['base'])], gloss_lang='ja', pos='adj')
    if surface[:1].isupper() and not first and not any(i.get('proper') for i in items):
        name = {'surface': surface, 'pos': 'noun', 'base': surface, 'ja': _katakana(surface), 'gloss_lang': 'ja',
                'proper': True, '_': [(c, 'sg', g) for c in ('Nom', 'Acc', 'Gen', 'Dat') for g in ('m', 'f')]}
        return [name] + [i for i in items if i['pos'] not in ('noun',)] if not items else items + [name]
    if not items and surface[:1].isupper():
        return [{'surface': surface, 'pos': 'noun', 'base': surface, 'ja': _katakana(surface), 'gloss_lang': 'ja',
                 'proper': True, '_': [(c, 'sg', g) for c in ('Nom', 'Acc', 'Gen', 'Dat') for g in ('m', 'f')]}]
    return items


# ----------------------------------------------------------------------
# 語の列の手直し

def _boundary(items):
    """節の切れ目 (句読点・接続詞)"""
    return items is None or any(i['pos'] == 'conj' for i in items) and all(i['pos'] in ('conj', 'adv') for i in items)


def _finite(items, lemmas):
    return [i for i in items or [] if i['pos'] == 'verb' and orthography.key(i['base']) in lemmas
            and i['mood'] in ('indicative', 'subjunctive', 'imperative')]


def merge_verbs(readings, trace):
    """助動詞と本動詞を助動詞の位置の1語にまとめる: 話法の動詞 + 不定詞、habban + 過去分詞 (完了)、
    bēon / wesan / weorþan + 過去分詞 (受動。移動・変化の自動詞は完了)"""
    from dragoman.core.japanese import attach_auxiliary
    removed = {}   # 本動詞の位置 → 助動詞の位置
    for i, items in enumerate(readings):
        modal = _finite(items, morphology.MODALS)
        perfect = _finite(items, morphology.PERFECT_AUXILIARIES)
        passive = _finite(items, morphology.PASSIVE_AUXILIARIES)
        if not (modal or perfect or passive):
            continue
        want = 'infinitive' if modal else 'participle'
        main_ix = _find_main(readings, i, want, removed)
        if main_ix is None:
            continue
        main = _main_readings(readings[main_ix], want)[0]
        aux_items = modal or perfect or passive
        merged = []
        for a in aux_items:
            data = dict(main, pos='verb', surface='%s … %s' % (a['surface'], main['surface']), person=a.get('person'),
                        number=a.get('number'), mood=a['mood'], tense=a['tense'], negated=a.get('negated'))
            data.pop('_', None)
            data.pop('existential', None)
            aux = orthography.key(a['base'])
            if modal:
                suffix = morphology.MODALS[aux]
                if main.get('gloss_lang') == 'ja':
                    data['ja'] = attach_auxiliary(main['ja'].split(',')[0], suffix)
                data.update(modal=a['base'], main_ja=main['ja'], form='話法の動詞 %s + 不定詞' % a['base'])
            elif perfect or orthography.key(main['base']) in INTRANSITIVE_PERFECT:
                data['tense'] = 'pluperfect' if a['tense'] == 'perfect' else 'perfect'
                data['form'] = '%s (%s + 過去分詞)' % ('過去完了' if a['tense'] == 'perfect' else '完了', a['base'])
            else:
                data['voice'] = 'passive'
                data['form'] = '受動 (%s + 過去分詞)' % a['base']
            merged.append(data)
        seen, unique = set(), []
        for m in merged:
            sig = tuple(x for x in _signature(m) if x[0] != 'form')
            if sig not in seen:
                seen.add(sig)
                unique.append(m)
        readings[i] = unique
        removed[main_ix] = i
        trace.append('// VERB #%d + #%d' % (i, main_ix))
    return removed


def _main_readings(r, want):
    if want == 'infinitive':
        return [x for x in r or [] if x['pos'] == 'verb' and x['mood'] == 'infinitive']
    return [x for x in r or [] if x['pos'] == 'participle' and x['tense'] == 'past']


def _find_main(readings, i, want, removed):
    """助動詞 i の本動詞 (不定詞・過去分詞): 後ろを節の切れ目・別の定動詞まで、無ければ前を3語まで"""
    for j in range(i + 1, min(len(readings), i + 1 + CLAUSE_WINDOW)):
        r = readings[j]
        if _boundary(r):
            break
        if j not in removed and _main_readings(r, want):
            return j
        if r and all(x['pos'] == 'verb' and x['mood'] in ('indicative', 'subjunctive') for x in r):
            break
    for j in range(i - 1, max(-1, i - 4), -1):
        r = readings[j]
        if _boundary(r):
            break
        if j not in removed and _main_readings(r, want):
            return j
    return None


# 完了を bēon / wesan で作る移動・変化の自動詞 (hē wæs ġecumen「彼は来ていた」)
INTRANSITIVE_PERFECT = {'cuman', 'gan', 'faran', 'feran', 'weorþan', 'gewitan', 'aweorþan', 'fleon', 'sweltan',
                        'astigan', 'feallan', 'becuman', 'gecuman', 'gefaran', 'ferian', 'ridan'}


SUBJECT_PRONOUNS = {'he', 'heo', 'hie', 'hi', 'hy', 'we', 'ic', 'þu', 'ge', 'hit', 'mon', 'man'}
ROMAN_NUMERAL = re.compile('^[mdclxvi]+$')


def comparisons(readings, surfaces):
    """比較の þonne「〜より」: 比較級の後ろ (4語まで) の þonne は、後ろの語を比べる相手にする前置詞のように
    (Hē is betera þonne his brōþor「彼は兄弟より良い」)。比較級の訳の「より」は外す"""
    for i, s in enumerate(surfaces):
        if orthography.key(s) != 'þonne':
            continue
        for j in range(max(0, i - 4), i):
            comparative = [r for r in readings[j] or [] if r.get('rank') == '+']
            if comparative:
                readings[i] = [{'surface': s, 'pos': 'preposition', 'base': 'þonne', 'dominates': c, 'ja': '〜より',
                                'gloss_lang': 'ja'} for c in ('Nom', 'Acc', 'Dat')]
                for r in comparative:
                    r['ja'] = ','.join(x[2:] if x.startswith('より') else x for x in r['ja'].split(','))
                break


def fix_function_words(readings, surfaces):
    """þā þā / þā ðā「〜した時」、þæt þæt (補文の þæt + 冠詞)、þæt + 定動詞 (þæt is「それは〜」) の読み分け"""
    keys = [orthography.key(s) for s in surfaces]
    removed = set()
    # 相関の þā … þā (Þā hē þæt hīerde, þā fērde hē「彼がそれを聞いた時、その時彼は行った」): 文頭の þā の後ろに、
    # 動詞の読みのある語を挟んでもう一度 þā があれば、最初の þā は「〜した時」
    if keys and keys[0] == 'þa' and (len(keys) < 2 or keys[1] != 'þa'):
        later = [j for j in range(2, len(keys)) if keys[j] == 'þa' and
                 any(r['pos'] == 'verb' for k2 in range(1, j) for r in readings[k2] or [])]
        if later:
            readings[0] = [{'surface': surfaces[0], 'pos': 'conj', 'base': 'þā', 'ja': '〜した時', 'gloss_lang': 'ja'}]
    for i, k in enumerate(keys):
        nxt = keys[i + 1] if i + 1 < len(keys) else None
        if k == 'þa' and nxt == 'þa':
            readings[i] = [{'surface': surfaces[i] + ' ' + surfaces[i + 1], 'pos': 'conj', 'base': 'þā þā',
                            'ja': '〜した時', 'gloss_lang': 'ja'}]
            removed.add(i + 1)
        elif k == 'þæt' and nxt == 'þæt' and readings[i]:
            readings[i] = [r for r in readings[i] if r['pos'] == 'conj']
        elif k == 'þæt' and i > 0 and keys[i - 1] in SUBJECT_PRONOUNS and readings[i] and \
                any(r['pos'] == 'pronoun' for r in readings[i]):
            readings[i] = [r for r in readings[i] if r['pos'] == 'pronoun']   # hē þæt hīerde「彼はそれを聞いた」
        elif k == 'þæt' and readings[i] and readings[i + 1 if nxt else i] and nxt and \
                all(r['pos'] == 'verb' and r['mood'] in FINITE_MOODS for r in readings[i + 1]):
            readings[i] = [r for r in readings[i] if r['pos'] == 'pronoun']
    return removed


def choose_relatives(readings, surfaces):
    """関係の小辞 þe と se þe: 名詞・代名詞・sē の後ろの þe は関係代名詞 (格は節の中の役で決まる)。
    se þe は sē の格の関係代名詞「〜する人」"""
    removed = set()
    for i, items in enumerate(readings):
        if orthography.key(surfaces[i]) != morphology.RELATIVE_PARTICLE or i == 0:
            continue
        prev = readings[i - 1] or []
        if orthography.key(surfaces[i - 1]) in morphology.SE_FORMS:
            cng = morphology.SE_FORMS[orthography.key(surfaces[i - 1])]
            readings[i - 1] = [{'surface': surfaces[i - 1] + ' ' + surfaces[i], 'pos': 'pronoun', 'base': 'se þe',
                                'ja': '〜するところの', 'gloss_lang': 'ja', 'desc': '関係代名詞', '_': list(cng),
                                'compact': True}]
            removed.add(i)
        elif any(x['pos'] in ('noun', 'pronoun') for x in prev) or readings[i - 1] is None:
            readings[i] = [{'surface': surfaces[i], 'pos': 'pronoun', 'base': 'þe', 'ja': '〜するところの',
                            'gloss_lang': 'ja', 'desc': '関係代名詞',
                            '_': [(c, n, g) for c in ('Nom', 'Acc', 'Dat') for n in ('sg', 'pl')
                                  for g in morphology.ALL_GENDERS], 'compact': True}]
    return removed


def _cng(word, pos):
    return [cng for item in (word.items or []) if item.pos in pos for cng in (item._ or [])]


def _same_case(a, b):
    return a == b or {a, b} == {'Dat', 'Ins'}   # 名詞の具格は与格と同じ形 (þȳ ilcan ġēare「同じ年に」)


def _agree(a, b):
    return [x for x in a for y in b if _same_case(x[0], y[0]) and x[1] == y[1] and
            (x[2] == y[2] or None in (x[2], y[2]))]


def attach_articles(words, trace):
    """sē の形 (冠詞) と þes「この」を、後ろの一致する名詞 (無ければ形容詞) の修飾語にし、名詞の格を絞る。
    掛からない sē は指示代名詞「その人・それ」(冠詞の読みを除く)"""
    for i, word in enumerate(words):
        article = _cng(word, ('article',)) or [c for item in (word.items or []) if item.attrib('demonstrative')
                                               for c in item._ or []]
        if not article:
            continue
        head = None
        for j in range(i + 1, min(len(words), i + 1 + ARTICLE_WINDOW)):
            w = words[j]
            if w.items is None:
                break
            if w.items and all(item.pos == 'verb' for item in w.items):
                break
            if any(item.pos == 'verb' and orthography.key(item.attrib('base') or '') in COMMON_VERBS
                   for item in w.items):
                break
            if _agree(article, _cng(w, ('noun',))):
                head = w
                break
            if head is None and _agree(article, _cng(w, ('adj', 'participle'))):
                head = w
        if head is None:
            word.items = [item for item in word.items if item.pos != 'article' and not item.attrib('demonstrative')]
            if orthography.key(word.surface) == 'þa' and any(item.pos == 'adv' for item in word.items):
                word.items = [item for item in word.items if item.pos == 'adv']   # þā「その時」(「彼らを」より)
            continue
        cng = _agree(_cng(head, ('noun', 'adj', 'participle')), article)
        word.items = [item for item in word.items if item.pos == 'article' or item.attrib('demonstrative')]
        for item in word.items:
            item._ = [x for x in item._ if any(_same_case(x[0], y[0]) and x[1] == y[1] for y in cng)] or item._
        cases = list(dict.fromkeys(c for c, _, _ in cng))
        head.restrict_cases(cases + (['Ins'] if 'Dat' in cases else []))
        head.items = [item for item in head.items if item._ and item.pos in ('noun', 'pronoun', 'adj', 'participle')] \
            or head.items   # 冠詞の掛かる語は名詞類 (sē sang「その歌」の動詞の読みを除く)
        head.add_modifier(word)
        trace.append('// ART#%d (%s) -> #%d (%s)' % (i, word.surface, head.index, head.surface))
        for w in words[i + 1:words.index(head)]:   # 冠詞と名詞の間の語は形容詞 (se gōda cyning の gōda を「財産」と読まない)
            adjs = [item for item in w.items or [] if item.pos in ('adj', 'participle') and _agree(article, item._ or [])]
            if adjs:
                w.items = adjs


SUBORDINATORS = {'þæt', 'gif', 'þeah', 'forþam', 'forþæm', 'forþon', 'siþþan', 'syþþan', 'oþ', 'ær', 'hwæþer',
                 'þenden', 'swa', 'þa', 'þonne', 'hwonne', 'butan', 'buton', 'þe'}
FINITE_MOODS = ('indicative', 'subjunctive', 'imperative')


def _segments(words):
    """節の区切り (句読点・and・ac・従属の接続詞) で語の列を分ける → [(従属節か, [語])]"""
    segments, current, subordinate = [], [], False
    for w in words:
        k = orthography.key(w.surface)
        boundary = w.items is None or k in ('and', 'ac', 'oþþe') or \
            (k in SUBORDINATORS and w.items and any(i.pos in ('conj', 'pronoun') and
                                                    (i.pos == 'conj' or i.attrib('desc') == '関係代名詞')
                                                    for i in w.items))
        if boundary:
            if current:
                segments.append((subordinate, current))
            current = []
            subordinate = w.items is not None and k in SUBORDINATORS
            continue
        current.append(w)
    if current:
        segments.append((subordinate, current))
    return segments


def _finite_items(word):
    return [i for i in word.items or [] if i.pos == 'verb' and i.attrib('mood') in FINITE_MOODS]


def _agrees_with_subject(word, segment):
    """節の中の主格だけの代名詞 (hē・wē・ic …) と人称・数の合う定動詞の読みがあるか"""
    for w in segment:
        if w is word or not w.items or not all(i.pos == 'pronoun' for i in w.items):
            continue
        cases = {c for i in w.items for c, _, _ in i._ or []}
        if cases != {'Nom'}:
            continue
        p, n = w.items[0].attrib('person'), w.items[0].attrib('number')
        if any(i.attrib('person') == p and i.attrib('number') == n for i in _finite_items(word)):
            return True
    return False


def choose_verbs(words):
    """節ごとに、動詞の読みだけを持つ語が無ければ、定動詞の読みのある語を1つ動詞に絞る
    (Sē cyning sang: sang「歌」/ singan の過去)。主格の代名詞と人称・数の合うものを先に、従属節では最後の、
    主節では最初の候補"""
    for subordinate, segment in _segments(words):
        if any(w.items and all(i.pos == 'verb' for i in w.items) for w in segment):
            continue
        candidates = [w for w in segment if _finite_items(w)]
        if not candidates:
            continue
        agreeing = [w for w in candidates if _agrees_with_subject(w, segment)]
        pool = agreeing or candidates
        w = pool[-1] if subordinate else pool[0]
        w.items = [i for i in w.items if i.pos == 'verb']


def _restrict(word, cases):
    """格を cases に絞る (残る読みが無ければそのまま)"""
    kept = []
    for item in word.items:
        if item._ is None:
            kept.append(item)
            continue
        cng = [x for x in item._ if x[0] in cases]
        if cng:
            item._ = cng
            kept.append(item)
    if any(i._ for i in kept):
        word.items = kept


def _nominals(segment):
    return [w for w in segment if w.items and getattr(w, 'attached_to', None) is None and
            any(i.pos in ('noun', 'pronoun') for i in w.items) and
            all(i.pos in ('noun', 'pronoun', 'adj') for i in w.items)]


def _subject_fits(word, verb_items):
    """主格の読みが動詞の人称・数と合うか (名詞は3人称)"""
    for item in word.items:
        for c, n, g in item._ or []:
            if c != 'Nom':
                continue
            person = item.attrib('person') or 3
            for v in verb_items:
                vn, vp = v.attrib('number'), v.attrib('person')
                if (vn is None or vn == n or n == 'du' and vn == 'pl') and (vp is None or vp == person):
                    return True
    return False


def assign_subjects(words):
    """節ごとに主語を1つ選んで主格に、残りの主格・対格の語を対格に絞る。主語は動詞の人称・数と合う語のうち、
    主格だけの語、無ければ動詞の前の語、無ければ動詞の後ろの最初の語 (þā ġeseah hē hīe「その時彼は彼らを見た」)"""
    for subordinate, segment in _segments(words):
        verbs = [w for w in segment if w.items and all(i.pos == 'verb' for i in w.items)]
        if len(verbs) != 1:
            continue
        verb = verbs[0]
        finite = _finite_items(verb)
        if not finite or any(orthography.key(i.attrib('base') or '') in morphology.COPULAS for i in finite):
            continue
        nominals = _nominals(segment)
        fits = [w for w in nominals if _subject_fits(w, finite)]
        if not fits:
            continue
        only_nom = [w for w in fits if {c for i in w.items for c, _, _ in i._ or []} == {'Nom'}]
        before = [w for w in fits if segment.index(w) < segment.index(verb)]
        subject = (only_nom or before or fits)[0]
        _restrict(subject, ('Nom',))
        for w in nominals:
            if w is not subject and any(c == 'Acc' for i in w.items for c, _, _ in i._ or []):
                _restrict(w, ('Acc', 'Dat', 'Gen', 'Ins'))


SECOND_PERSON = {'þu', 'ge', 'þe', 'þec', 'eow', 'þin', 'eower'}


def mark_vocatives(words):
    """呼びかけ: 2人称の代名詞か命令法のある文の、文頭からコンマまでの名詞句 (3語まで) の主格を呼格に
    (Fæder ūre, þū þe eart on heofonum「天にいる私たちの父よ」)。古英語の呼格は主格と同じ形"""
    second = any(orthography.key(w.surface) in SECOND_PERSON for w in words) or \
        any(w.items and all(i.pos == 'verb' and i.attrib('mood') == 'imperative' for i in w.items) for w in words)
    if not second:
        return
    comma = next((k for k, w in enumerate(words) if w.items is None), None)
    if comma is None or not 0 < comma <= 3 or words[comma].surface != ',':
        return
    phrase = words[:comma]
    if not any(w.items and any(i.pos == 'noun' and any(c == 'Nom' for c, _, _ in i._ or []) for i in w.items)
               for w in phrase):
        return
    nxt = words[comma + 1] if comma + 1 < len(words) else None
    if nxt is not None and orthography.key(nxt.surface) in ('þu', 'ge') and \
            any(w.items is None for w in words[comma + 2:]):
        phrase = phrase + [nxt]   # 続く「þū þe …」(天にいる君よ) も呼びかけ
    for w in phrase:
        for item in w.items or []:
            if item._:
                item._ = [('Voc',) + x[1:] for x in item._ if x[0] == 'Nom'] or item._


def mark_wishes(words):
    """祈願の接続法: 従属節でない節の、読みがすべて現在の接続法の動詞は「〜ように」(sī þīn nama ġehālgod
    「君の名前が神聖にされますように」)。共通の訳 (core/Predicate.py) が印 wish を見て付ける"""
    for subordinate, segment in _segments(words):
        if subordinate:
            continue
        for w in segment:
            if w.items and all(i.pos == 'verb' and i.attrib('mood') == 'subjunctive' and i.attrib('tense') == 'present'
                               for i in w.items):
                for i in w.items:
                    i.item['wish'] = True


def _drop_negation(readings, surfaces, origins):
    """否定の縮約 (nis) は否定の副詞を前に足す (共通の解析器は ne を述語の否定に読む)"""
    out_r, out_s, out_o = [], [], []
    for r, s, k in zip(readings, surfaces, origins):
        if r and any(i.get('negated') for i in r):
            out_r.append([{'surface': '(ne)', 'pos': 'adv', 'base': 'ne', 'ja': '〜ない', 'gloss_lang': 'ja',
                           'negation': True}])
            out_s.append('(ne)')
            out_o.append(None)
        if r:
            r = [dict(i) for i in r]
            for i in r:
                i.pop('negated', None)
        out_r.append(r)
        out_s.append(s)
        out_o.append(k)
    return out_r, out_s, out_o


def lookup_all(surfaces, trace=None):
    trace = [] if trace is None else trace
    readings = [None if s in PUNCTUATION else
                word_items(s, first=(k == 0 or surfaces[k - 1] in PUNCTUATION),
                           following=surfaces[k + 1] if k + 1 < len(surfaces) else None)
                for k, s in enumerate(surfaces)]
    comparisons(readings, surfaces)
    removed = fix_function_words(readings, surfaces)
    removed |= choose_relatives(readings, surfaces)
    global _spellings
    _spellings = [_spelling(r, s) for r, s in zip(readings, surfaces)]   # まとめる前の綴り (助動詞の綴りも)
    merged = merge_verbs(readings, trace)
    removed |= set(merged)
    kept = [(r, s, k) for k, (r, s) in enumerate(zip(readings, surfaces)) if k not in removed]
    readings, surfaces, origins = _drop_negation([r for r, _, _ in kept], [s for _, s, _ in kept],
                                                 [k for _, _, k in kept])
    words = []
    for r, s, k in zip(readings, surfaces, origins):
        surface = r[0]['surface'] if r and r[0].get('surface') and '…' in r[0]['surface'] else s
        word = Word(surface, r)
        word.token_ix = k   # 元の語の位置 (まとめた動詞は助動詞の位置。補った (ne) は None)
        word.merged_ixs = tuple(m for m, a in merged.items() if a == k)   # まとめた本動詞の位置
        words.append(word)
    for i, word in enumerate(words):
        word.index = i
    return words


_spellings = []


def _spelling(items, surface):
    """読みの辞書の綴り (長音符付き)。鍵が元の語と同じものだけ (綴りの揺れで引いた語は元のまま)"""
    k = orthography.key(surface)
    if k in morphology.LONG_SPELLINGS and k != 'þe':   # よく使う機能語 (辞書には長音符の無い異綴りもある: si)
        long_ = morphology.LONG_SPELLINGS[k]
        return long_[0].upper() + long_[1:] if surface[:1].isupper() else long_
    matching = []
    for item in items or []:
        spelling = item.get('spelling') if isinstance(item, dict) else item.attrib('spelling')
        if spelling and orthography.key(spelling).replace('-', '') == orthography.key(surface):
            base = item.get('base') if isinstance(item, dict) else item.attrib('base')
            pos = item.get('pos') if isinstance(item, dict) else item.pos
            spelling = spelling.replace('-', '')
            # 見出し語の長音符を写すのは名詞・形容詞だけ (動詞は語幹の母音が変わる: sēon の seah)
            matching.append(_overlay_prefix(spelling, base or '') if pos in ('noun', 'adj') else spelling)
    if matching:   # 長音符・点の付いた綴りを先に (変化形だけの項目の forlet より変化表の forlēt)
        marked = [m for m in matching if unicodedata.normalize('NFD', m) != m]
        return _keep_case((marked or matching)[0], surface)
    for item in items or []:   # 綴りの揺れで引いた語 (gefrunon → ġefrūnen): 同じ字の長音符・点だけを写す
        spelling = item.get('spelling') if isinstance(item, dict) else item.attrib('spelling')
        transferred = _transfer_marks(surface, spelling) if spelling else None
        if transferred:
            return transferred
    first = (items or [None])[0]
    if first is None:
        return surface
    pos = first.get('pos') if isinstance(first, dict) else first.pos
    desc = first.get('desc') if isinstance(first, dict) else first.attrib('desc')
    if desc == '関係代名詞' or ' ' in surface:
        return surface   # 関係の þe は短母音
    if k == 'þe' and pos == 'pronoun':
        return surface[0] + 'ē'   # þē「君を・君に」
    # 手で書いた表の語 (þǣm・þā・ūre・þū …): 辞書の同じ鍵の語形の綴り (同じ品詞のものを先に)
    pairs = dictionary.forms(surface)
    pairs = sorted(pairs, key=lambda p: (p[0]['pos'] != pos, -(p[0].get('senses') or 0)))
    for info, feats in pairs:
        spelling = feats.get('surface')
        if spelling and orthography.key(spelling) == orthography.key(surface):
            return spelling[0].upper() + spelling[1:] if surface[:1].isupper() else spelling
    return surface


def _keep_case(spelling, surface):
    return spelling[0].upper() + spelling[1:] if surface[:1].isupper() else spelling[0].lower() + spelling[1:]


def _letters(text):
    """字ごとの (鍵の字, 元の字 (長音符・点を含む))"""
    out = []
    for c in unicodedata.normalize('NFC', text):
        k = orthography.key(c)
        if unicodedata.category(c) == 'Mn' and out:
            out[-1] = (out[-1][0], unicodedata.normalize('NFC', out[-1][1] + c))
        elif k:
            out.append((k, c))
    return out


def _overlay_prefix(spelling, base):
    """長音符の無い語形の綴り (変化形だけの項目の Gardena) に、見出し語 (Gārdene) と頭から同じ字の長音符・点を写す"""
    a, b = _letters(spelling), _letters(base.replace('-', ''))
    if any(unicodedata.normalize('NFD', ch) != ch for _, ch in a):
        return spelling   # 長音符・点があればそのまま
    out = []
    for k, (x, ch) in enumerate(a):
        same_prefix = k < len(b) and all(a[j][0] == b[j][0] for j in range(k + 1))
        out.append(b[k][1] if same_prefix else ch)
    return ''.join(out)


def _transfer_marks(surface, spelling):
    """辞書の綴りの長音符・点を、字数の同じ元の語の同じ字に写す (違う字はそのまま)。3/4 以上の字が同じときだけ"""
    a, b = _letters(surface), _letters(spelling.replace('-', ''))
    if len(a) != len(b) or not a:
        return None
    same = sum(x[0] == y[0] for x, y in zip(a, b))
    if same * 4 < len(a) * 3:
        return None
    out = ''.join(y[1] if x[0] == y[0] else x[1] for x, y in zip(a, b))
    return _keep_case(out, surface)


def spelled(analysis):
    """解析で選んだ読みの綴りで元の文を書き直す (音読で長母音を読むため: god (神) / gōd (良い))。
    → [(綴り, 見出し語)] (見出し語は接頭辞の判定に。分からなければ None)"""
    out = [(s, None) for s in (getattr(analysis, 'spellings', None) or analysis.original)]
    for word in analysis.words:
        k = getattr(word, 'token_ix', None)
        if k is not None and k < len(out) and word.items and not getattr(word, 'merged_ixs', ()):
            out[k] = (_spelling(word.items, analysis.original[k]), word.items[0].attrib('base'))
    return out


def analyze_sentence(surfaces):
    trace = []
    words = lookup_all(surfaces, trace)
    word_details = [word.detail() for word in words]
    attach_articles(words, trace)
    choose_verbs(words)
    mark_vocatives(words)
    mark_wishes(words)
    assign_subjects(words)
    with language.using(OLD_ENGLISH):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, trace)
    analysis.original = list(surfaces)
    analysis.spellings = list(_spellings)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
