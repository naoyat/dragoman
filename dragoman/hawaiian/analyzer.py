#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ハワイ語の文の解析
#
# 語形はほとんど変わらず、語順 (動詞 - 主語 - 目的語) と小辞が文の形を決めるので、節 (句読点・接続詞で区切る) の頭から
# 順に読んで語の役割 (格) を決め、並列・係り先・格の枠・日本語訳は共通の解析器 (core/analyzer.py) をハワイ語の設定
# (HAWAIIAN) で使う:
#   - 動詞: 時制・相の小辞の後ろ (ua 完了「〜した」、e … ana 未完了・未来「〜する (だろう)」、ke … nei 進行「〜している」)、
#     否定 ʻaʻole (+ i で過去) の後ろ、無ければ節の頭の動詞の読みのある語 (Nani ka wahine「その女は美しい」: 状態の動詞)。
#     動詞の後ろの ʻia は受け身、mai・aku・iho・aʻe (方向) は訳さない。mai + 動詞は禁止「〜するな」
#   - 名詞句: 冠詞 (ke / ka「その」、nā 複数、he「ある」) は名詞に掛けて訳さない。指示詞 kēia「この」、所有の語 kaʻu / koʻu「私の」
#     (a 類・o 類) は名詞の前、状態の動詞 (nui「大きい」) と nei・lā は名詞の後ろ。名詞の後ろの o / a + 名詞句は所有「〜の」
#   - 役割: 動詞の後ろの印の無い最初の名詞句・代名詞は主語「が」、ʻo + 名詞句も主語、i / iā + 名詞句は目的語「を」
#     (移動の動詞の後ろでは「〜へ」)、ma・mai・me・no・na は前置詞「〜で・〜から・〜と・〜のために」、受け身の e は動作主
#   - 動詞の無い文: He kumu ʻo ia「彼は先生である」・ʻO ia ke kumu「彼がその先生である」には見えない繋辞、
#     Aia ka puke ma ka papa「本はテーブルの上にある」の aia は「ある・いる」
#   - 綴り: ʻokina・長音符の無い本文 (19世紀の新聞・聖書) も読む。機能語は綴りが合わなければ鍵の同じ候補から文脈で選び、
#     辞書の語は鍵で引いて綴りの合うものを先に (hawaiian/orthography.py)
#
import re

from dragoman.core import analyzer as common
from dragoman.core import language
from dragoman.core.Word import Word
from . import dictionary, morphology, orthography

PUNCTUATION = {'.': 'period', '!': 'period', '?': 'question', ',': 'comma', ';': 'comma', ':': 'comma',
               '"': None, '“': None, '”': None, '(': 'comma', ')': 'comma', '—': 'comma', '–': 'comma'}
LETTER = "A-Za-zĀĒĪŌŪāēīōūʻ'‘`’"
TOKEN = re.compile(r"[%s]+(?:-[%s]+)*|[0-9]+|[.!?,;:\"“”()—–]" % (LETTER, LETTER))
CASES = ('Nom', 'Acc', 'Gen', 'Dat')
GENDER = None
# i + 名詞句を「〜へ・〜に」(場所・方向) と読む移動・所在の動詞 (ほかの動詞の i は目的語「を」)
MOTION = {'hele', 'hoʻi', 'holo', 'lele', 'kū', 'noho', 'hiki', 'piʻi', 'iho', 'komo', 'puka', 'haʻalele', 'mai', 'loaʻa'}
# 動詞の直後で動詞を修飾する状態の動詞 (aloha nui「とても愛する」・hana pono「正しく行う」)
ADVERBIAL_STATIVES = {'nui': 'とても', 'loa': 'とても', 'pono': '正しく', 'maikai': 'よく', 'wikiwiki': '速く',
                      'mau': 'いつも', 'hou': '再び'}
# i + 名詞句を「〜に」と読み、主語を「ある」の主語にする所有・獲得の動詞 (Loaʻa iaʻu ke kaʻa「私に車がある」)
POSSESSION = {'loaʻa'}


def _root_items(lemma):
    return []


def predicative_adjective(adj, noun):
    """述語の形容詞 (状態の動詞を補語にしたもの: ua maikaʻi「良かった」) は名詞に掛けない"""
    return isinstance(adj, Word) and getattr(adj, 'predicate', False)


def particle(case, obj, pred):
    """ʻo の名詞句 (主語・主題) は「は」(He kumu ʻo ia「彼は先生である」)"""
    if isinstance(obj, Word) and getattr(obj, 'focus', False) and case == 'Nom':
        return 'は'
    return None


HAWAIIAN = language.Language(
    name='haw',
    and_words=('a me', 'a'),
    or_words=('a i ʻole',),
    copulas=frozenset({'(he)'}),
    negations=frozenset({'ʻaʻole', 'aole', "a'ole", '(mai)'}),
    case_particles={'Nom': 'が', 'Acc': 'を', 'Gen': 'の', 'Dat': 'に'},
    absolute_case=None,
    lookup=_root_items,
    particle=particle,
    predicative_adjective=predicative_adjective,
    dictionary=dictionary,
    pronoun_subject=True,
    genitive_follows_head=True,
    objects_follow_verb=True,
    topic_first=True,
    possessor_cases=(),
)

COPULA = {'pos': 'verb', 'pres1sg': '(he)', 'lemma': '(he)', 'base': '(繋辞なし)', 'ja': 'である', 'gloss_lang': 'ja',
          'voice': 'active', 'mood': 'indicative', 'tense': 'present', 'person': None, 'number': None,
          'copula': True, 'surface': '(he)'}


def tokens(text):
    out = [orthography.normalize(t) for t in TOKEN.findall(orthography.normalize(text))]
    merged = []
    i = 0
    while i < len(out):   # 2語以上の機能語 (no ka mea・a me …) を1語に
        for words, joined in sorted(morphology.MULTIWORD.items(), key=lambda kv: -len(kv[0])):
            n = len(words)
            if [orthography.key(w) for w in out[i:i + n]] == [orthography.key(w) for w in words]:
                merged.append(' '.join(out[i:i + n]))
                i += n
                break
        else:
            merged.append(out[i])
            i += 1
    return merged


def sentences(text):
    current = []
    for line in text.splitlines():
        for token in tokens(line):
            current.append(token)
            if PUNCTUATION.get(token) in ('period', 'question'):
                yield current
                current = []
    if current:
        yield current


# ----------------------------------------------------------------------
# 辞書の読み

