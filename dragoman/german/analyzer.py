#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ドイツ語の文の解析
#
# spaCy (de_core_news_sm) の品詞・原形・格・性・数・依存関係で語の項目を作り (german/morphology.py)、動詞の組を
# 1語にまとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器 (core/analyzer.py) をドイツ語の設定
# (GERMAN) で使う:
#   - 格は冠詞・形容詞・名詞の形から spaCy が文脈で決めたもの (der Mann 主格、den Mann 対格、dem Mann 与格)。
#     冠詞は名詞に掛けて訳さない。前置詞は後ろの名詞の格で訳を選ぶ (in + 与格「〜で」、in + 対格「〜へ」)。
#     前置詞と冠詞の融合形 (im・zum・ins …) は前置詞
#   - 動詞の組 (枠構造) を本動詞にまとめる: haben / sein + 過去分詞 → 完了「〜した」、werden + 過去分詞 → 受動、
#     werden + 不定詞 → 未来、話法の助動詞 + 不定詞 (können「〜できる」、müssen「〜なければならない」、wollen「〜したい」)。
#     まとめた動詞は定動詞の位置 (主文は2番目、副文は最後) に置く
#   - 分離動詞の前つづり (ruft … an) は動詞に付ける (anrufen「電話する」)
#   - nicht・kein は否定。es gibt + 対格は「〜がある」
#   - 関係代名詞 (der / die / das …) は共通の解析器の関係節に (先行詞と性・数が一致するもの)
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, orthography

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', '…': 'period', ',': 'comma', ';': 'comma',
               ':': 'comma', '—': 'comma', '–': 'comma', '-': 'comma', '(': 'comma', ')': 'comma', '"': None,
               '„': None, '“': None, '”': None, '»': None, '«': None, "'": None, '‚': None, '‘': None}
TOKEN = re.compile(r"[A-Za-zÄÖÜäöüßÀ-ÿ]+(?:[-'][A-Za-zÄÖÜäöüßÀ-ÿ]+)*|\d+(?:[.,]\d+)*\.?|[.!?…,;:—–\-()\"„“”»«'‚‘]")
FINITE_TAGS = ('VVFIN', 'VAFIN', 'VMFIN', 'VVIMP', 'VAIMP')
NONFINITE_TAGS = ('VVINF', 'VAINF', 'VMINF', 'VVPP', 'VAPP', 'VMPP', 'VVIZU')


def _root_items(lemma):
    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


