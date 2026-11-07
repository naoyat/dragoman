#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語の文の解析
#
# 語に切り分け (vietnamese/segment.py)、Stanza (UD Vietnamese-VTB で学習したモデル) の品詞・依存関係で語の項目を作り
# (vietnamese/morphology.py)、ベトナム語の構文をまとめてから、並列・係り先・前置詞句・格の枠・日本語訳は共通の解析器
# (core/analyzer.py) をベトナム語の設定 (VIETNAMESE) で使う:
#   - 語順は 主語-動詞-目的語。格は依存関係から (nsubj → 主格、obj → 対格、前置詞の目的語 → 前置詞句)
#   - 修飾語・所有者・指示詞は名詞の後ろ (sách mới「新しい本」、mẹ tôi「私の母」、sách của tôi「私の本」、
#     sách này「この本」)。数詞 + 量詞は名詞の前 (hai con chó「二匹の犬」)。数の無い量詞 (con mèo) は訳さない
#   - 相・時制は動詞の前の副詞 (đã → 過去・完了、đang → 進行、sẽ → 未来、vừa / mới → 直前の完了、từng → 経験)。
#     相の副詞が無ければ時の語 (hôm qua「昨日」→ 過去、ngày mai「明日」→ 未来)
#   - 否定 (không・chẳng・chưa「まだ〜ない」・đừng「〜するな」)、助動詞 (muốn「〜たい」・có thể「〜できる」・phải …)
#   - 受動: bị (被害)・được (恩恵) + (動作主) + 動詞
#   - 形容詞の述語 (Trời đẹp「空は 美しい」) は形容詞 + 見えない繋辞。rất + 形容詞・形容詞 + lắm / quá は1語に
#   - 疑問: 文末の không・chưa (có … không?「〜か」)、疑問詞 (gì・ai・đâu・nào …)。文末の助詞 (à・nhé・ạ …) は訳さない
#   - 関係節: 名詞 + mà + 節、名詞 + 節 (Stanza の acl)
#
from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, segment

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', ',': 'comma', ';': 'comma', ':': 'comma', '…': 'period',
               '"': None, '“': None, '”': None, '(': 'comma', ')': 'comma', '–': 'comma', '—': 'comma', '-': None,
               "'": None, '‘': None, '’': None}
ALL_CASES = ('Nom', 'Acc', 'Dat', 'Gen')
GENDER = morphology.GENDER


def _root_items(lemma):
    ja, gloss_lang, _ = morphology.gloss(lemma, 'verb')
    return [{'pos': 'verb', 'ja': ja, 'gloss_lang': gloss_lang}] if ja else []


QUESTION_VERBS = frozenset({'biết', 'hỏi', 'hiểu', 'nhớ', 'quên', 'xem', 'nghĩ', 'nói', 'cho biết'})
INTERROGATIVES = {'gì': None, 'cái gì': None, 'ai': None, 'đâu': None, 'ở đâu': None, 'nào': None, 'bao giờ': 'いつ',
                  'khi nào': 'いつ', 'lúc nào': 'いつ', 'tại sao': 'なぜ', 'vì sao': 'なぜ', 'sao': 'なぜ',
                  'thế nào': 'どのように', 'như thế nào': 'どのように', 'bao nhiêu': None, 'mấy': None, 'có … không': ''}
INTERROGATIVE_ADVERBS = {'bao giờ': 'いつ', 'khi nào': 'いつ', 'lúc nào': 'いつ', 'tại sao': 'なぜ', 'vì sao': 'なぜ',
                         'thế nào': 'どのように', 'như thế nào': 'どのように', 'làm sao': 'どうやって',
                         'bao lâu': 'どのくらい'}


def predicative_adjective(adj, noun):
    """名詞に掛けない形容詞: 名詞の前の形容詞 (数量の語の他) と、述語の形容詞 (見えない繋辞の前)"""
    if not isinstance(adj, Word) or not isinstance(noun, Word) or not adj.items or not noun.items:
        return False
    item = adj.items[0]
    a, n = getattr(adj, 'index', 0), getattr(noun, 'index', 0)
    if item.attrib('prenominal'):
        return a > n
    if item.attrib('predicative'):
        return True
    return a < n


VIETNAMESE = language.Language(
    name='vi',
    question_moods=('indicative',), question_verbs=QUESTION_VERBS, interrogatives=INTERROGATIVES,
    subordinators=morphology.SUBORDINATORS,
    and_words=('và', 'với', 'cùng'),
    or_words=('hoặc', 'hay', 'hoặc là'),
    copulas=frozenset({'là', '(là)', 'có'}),
    negations=frozenset(morphology.NEGATIONS),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'},
    absolute_case=None,
    lookup=_root_items,
    predicative_adjective=predicative_adjective,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    possessor_cases=('Dat',),
)


def sentences(text):
    """テキストを文 (. ! ? で区切る) に分け、各文の語の列を返す"""
    for line in text.splitlines():
        current = []
        for token in segment.segment(line):
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


def _low(word):
    return word.surface.lower() if isinstance(word, Word) else ''


def _cngs(cases, number=None):
    return [(c, n, GENDER) for c in cases for n in ((number,) if number else ('sg', 'pl'))]


def _set(word, **kw):
    item = _item(word)
    word.items = [type(item)(dict(item.item, **kw))]


def _drop(word):
    word.merged_into = True


MOTION_VERBS = {'đi', 'đến', 'tới', 'về', 'vào', 'ra', 'lên', 'xuống', 'sang', 'qua', 'trở về', 'trở lại'}


def _case_of(token):
    dep = token.dep_
    head = token.head
    if any(c.dep_ == 'case' for c in token.children):
        return ('Gen',)   # 前置詞の目的語 (ở Hà Nội)
    if head.text.lower() == 'có' and head.i != token.i and head.pos_ in ('VERB', 'AUX'):
        # có の前の所有者・場所と、後ろの有るもの (Tôi có hai người bạn「私には 二人の友人が いる」)
        if token.i > head.i and dep in ('obj', 'nsubj'):
            return ('Nom',)
        if token.i < head.i and dep.startswith('nsubj'):
            return ('Dat',)
    if dep.startswith('nsubj'):
        return ('Nom',)
    if dep in ('obj', 'obl') and head.text.lower() in MOTION_VERBS | {'ở', 'sống'}:
        return ('Dat',)   # 移動の動詞の行き先・居る所 (đi Hà Nội「ハノイに 行く」、ở nhà「家に いる」)
    if dep == 'iobj' or dep == 'obj' and any(c.dep_ == 'obj' and c.i > token.i for c in head.children):
        return ('Dat',)   # 二重目的語の前のほうは受け手 (cho tôi quyển sách「私に 本を くれる」)
    if dep in ('obj', 'obl:comp'):
        return ('Acc',)
    if dep in ('nmod:poss', 'nmod', 'compound', 'det:pmod') and head.i < token.i:
        return ('Gen',)   # 名詞の後ろの所有者・修飾の名詞 (mẹ tôi「私の母」)
    if dep == 'root' or any(c.dep_ == 'cop' for c in token.children):
        return ('Nom',)   # là の補語 (Tôi là sinh viên)
    return ('Nom', 'Acc')