def _gloss(word, pos, en):
    from dragoman.core import en_ja
    hand = morphology.gloss(word, pos)
    if hand:
        return hand, 'ja'
    ja = en_ja.translate(en, pos if pos in ('noun', 'verb', 'adj', 'adv') else 'noun', limit=2) if en else None
    return (ja, 'ja') if ja else (en or word, 'en')


def content(token):
    """内容語の読み: [(品詞, 見出し, 訳, 訳の言語, 複数)]。複数形 (kānaka) は見出し (kanaka) の複数"""
    out = []
    spelled = orthography.normalize(token).lower()
    # 複数形 (kānaka ← kanaka): 綴りが複数形と同じときだけ。長音符の無い綴り (kanaka) は単数を先に、複数は後ろの候補に
    # (表の鍵は長音符を除くので、単数の kanaka も複数形 kānaka に当たる)
    exact_plural, unmarked_plural = [], []
    for form, lemma, pos, tags in dictionary.forms(token):
        if 'plural' not in tags or orthography.normalize(lemma).lower() == spelled:
            continue
        if orthography.normalize(form).lower() == spelled:
            exact_plural.append((lemma, pos))
        elif not orthography.marked(token):
            unmarked_plural.append((lemma, pos))
    for lemma, pos in exact_plural:
        for row in dictionary.lemmas(lemma, pos):
            ja, lang = _gloss(row['word'], row['pos'], row['en'])
            out.append((row['pos'], row['word'], ja, lang, True))
    alternatives = [(lemma, pos) for form, lemma, pos, tags in dictionary.forms(token) if 'plural' not in tags]
    rows = list(dictionary.lemmas(token))
    for lemma, pos in alternatives:   # 異綴り (wau = au)
        rows += [r for r in dictionary.lemmas(lemma, pos) if r not in rows]
    for row in rows:
        pos = {'name': 'noun', 'det': 'adj', 'num': 'adj'}.get(row['pos'], row['pos'])
        if pos not in ('noun', 'verb', 'adj', 'adv'):
            continue
        ja, lang = _gloss(row['word'], 'noun' if pos == 'noun' else pos, row['en'])
        if row['pos'] == 'name':
            from dragoman.core.katakana_names import latin
            ja, lang = latin(orthography.key(row['word'])), 'ja'
        out.append((pos, row['word'], ja, lang, False, row['pos'] == 'name'))
    for lemma, pos in unmarked_plural:   # 長音符の無い綴りの複数の読み (冠詞 nā の後ろで選ぶ)
        for row in dictionary.lemmas(lemma, pos):
            ja, lang = _gloss(row['word'], row['pos'], row['en'])
            out.append((row['pos'], row['word'], ja, lang, True))
    out = [x if len(x) == 6 else x + (False,) for x in out]
    if token[:1].isupper():   # 大文字の語は名前を先に
        out.sort(key=lambda x: not x[5])
    else:
        out.sort(key=lambda x: x[5])
    return out


def _guess(token):
    """辞書に無い語: 使役の hoʻo-、重ね (wikiwiki → wiki) を外して引く。大文字なら名前 (カタカナ)"""
    k = orthography.normalize(token)
    for prefix in ('hoʻo', 'hoo', 'ho'):
        if k.lower().startswith(prefix) and len(k) > len(prefix) + 2:
            found = [x for x in content(k[len(prefix):]) if x[0] == 'verb']
            if found:
                pos, base, ja, lang, plural, proper = found[0]
                return [('verb', 'hoʻo' + base, ja + 'させる' if lang == 'ja' else 'cause to ' + ja, lang, False, False)]
    half = len(k) // 2
    if len(k) >= 4 and k[:half].lower() == k[half:].lower():
        found = content(k[:half])
        if found:
            return found
    if token[:1].isupper():
        from dragoman.core.katakana_names import latin
        return [('noun', token, latin(orthography.key(token)), 'ja', False, True)]
    return []


# ----------------------------------------------------------------------
# 節の読み