GERMAN = language.Language(
    name='de',
    and_words=('und',),
    nor_words=('noch',),
    or_words=('oder',),
    copulas=frozenset({'sein'}),
    negations=frozenset({'nicht', 'kein', 'keine', 'keinen', 'keinem', 'keiner', 'keines', '(nicht)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
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
# 語の項目

def _base(lemma, row=None):
    gender = (row or {}).get('gender')
    article = {'m': 'der', 'f': 'die', 'n': 'das', 'p': 'die (複数)'}.get(gender)
    return '%s%s' % (lemma, ' (%s)' % article if article else '')


def _verb_lemma(text):
    """語形の表で動詞の見出しを引く (spaCy が原形に戻せない強変化の形: aß → essen、fing → fangen)"""
    found = [lemma for lemma, pos, tags in dictionary.forms(text) if pos == 'verb' and tags]
    return found[0] if found else None


def _verb_data(token, feats, lemma=None):
    lemma = lemma or token.lemma_
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    if ja is None or gloss_lang == 'en' and lemma not in morphology.GLOSSES:
        better = _verb_lemma(token.text)
        if better and better != lemma:
            found = morphology.gloss(better, 'verb')
            if found[0]:
                lemma, (ja, gloss_lang, row) = better, found
    tense = {'Pres': 'present', 'Past': 'perfect'}.get(feats.get('Tense'), 'present')
    mood = {'Ind': 'indicative', 'Sub': 'subjunctive', 'Imp': 'imperative'}.get(feats.get('Mood'), 'indicative')
    if token.tag_ in NONFINITE_TAGS:
        mood = 'participle' if token.tag_.endswith('PP') else 'infinitive'
    if token.tag_ in ('VVIMP', 'VAIMP'):
        mood = 'imperative'
    person = int(feats['Person']) if feats.get('Person', '').isdigit() else 3
    number = morphology.NUMBERS.get(feats.get('Number'), 'sg')
    data = {'surface': token.text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma,
            'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': mood, 'tense': tense,
            'person': person, 'number': number, 'main': True}
    if lemma == 'sein':
        data['existential'] = True
    return data


RELATIVE_FORMS = {'der', 'die', 'das', 'dem', 'den', 'dessen', 'deren', 'denen'}


def item_of(token, doc):
    """spaCy の語 → 項目 (dict)。扱わない語は None (句読点)"""
    tag, lemma, text = token.tag_, token.lemma_, token.text
    feats = morphology.morph(token)
    lower = text.lower()
    if tag.startswith('$') or token.pos_ == 'PUNCT':
        return None
    if lower in morphology.CONTRACTIONS:
        prep, case = morphology.CONTRACTIONS[lower]
        return _preposition(text, prep, case)
    if tag in ('APPR', 'APPO', 'APZR', 'APPRART'):
        case = _governed_case(token, doc, lemma)
        return _preposition(text, lemma, case)
    if tag == 'ART' or tag in ('PPOSAT', 'PDAT', 'PIAT', 'PIDAT', 'PWAT', 'PRELAT') and token.dep_ == 'nk':
        base = lemma if lemma in morphology.DETERMINERS else lower.rstrip('enrsm') or lemma
        base = next((b for b in (lemma, lower[:4], lower[:3], lower[:5]) if b in morphology.DETERMINERS), base)
        if base == morphology.NEGATIVE_ARTICLE:
            return {'surface': text, 'pos': 'adv', 'base': 'kein', 'ja': '〜ない', 'gloss_lang': 'ja', 'negation': True}
        ja = morphology.DETERMINERS.get(base, '')
        pos = 'article' if not ja else 'adj'
        return {'surface': text, 'pos': pos, 'base': base, 'ja': ja, 'gloss_lang': 'ja', '_': morphology.cngs(feats),
                'compact': True}
    if tag == 'PDS' and lower in RELATIVE_FORMS and token.i >= 2 and doc[token.i - 1].text == ',' and \
            doc[token.i - 2].pos_ in ('NOUN', 'PROPN'):
        tag = 'PRELS'   # 名詞 + カンマの後ろの d- の代名詞は関係代名詞 (Der Mann, der kam。spaCy は指示代名詞 PDS にすることがある)
    if tag in ('PPER', 'PRF', 'PDS', 'PIS', 'PWS', 'PPOSS', 'PRELS', 'PWAV'):
        if tag == 'PRELS':
            return {'surface': text, 'pos': 'pronoun', 'base': lemma, 'ja': '〜するところの', 'gloss_lang': 'ja',
                    'desc': '関係代名詞', '_': morphology.cngs(feats), 'compact': True}
        key = text if text == 'Sie' and token.i > 0 else lower
        ja, person, number = morphology.PRONOUNS.get(key) or morphology.PRONOUNS.get(lemma) or (lemma, 3, 'sg')
        if lower == 'sie' and feats.get('Number') == 'Plur':
            ja, number = '彼ら', 'pl'
        if lower in ('mir', 'mich'):
            ja, person = '私', 1
        elif lower in ('dir', 'dich'):
            ja, person = '君', 2
        elif lower in ('ihm', 'ihn'):
            ja = '彼'
        elif lower == 'ihnen':
            ja, number = '彼ら', 'pl'
        if tag == 'PWAV':
            return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': {'wo': 'どこで', 'wann': 'いつ', 'wie': 'どのように',
                                                                       'warum': 'なぜ', 'wohin': 'どこへ', 'woher': 'どこから'}.get(lower, lemma),
                    'gloss_lang': 'ja'}
        return {'surface': text, 'pos': 'pronoun', 'base': lemma, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': morphology.cngs(feats), 'compact': True}
    if tag in ('NN', 'NE', 'FM', 'XY', 'TRUNC') and text.islower():
        verb = _verb_form(token)   # 小文字の名詞は動詞の読み誤り (命令形 hüte・bring)
        if verb is not None:
            return verb
    if tag in ('NN', 'NE', 'FM', 'XY', 'TRUNC'):
        ja, gloss_lang, row = morphology.gloss(lemma, 'name' if tag == 'NE' else 'noun')
        if ja is None and lemma != text:
            ja, gloss_lang, row = morphology.gloss(text, 'name' if tag == 'NE' else 'noun')
        if (ja is None or gloss_lang == 'en') and text.endswith('s') and text[:-1] in morphology.GLOSSES:
            lemma = text[:-1]   # 名前の属格 (Sneewittchens)
            ja, gloss_lang, row = morphology.gloss(lemma, 'noun')
        diminutive = None
        if ja is None or ja == text:
            diminutive = orthography.diminutive_base(lemma) or orthography.diminutive_base(text)
            if diminutive:   # 縮小形 (Spieglein → Spiegel)
                ja, gloss_lang, row = morphology.gloss(diminutive, 'noun')
                feats = dict(feats, Gender='Neut')
        # 辞書の名前 (Hänsel・Gretel は NN と読まれる)。日本語の訳のある語 (Buch「本」。姓の Buch もある) は普通名詞
        proper = tag == 'NE' or (row or {}).get('pos') == 'name' and gloss_lang != 'ja'
        if proper and not diminutive and (ja is None or gloss_lang == 'en' and ja.split(',')[0] in (lemma, text)):
            from .katakana import katakana
            ja, gloss_lang = katakana(lemma), 'ja'   # 辞書に無い名前はカタカナ (Hänsel → ヘンゼル)
        data = {'surface': text, 'pos': 'noun', 'base': _base(lemma, row), 'lemma': lemma, 'ja': ja or text,
                'gloss_lang': gloss_lang or 'en', '_': morphology.cngs(feats, (row or {}).get('gender')), 'main': True}
        if proper:
            data['proper'] = True
        if diminutive:
            data.update(base='%s (das。%s の縮小形)' % (text, diminutive), form='縮小形 (-lein / -chen)')
        return data
    if tag == 'ADJA' and re.sub('(e|er|en|em|es)$', '', lower) in morphology.ORDINALS_JA:
        return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': morphology.ORDINALS_JA[re.sub('(e|er|en|em|es)$', '', lower)],
                'gloss_lang': 'ja', '_': morphology.cngs(feats), 'main': True}
    if tag == 'ADJA':
        ja, gloss_lang, row = morphology.gloss(lemma, 'adj')
        return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                '_': morphology.cngs(feats), 'main': True}
    if tag == 'ADJD':
        ja, gloss_lang, row = morphology.gloss(lemma, 'adj')
        if token.dep_ == 'pd':   # 述語 (Das Haus ist schön)
            return {'surface': text, 'pos': 'adj', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en',
                    '_': [(c, n, g) for c in ('Nom',) for n in ('sg', 'pl') for g in ('m', 'f', 'n')], 'main': True,
                    'predicative': True}
        ja = morphology.adverbial(ja) if ja and gloss_lang == 'ja' else ja
        return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en'}
    if tag == 'CARD':
        return {'surface': text, 'pos': 'adj', 'base': text, 'ja': morphology.NUMBERS_JA.get(lower, text), 'gloss_lang': 'ja',
                '_': [(c, n, g) for c in morphology.ALL_CASES for n in ('sg', 'pl') for g in ('m', 'f', 'n')]}
    if tag in FINITE_TAGS or tag in NONFINITE_TAGS:
        return _verb_data(token, feats)
    if tag == 'PTKNEG':
        return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': morphology.NEGATIONS.get(lower, '〜ない'),
                'gloss_lang': 'ja'}
    if tag in ('KON', 'KOUS', 'KOKOM', 'KOUI'):
        return {'surface': text, 'pos': 'conj', 'base': lemma, 'ja': morphology.CONJUNCTIONS.get(lower, lemma),
                'gloss_lang': 'ja'}
    if tag in ('ADV', 'PAV', 'PTKA', 'PTKANT', 'ITJ', 'PROAV') or token.pos_ in ('ADV', 'PART', 'INTJ'):
        verb = _verb_form(token)
        if verb is not None:
            return verb
        if lower in morphology.NEGATIONS:
            return {'surface': text, 'pos': 'adv', 'base': lower, 'ja': morphology.NEGATIONS[lower], 'gloss_lang': 'ja'}
        ja, gloss_lang, row = morphology.gloss(lower if lower in morphology.GLOSSES else lemma, 'adv')
        return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': ja or lemma, 'gloss_lang': gloss_lang or 'en'}
    if tag in ('PTKZU', 'PTKVZ'):
        return {'surface': text, 'pos': 'particle', 'base': lemma or text, 'ja': '', 'gloss_lang': 'ja'}
    return {'surface': text, 'pos': 'adv', 'base': lemma, 'ja': lemma, 'gloss_lang': 'en'}