def _verb(text, lemma, **kw):
    ja, gloss_lang, row = morphology.gloss(lemma, 'verb')
    data = {'surface': text, 'pos': 'verb', 'lemma': lemma, 'pres1sg': lemma, 'base': lemma, 'ja': ja or lemma,
            'gloss_lang': gloss_lang or 'en', 'voice': 'active', 'mood': 'indicative', 'tense': 'present',
            'person': 3, 'number': 'sg', 'main': True, 'impersonal_person': True}
    if row and row['han']:
        data['han'] = row['han']
    data.update(kw)
    return data


def _noun(text, word, token, proper=False):
    low = word.lower()
    ja, gloss_lang, row = morphology.gloss(word, 'name' if proper else 'noun')
    if low.startswith('người ') and low[6:] in morphology.NATIONS:
        ja, gloss_lang = morphology.NATIONS[low[6:]] + '人', 'ja'      # người Việt Nam「ベトナム人」
    elif low.startswith('tiếng ') and low[6:] in morphology.LANGUAGE_NAMES:
        ja, gloss_lang = morphology.LANGUAGE_NAMES[low[6:]] + '語', 'ja'   # tiếng Việt「ベトナム語」
    elif proper and low in morphology.NATIONS:
        ja, gloss_lang = morphology.NATIONS[low], 'ja'
    if ja is None or proper and gloss_lang == 'en':
        from .katakana import katakana
        ja, gloss_lang = katakana(word).replace(' ', ''), 'ja'   # 辞書に無い名前は読みのカタカナ (Nguyễn Văn An)
    data = {'surface': text, 'pos': 'noun', 'base': word, 'lemma': word, 'ja': ja, 'gloss_lang': gloss_lang or 'en',
            '_': _cngs(_case_of(token)), 'main': True, **({'clause_start': True} if _later_subject(token) else {})}
    if proper:
        data['proper'] = True
    if row and row['han']:
        data['han'] = row['han']
    if row and row['classifiers']:
        data['classifiers'] = row['classifiers']
    return data