class Clause:
    """節の読みの途中の状態"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.words = []

    def peek(self, k=0):
        j = self.i + k
        return self.tokens[j] if j < len(self.tokens) else None

    def is_(self, table, k=0):
        tok = self.peek(k)
        return tok is not None and bool(morphology.candidates(table, tok))


def _key(token):
    return orthography.key(token or '')


def _spelled(token):
    return orthography.normalize(token or '').lower()


_notes = {}   # 元の語の位置 → (見出し, 働き)。解析で語の列から外した小辞 (ua・ʻia・mai …) の説明 (語の一覧に出す)


def _note(ix, base, text):
    _notes[ix] = (base, text)


def _word(surface, item, ix):
    w = Word(surface, None if item is None else [item])
    w.token_ix = ix
    return w


def _noun_item(surface, entry, case, number):
    pos, base, ja, lang, plural, proper = entry
    item = {'surface': surface, 'pos': 'noun', 'base': base, 'lemma': base, 'ja': ja, 'gloss_lang': lang,
            '_': [(case, 'pl' if plural or number == 'pl' else number, GENDER)]}
    if proper:
        item['proper'] = True
    return item


def parse_np(c, case, start_ix, relative=False, statives=True):
    """名詞句: [冠詞・指示詞・所有の語] 名詞・代名詞 [状態の動詞 (形容詞)] [nei・lā] [o / a + 名詞句 (所有)]。
    → 語のリスト (頭の語と修飾語)。名詞句が無ければ []"""
    words = []
    number = 'sg'
    pre = []
    while c.peek() is not None:
        tok = c.peek()
        art = morphology.candidates(morphology.ARTICLES, tok)
        dem = morphology.candidates(morphology.DEMONSTRATIVES, tok) or morphology.candidates(morphology.NUMERALS, tok)
        pos_ = morphology.candidates(morphology.POSSESSIVES, tok)
        nxt_content = c.peek(1) is not None and c.peek(1) not in PUNCTUATION
        if art and nxt_content:   # 名詞句の中の ke は冠詞 (進行の ke … nei は節の頭で判定)
            spelled, (base, n, definite) = art[0]
            number = 'pl' if n == 'pl' else number
            pre.append(_word(tok, {'surface': tok, 'pos': 'article', 'base': base, 'ja': '', 'gloss_lang': 'ja',
                                   'compact': True, 'definite': definite}, start_ix + c.i))
            c.i += 1
            continue
        if dem and not nxt_content and orthography.normalize(tok).lower() in morphology.DEMONSTRATIVE_PRONOUNS and not pre:
            break   # 名詞の付かない指示詞は代名詞 (下で)
        if pos_ and pos_[0][0] in ('ko', 'kā') and morphology.candidates(morphology.ARTICLES, c.peek(1) or '') and not pre:
            # ko ke ao nei「この世のもの (人々)」: ko / kā + 名詞句は「〜のもの」
            _note(start_ix + c.i, pos_[0][0], '所有の語 %s + 名詞句「〜のもの」(%s 類)' % (pos_[0][0], pos_[0][1][2]))
            c.i += 1
            owner = parse_np(c, 'Gen', start_ix)
            if owner:
                thing = _word('(mea)', {'surface': '(mea)', 'pos': 'noun', 'base': 'mea', 'ja': 'もの', 'gloss_lang': 'ja',
                                        '_': [(case, 'sg', GENDER)]}, None)
                return [thing] + owner
            c.i -= 1
        if (dem or pos_) and nxt_content:
            spelled, (base, ja, *rest) = (dem or pos_)[0]
            if len(pos_) > 1 and not orthography.marked(tok):   # kau: kaʻu「私の」/ kāu「君の」は決められない
                ja = '{%s}' % ','.join(v[1] for _, v in pos_)
            pre.append(_word(tok, {'surface': tok, 'pos': 'adj', 'base': base, 'ja': ja, 'gloss_lang': 'ja',
                                   '_': [(case, n, GENDER) for n in ('sg', 'pl')], 'possessive': bool(pos_),
                                   'class': rest[0] if rest else None}, start_ix + c.i))
            c.i += 1
            continue
        break
    tok = c.peek()
    if tok is None or tok in PUNCTUATION:
        c.i -= len(pre)
        return []
    standalone = orthography.normalize(tok).lower()
    if standalone in morphology.DEMONSTRATIVE_PRONOUNS and not pre:   # kēia「これ」
        word = _word(tok, {'surface': tok, 'pos': 'pronoun', 'base': standalone, 'lemma': standalone,
                           'ja': morphology.DEMONSTRATIVE_PRONOUNS[standalone], 'gloss_lang': 'ja', 'person': 3,
                           'number': 'sg', '_': [(case, 'sg', GENDER)], 'compact': True, 'desc': '指示代名詞'},
                     start_ix + c.i)
        c.i += 1
        return [word]
    question = morphology.candidates(morphology.QUESTION_WORDS, tok)
    if question and question[0][1][2] == 'pronoun':   # 疑問詞 wai「誰」・aha「何」・hea「どこ」
        spelled, (base, ja, _) = question[0]
        word = _word(tok, {'surface': tok, 'pos': 'pronoun', 'base': base, 'lemma': base, 'ja': ja, 'gloss_lang': 'ja',
                           'person': 3, 'number': 'sg', '_': [(case, 'sg', GENDER)], 'compact': True,
                           'desc': '疑問代名詞'}, start_ix + c.i)
        c.i += 1
        for p in pre:
            word.add_modifier(p) if p.items[0].pos == 'article' else None
        return [word]
    pron = morphology.candidates(morphology.PRONOUNS, tok)
    if pron and not pre:
        spelled, (base, ja, person, n) = pron[0]
        if base == 'iaʻu':   # i + au は目的語の形 (所有・移動の動詞の後ろでは「私に」)
            verb_base = orthography.normalize((getattr(c, 'verb', None) or {}).get('base', ''))
            case = 'Dat' if verb_base in MOTION else 'Acc'
        words.append(_word(tok, {'surface': tok, 'pos': 'pronoun', 'base': base, 'lemma': orthography.key(base),
                                 'ja': ja, 'gloss_lang': 'ja', 'person': person, 'number': 'pl' if n == 'du' else n,
                                 '_': [(case, 'pl' if n == 'du' else n, GENDER)], 'compact': True}, start_ix + c.i))
        c.i += 1
    else:
        entries = [e for e in content(tok) if e[0] in ('noun', 'verb', 'adj')] or _guess(tok)
        nouns = [e for e in entries if e[0] == 'noun'] or entries
        # 冠詞の数で単数・複数の読みを選ぶ (nā kanaka → 複数、ke kanaka → 単数)
        nouns = sorted(nouns, key=lambda e: e[4] != (number == 'pl'))
        if not nouns or _function_word(tok):
            c.i -= len(pre)
            return []
        head = _word(tok, _noun_item(tok, nouns[0], case, number), start_ix + c.i)
        c.i += 1
        words.append(head)
        for p in pre:
            if p.items[0].pos == 'article':
                head.add_modifier(p)
            else:
                words.insert(len(words) - 1, p)
        # 名詞の後ろの状態の動詞 (形容詞: ka hale nui「大きい家」) と nei・lā
        while c.peek() is not None and c.peek() not in PUNCTUATION:
            tok = c.peek()
            post = morphology.candidates(morphology.POST_DEMONSTRATIVES, tok)
            if post:
                words.append(_word(tok, {'surface': tok, 'pos': 'adj', 'base': post[0][1][0], 'ja': post[0][1][1],
                                         'gloss_lang': 'ja', '_': [(case, n, GENDER) for n in ('sg', 'pl')]},
                                   start_ix + c.i))
                c.i += 1
                continue
            if _function_word(tok) or not statives:
                break   # 文頭の前置詞句の名詞の後ろは動詞 (I kinohi hana …)
            found = [e for e in content(tok) if e[0] in ('verb', 'adj')]
            noun_mod = [e for e in content(tok) if e[0] == 'noun' and not e[5]]
            if noun_mod and not found and not morphology.candidates(morphology.PRONOUNS, tok):
                # 名詞の後ろの冠詞の無い名詞は修飾語 (ka poʻe naʻau haʻahaʻa「へりくだった心の人々」)。続く状態の動詞も
                c.i += 1
                desc = []
                while c.peek() is not None and not _function_word(c.peek()) and c.peek() not in PUNCTUATION:
                    more = [e for e in content(c.peek()) if e[0] in ('verb', 'adj')]
                    if not more:
                        break
                    desc.append(more[0][2].split(',')[0])
                    c.i += 1
                pos, base, ja, lang, plural, proper = noun_mod[0]
                mod_ja = ''.join(desc) + ja.split(',')[0] + 'の'
                words.append(_word(tok, {'surface': tok, 'pos': 'adj', 'base': base, 'lemma': base, 'ja': mod_ja,
                                         'gloss_lang': 'ja', '_': [(case, n, GENDER) for n in ('sg', 'pl')]},
                                   start_ix + c.i - 1 - len(desc)))
                continue
            if not found:
                break
            pos, base, ja, lang, plural, proper = found[0]
            words.append(_word(tok, {'surface': tok, 'pos': 'adj', 'base': base, 'lemma': base, 'ja': ja,
                                     'gloss_lang': lang, '_': [(case, n, GENDER) for n in ('sg', 'pl')]},
                               start_ix + c.i))
            c.i += 1
    # 関係節: 名詞 + i (過去) / e (… ana) + 動詞 (ka wahine i hīmeni「歌った女」・ke kanaka i ʻike ai au「私が見た人」)
    head = next((w for w in words if w.items and w.items[0].pos == 'noun'), None)   # 代名詞には付けない (ʻoe i hea)
    if relative and head is not None and _key(c.peek()) in ('i', 'e') and c.peek(1) is not None and \
            any(e[0] == 'verb' for e in content(c.peek(1))) and not _function_word(c.peek(1)) and \
            not morphology.candidates(morphology.QUESTION_WORDS, c.peek(1)):
        _relative_clause(c, head, start_ix)
    # 所有: o / a + 名詞句
    while c.peek() is not None and morphology.candidates(morphology.GENITIVES, c.peek()) and c.peek(1) is not None:
        save = c.i
        kind = morphology.candidates(morphology.GENITIVES, c.peek())[0][1][1]
        _note(start_ix + c.i, kind, '所有の印「〜の」(%s 類)' % kind)
        c.i += 1
        genitive = parse_np(c, 'Gen', start_ix)
        if not genitive:
            c.i = save
            break
        words += genitive
    return words


def _relative_clause(c, head, start_ix):
    """関係節を読み、日本語の連体節にして頭の名詞の訳に付ける (タガログ語の関係節と同じ: 節の語は除く)。
    ai があれば頭の名詞は目的語・場所の空所 (私が見た人)、無ければ主語の空所 (歌った女)"""
    from dragoman.kobun.modernize import Modern
    particle = _key(c.peek())
    _note(start_ix + c.i, particle, '関係節の時制の小辞 (%s)' % ('i: 過去' if particle == 'i' else 'e: 未来・未完了'))
    c.i += 1
    first = c.i
    tense = 'perfect' if particle == 'i' else ('progressive' if any(_key(t) == 'ana' for t in c.tokens[c.i:]) else 'future')
    tokens = list(c.tokens[c.i:])
    ana = next((j for j, t in enumerate(tokens) if _key(t) == 'ana'), None) if particle == 'e' else None
    if ana is not None:   # e … ana の閉じ (関係節の中)
        _note(start_ix + c.i + ana, 'ana', '時制・相の小辞の閉じ (e … ana)')
        tokens[ana] = ','   # 語の位置を保つため句読点に (読み飛ばされる)
    inner = parse_clause(tokens, start_ix + c.i, tense=tense, preset_subject=[])
    c.i = len(c.tokens)   # 関係節は節の終わりまで
    verb = next((w.items[0] for w in inner if w.items and w.items[0].pos == 'verb'), None)
    if verb is None:
        return
    ja = (verb.ja or '').split(',')[0]
    try:
        ja = Modern.past_form(ja) if tense == 'perfect' else Modern.te(ja) + 'いる' if tense == 'progressive' else ja
    except Exception:
        pass
    parts = []
    pending = ''
    for w in inner:
        if not w.items or w.items[0].pos in ('verb', 'article', 'adv'):
            continue
        item = w.items[0]
        if item.pos == 'preposition':
            pending = (item.ja or '').split(',')[0].lstrip('〜')
            continue
        if item.pos not in ('noun', 'pronoun'):
            continue
        case = (item._ or [('Nom',)])[0][0]
        noun = (item.ja or '').split(',')[0]
        parts.append(noun + (pending or {'Nom': 'が', 'Acc': 'を', 'Dat': 'に', 'Gen': 'の'}.get(case, '')))
        pending = ''
    item = head.items[0]
    relative = ''.join(parts) + ja
    head.items = [type(item)(dict(item.item, ja=relative + (item.ja or '').split(',')[0], gloss_lang='ja',
                                  relative=' '.join(c.tokens[first - 1:])))]
    for w in inner:   # 語の一覧には関係節の語も (頭の名詞に掛かる)
        k = getattr(w, 'token_ix', None)
        if k is not None and w.items:
            _relative_words[k] = (w, head)


_relative_words = {}   # 関係節の語 (元の語の位置 → (語, 頭の名詞))。語の列からは外し、一覧に出す


def _is_tam_ke(c):
    """ke … nei (進行) の ke か: 後ろが動詞の読みのある語で、節の中に nei がある"""
    nxt = c.peek(1)
    return nxt is not None and any(e[0] == 'verb' for e in content(nxt)) and \
        any(_key(t) == 'nei' for t in c.tokens[c.i + 2:])


FUNCTION_TABLES = (morphology.ARTICLES, morphology.DEMONSTRATIVES, morphology.POSSESSIVES, morphology.TAM,
                   morphology.NEGATIONS, morphology.PREPOSITIONS, morphology.CONJUNCTIONS, morphology.DIRECTIONALS,
                   morphology.POST_DEMONSTRATIVES, morphology.GENITIVES)


def _function_word(tok):
    """機能語か (綴りが合うもの。長音符の無い綴りは鍵の同じ機能語があれば)"""
    spelled = _spelled(tok)
    if spelled in (morphology.TOPIC, morphology.EXISTENTIAL, morphology.PASSIVE):
        return True
    return any(spelled in t for t in FUNCTION_TABLES) or \
        not orthography.marked(tok) and any(morphology.candidates(t, tok) for t in FUNCTION_TABLES)


def parse_clause(tokens, start_ix, tense='present', mood='indicative', preset_subject=None):
    """節 (句読点・接続詞の間) → 語の列 (共通の解析器に渡す Word。格の決まった項目)。preset_subject は前に出した
    名詞句 (主語として、動詞の後ろの印の無い句より先に)"""
    c = Clause(tokens)
    out = list(preset_subject or [])
    voice, negated, prohibitive = 'active', False, False
    closing = None
    # 否定・時制と相の小辞
    while c.peek() is not None:
        tok = c.peek()
        if morphology.candidates(morphology.NEGATIONS, tok):
            negated = True
            out.append(_word(tok, {'surface': tok, 'pos': 'adv', 'base': 'ʻaʻole', 'ja': '〜ない', 'gloss_lang': 'ja',
                                   'negation': True}, start_ix + c.i))
            c.i += 1
            if _key(c.peek()) == 'i':   # ʻaʻole i + 動詞「〜しなかった」
                tense = 'perfect'
                _note(start_ix + c.i, 'i', '過去の印 (ʻaʻole i + 動詞「〜しなかった」)')
                c.i += 1
            continue
        if _key(tok) == 'mai' and c.i == 0 and c.peek(1) is not None and \
                any(e[0] == 'verb' for e in content(c.peek(1))):   # 禁止 mai + 動詞「〜するな」
            prohibitive = True
            mood = 'imperative'
            out.append(_word('(mai)', {'surface': '(mai)', 'pos': 'adv', 'base': 'mai', 'ja': '〜ない', 'gloss_lang': 'ja',
                                       'negation': True}, None))
            _note(start_ix + c.i, 'mai', '禁止 (mai + 動詞「〜するな」)')
            c.i += 1
            continue
        tam = morphology.candidates(morphology.TAM, tok)
        if tam and c.peek(1) is not None and any(e[0] == 'verb' for e in content(c.peek(1))) and \
                not (_key(tok) == 'ke' and not _is_tam_ke(c)):
            spelled, (base, t, close) = tam[0]
            if base == 'e' and not any(_key(x) == 'ana' for x in c.tokens[c.i + 2:]):
                mood = 'imperative'   # e + 動詞 (ana なし): 命令・勧め「〜せよ・〜しよう」
            else:
                tense = t
            closing = close
            _note(start_ix + c.i, base, TAM_NOTES[base] if mood != 'imperative' else '命令・勧めの小辞 (e + 動詞「〜せよ」)')
            c.i += 1
            continue
        break
    # 文頭の前置詞句 (I kinohi hana ke Akua「初めに神が造った」): 前置詞句を読んでから動詞へ
    no_pronoun = _key(c.peek()) in ('no', 'na') and bool(morphology.candidates(morphology.PRONOUNS, c.peek(1) or ''))
    if morphology.candidates(morphology.PREPOSITIONS, c.peek() or '') and c.peek(1) is not None and \
            _key(c.peek()) not in ('e',) and not no_pronoun:
        save = c.i
        pp = _arguments_pp(c, start_ix)
        if pp and c.peek() is not None and not _function_word(c.peek()) and \
                any(e[0] == 'verb' for e in content(c.peek())):
            out += pp
        else:
            c.i = save
    # 動詞の無い文
    first = _spelled(c.peek())
    if first == morphology.EXISTENTIAL or (_key(c.peek()) == 'aia' and not orthography.marked(c.peek() or '')):
        out.append(_word(c.peek(), {'surface': c.peek(), 'pos': 'verb', 'pres1sg': 'aia', 'lemma': 'aia', 'base': 'aia',
                                    'ja': 'ある,いる', 'gloss_lang': 'ja', 'voice': 'active', 'mood': 'indicative',
                                    'tense': 'present', 'person': None, 'number': None, 'existential': True},
                         start_ix + c.i))
        c.i += 1
        return out + _arguments(c, start_ix, None)
    if _key(c.peek()) in ('no', 'na') and morphology.candidates(morphology.PRONOUNS, c.peek(1) or '') and \
            c.peek(2) is not None and (_function_word(c.peek(2)) or
                                       not any(e[0] == 'verb' for e in content(c.peek(2) or ''))):
        # no lākou ke aupuni「御国は彼らのものだ」(no / na + 代名詞の述語)
        spelled, (base, ja, person, n) = morphology.candidates(morphology.PRONOUNS, c.peek(1))[0]
        _note(start_ix + c.i, _key(c.peek()), '所有の述語 (%s + 代名詞「〜のもの」)' % _key(c.peek()))
        predicate = _word(c.peek(1), {'surface': c.peek(1), 'pos': 'noun', 'base': base, 'ja': ja + 'のもの',
                                      'gloss_lang': 'ja', '_': [('Nom', 'sg', GENDER)]}, start_ix + c.i + 1)
        c.i += 2
        rest = _arguments(c, start_ix, None)
        for w in rest:
            w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
        return out + [predicate, _word('(he)', dict(COPULA), None)] + rest
    pred_pos = morphology.candidates(morphology.PREDICATE_POSSESSIVES, c.peek() or '')
    if pred_pos and c.peek(1) is not None:   # Naʻu kēia「これは私のものだ」(na / no の所有の語の述語)
        spelled, (ja, kind) = pred_pos[0]
        _note(start_ix + c.i, spelled, '所有の述語 (%s 類「%s」)' % (kind, ja))
        predicate = _word(c.peek(), {'surface': c.peek(), 'pos': 'noun', 'base': spelled, 'ja': ja, 'gloss_lang': 'ja',
                                     '_': [('Nom', 'sg', GENDER)]}, None)
        c.i += 1
        rest = _arguments(c, start_ix, None)
        for w in rest:
            w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
        return out + [predicate, _word('(he)', dict(COPULA), None)] + rest
    if _key(c.peek()) == 'he' and c.peek(1) is not None:   # He kumu ʻo ia「彼は先生である」
        complement = parse_np(c, 'Nom', start_ix)
        owner = morphology.candidates(morphology.POSSESSIVES, c.peek() or '')
        if complement and owner and c.peek(1) is None or complement and owner and c.peek(1) in PUNCTUATION:
            # He kaʻa koʻu「私には車がある」: he + 名詞 + 所有の語は所有の文
            spelled, (base, ja, kind) = owner[0]
            owner_ja = {'私の': '私', '君の': '君', '彼の': '彼'}.get(ja, ja.rstrip('の'))
            _note(start_ix + c.i, spelled, '所有の文の持ち主 (%s 類「%s」)' % (kind, ja))
            c.i += 1
            verb = _word('(he)', {'surface': '(he)', 'pos': 'verb', 'pres1sg': 'he', 'lemma': 'he', 'base': 'he',
                                  'ja': 'ある,いる', 'gloss_lang': 'ja', 'voice': 'active', 'mood': 'indicative',
                                  'tense': 'present', 'person': None, 'number': None, 'existential': True}, None)
            holder = _word(spelled, {'surface': spelled, 'pos': 'pronoun', 'base': spelled, 'ja': owner_ja,
                                     'gloss_lang': 'ja', '_': [('Dat', 'sg', GENDER)], 'compact': True}, None)
            prep = _word('(i)', {'surface': '(i)', 'pos': 'preposition', 'base': 'i', 'dominates': 'Dat', 'ja': '〜には',
                                 'gloss_lang': 'ja'}, None)
            return out + [verb, prep, holder] + complement
        copula = _word('(he)', dict(COPULA), None)
        rest = _arguments(c, start_ix, None)
        for w in rest:   # he の名詞が述語、後ろの名詞句・代名詞が主語 (He aha kēia?「これは何か」)
            w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
        return out + complement + [copula] + rest
    if first == morphology.TOPIC or _key(c.peek()) == 'o' and not orthography.marked(c.peek() or '') and c.i == 0:
        _note(start_ix + c.i, 'ʻo', '同定の印 (文頭の ʻo + 名詞句が述語「〜である」)')
        c.i += 1   # ʻO Kimo koʻu inoa「私の名前はキモだ」: 文頭の ʻo の句が述語 (同定)、後ろの名詞句が主語
        predicate = parse_np(c, 'Nom', start_ix)
        rest = _arguments(c, start_ix, None)
        if not any(w.items and w.items[0].pos == 'verb' for w in rest):
            for w in rest:
                w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
            if predicate and predicate[0].items and predicate[0].items[0].attrib('base') == 'wai' and \
                    any(w.items and orthography.key(w.items[0].attrib('base') or '') == 'inoa' for w in rest):
                item = predicate[0].items[0]   # ʻO wai kou inoa?「君の名前は何か」(名前を尋ねる wai は「何」)
                predicate[0].items = [type(item)(dict(item.item, ja='何'))]
            return out + predicate + [_word('(he)', dict(COPULA), None)] + rest
        return out + predicate + rest
    question = morphology.candidates(morphology.QUESTION_WORDS, c.peek() or '')
    if question and question[0][1][2] == 'adv':   # Pehea ʻoe?「君はどうですか」・Ināhea ʻoe i hele ai?
        spelled, (base, ja, _) = question[0]
        adv = _word(c.peek(), {'surface': c.peek(), 'pos': 'noun', 'base': base, 'ja': ja, 'gloss_lang': 'ja',
                               '_': [('Nom', 'sg', GENDER)], 'question': True}, start_ix + c.i)
        c.i += 1
        rest_tokens = c.tokens[c.i:]
        if any(_key(t) in ('i', 'e') for t in rest_tokens[1:3]):   # No ke aha ʻoe i hele ai?「なぜ君は行ったのか」
            adv.items = [type(adv.items[0])(dict(adv.items[0].item, pos='adv', _=None))]
            return out + [adv] + parse_clause(rest_tokens, start_ix + c.i, mood=mood)
        rest = _arguments(c, start_ix, None)
        if not any(w.items and w.items[0].pos == 'verb' for w in rest):
            for w in rest:
                w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
            return out + [adv, _word('(he)', dict(COPULA), None)] + rest
        return out + [adv] + rest
    # 動詞
    tok = c.peek()
    verbs = [e for e in content(tok)] if tok is not None else []
    verb_entries = [e for e in verbs if e[0] == 'verb'] or (_guess(tok) if tok is not None and not verbs else [])
    verb_entries = [e for e in verb_entries if e[0] == 'verb']
    verb = None
    if verb_entries and not _function_word(tok) and not morphology.candidates(morphology.PRONOUNS, tok):
        # 代名詞は動詞にしない (ʻoe「君」: Andrews の辞書には動詞「唸る」の見出しもある)
        pos, base, ja, lang, plural, proper = verb_entries[0]
        verb = {'surface': tok, 'pos': 'verb', 'pres1sg': base, 'lemma': base, 'base': base, 'ja': ja, 'gloss_lang': lang,
                'voice': voice, 'mood': mood, 'tense': tense, 'person': None, 'number': None}
        if orthography.normalize(base) in POSSESSION:
            verb.update(existential=True, ja='ある,手に入る')
        c.verb = verb
        vword = _word(tok, verb, start_ix + c.i)
        c.i += 1
        while c.peek() is not None:   # 動詞の後ろ: ʻia (受け身)・方向の小辞・ana / nei (時制の閉じ)
            nxt = c.peek()
            if _spelled(nxt) == morphology.PASSIVE or _key(nxt) == 'ia' and not orthography.marked(nxt) and \
                    _key(c.peek(1)) == 'e':
                verb['voice'] = 'passive'
                _note(start_ix + c.i, 'ʻia', '受け身の印「〜される」')
                c.i += 1
                continue
            if morphology.candidates(morphology.DIRECTIONALS, nxt):   # 動詞の直後の mai は方向「こちらへ」(〜から ではない)
                d = morphology.candidates(morphology.DIRECTIONALS, nxt)[0][0]
                _note(start_ix + c.i, d, '方向の小辞「%s」(訳さない)' % DIRECTIONAL_NOTES.get(d, ''))
                if orthography.normalize(verb['base']) == 'hele' and d in ('mai', 'aku'):   # hele mai「来る」・hele aku「行く」
                    verb['ja'] = '来る' if d == 'mai' else '行く'
                    _note(start_ix + c.i, d, '方向の小辞「%s」(hele %s「%s」)' % (DIRECTIONAL_NOTES[d], d, verb['ja']))
                c.i += 1
                continue
            if _spelled(nxt) == morphology.RESUMPTIVE or _key(nxt) == 'ai' and not orthography.marked(nxt) and \
                    preset_subject is not None:
                _note(start_ix + c.i, 'ai', '空所の印 ai (前の名詞句・疑問詞が主語でない: 目的語・場所・理由)')
                c.i += 1
                if preset_subject:   # 前に出した句は主語でない (No ke aha ʻoe i hele ai: ʻoe が主語)
                    pass
                continue
            if _key(nxt) == 'la' and (not orthography.marked(nxt) or _spelled(nxt) == 'lā'):
                _note(start_ix + c.i, 'lā', '語りの小辞 lā (動詞の後ろ: 過去の出来事・その時)')
                if verb['tense'] == 'present':
                    verb['tense'] = 'perfect'   # olelo mai la「言った」(語りの過去)
                c.i += 1
                continue
            adverbial = ADVERBIAL_STATIVES.get(_key(nxt))
            if adverbial and c.peek(1) is not None and (_function_word(c.peek(1)) or c.peek(1) in PUNCTUATION):
                _note(start_ix + c.i, nxt, '動詞を修飾する状態の動詞「%s」' % adverbial)
                out.append(_word(nxt, {'surface': nxt, 'pos': 'adv', 'base': nxt, 'ja': adverbial, 'gloss_lang': 'ja'},
                                 None))
                c.i += 1   # aloha nui「とても愛する」
                continue
            if closing and _key(nxt) == closing:
                _note(start_ix + c.i, closing, '時制・相の小辞の閉じ (%s)' % {'ana': 'e … ana', 'nei': 'ke … nei'}[closing])
                c.i += 1
                continue
            if _key(nxt) in ('loa', 'nō', 'no', 'hou', 'pū', 'koke', 'wale', 'paha') and \
                    morphology.candidates(morphology.ADVERBS, nxt):
                out.append(_word(nxt, {'surface': nxt, 'pos': 'adv', 'base': nxt,
                                       'ja': morphology.candidates(morphology.ADVERBS, nxt)[0][1], 'gloss_lang': 'ja'},
                                 start_ix + c.i))
                c.i += 1
                continue
            break
        vword.items = [type(vword.items[0])(verb)]   # 動詞の後ろの小辞で変えた訳・態 (hele mai「来る」) を項目に
        first_ja = (verb['ja'] or '').split(',')[0]
        if verb['gloss_lang'] == 'ja' and first_ja.endswith(('い', 'な', 'の')) and verb['voice'] == 'active' and \
                not verb.get('existential'):
            # 状態の動詞の訳が日本語の形容詞 (nani「美しい」・maikaʻi「良い」): 補語の形容詞 + 見えない繋辞
            # (Ua maikaʻi「良かった」・Nani ka wahine「その女は美しい」)
            adj = _word(tok, {'surface': tok, 'pos': 'adj', 'base': verb['base'], 'lemma': verb['base'], 'ja': verb['ja'],
                              'gloss_lang': 'ja', '_': [('Nom', n, GENDER) for n in ('sg', 'pl')]}, vword.token_ix)
            adj.predicate = True
            copula = _word('(he)', dict(COPULA, tense=verb['tense'], mood=verb['mood']), None)
            rest = _arguments(c, start_ix, None, subject_done=bool(preset_subject))
            for w in rest:
                w.focus = getattr(w, 'focus', False) or bool(w.items and w.items[0].pos in ('noun', 'pronoun'))
            return out + [adj, copula] + rest
        out.append(vword)
    elif tok is not None:
        # 名詞句を前に出した文: 名詞句 + i (過去) / e (… ana) + 動詞 (ʻElua kanaka i hele mai「2人が来た」・
        # ʻO wai i hele?「誰が行ったか」・No ke aha ʻoe i hele ai?)。名詞句が主語 (ai があれば主語でない空所)
        save = c.i
        fronted = parse_np(c, 'Nom', start_ix)
        if fronted and _key(c.peek()) in ('i', 'e') and c.peek(1) is not None and \
                any(e[0] == 'verb' for e in content(c.peek(1))):
            particle = _key(c.peek())
            _note(start_ix + c.i, particle, '前に出した名詞句の後ろの時制の小辞 (%s)' % ('i: 過去' if particle == 'i' else 'e: 未来・未完了'))
            c.i += 1
            inner = parse_clause(c.tokens[c.i:], start_ix + c.i, tense='perfect' if particle == 'i' else 'future',
                                 mood=mood, preset_subject=fronted)
            return out + inner
        c.i = save
        # 動詞の読みの無い語で始まる節: 名詞の述語 (Kumu ʻo ia「彼は先生だ」) か、主語だけ
        predicate = parse_np(c, 'Nom', start_ix)
        rest = _arguments(c, start_ix, None)
        if predicate and any(getattr(w, 'focus', False) for w in rest):
            return out + predicate + [_word('(he)', dict(COPULA), None)] + rest
        return out + predicate + rest
    return out + _arguments(c, start_ix, verb, subject_done=bool(preset_subject))


def _arguments_pp(c, start_ix):
    """前置詞句1つ (前置詞 + 名詞句)。読めなければ []"""
    tok = c.peek()
    preps = morphology.candidates(morphology.PREPOSITIONS, tok)
    if not preps:
        return []
    base, case, ja = [r for r in preps[0][1] if r[1] == 'Dat'][0] if any(r[1] == 'Dat' for r in preps[0][1]) \
        else preps[0][1][0]
    ix = start_ix + c.i
    c.i += 1
    np = parse_np(c, 'Dat', start_ix, statives=False)
    if not np:
        return []
    return [_word(tok, {'surface': tok, 'pos': 'preposition', 'base': base, 'dominates': 'Dat', 'ja': ja or '〜に',
                        'gloss_lang': 'ja'}, ix)] + np


def _arguments(c, start_ix, verb, subject_done=False):
    """動詞の後ろの名詞句: 印の無い最初の句は主語、ʻo の句は主語 (主題)、i / iā は目的語 (移動の動詞では「〜へ」)、
    前置詞の句。受け身の動詞では印の無い句が主語 (受け手)、e + 句が動作主"""
    out = []
    while c.peek() is not None:
        tok = c.peek()
        if tok in PUNCTUATION:
            c.i += 1
            continue
        spelled, k = _spelled(tok), _key(tok)
        if spelled == morphology.TOPIC or k == 'o' and not orthography.marked(tok) and not subject_done:
            _note(start_ix + c.i, 'ʻo', '主語・主題の印 (ʻo + 名詞句)')
            c.i += 1
            np = parse_np(c, 'Nom', start_ix)
            for w in np:
                w.focus = True
            out += np
            subject_done = True
            continue
        preps = morphology.candidates(morphology.PREPOSITIONS, tok)
        if preps and c.peek(1) is not None:
            spelled_p, readings = preps[0]
            if len(preps) > 1:   # ia (長音符なし): iā「〜を」か ia「彼」。後ろが名詞句なら iā
                readings = next((r for s, r in preps if s == 'iā'), readings)
            prep_ix = start_ix + c.i
            c.i += 1
            # 場所の名詞 (ma luna o「〜の上に」)
            loc = morphology.LOCATIVES.get(_key(c.peek()))
            if loc and _key(c.peek(1)) == 'o':
                _note(start_ix + c.i, c.peek(), '場所の名詞 (%s %s o「%s」)' % (spelled_p, c.peek(), loc))
                _note(start_ix + c.i + 1, 'o', '所有の印「〜の」(場所の名詞の後ろ)')
                c.i += 2
                np = parse_np(c, 'Dat', start_ix)
                if np:
                    out.append(_word(tok, {'surface': tok, 'pos': 'preposition', 'base': spelled_p, 'dominates': 'Dat',
                                           'ja': loc, 'gloss_lang': 'ja'}, prep_ix))
                    out += np
                continue
            base, case, ja = readings[0]
            if base in ('i', 'iā') and verb is not None:
                if orthography.normalize(verb['base']) in MOTION or verb.get('voice') == 'passive':
                    base, case, ja = ('i', 'Dat', '〜に,〜へ')
                else:
                    np = parse_np(c, 'Acc', start_ix, relative=True)   # 目的語「を」(i は訳さない。名詞に掛けて綴りを音読に残す)
                    head = next((w for w in np if w.items and w.items[0].pos in ('noun', 'pronoun')), None)
                    if head is not None:
                        head.add_modifier(_word(tok, {'surface': tok, 'pos': 'article', 'base': base, 'ja': '',
                                                      'gloss_lang': 'ja', 'compact': True}, prep_ix))
                    out += np
                    continue
            if base == 'e' and verb is not None and verb.get('voice') == 'passive':
                ja = '〜によって'
            np = parse_np(c, 'Dat', start_ix, relative=True)
            if np:
                out.append(_word(tok, {'surface': tok, 'pos': 'preposition', 'base': base, 'dominates': 'Dat',
                                       'ja': ja or '〜に', 'gloss_lang': 'ja'}, prep_ix))
                out += np
            continue
        if _key(tok) == 'a me':   # 名詞句の並列: 前の句と同じ格で読む
            prev_case = next((w.items[0]._[0][0] for w in reversed(out) if w.items and w.items[0]._), 'Nom')
            out.append(_word(tok, {'surface': tok, 'pos': 'conj', 'base': 'a me', 'ja': 'と', 'gloss_lang': 'ja'},
                             start_ix + c.i))
            c.i += 1
            out += parse_np(c, prev_case, start_ix, relative=True)
            continue
        direction = morphology.candidates(morphology.DIRECTIONALS, tok)
        if direction and (c.peek(1) is None or c.peek(1) in PUNCTUATION or _function_word(c.peek(1))):
            _note(start_ix + c.i, direction[0][0], '方向の小辞「%s」(訳さない)' % DIRECTIONAL_NOTES.get(direction[0][0], ''))
            c.i += 1   # mai ka hale mai「家から」の後ろの mai
            continue
        adv = morphology.candidates(morphology.ADVERBS, tok)
        if adv and not content(tok):
            out.append(_word(tok, {'surface': tok, 'pos': 'adv', 'base': tok, 'ja': adv[0][1], 'gloss_lang': 'ja'},
                             start_ix + c.i))
            c.i += 1
            continue
        np = parse_np(c, 'Nom' if not subject_done else 'Acc', start_ix, relative=True)
        if np:
            out += np
            if not (np[0].items and np[0].items[0].attrib('base') == 'iaʻu'):   # iaʻu は目的語の形 (主語ではない)
                subject_done = True
            continue
        out.append(_word(tok, {'surface': tok, 'pos': 'adv', 'base': tok, 'ja': tok, 'gloss_lang': 'en'},
                         start_ix + c.i))   # 読めない語 (訳に出す)
        c.i += 1
    return out


TAM_NOTES = {'ua': '時制・相の小辞: 完了「〜した」', 'e': '時制・相の小辞: e … ana 未完了・未来「〜する (だろう)」',
             'ke': '時制・相の小辞: ke … nei 進行「〜している」'}
DIRECTIONAL_NOTES = {'mai': 'こちらへ', 'aku': 'あちらへ', 'iho': '下へ・自分で', 'aʻe': '上へ・次の'}


def lookup_all(surfaces):
    """文 → 語の列 (節ごとに読む)"""
    _notes.clear()
    _relative_words.clear()
    words = []
    clause, start = [], 0
    for ix, tok in enumerate(surfaces + [None]):
        conj = morphology.candidates(morphology.CONJUNCTIONS, tok) if tok is not None else []
        if conj and orthography.key(tok) == 'a' and clause and _genitive_a(surfaces, ix):
            conj = []   # 名詞の後ろの a は所有「〜の」
        if conj and conj[0][0] == 'a me':
            conj = []   # a me「と」は名詞句の並列 (ka lani a me ka honua「天と地」)。節の中で読む
        if tok is None or tok in PUNCTUATION or conj:
            if clause:
                words += parse_clause(clause, start)
            if tok is not None:
                if conj:
                    spelled, (base, ja) = conj[0]
                    words.append(_word(tok, {'surface': tok, 'pos': 'conj', 'base': base, 'ja': ja, 'gloss_lang': 'ja'},
                                       ix))
                else:
                    words.append(_word(tok, None, ix))
            clause, start = [], ix + 1
        else:
            clause.append(tok)
    for i, word in enumerate(words):
        word.index = i
    return words


def _genitive_a(surfaces, ix):
    """名詞の後ろの a は所有「〜の」(ka puke a ke kumu「先生の本」)。動詞・句読点の後ろの a は接続詞「そして」"""
    prev = surfaces[ix - 1] if ix > 0 else None
    nxt = surfaces[ix + 1] if ix + 1 < len(surfaces) else None
    return prev is not None and nxt is not None and orthography.key(nxt) in ('ke', 'ka', 'na') and \
        any(e[0] == 'noun' for e in content(prev))


def spelled(analysis):
    """音読: 元の文の語を、解析で選んだ読みの辞書の綴り (ʻokina・長音符付き) に (aina → ʻāina、kau → kaʻu)"""
    out = list(analysis.original)
    for word in analysis.words:
        k = getattr(word, 'token_ix', None)
        if k is None or k >= len(out) or not word.items:
            continue
        base = word.items[0].attrib('base') or ''
        if base and orthography.key(base) == orthography.key(out[k]) and not orthography.marked(out[k]):
            out[k] = base if not out[k][:1].isupper() else base[:1].upper() + base[1:]
        for m in word.modifiers:   # 冠詞
            mk = getattr(m, 'token_ix', None)
            mb = m.items[0].attrib('base') if m.items else None
            if mk is not None and mb and orthography.key(mb) == orthography.key(out[mk]):
                out[mk] = mb
    return out


def analyze_sentence(surfaces):
    words = lookup_all(surfaces)
    word_details = [word.detail() for word in words]
    with language.using(HAWAIIAN):
        analysis = common.analyze_words([w.surface for w in words], words, word_details, [])
    analysis.original = list(surfaces)
    analysis.notes = dict(_notes)
    analysis.relative_words = dict(_relative_words)
    return analysis


def analyze_text(text):
    for surfaces in sentences(text):
        yield analyze_sentence(surfaces)