PERSON_TAGS = {'first-person': 1, 'second-person': 2, 'third-person': 3}


def _verb_form(token):
    """spaCy が副詞と読んだ動詞の定形 (dass du mich liebst の liebst): 副詞の見出しに無く、辞書の語形の表で
    動詞の人称の形なら動詞にする"""
    text = token.text
    if not text.islower() or dictionary.lemmas(text, ('adv', 'particle', 'adj', 'conj')) or text in morphology.GLOSSES:
        return None
    for lemma, pos, tags in dictionary.forms(text):
        if pos == 'verb' and 'imperative' in tags:
            data = _verb_data(token, {'Person': '2', 'Number': 'Plur' if 'plural' in tags else 'Sing'}, lemma)
            data['mood'] = 'imperative'
            return data
        if pos != 'verb' or not set(tags) & set(PERSON_TAGS):
            continue
        feats = {'Person': str(next(PERSON_TAGS[t] for t in tags if t in PERSON_TAGS)),
                 'Number': 'Plur' if 'plural' in tags else 'Sing',
                 'Tense': 'Past' if 'past' in tags or 'preterite' in tags else 'Pres',
                 'Mood': 'Sub' if any(t.startswith('subjunctive') for t in tags) else 'Ind'}
        data = _verb_data(token, feats, lemma)
        data['mood'] = 'indicative' if data['mood'] in ('infinitive', 'participle') else data['mood']
        return data
    return None