def item_of(token, text):
    """Stanza の語 → 項目 (dict)。扱わない語は None (句読点)"""
    word, low, upos, xpos, dep = token.text, token.text.lower(), token.pos_, token.tag_, token.dep_
    if upos == 'PUNCT' or word in PUNCTUATION:
        return None
    if low in morphology.NEGATIONS and upos in ('ADV', 'AUX', 'PART', 'VERB', 'X') and \
            (dep != 'root' or low in ('đừng', 'chớ') and token.i + 1 < len(_tokens) and _tokens[token.i + 1].pos_ == 'VERB'):
        ja = morphology.NEGATIONS[low]
        return {'surface': text, 'pos': 'adv', 'base': low, 'ja': 'まだ' if low == 'chưa' else '', 'gloss_lang': 'ja',
                'negation': True, 'neg_word': low, 'neg_ja': ja,
                **({'prohibitive': True} if low in ('đừng', 'chớ') else {})}
    if low in morphology.ASPECTS and upos in ('ADV', 'AUX', 'X', 'ADJ') and dep in ('advmod', 'aux', 'advmod:adj', 'dep',
                                                                                   'compound:svc', 'amod'):
        if low != 'mới' or token.head.pos_ in ('VERB', 'ADJ') and token.head.i > token.i:
            return {'surface': text, 'pos': 'aspect', 'base': low, 'ja': '', 'gloss_lang': 'ja',
                    'aspect': morphology.ASPECTS[low]}
    if low == 'hãy' and dep in ('advmod', 'aux', 'dep'):
        return {'surface': text, 'pos': 'aspect', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'imperative': True}
    if low in INTERROGATIVE_ADVERBS:
        return {'surface': text, 'pos': 'adv', 'base': low, 'ja': morphology_ja(low), 'gloss_lang': 'ja',
                'desc': '疑問詞'}
    after_count = token.i > 0 and (_tokens[token.i - 1].tag_ == 'Nc' or _tokens[token.i - 1].pos_ == 'NUM' or
                                   _tokens[token.i - 1].text.lower() in morphology.PLURAL_MARKERS | {'người'})
    if low in morphology.PRONOUNS and upos in ('PRON', 'NOUN', 'DET', 'PROPN', 'X') and \
            not (after_count and low in ('bạn', 'anh', 'chị', 'em', 'ông', 'bà', 'cô', 'chú', 'bác', 'người ta')) and \
            not (low in morphology.DEMONSTRATIVES and dep.startswith('det')) and \
            not (low in ('anh', 'chị', 'em', 'ông', 'bà', 'cô', 'chú', 'bác', 'bạn') and
                 any(c.dep_ in ('nmod:poss', 'det:pmod', 'amod', 'nmod', 'compound') for c in token.children)):
        ja, person, number = morphology.PRONOUNS[low]
        gender = morphology.PRONOUN_GENDERS.get(low, GENDER)
        data = {'surface': text, 'pos': 'pronoun', 'base': low, 'ja': ja, 'gloss_lang': 'ja', 'person': person,
                'number': number, '_': [(c, n, gender) for c, n, _ in _cngs(_case_of(token))], 'compact': True}
        if low in morphology.KINSHIP:
            data['kinship'] = True
        if low in morphology.INTERROGATIVE_PRONOUNS:
            data['desc'] = '疑問代名詞'
        if _later_subject(token):
            data['clause_start'] = True
        return data
    if low in morphology.DEMONSTRATIVES and (dep.startswith('det') or upos == 'DET' or
                                             token.head.pos_ in ('NOUN', 'PROPN') and token.head.i < token.i):
        return {'surface': text, 'pos': 'adj', 'base': low, 'ja': morphology.DEMONSTRATIVES[low], 'gloss_lang': 'ja',
                '_': _cngs(ALL_CASES), 'determiner': True, 'demonstrative': True}
    if low in morphology.PRENOMINAL and (upos in ('DET', 'NUM', 'ADJ', 'ADV', 'X') or dep in ('det', 'nummod', 'amod')) and \
            token.head.i > token.i and token.head.pos_ in ('NOUN', 'PROPN', 'PRON', 'NUM'):
        data = {'surface': text, 'pos': 'adj', 'base': low, 'ja': morphology.PRENOMINAL[low], 'gloss_lang': 'ja',
                '_': _cngs(ALL_CASES), 'determiner': True, 'prenominal': True}
        if low in morphology.PLURAL_MARKERS:
            data['plural_marker'] = True
        if low == 'một' or low in morphology.NUMBERS and low not in ('không', 'linh', 'lẻ'):
            data.update(numeral=True, value=morphology.NUMBERS.get(low))
        return data
    if upos == 'NUM' or xpos == 'Num':
        value = morphology.number([word]) if not word.replace('.', '').replace(',', '').isdigit() else None
        ja = morphology.kanji_number(value) if value is not None else word
        return {'surface': text, 'pos': 'adj', 'base': low, 'ja': ja, 'gloss_lang': 'ja', '_': _cngs(ALL_CASES),
                'numeral': True, 'value': value, 'prenominal': True}
    if xpos == 'Nc' or dep == 'clf:det' or low in morphology.CLASSIFIERS and dep.startswith('clf'):
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': morphology.CLASSIFIERS.get(low, 'つ'),
                'gloss_lang': 'ja', 'classifier': True}
    if low == 'của' and upos == 'ADP':
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'possessive_marker': True}
    if low == 'thì' and upos in ('SCONJ', 'CCONJ', 'ADP', 'PART', 'X', 'ADV'):
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'topic': True}
    if low in morphology.FINAL_PARTICLES and dep in ('discourse', 'advmod', 'dep', 'punct', 'mark') and \
            token.i == len(_tokens) - 1 - _trailing_punct() and token.i > 0:
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'final': True}
    if upos == 'ADP' or low in morphology.PREPOSITIONS and upos in ('ADP',):
        ja = morphology.PREPOSITIONS.get(low, '〜' + low)
        return {'surface': text, 'pos': 'preposition', 'base': low, 'dominates': 'Gen', 'ja': ja, 'gloss_lang': 'ja'}
    if low in ('rằng', 'là') and upos in ('SCONJ', 'CCONJ', 'ADP') and token.i > 0 and \
            any(t.text.lower() in COMPLEMENT_VERBS and t.i < token.i for t in _tokens):
        verb = next(t.text.lower() for t in reversed(_tokens[:token.i]) if t.text.lower() in COMPLEMENT_VERBS)
        return {'surface': text, 'pos': 'conj', 'base': low, 'ja': '〜ということ', 'gloss_lang': 'ja',
                'clause_suffix': COMPLEMENT_VERBS[verb], 'clause_start': True, 'complement': True,
                'desc': '補文の接続詞 (英語の that)'}
    if low in ('nên', 'thì', 'cho nên', 'mà') and upos in ('SCONJ', 'CCONJ') and \
            any(t.text.lower() in morphology.SUBORDINATORS for t in _tokens[:token.i]):
        # 従属節の後ろの nên・thì (Vì tôi mệt nên …「疲れたので」、Nếu … thì …「〜なら」) は訳さない
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'topic': True}
    if upos in ('SCONJ', 'CCONJ') or low in morphology.CONJUNCTIONS and upos not in ('VERB', 'NOUN', 'ADJ'):
        return {'surface': text, 'pos': 'conj', 'base': low, 'ja': morphology.CONJUNCTIONS.get(low, low),
                'gloss_lang': 'ja'}
    if low == 'là' and dep == 'cop' and token.head.pos_ == 'VERB' and token.head.i > token.i:
        # 動詞の前の là は強め (khéo là ghét nhau「なんとも 憎み合う」)。繋辞にしない
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'topic': True}
    if low == 'là' and (upos == 'AUX' or dep == 'cop'):
        return _verb(text, 'là', ja='〜である', gloss_lang='ja', copula=True)
    if low == 'có' and dep in ('advmod', 'aux') and token.head.pos_ in ('VERB', 'ADJ') and token.head.i > token.i:
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'affirmative': True}
    if low == 'có' and upos in ('VERB', 'AUX'):
        return _verb(text, 'có', ja='ある,いる', gloss_lang='ja', existential=True, form='所有・存在 (có)')
    if low in ('bị', 'được') and (dep == 'aux:pass' or low == 'bị' and dep in ('aux', 'advmod')):
        return {'surface': text, 'pos': 'particle', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'passive': low}
    if low in morphology.MODALS and (upos == 'AUX' or dep in ('aux', 'xcomp') and token.head.i > token.i or
                                     ' ' in low and dep == 'advmod' and token.head.i > token.i) and \
            any(t.pos_ in ('VERB', 'ADJ') and t.i > token.i for t in _tokens):
        return {'surface': text, 'pos': 'modal', 'base': low, 'ja': '', 'gloss_lang': 'ja', 'modal': low}
    if upos in ('VERB', 'AUX'):
        data = _verb(text, word)
        if low == 'nói' and any(c.dep_ == 'obj' and c.text.lower().startswith('tiếng') for c in token.children):
            data['ja'] = '話す'   # 言葉を話す (nói tiếng Việt「ベトナム語を 話す」)
        return data
    if upos == 'ADJ':
        ja, gloss_lang, row = morphology.gloss(word, 'adj')
        data = {'surface': text, 'pos': 'adj', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en',
                '_': _cngs(ALL_CASES), 'main': True}
        if dep in ('xcomp', 'advmod') and token.head.pos_ == 'VERB' and token.head.i < token.i and \
                gloss_lang == 'ja' and ja:
            return {'surface': text, 'pos': 'adv', 'base': word, 'ja': morphology.adverbial(ja.split(',')[0]),
                    'gloss_lang': 'ja'}   # 動詞の後ろの形容詞は副詞 (ngủ sớm「早く 寝る」)
        if dep == 'root' or dep in ('conj', 'ccomp', 'advcl', 'parataxis') and \
                any(c.dep_.startswith('nsubj') for c in token.children):
            data.update(predicative=True, _=_cngs(('Nom',)))
        if row and row['han']:
            data['han'] = row['han']
        return data
    if low == 'nhau' and dep in ('obj', 'advmod', 'obl', 'nmod'):
        return {'surface': text, 'pos': 'adv', 'base': low, 'ja': '互いに', 'gloss_lang': 'ja'}   # ghét nhau「互いに 憎む」
    counted = token.i > 0 and _tokens[token.i - 1].pos_ == 'NUM'
    if upos == 'ADV' or dep == 'obl:tmod' and not counted or low in morphology.TIME_TENSES:
        ja, gloss_lang, _ = morphology.gloss(word, 'adv')
        return {'surface': text, 'pos': 'adv', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en',
                **({'time_tense': morphology.TIME_TENSES[low]} if low in morphology.TIME_TENSES else {})}
    if upos in ('NOUN', 'PROPN', 'X', 'SYM', 'PRON', 'DET'):
        return _noun(text, word, token, proper=upos == 'PROPN' or word[:1].isupper() and token.i > 0)
    if upos == 'INTJ':
        ja, gloss_lang, _ = morphology.gloss(word, 'noun')
        return {'surface': text, 'pos': 'interj', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en'}
    ja, gloss_lang, _ = morphology.gloss(word, 'adv')
    return {'surface': text, 'pos': 'adv', 'base': word, 'ja': ja or word, 'gloss_lang': gloss_lang or 'en'}


# 補文 (rằng / là + 節) を取る「言う・思う」の動詞 → 節の後ろに付ける形
COMPLEMENT_VERBS = {'nói': 'と', 'nghĩ': 'と', 'tin': 'と', 'cho': 'と', 'cho rằng': 'と', 'tưởng': 'と', 'bảo': 'と',
                    'kể': 'と', 'trả lời': 'と', 'hy vọng': 'ことを', 'biết': 'ことを', 'thấy': 'ことを', 'nghe': 'ことを',
                    'hiểu': 'ことを', 'nhớ': 'ことを', 'quên': 'ことを', 'mong': 'ことを', 'sợ': 'ことを'}


def _later_subject(token):
    """後ろの節 (補文・並列の動詞・従属節の後ろの主節) の主語か: 節を分けるとき後ろの動詞に
    (Tôi không biết | anh ấy ở đâu、Nếu trời mưa thì | tôi sẽ ở nhà)"""
    if not token.dep_.startswith('nsubj') or token.i == 0:
        return False
    if token.head.dep_ in ('ccomp', 'conj', 'xcomp', 'advcl', 'parataxis') and token.head.i > token.i:
        return True
    prev = _tokens[token.i - 1].text.lower()
    return prev in ('thì', 'nên', 'cho nên', 'mà', ',') and \
        any(t.text.lower() in morphology.SUBORDINATORS for t in _tokens[:token.i])


def morphology_ja(low):
    return morphology.PRONOUNS.get(low, (INTERROGATIVE_ADVERBS.get(low, low),))[0]


_tokens = []


def _trailing_punct():
    n = 0
    for t in reversed(_tokens):
        if t.pos_ != 'PUNCT':
            break
        n += 1
    return n


# ----------------------------------------------------------------------

def numerals(words):
    """続く数詞 (hai mươi ba) を1語に (二十三)"""
    out = []
    for word in words:
        item = _item(word)
        prev = _item(out[-1]) if out else None
        if item is not None and prev is not None and item.attrib('numeral') and prev.attrib('numeral') and \
                not prev.attrib('plural_marker'):
            parts = out[-1].surface.split() + word.surface.split()
            value = morphology.number(parts)
            if value is not None:
                _set(out[-1], ja=morphology.kanji_number(value), value=value, surface=' '.join(parts))
                out[-1].surface = ' '.join(parts)
                _drop(word)
                continue
        out.append(word)
    return out


def _is_person(noun):
    en = ' '.join(r['en'] or '' for r in dictionary.lookup(noun.attrib('lemma') or ''))
    return any(w in en.split(',')[0] for w in ('person', 'people', 'friend', 'student', 'teacher', 'child', 'man',
                                               'woman', 'boy', 'girl', 'doctor', 'worker', 'mother', 'father'))


def classifiers(words):
    """数詞・数量の語 + 量詞 + 名詞: 数詞と量詞を名詞に掛かる形容詞1つに (hai con chó「二匹の犬」)。
    量詞だけ (con mèo「猫」) は落とす。các・những (複数の印) は名詞を複数に"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.attrib('classifier'):
            nxt = next((w for w in words[k + 1:k + 3] if _pos(w) in ('noun', 'pronoun')), None)
            prev = _item(out[-1]) if out else None
            if nxt is None:   # 名詞の無い量詞 (cái này「これ」・con「子」): 名詞として読む
                _set(word, **_noun_data_of(word))
                out.append(word)
                continue
            if prev is not None and prev.attrib('numeral') and prev.attrib('value') not in (None,):
                unit = item.ja
                if item.attrib('base') in ('cái', 'chiếc') and _is_person(_item(nxt)):
                    unit = '人'
                ja = prev.ja + unit + 'の'
                _set(out[-1], ja=ja, surface=out[-1].surface + ' ' + word.surface, classifier_unit=item.attrib('base'))
                out[-1].surface += ' ' + word.surface
            elif prev is not None and prev.attrib('determiner'):
                out[-1].surface += ' ' + word.surface
            _set(nxt, measure=item.attrib('base'))
            _drop(word)
            continue
        if item is not None and item.attrib('plural_marker'):
            nxt = next((w for w in words[k + 1:k + 3] if _pos(w) in ('noun', 'pronoun')), None)
            if nxt is not None:
                nit = _item(nxt)
                _set(nxt, _=[t for t in nit._ or [] if t[1] == 'pl'] or nit._, plural_marker=word.surface)
                _drop(word)
                continue
        out.append(word)
    return out


def _noun_data_of(word):
    item = _item(word)
    ja, gloss_lang, _ = morphology.gloss(word.surface, 'noun')
    return dict(pos='noun', ja=ja or item.ja, gloss_lang=gloss_lang or 'ja', _=_cngs(('Nom', 'Acc')), classifier=None,
                main=True, lemma=word.surface, base=word.surface)


def possessives(words):
    """của + 名詞 (sách của tôi「私の本」) は名詞を属格に、của を落とす。名詞 + 代名詞 (mẹ tôi「私の母」) も属格"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.attrib('possessive_marker'):
            nxt = next((w for w in words[k + 1:k + 4] if _pos(w) in ('noun', 'pronoun')), None)
            if nxt is not None:
                if _pos(nxt) == 'pronoun':
                    _possessive_pronoun(nxt)
                else:
                    _set(nxt, _=_cngs(('Gen',)), possessor=True)
                _drop(word)
                continue
        if item is not None and item.pos == 'pronoun' and out and _pos(out[-1]) == 'noun' and \
                not item.attrib('desc') and item._ and all(t[0] == 'Gen' for t in item._):
            _possessive_pronoun(word)   # mẹ tôi「私の母」: 代名詞は前の名詞の所有者
        out.append(word)
    return out


def _possessive_pronoun(word):
    """所有者の代名詞 → 名詞に掛かる「〜の」(sách của tôi・mẹ tôi の tôi「私の」)"""
    item = _item(word)
    _set(word, pos='adj', ja=item.ja.split(',')[0] + 'の', _=_cngs(ALL_CASES), possessive=True, possessor=True)


def bare_numerals(words):
    """量詞の無い数詞 + 名詞: một + 名詞は「ある」(một nhà văn「ある作家」)、数える名詞 (người・ngày・năm …) は
    数詞と1語に (hai người「二人」、ba ngày「三日」)、ほかは「〜つの」"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        prev = _item(out[-1]) if out else None
        if item is not None and item.pos == 'noun' and prev is not None and prev.attrib('numeral') and \
                not prev.attrib('classifier_unit') and prev.attrib('value') is not None:
            nxt = _item(words[k + 1]) if k + 1 < len(words) else None
            unit = morphology.CLASSIFIERS.get(_low(word))
            if unit and nxt is not None and nxt.pos == 'noun':
                # 数える名詞が量詞の働き (hai người bạn「二人の友人」)
                _set(out[-1], ja=prev.ja + unit + 'の', surface=out[-1].surface + ' ' + word.surface,
                     classifier_unit=_low(word))
                out[-1].surface += ' ' + word.surface
                _set(words[k + 1], measure=_low(word), _=item._)   # 格は数える名詞のもの (Stanza は後ろの名詞を nmod に)
                _drop(word)
                continue
            if unit:
                together = out[-1].surface + ' ' + word.surface
                _set(word, ja=prev.ja + unit, gloss_lang='ja', surface=together, count=prev.attrib('value'))
                word.surface = together
                _drop(out.pop())
            elif prev.attrib('value') == 1:
                _set(out[-1], ja='ある')
            else:
                _set(out[-1], ja=prev.ja + 'つの')
        out.append(word)
    return out


def serial_modals(words, tokens):
    """動詞 + 補語の動詞 (Stanza の xcomp) で、前の動詞が助動詞の表のもの (thích ăn「食べるのが好きだ」、
    muốn đi「行きたい」、bắt đầu học「学び始める」) は1語に"""
    from dragoman.core.japanese import attach_auxiliary
    by_i = {w.doc_i: w for w in words if getattr(w, 'doc_i', None) is not None}
    for token in tokens:
        if token.dep_ != 'xcomp' or token.head.i >= token.i or token.i not in by_i or token.head.i not in by_i:
            continue
        first, second = by_i[token.head.i], by_i[token.i]
        modal = _low(first)
        if _pos(first) != 'verb' or _pos(second) != 'verb' or modal not in morphology.MODALS or \
                getattr(first, 'merged_into', False):
            continue
        it, it2 = _item(first), _item(second)
        if modal == 'bắt đầu':
            ja = ','.join(_masu(j) + '始める' for j in it2.ja.split(',')[:1])
        else:
            ja = ','.join(attach_auxiliary(j, morphology.MODALS[modal]) for j in it2.ja.split(',')[:1])
        _set(second, ja=ja if it2.attrib('gloss_lang') == 'ja' else it2.ja, tense=it.attrib('tense'),
             mood=it.attrib('mood'), modal=modal, form='%s + 動詞' % modal,
             **({'form': it.attrib('form') + ' / %s + 動詞' % modal} if it.attrib('form') else {}))
        second.surface = first.surface + ' ' + second.surface
        _set(second, surface=second.surface)
        _drop(first)
    return [w for w in words if not getattr(w, 'merged_into', False)]


def _masu(verb):
    try:
        from dragoman.kobun.modernize import Modern
        return Modern.masu_stem(verb)
    except Exception:
        return verb


def degrees(words):
    """rất + 形容詞「とても〜」、形容詞 + lắm / quá「とても〜」を1語に"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos in ('adj', 'verb') and out and _low(out[-1]) in morphology.DEGREE_BEFORE and \
                _pos(out[-1]) in ('adv', 'adj') and item.attrib('gloss_lang') == 'ja':
            adv = morphology.DEGREE_BEFORE[_low(out[-1])]
            together = out[-1].surface + ' ' + word.surface
            _set(word, ja=','.join(adv + j for j in item.ja.split(',')[:2]), surface=together, degree=_low(out[-1]))
            word.surface = together
            _drop(out.pop())
        if item is not None and item.pos == 'adj' and k + 1 < len(words) and _low(words[k + 1]) in morphology.DEGREE_AFTER \
                and _pos(words[k + 1]) in ('adv', 'adj', 'particle') and _item(word).attrib('gloss_lang') == 'ja':
            item = _item(word)
            adv = morphology.DEGREE_AFTER[_low(words[k + 1])]
            if adv in ('最も', 'もっと') and _low(words[k + 1]) == 'hơn':
                adv = 'より'
            if not item.attrib('degree'):
                _set(word, ja=','.join(adv + j for j in item.ja.split(',')[:2]))
            word.surface = word.surface + ' ' + words[k + 1].surface
            _set(word, surface=word.surface)
            _drop(words[k + 1])
        if getattr(word, 'merged_into', False):
            continue
        out.append(word)
    return out


def _experienced(verb):
    try:
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as V
        return JaVerb(verb).form(V.INDICATIVE | V.PERFECT, False) + 'ことがある'
    except Exception:
        return verb + 'ことがある'


def _just_done(verb):
    try:
        from dragoman.core.japanese import JaVerb
        from dragoman.core import verb_flags as V
        return JaVerb(verb).form(V.INDICATIVE | V.PERFECT, False) + 'ばかりだ'
    except Exception:
        return verb + 'ばかりだ'


def aspects(words):
    """動詞の前の相の副詞 (đã・đang・sẽ・vừa・từng …)・否定 (chưa・đừng)・hãy を後ろの動詞の時制・法に。
    動詞の後ろの rồi「もう〜した」も完了。相の語は訳に出さない"""
    out = []
    pending = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'aspect':
            pending.append(item)
            continue
        if item is not None and item.attrib('negation'):
            pending.append(item)
            out.append(word)
            continue
        if item is not None and item.pos in ('verb', 'adj') and pending:
            data = dict(item.item)
            forms = []
            experiential = any(p.attrib('aspect') == 'experiential' for p in pending)
            for p in pending:
                aspect = p.attrib('aspect')
                if experiential and aspect == 'perfect':
                    continue   # đã từng「〜したことがある」(đã の過去を重ねない)
                if aspect == 'experiential' and data.get('gloss_lang') == 'ja' and item.pos == 'verb':
                    data['ja'] = ','.join(_experienced(j) for j in data['ja'].split(',')[:2])
                elif aspect == 'perfect' and p.attrib('base') in ('vừa', 'mới', 'vừa mới') and \
                        data.get('gloss_lang') == 'ja' and item.pos == 'verb':
                    data['ja'] = ','.join(_just_done(j) for j in data['ja'].split(',')[:1])
                elif aspect and item.pos == 'verb':
                    data['tense'] = aspect
                if p.attrib('imperative'):
                    data.update(mood='imperative', person=2)
                    forms.append('命令 (hãy + 動詞)')
                if p.attrib('prohibitive'):
                    data.update(mood='imperative', person=2)
                    forms.append('禁止 (%s + 動詞「〜するな」)' % p.attrib('base'))
                if p.attrib('neg_word') == 'chưa' and item.pos == 'verb':
                    data['tense'] = 'progressive'   # chưa ăn「まだ 食べていない」
                    forms.append('chưa + 動詞「まだ〜ない」')
                if aspect:
                    forms.append(morphology.ASPECT_FORMS.get(p.attrib('base'), ''))
            if forms:
                data['form'] = ' / '.join(f for f in forms if f)
            word.items = [type(item)(data)]
            pending = []
        elif item is not None and item.pos not in ('adv', 'modal', 'particle'):
            pending = []
        if _low(word) == 'rồi' and out and _pos(out[-1]) in ('verb',) or \
                _low(word) == 'rồi' and any(_pos(w) == 'verb' for w in out) and k >= len(words) - 2:
            verb = next((w for w in reversed(out) if _pos(w) == 'verb'), None)
            if verb is not None:
                _set(verb, tense='perfect', form='完了 (動詞 + rồi「もう〜した」)')
                continue
        out.append(word)
    return out


def time_words(words):
    """相の副詞の無い動詞の時制を時の語から (hôm qua「昨日」→ 過去、ngày mai「明日」→ 未来)"""
    tense = next((_item(w).attrib('time_tense') for w in words if _item(w) is not None and _item(w).attrib('time_tense')),
                 None)
    if tense is None:
        return
    for word in words:
        item = _item(word)
        if item is not None and item.pos == 'verb' and item.attrib('tense') == 'present' and not item.attrib('copula') \
                and not item.attrib('form'):
            _set(word, tense=tense)


def modals(words):
    """助動詞 (muốn・có thể・phải …) + 動詞を1語に (muốn đi「行きたい」)"""
    from dragoman.core.japanese import attach_auxiliary
    out = []
    pending = None
    for word in words:
        item = _item(word)
        if item is not None and item.pos == 'modal':
            pending = word
            continue
        if pending is not None and item is not None and item.pos in ('verb', 'adj'):
            modal = _item(pending).attrib('modal')
            suffix = morphology.MODALS[modal]
            ja = item.ja
            if item.attrib('gloss_lang') == 'ja':
                if modal == 'hãy':
                    _set(word, mood='imperative', person=2)
                else:
                    ja = ','.join(attach_auxiliary(j, suffix) for j in item.ja.split(',')[:1])
            _set(word, ja=ja, modal=modal, main_ja=item.ja, surface=pending.surface + ' ' + word.surface,
                 form='助動詞 %s + 動詞' % modal)
            word.surface = pending.surface + ' ' + word.surface
            pending = None
        elif pending is not None and item is not None and item.pos not in ('adv', 'aspect'):
            out.append(pending)   # 助動詞の後ろに動詞が無い (Tôi muốn cà phê「コーヒーが 欲しい」): 動詞として
            _set(pending, **_verb(pending.surface, _low(pending)))
            pending = None
        out.append(word)
    if pending is not None:
        _set(pending, **_verb(pending.surface, _low(pending)))
        out.append(pending)
    return out


def passives(words):
    """bị・được + (動作主) + 動詞: 動詞を受動に、動作主は「〜によって」(Tôi bị mẹ mắng「私は 母に 叱られた」)"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is None or not item.attrib('passive'):
            out.append(word)
            continue
        verb = next((w for w in words[k + 1:k + 5] if _pos(w) == 'verb'), None)
        if verb is None:
            _set(word, **_verb(word.surface, _low(word)))   # được「得る」・bị「被る」(動詞の無い文)
            out.append(word)
            continue
        kind = '被害' if _low(word) == 'bị' else '恩恵'
        _set(verb, voice='passive', form='受動 (%s + 動詞、%s)' % (_low(word), kind))
        agent = words[k + 1] if k + 1 < len(words) and words[k + 1] is not verb and \
            _pos(words[k + 1]) in ('noun', 'pronoun') else None
        if agent is not None:
            by = Word('(bởi)', [{'surface': '(bởi)', 'pos': 'preposition', 'base': 'bởi', 'dominates': 'Gen',
                                 'ja': '〜によって', 'gloss_lang': 'ja'}])
            by.token_ix = getattr(word, 'token_ix', None)
            out.append(by)
            _set(agent, _=_cngs(('Gen',)))
        _drop(word)
    return out


COPULA = {'surface': '(là)', 'pos': 'verb', 'lemma': 'là', 'pres1sg': 'là', 'base': 'là', 'ja': '〜である',
          'gloss_lang': 'ja', 'voice': 'active', 'mood': 'indicative', 'tense': 'present', 'person': 3, 'number': 'sg',
          'copula': True, 'desc': '省略された繋辞 (形容詞の述語)'}


def adjective_predicates(words):
    """形容詞の述語 (Trời đẹp) の前に見えない繋辞を補う (共通の解析器の形容詞の補語「空は 美しい」)"""
    out = []
    for k, word in enumerate(words):
        item = _item(word)
        if item is not None and item.pos == 'adj' and item.attrib('predicative'):
            k_out = len(out)
            while k_out > 0 and _item(out[k_out - 1]) is not None and _item(out[k_out - 1]).attrib('negation'):
                k_out -= 1   # 否定 (không đẹp) の前に
            cop = Word('(là)', [dict(COPULA, tense=item.attrib('tense') or 'present')])
            cop.token_ix = getattr(word, 'token_ix', None)
            cop.doc_i = None
            out.insert(k_out, cop)
        out.append(word)
    return out


def questions(words, marks):
    """文末の không・chưa (có … không?「〜か」) と疑問の助詞は疑問: 文末の？が無ければ補う。có は落とす"""
    content = [w for w in words if w.items is not None]
    last = content[-1] if content else None
    question = False
    if last is not None and _low(last) in morphology.QUESTION_PARTICLES and len(content) > 1 and \
            (_item(last).attrib('negation') or _item(last).attrib('final') or _pos(last) in ('adv', 'particle')):
        question = True
        _drop(last)
        if _low(last) == 'chưa':
            verb = next((w for w in reversed(content) if _pos(w) == 'verb'), None)
            if verb is not None:
                _set(verb, tense='perfect')   # Bạn ăn cơm chưa?「もう ご飯を 食べたか」
    for k, w in enumerate(words):
        if _item(w) is not None and _item(w).attrib('desc') in ('疑問代名詞', '疑問詞') and \
                not any(_pos(v) == 'verb' and _item(v).attrib('lemma') in QUESTION_VERBS for v in words[:k]):
            question = True   # 疑問詞の疑問文 (間接疑問 Tôi không biết anh ấy ở đâu は除く)
    if question and (not marks or marks[-1] not in ('?',)):
        marks.append('?')
    if question:
        for w in words:
            it = _item(w)
            if it is not None and it.attrib('kinship') and it._ and it._[0][0] == 'Nom':
                _set(w, ja=morphology.KINSHIP[it.attrib('base')], person=2)   # Anh có khỏe không?「あなたは 元気か」
    return [w for w in words if not getattr(w, 'merged_into', False) and
            not (_item(w) is not None and (_item(w).attrib('affirmative') or _item(w).attrib('final') or
                                           _item(w).attrib('topic')))]


def relative_clauses(words, tokens):
    """名詞 + (mà) + 節: 節を名詞の訳に組み込む (quyển sách mà anh cho tôi「あなたが 私に くれた 本」)。
    Stanza の acl・acl:relcl と、mà で始まる節"""
    by_i = {w.doc_i: w for w in words if getattr(w, 'doc_i', None) is not None}
    for token in tokens:
        verb, head = None, None
        if token.dep_.startswith('acl') and token.pos_ in ('VERB', 'ADJ') and token.head.i < token.i and \
                token.head.pos_ in ('NOUN', 'PROPN'):
            verb, head = token, token.head
        elif token.text.lower() == 'mà' and token.i > 0 and tokens[token.i - 1].pos_ in ('NOUN', 'PROPN', 'PRON') and \
                token.head.i > token.i and token.head.pos_ in ('VERB', 'ADJ'):
            verb, head = token.head, tokens[token.i - 1]
            while head.dep_ in ('nmod:poss', 'det:pmod', 'amod', 'nmod') and head.head.i < head.i:
                head = head.head
        if verb is None or head.i not in by_i or verb.i not in by_i or _pos(by_i[head.i]) not in ('noun', 'pronoun'):
            continue
        sub = [t for t in verb.subtree if t.i > head.i and t.i != head.i and t.pos_ != 'PUNCT']
        if not sub:
            continue
        sub_words = [by_i[t.i] for t in sub if t.i in by_i and not getattr(by_i[t.i], 'merged_into', False)]
        clause = _clause_ja(sub, by_i, verb)
        noun = by_i[head.i]
        it = _item(noun)
        data = dict(it.item, ja=clause + it.ja.split(',')[0], gloss_lang='ja', noun_ja=it.ja,
                    relative=' '.join(t.text for t in sub))
        noun.items = [type(it)(data)]
        for w in sub_words:
            _drop(w)
    return [w for w in words if not getattr(w, 'merged_into', False)]


def _clause_ja(sub, by_i, verb_token):
    """関係節の語 → 日本語 (anh cho tôi → あなたが私にくれた)"""
    parts, verb, negative, tense = [], '', False, 'present'
    for t in sub:
        w = by_i.get(t.i)
        it = _item(w) if w is not None else None
        low = t.text.lower()
        if low == 'mà' or it is None:
            continue
        if low in morphology.ASPECTS:
            tense = morphology.ASPECTS[low]
            continue
        if it.attrib('negation'):
            negative = True
            continue
        if t.i == verb_token.i:
            verb = (it.ja or '').split(',')[0]
            continue
        if it.pos in ('noun', 'pronoun'):
            particle = 'が' if t.dep_.startswith('nsubj') else 'に' if t.dep_ == 'iobj' or \
                (t.dep_ == 'obj' and verb_token.text.lower() == 'cho') else 'を' if t.dep_ == 'obj' else 'の'
            ja = it.ja.split(',')[0]
            if verb_token.text.lower() == 'cho' and it.attrib('base') == 'tôi':
                particle = 'に'
            parts.append(ja + particle)
        elif it.pos in ('adv', 'adj'):
            parts.append(it.ja.split(',')[0])
    if verb_token.text.lower() == 'cho' and any(p.endswith('私に') for p in parts):
        verb = 'くれる'
    if verb:
        try:
            from dragoman.core.japanese import JaVerb
            from dragoman.core import verb_flags as V
            flag = V.INDICATIVE | (V.PERFECT if tense in ('perfect', 'experiential') else 0)
            if verb_token.pos_ == 'VERB' and tense == 'present' and verb_token.text.lower() == 'cho':
                flag |= V.PERFECT
            verb = JaVerb(verb).form(flag, negative) if verb_token.pos_ == 'VERB' else verb
        except Exception:
            pass
    return ''.join(parts) + verb


def nationalities(words):
    """người + 国名 (người Nhật「日本人」)、tiếng + 国名 (tiếng Việt「ベトナム語」) を1語に"""
    out = []
    for word in words:
        prev = out[-1] if out else None
        if prev is not None and _low(prev) in ('người', 'tiếng') and _pos(prev) == 'noun' and \
                _low(word) in (morphology.NATIONS if _low(prev) == 'người' else morphology.LANGUAGE_NAMES):
            ja = (morphology.NATIONS[_low(word)] + '人') if _low(prev) == 'người' else \
                (morphology.LANGUAGE_NAMES[_low(word)] + '語')
            together = prev.surface + ' ' + word.surface
            _set(prev, ja=ja, gloss_lang='ja', surface=together, lemma=together, base=together)
            prev.surface = together
            _drop(word)
            continue
        out.append(word)
    return out


def kinship_vocatives(words):
    """親族名詞の代名詞が命令文の主語なら聞き手 (Anh hãy đi đi「あなたは 行きなさい」)"""
    if any(_item(w) is not None and _item(w).attrib('mood') == 'imperative' for w in words):
        for w in words:
            it = _item(w)
            if it is not None and it.attrib('kinship'):
                _set(w, ja=morphology.KINSHIP[it.attrib('base')], person=2)
                break


DIRECTIONS = {'xuống', 'lên', 'ra', 'vào', 'lại', 'về', 'dậy', 'qua', 'sang', 'đi', 'tới', 'đến'}
COMPLEMENT_GLOSSES = {('ngồi', 'xuống'): '座る', ('đứng', 'lên'): '立ち上がる', ('đứng', 'dậy'): '立ち上がる',
                      ('đi', 'ra'): '出て行く', ('đi', 'vào'): '入って行く', ('chạy', 'ra'): '走り出る',
                      ('đi', 'về'): '帰る', ('trở', 'về'): '帰る', ('quay', 'lại'): '戻る', ('nhìn', 'lên'): '見上げる',
                      ('nằm', 'xuống'): '横になる', ('mang', 'đến'): '持って来る', ('mang', 'đi'): '持って行く',
                      ('lấy', 'ra'): '取り出す', ('bước', 'vào'): '入る', ('bước', 'ra'): '出る', ('nhảy', 'lên'): '跳び上がる'}


def complements(words, tokens):
    """動詞 + 方向の動詞 (ngồi xuống「座る」、đứng lên「立ち上がる」) を1語に。đi + 動詞 (đi ngủ「寝に行く」) も"""
    out = []
    for k, word in enumerate(words):
        prev = out[-1] if out else None
        if prev is not None and _pos(prev) == 'verb' and _low(word) in DIRECTIONS and \
                getattr(word, 'doc_i', None) is not None and tokens[word.doc_i].head.i == getattr(prev, 'doc_i', -1) and \
                tokens[word.doc_i].dep_ in ('advmod', 'compound:dir', 'compound:svc', 'xcomp', 'compound', 'dep'):
            it = _item(prev)
            ja = COMPLEMENT_GLOSSES.get((_low(prev), _low(word)), it.ja)
            together = prev.surface + ' ' + word.surface
            _set(prev, ja=ja, surface=together, form='方向の補語 (動詞 + %s)' % _low(word))
            prev.surface = together
            continue
        if prev is not None and _low(prev) == 'đi' and _pos(prev) == 'verb' and _pos(word) == 'verb' and \
                getattr(word, 'doc_i', None) is not None and tokens[word.doc_i].head.i == getattr(prev, 'doc_i', -1) and \
                _item(word).attrib('gloss_lang') == 'ja':
            it, it2 = _item(prev), _item(word)
            together = prev.surface + ' ' + word.surface
            ja = ','.join(_masu(j) + 'に行く' for j in it2.ja.split(',')[:1])
            _set(word, ja=ja, surface=together, tense=it.attrib('tense'), mood=it.attrib('mood'),
                 form='đi + 動詞「〜しに行く」')
            word.surface = together
            out[-1] = word
            continue
        out.append(word)
    return out


WEATHER = {'mưa': '雨が降る', 'nắng': '晴れる', 'gió': '風が吹く', 'sấm': '雷が鳴る', 'tuyết': '雪が降る',
           'tối': '暗くなる', 'sáng': '明るくなる', 'lạnh': '寒い', 'nóng': '暑い'}


def weather(words):
    """trời + mưa「雨が降る」(Stanza は mưa を trời に掛かる名詞と読む) を1つの動詞に"""
    out = []
    for word in words:
        prev = out[-1] if out else None
        if prev is not None and _low(prev) == 'trời' and _low(word) in WEATHER and _pos(word) in ('noun', 'verb'):
            together = prev.surface + ' ' + word.surface
            data = _verb(together, together, ja=WEATHER[_low(word)], gloss_lang='ja')
            data.update({k: v for k, v in _item(word).item.items() if k in ('tense', 'form')})
            if _low(word) in ('lạnh', 'nóng'):
                continue
            prev.items = [type(_item(prev))(data)]
            prev.surface = together
            continue
        out.append(word)
    return out


def pronoun_phrases(words):
    """親族名詞 + ấy (anh ấy「彼」、chị ấy「彼女」) を代名詞1語に。代名詞 + tên (Anh tên là gì?「あなたの名前は 何か」) は所有"""
    out = []
    for k, word in enumerate(words):
        prev = out[-1] if out else None
        if prev is not None and _low(word) == 'ấy' and (_low(prev) + ' ấy') in morphology.PRONOUNS:
            key = _low(prev) + ' ấy'
            ja, person, number = morphology.PRONOUNS[key]
            cases = (_item(prev)._ if _item(prev) is not None and _item(prev)._ else _cngs(('Nom', 'Acc')))
            gender = morphology.PRONOUN_GENDERS.get(key, GENDER)
            prev.items = [type(_item(prev))({'surface': prev.surface + ' ' + word.surface, 'pos': 'pronoun', 'base': key,
                                             'ja': ja, 'gloss_lang': 'ja', 'person': person, 'number': number,
                                             '_': [(c, n, gender) for c, n, _ in cases], 'compact': True,
                                             **({'clause_start': True} if _item(prev).attrib('clause_start') else {})})]
            prev.surface += ' ' + word.surface
            continue
        if prev is not None and _low(word) == 'tên' and (_low(prev) in morphology.PRONOUNS or _low(prev) in morphology.KINSHIP):
            low = _low(prev)
            ja = morphology.KINSHIP.get(low) or morphology.PRONOUNS[low][0].split(',')[0]
            prev.items = [type(_item(prev) or _item(word))({'surface': prev.surface, 'pos': 'adj', 'base': low,
                                                            'ja': ja + 'の', 'gloss_lang': 'ja', '_': _cngs(ALL_CASES),
                                                            'possessive': True, 'possessor': True, 'prenominal': True})]
            _set(word, _=_cngs(('Nom',)))
            out.append(word)
            continue
        out.append(word)
    return out


def lookup_all(surfaces):
    global _tokens
    tokens = morphology.parse(surfaces)
    _tokens = tokens
    words = []
    for token in tokens:
        data = item_of(token, surfaces[token.i])
        word = Word(surfaces[token.i], None if data is None else [data])
        word.token_ix = token.i
        word.doc_i = token.i
        words.append(word)
    words = relative_clauses(words, tokens)
    words = pronoun_phrases(words)
    words = weather(words)
    words = nationalities(words)
    words = numerals(words)
    words = classifiers(words)
    words = bare_numerals(words)
    words = possessives(words)
    words = passives(words)
    words = aspects(words)
    words = modals(words)
    words = serial_modals(words, tokens)
    words = complements(words, tokens)
    time_words(words)
    words = degrees(words)
    kinship_vocatives(words)
    words = [w for w in words if not getattr(w, 'merged_into', False)]
    words = adjective_predicates(words)
    for i, word in enumerate(words):
        word.index = i
    return words


def analyze_sentence(surfaces):
    surfaces = list(surfaces)
    words = lookup_all(surfaces)
    marks = [s for s in surfaces if s in PUNCTUATION]
    words = questions(words, marks)
    if marks[-1:] == ['?'] and (not words or words[-1].surface != '?'):
        q = Word('?', None)
        q.token_ix = None
        words = [w for w in words if w.surface not in ('.',)] + [q]
    words = [w for w in words if not (_pos(w) == 'particle')]
    for i, word in enumerate(words):
        word.index = i
    word_details = [word.detail() for word in words]
    with language.using(VIETNAMESE):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