def _governed_case(token, doc, prep):
    """前置詞の格: 後ろの名詞句の最初の格の付いた語の格。無ければ前置詞の決まった格"""
    for t in doc[token.i + 1:token.i + 5]:
        feats = morphology.morph(t)
        if feats.get('Case') in morphology.CASES and t.tag_ in ('ART', 'NN', 'NE', 'ADJA', 'PPER', 'PDS', 'PPOSAT',
                                                                 'PDAT', 'PIAT', 'PIS', 'PRF', 'PRELS', 'CARD'):
            return morphology.CASES[feats['Case']]
        if t.tag_.startswith('$') or t.tag_ in FINITE_TAGS:
            break
    return morphology.GOVERNS.get(prep, 'Dat')


def _preposition(text, prep, case):
    ja = morphology.PREPOSITIONS.get((prep, case)) or morphology.PREPOSITIONS.get((prep, None)) or '〜' + prep
    return {'surface': text, 'pos': 'preposition', 'base': prep, 'dominates': case, 'ja': ja, 'gloss_lang': 'ja'}


# ----------------------------------------------------------------------
# 動詞の組

def merge_verbs(words, doc):
    """助動詞・話法の助動詞と本動詞 (過去分詞・不定詞)、分離動詞の前つづりを、定動詞の位置の1語にまとめる"""
    by_i = {w.doc_i: w for w in words}   # spaCy の語の番号 (縮約を分けた語の列での位置)
    removed = set()
    for token in doc:
        word = by_i.get(token.i)
        if word is None or not word.items:
            continue
        if token.tag_ == 'PTKVZ' and token.head.i in by_i:   # 分離動詞の前つづり (ruft … an)
            verb = by_i[token.head.i]
            item = _item(verb)
            if item is not None and item.pos == 'verb':
                lemma = morphology.separable(token.text.lower(), item.attrib('lemma'))
                if lemma:
                    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
                    verb.items = [type(item)(dict(item.item, lemma=lemma, pres1sg=lemma, base=lemma, ja=ja or lemma,
                                                  gloss_lang=gloss_lang or 'en', separable=token.text))]
            removed.add(token.i)
            word.prefix_of = verb if item is not None else None
        elif token.tag_ == 'PTKZU':
            removed.add(token.i)
    # 本動詞 (非定形) → 支配する助動詞 (依存関係の oc を上へ)
    for token in doc:
        if token.tag_ not in NONFINITE_TAGS or token.i in removed:
            continue
        head = token.head
        if head.i == token.i or head.tag_ not in FINITE_TAGS + NONFINITE_TAGS or token.dep_ not in ('oc', 'pd'):
            continue
        if head.lemma_ not in ('haben', 'sein', 'werden') and head.lemma_ not in morphology.MODALS:
            continue
        aux_word, main_word = by_i.get(head.i), by_i.get(token.i)
        if aux_word is None or main_word is None or not aux_word.items or not main_word.items:
            continue
        _merge(aux_word, main_word, head, token)
        removed.add(token.i)
    dropped = {id(by_i[i]) for i in removed if i in by_i}
    for w in words:
        if id(w) in dropped:
            w.merged_into = True
    return [w for w in words if id(w) not in dropped]


def attach_articles(words):
    """冠詞 (der / ein …) を後ろの名詞 (間に形容詞・数詞があってもよい) に掛け、語の列から除く (訳さない)"""
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


def _merge(aux_word, main_word, aux, main):
    """aux_word の位置に、本動詞の訳・時制・態をまとめた動詞を作る"""
    a, m = _item(aux_word), _item(main_word)
    data = dict(m.item)
    data.update(person=a.attrib('person'), number=a.attrib('number'), mood=a.attrib('mood'),
                surface=aux_word.surface + ' … ' + main_word.surface)
    data.pop('existential', None)
    aux_lemma = aux.lemma_
    aux_tense = a.attrib('tense')
    past = aux_tense == 'perfect'
    form = ''
    if aux_lemma in ('haben', 'sein') and main.tag_.endswith('PP'):
        if aux_lemma == 'sein' and 'sein' not in morphology.auxiliary(m.attrib('lemma')):
            data.update(voice='passive', tense='perfect' if past else 'present')   # 状態受動 (ist geschlossen)
            form = '状態受動 (sein + 過去分詞)'
        else:
            data['tense'] = 'pluperfect' if past else 'perfect'
            form = '%s (%s + 過去分詞)' % ('過去完了' if past else '現在完了', aux_lemma)
    elif aux_lemma == 'werden' and main.tag_.endswith('PP'):
        data.update(voice='passive', tense='perfect' if past else 'present')
        form = '受動 (werden + 過去分詞)'
    elif aux_lemma == 'werden' and main.tag_.endswith('INF'):
        data['tense'] = 'future'
        form = '未来 (werden + 不定詞)'
    elif aux_lemma not in morphology.MODALS:
        data['tense'] = a.attrib('tense')
    if aux_lemma in morphology.MODALS:
        suffix = morphology.MODALS[aux_lemma]
        data['ja'] = ','.join(_attach(j, suffix) for j in (m.ja or '').split(',')[:1]) if m.attrib('gloss_lang') == 'ja' \
            else m.ja
        data['tense'] = a.attrib('tense')
        form = '話法の助動詞 %s + 不定詞' % aux_lemma
        data.update(modal=aux_lemma, main_ja=m.ja)   # 文の枠では話法の動詞 + 不定詞の節に (possum legere)
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

def existential_es_gibt(words):
    """es gibt + 対格「〜がある」: es を除き、対格の名詞を主語に"""
    for i, word in enumerate(words):
        item = _item(word)
        if item is None or item.pos != 'verb' or item.attrib('lemma') != 'geben':
            continue
        es = [w for w in words if w.surface.lower() == 'es' and _pos(w) == 'pronoun']
        if not es:
            continue
        item.item.update(ja='ある,いる', gloss_lang='ja', existential=True, lemma='es gibt')
        word.items = [type(item)(item.item)]
        for w in es:
            w.items = [type(_item(w))(dict(_item(w).item, pos='particle', ja='', _=None))]
        for w in words:
            it = _item(w)
            if it is not None and it.pos == 'noun' and it._ and it._[0][0] == 'Acc':
                it._ = [('Nom',) + c[1:] for c in it._]
        return


WEATHER_VERBS = {'regnen', 'schneien', 'donnern', 'blitzen', 'hageln', 'frieren'}


def weather_es(words):
    """天候の es (es regnet「雨が降る」) は訳さない"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('lemma') in WEATHER_VERBS for w in words):
        return words
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'verb' and item.attrib('lemma') in WEATHER_VERBS:
            w.items = [type(item)(dict(item.item, person=None, impersonal=True))]   # 主語を補わない
    return [w for w in words if not (w.surface.lower() == 'es' and _pos(w) == 'pronoun')]


def passive_agents(words):
    """受動の文の von + 与格は動作主「〜によって」"""
    if not any(_pos(w) == 'verb' and _item(w).attrib('voice') == 'passive' for w in words):
        return
    for w in words:
        item = _item(w)
        if item is not None and item.pos == 'preposition' and item.attrib('base') == 'von':
            w.items = [type(item)(dict(item.item, ja='〜によって'))]


def lookup_all(surfaces):
    modern, origin = orthography.tokens(surfaces)   # 古い綴りを今の綴りに (roth → rot、gieng → ging)
    doc = morphology.parse(modern)
    words = []
    for token in doc:
        data = item_of(token, doc)
        old = surfaces[origin[token.i]]
        if data is not None and old != token.text:
            data['old_spelling'] = old
        word = Word(token.text, None if data is None else [data])
        word.token_ix = origin[token.i]
        word.doc_i = token.i
        words.append(word)
    global _display
    _display = list(words)
    words = merge_verbs(words, doc)
    words = attach_articles(words)
    words = [w for w in words if _pos(w) != 'particle']
    existential_es_gibt(words)
    words = weather_es(words)
    passive_agents(words)
    from dragoman.core.Adverbial import mark_subordinators
    mark_subordinators(words, morphology.SUBORDINATORS)
    words = [w for w in words if _pos(w) != 'particle']
    for i, word in enumerate(words):
        word.index = i
    return words


_display = []


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(GERMAN):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
