#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) から日本語の文を作る (日本語 → 文の枠 → 日本語の訳し戻し、ラテン語などからの自然な訳)
#
#   語: ラテン語の語 (Lex) の辞書の日本語の訳語の最初のもの (magister「教師,先生」→ 教師)。代名詞は表から
#   語順: 主語 - 受け手 - 目的語 - そのほか - 副詞 - 述語 (日本語は述語が最後)。修飾語・関係節・属格は名詞の前
#   助詞: 主節の主語は「は」、従属節・関係節の主語は「が」、目的語「を」、受け手「に」、手段「で」、前置詞句は表から
#   述語: core/japanese.py の JaVerb で時制・態・否定を活用 (褒められた、読んでいた、愛さない)。繋辞は補語 + だ / である
#   節: 関係節は連体修飾 ({先生が 褒める}少年)、不定詞句は 〜のを (知覚) / 〜と (言う) / 〜ことが (できる) / 〜ことを、
#       間接疑問は 〜か、ubi → 〜とき、quod → 〜ので、sī → 〜なら、dum → 〜あいだ、et → 〜て、sed → 〜が
#
import re

from dragoman.core.japanese import JaVerb, copula_predicate
from dragoman.core import verb_flags as Verb
from . import ja_lexicon

PRONOUNS = {('ego', 'sg'): '私', ('ego', 'pl'): '私たち', ('tū', 'sg'): 'あなた', ('tū', 'pl'): 'あなたたち',
            ('nōs', 'pl'): '私たち', ('vōs', 'pl'): 'あなたたち', ('quis', 'sg'): '誰', ('quid', 'sg'): '何',
            ('sē', 'sg'): '自分', ('sē', 'pl'): '自分たち'}
DEMONSTRATIVE_NOUNS = {'hic': 'これ', 'hīc': 'これ', 'ille': 'あれ', 'is': 'それ', 'iste': 'それ'}
DEMONSTRATIVE_ADJ = {'hic': 'この', 'hīc': 'この', 'ille': 'あの', 'is': 'その', 'iste': 'その', 'īdem': '同じ'}
PREPOSITIONS = {('in', 'Abl'): 'で', ('in', 'Acc'): 'へ', ('ad', 'Acc'): 'へ', ('ex', 'Abl'): 'から',
                ('ē', 'Abl'): 'から', ('ab', 'Abl'): 'から', ('ā', 'Abl'): 'から', ('cum', 'Abl'): 'と',
                ('dē', 'Abl'): 'について', ('sine', 'Abl'): 'なしで', ('per', 'Acc'): 'を通って',
                ('post', 'Acc'): 'の後で', ('ante', 'Acc'): 'の前で', ('sub', 'Abl'): 'の下で', ('prō', 'Abl'): 'のために',
                ('apud', 'Acc'): 'のもとで', ('inter', 'Acc'): 'の間で', ('propter', 'Acc'): 'のために',
                ('ob', 'Acc'): 'のために', ('contrā', 'Acc'): 'に対して', ('trāns', 'Acc'): 'を越えて',
                ('circum', 'Acc'): 'のまわりで', ('prope', 'Acc'): 'の近くで', ('super', 'Acc'): 'の上で'}
ROLE_PARTICLES = {'object': 'を', 'recipient': 'に', 'means': 'で', 'place': 'で', 'possessor': 'の',
                  'source': 'から', 'complement': ''}
SUBORDINATORS = {'ubi': 'とき', 'cum': 'とき', 'postquam': '後で', 'quod': 'ので', 'quia': 'ので', 'sī': 'なら',
                 'dum': 'あいだ', 'nisi': 'のでなければ', 'antequam': '前に', 'quamquam': 'けれども',
                 'etsī': 'けれども', 'ut': 'ように', 'nē': 'ないように', 'simul': 'とすぐに', 'quoniam': 'ので',
                 'dōnec': 'まで', 'priusquam': '前に', 'quīn': 'ことなく'}
WH = {'quis': '誰', 'quid': '何', 'cūr': 'なぜ', 'quārē': 'なぜ', 'ubi': 'どこで', 'quō': 'どこへ', 'unde': 'どこから',
      'quandō': 'いつ', 'quōmodo': 'どのように', 'num': '', 'utrum': ''}


def available():
    return True


JAPANESE = re.compile('[\u3040-\u30ff\u4e00-\u9fff]')


def gloss(lex):
    """ラテン語の語 → 日本語の訳語 (最初のもの。注記・〜を除く)"""
    from . import transfer
    first = transfer.FIRST_GLOSSES.get(lex.lang, {}).get(lex.lemma)
    if first and lex.lemma not in transfer.hand_glosses(lex.lang):
        # 先に使う英語の訳語の決まっている語 (βασιλεύς: king → 王)。解析器の手作りの日本語の訳語があればそちら (partir「出発する」)
        from dragoman.core import en_ja
        ja = en_ja.translate(first, lex.pos if lex.pos in ('noun', 'verb', 'adj', 'adv') else 'noun')
        if ja:
            return ja.split(',')[0]
    keys = ja_lexicon._keys(lex.ja or '')
    if keys:
        return keys[0]
    if lex.ja and JAPANESE.search(lex.ja.split(',')[0]):   # 英語の語義にギリシア文字などが混じるもの (form of θνῄσκω) は除く
        return re.sub('[〜～]', '', lex.ja.split(',')[0])
    # 日本語の訳語が無い語 (英語の語義だけの imber) は英語 → 日本語の表で
    from dragoman.core import en_ja
    from . import english
    en = english.gloss(lex) or (lex.ja if lex.ja and lex.ja.isascii() else None)
    pos = lex.pos if lex.pos in ('noun', 'verb', 'adj', 'adv') else 'noun'
    ja = en_ja.translate(en.split(',')[0], pos) if en else None
    if not ja and lex.lang:
        # ほかの言語の語: 英語の訳語を順に、簡単な形も (ὁράω: look with the eyes → … → see)
        from . import transfer
        sources = [e for e in (lex.ja or '').split(',') if e] + transfer.english_glosses(lex.lang, lex.lemma, lex.pos)
        for _, candidate in sorted(transfer._variants(sources[:8])):
            ja = en_ja.translate(candidate, pos)
            if ja:
                break
    return ja.split(',')[0] if ja else (lex.surface or lex.lemma)


# 数詞 (ラテン語の見出し) → 漢数字。人は「〜人」、ほかは「〜つ」(十以上は数だけ)
NUMERALS = {'ūnus': '一', 'duo': '二', 'trēs': '三', 'quattuor': '四', 'quīnque': '五', 'sex': '六', 'septem': '七',
            'octō': '八', 'novem': '九', 'decem': '十', 'centum': '百', 'mīlle': '千'}


def _numeral(np):
    return next((m for m in np.modifiers if not hasattr(m, 'members') and m.lemma in NUMERALS), None)


def count(numeral, np):
    """数詞 + 助数詞 (二人・三つ・十)"""
    n = NUMERALS[numeral.lemma]
    if np.animate:
        return {'一': '一人', '二': '二人'}.get(n, n + '人')
    return n + 'つ' if numeral.lemma not in ('decem', 'centum', 'mīlle') else n


def noun_phrase(np):
    if np.members:
        return 'と'.join(noun_phrase(m) for m in np.members)
    head = np.head
    if head.pos == 'pronoun' and head.lemma == 'quis' and np.gender == 'n':
        word = '何'   # 中性の疑問代名詞 (τί、quid)
    elif head.pos == 'pronoun' and (head.lemma, np.number) in PRONOUNS:
        word = PRONOUNS[(head.lemma, np.number)]
    elif head.pos == 'pronoun' and head.lemma == 'is' and not np.modifiers and not np.relatives:
        word = '彼女' if np.gender == 'f' else '彼ら' if np.number == 'pl' else '彼'
    elif head.pos == 'pronoun' and np.relatives and head.lemma in DEMONSTRATIVE_NOUNS:
        word = 'もの' if np.gender == 'n' else '人'   # is quī … 「…する人」
    elif head.pos == 'pronoun' and head.lemma in DEMONSTRATIVE_NOUNS:
        word = DEMONSTRATIVE_NOUNS[head.lemma]
    else:
        word = gloss(head)
        if np.number == 'pl' and np.animate and not word.endswith('たち') and _numeral(np) is None:
            word += 'たち'   # 数詞が付けば付けない (二人の友人)
    before = []
    for gen in np.genitives:
        before.append(noun_phrase(gen) + 'の')
    for r in np.relatives:
        before.append(clause_text(r, final=False, attributive=True))
    for m in np.modifiers:
        if hasattr(m, 'members'):
            before.append('、'.join(gloss(x.head) for x in m.members))
        elif m.lemma in NUMERALS:
            before.append(count(m, np) + 'の')   # 二人の友人・三つの町
        elif m.pos == 'pronoun' and m.lemma in DEMONSTRATIVE_ADJ:
            # 指示詞は関係節・属格の後ろ (メドゥーサが住んでいたその場所)、形容詞の前
            before.insert(len(np.genitives) + len(np.relatives), DEMONSTRATIVE_ADJ[m.lemma])
        else:
            adj = gloss(m)
            before.append(adj if adj.endswith(('い', 'な', 'の')) else adj + 'な')
    return ''.join(before) + word


def _flag(clause):
    flag = Verb.IMPERATIVE if clause.mood == 'imperative' else Verb.INDICATIVE
    if clause.voice == 'passive':
        flag |= Verb.PASSIVE
    flag |= {'imperfect': Verb.PAST | Verb.ING, 'perfect': Verb.PERFECT, 'past-perfect': Verb.PERFECT,
             'future': Verb.FUTURE, 'future-perfect': Verb.FUTURE}.get(clause.tense, 0)
    return flag


# 主語と動詞の連語: 雨・雪が「落ちる」→「降る」(rain falls、imber cadit を日本語の言い回しに)
COLLOCATIONS = {('雨', '落ちる'): '降る', ('雪', '落ちる'): '降る', ('霰', '落ちる'): '降る', ('雹', '落ちる'): '降る',
                ('霜', '落ちる'): '降りる', ('露', '落ちる'): '降りる', ('日', '落ちる'): '沈む', ('太陽', '落ちる'): '沈む'}


def collocation(clause, verb):
    for np in clause.role('subject'):
        if np.head is not None and not np.members:
            replaced = COLLOCATIONS.get((gloss(np.head), verb))
            if replaced:
                return replaced
    return verb


def predicate(clause, final=True):
    """述語の形 (主節の終わりなら終止形、ほかは同じ形で連体修飾・接続に使う)"""
    tense = {'imperfect': 'past', 'perfect': 'past', 'past-perfect': 'past', 'future': 'future'}.get(
        clause.tense, 'present')
    if clause.copula or clause.verb.lemma == 'sum':   # 日本語の入口の いる・ある (sum) も
        complements = clause.role('complement')
        if not complements:
            if any(np.animate for np in clause.role('subject')):   # 人・動物の存在は いる
                return JaVerb('いる').form(_flag(clause), clause.negated)
            if tense == 'past':
                return 'あった' if not clause.negated else 'なかった'
            return 'ある' if not clause.negated else 'ない'
        np = complements[0]
        from .frame import adjective_members
        members = adjective_members(np)
        if members:   # 形容詞の並列: 長くて広い (最後以外は連用の形)
            from dragoman.core.japanese import copula_conjunctive
            heads = [gloss(m.head).split(',')[0] for m in members]
            return ''.join(copula_conjunctive(h, True, clause.negated) for h in heads[:-1]) + \
                copula_predicate(heads[-1], True, tense, clause.negated, also=True).split(',')[0]   # 長くも広くもない
        adjective = not np.members and np.head is not None and np.head.pos in ('adj', 'participle')
        text = gloss(np.head) if adjective else noun_phrase(np)
        return copula_predicate(text, adjective, tense, clause.negated).split(',')[0]
    verb = collocation(clause, gloss(clause.verb))
    if verb.endswith(('ない', 'たい', 'しい')):   # 〜てほしい も   # 形容詞の活用の補助 (出発しなければならない・読みたい → ならなかった・読みたかった)
        return copula_predicate(verb, True, tense, clause.negated).split(',')[0]
    if not re.search('[うくぐすつぬぶむる]$', verb):
        verb += 'する' if not verb.endswith('する') else ''
    try:
        return JaVerb(verb).form(_flag(clause), clause.negated)
    except Exception:
        return verb


# 否定の代名詞: 「誰も」「何も」+ 述語の否定 (nēmō venit「誰も来ない」、nihil videt「何も見ない」)。助詞は付けない
NEGATIVE_PRONOUNS = {'nēmō': '誰も', 'nihil': '何も', 'nūllus': '誰も'}


def _negative_pronoun(np):
    return np.head is not None and not np.members and np.head.lemma in NEGATIVE_PRONOUNS and np.head.pos != 'adj'


# 不定詞を支配する話法の動詞 → 本動詞に付ける形 (possum legere「読むことができる」、dēbeō「〜なければならない」、
# faciō + 不定詞「〜させる」)
JA_MODALS = {'possum': 'ことができる', 'volō': 'たい', 'dēbeō': 'なければならない', 'oportet': 'なければならない',
             'faciō': 'させる', 'sinō': 'させておく'}


WANT_VERBS = {'volō', 'cupiō', 'optō', 'vouloir', 'souhaiter', 'désirer', 'wollen', 'wünschen'}


def _fold_want(clause):
    """望む + 主語のある補文 (Je veux que tu viennes・Volō tē venīre) → 「君に来てほしい」"""
    import dataclasses
    from .frame import Lex
    from dragoman.core.japanese import japanese_form
    if clause.verb is None or clause.verb.lemma not in WANT_VERBS or len(clause.infinitives) != 1:
        return clause
    inner = clause.infinitives[0]
    subjects = inner.role('subject')
    if inner.infinitive_kind not in ('command', 'saying', 'complement') or not subjects or inner.copula:
        return clause
    ja = japanese_form(gloss(inner.verb).split(',')[0], False, 'te', 'present', inner.negated) + 'ほしい'
    args = [(r, np) for r, np in clause.args] + [('recipient', subjects[0])] + \
        [(r, np) for r, np in inner.args if np is not subjects[0]]
    return dataclasses.replace(clause, verb=Lex(ja, 'verb', ja), infinitives=[], args=args,
                               adverbs=clause.adverbs + inner.adverbs)


# 補文を取るときの日本語の訳語 (demander que「頼む」。尋ねる ではない)
COMPLEMENT_VERBS_JA = {'command': {'demander': '頼む', 'rogō': '頼む', 'ordonner': '命じる', 'iubeō': '命じる',
                                   'exiger': '要求する', 'bitten': '頼む', 'befehlen': '命じる', 'fordern': '要求する'},
                       'emotion': {'regretter': '残念に思う', 'craindre': '恐れる', 'bedauern': '残念に思う'}}


def _complement_verb(clause):
    """補文の種類で主節の動詞の訳語を選ぶ (Il demande que tu viennes「頼む」)"""
    import dataclasses
    for inner in clause.infinitives:
        ja = COMPLEMENT_VERBS_JA.get(inner.infinitive_kind, {}).get(clause.verb.lemma if clause.verb else '')
        if ja:
            return dataclasses.replace(clause, verb=dataclasses.replace(clause.verb, ja=ja, lemma=clause.verb.lemma))
    return clause


def _fold_modal(clause):
    """話法の動詞 + 不定詞の節を1つの述語に (出発しなければならない、私を笑わせる)。当てはまらなければ元の節"""
    import dataclasses
    from dragoman.core.japanese import attach_auxiliary
    from .frame import Lex
    if clause.copula or clause.verb is None or clause.verb.lemma not in JA_MODALS or len(clause.infinitives) != 1:
        return clause
    inner = clause.infinitives[0]
    if inner.copula or inner.infinitives:
        return clause
    causative = clause.verb.lemma in ('faciō', 'sinō')
    args = []
    for role, np in inner.args:
        if role == 'subject':
            if clause.verb.lemma == 'oportet':
                args.append((role, np))   # il faut que je parte「私が出発しなければならない」
                continue
            if not causative:
                continue   # 主節と同じ主語
            role = 'object'   # 使役の人は「を」(私を笑わせる)
        args.append((role, np))
    ja = attach_auxiliary(gloss(inner.verb), JA_MODALS[clause.verb.lemma])
    return dataclasses.replace(clause, verb=Lex(ja, 'verb', ja), infinitives=[], args=clause.args + args,
                               adverbs=clause.adverbs + inner.adverbs)


OWNER_PRONOUNS = {1: 'ego', 2: 'tū', 3: 'is'}


def have_as_existence(clause):
    """habeō (have) + 人の目的語 → 所有の繋辞 (Puer duōs amīcōs habet・Eu tenho dois amigos →
    少年には友人が二人いる。人を「持つ」と訳さない)。物の目的語はそのまま (本を持つ)"""
    import dataclasses
    from .frame import Lex, NP
    from . import english
    objects = clause.role('object')
    if clause.copula or clause.mood != 'indicative' or clause.gap or len(objects) != 1 or not objects[0].animate or \
            objects[0].head is None or objects[0].head.pos == 'pronoun':
        return clause
    if clause.verb.lemma != 'habeō' and english.word(clause.verb) != 'have':
        return clause
    owner = (clause.role('subject') or [None])[0]
    if owner is None:   # 代名詞の主語の書かれない文 (Frātrem habeō → 私には兄弟がいる)
        owner = NP(Lex(OWNER_PRONOUNS.get(clause.person, 'is'), 'pronoun'), number=clause.number or 'sg')
    owned = objects[0] if objects[0].definite is True else dataclasses.replace(objects[0], definite=False)
    rest = [(r, np) for r, np in clause.args if r not in ('subject', 'object')]
    return dataclasses.replace(clause, verb=Lex('sum', 'verb', 'ある,いる'), copula=True,
                               args=[('recipient', owner), ('subject', owned)] + rest)


def clause_text(clause, final=True, attributive=False):
    """節 → 日本語 (述語まで)"""
    import dataclasses
    from .frame import dative_as_object, prohibition
    clause = dative_as_object(prohibition(clause), 'ja')   # miserēre nōbīs → 私たちを憐れめ、Nōlī timēre → 恐れるな
    clause = have_as_existence(clause)
    clause = _complement_verb(_fold_want(_fold_modal(clause)))
    if any(_negative_pronoun(np) for _, np in clause.args):
        clause = dataclasses.replace(clause, negated=True)
    parts = [_participial(p) for p in clause.adjuncts if p.kind == 'absolute']   # 独立奪格は節の頭 (王が死んで、…)
    subjects = clause.role('subject')
    topic = final and not attributive and not clause.subordinator
    # 不定の主語の存在・所有の文 (冠詞・一 + 量詞のある言語から): 場所・所有者を先に、主語は「が」で述語の前
    # (Há um livro na mesa「テーブルに 本が ある」、我有一本书「私には 本が ある」)
    # 疑問代名詞の主語も同じ (Quid eī est?・他有什么「彼には 何が あるか」)
    existential = clause.copula and not clause.role('complement') and bool(subjects) and \
        (subjects[0].definite is False or subjects[0].interrogative or _numeral(subjects[0]) is not None or
         clause.role('recipient') and subjects[0].definite is not True)   # 所有の与格 (Mihi est liber「私には本がある」)
    late = []
    for np in subjects:
        if attributive and clause.gap == 'subject':
            continue
        wh = np.head is not None and np.head.lemma in ('quis', 'quid')   # 疑問詞の主語は「が」(誰が来るか)
        numeral = _numeral(np) if existential and not np.members else None
        if numeral is not None:   # 数量は述語の前に (私には 友人が 二人 いる)
            import dataclasses
            bare = dataclasses.replace(np, modifiers=[m for m in np.modifiers if m is not numeral], number='sg')
            late.append(noun_phrase(bare) + 'が' + count(numeral, np))
            continue
        (late if existential else parts).append(NEGATIVE_PRONOUNS[np.head.lemma] if _negative_pronoun(np) else
                                                noun_phrase(np) + ('は' if topic and not wh and not existential else 'が'))
    for p in clause.adjuncts:
        if p.kind != 'absolute':
            parts.append(_participial(p))
    for role in ('recipient', 'object'):
        for np in clause.role(role):
            if attributive and clause.gap == role:
                continue
            parts.append(NEGATIVE_PRONOUNS[np.head.lemma] if _negative_pronoun(np) else
                         noun_phrase(np) + ('には' if existential and role == 'recipient' else ROLE_PARTICLES[role]))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement'):
            continue
        if role == 'prep' and np.prep is not None:
            if clause.voice == 'passive' and np.prep.lemma in ('ā', 'ab'):
                parts.append(noun_phrase(np) + 'に')   # 受動の動作主
            else:
                particle = PREPOSITIONS.get((np.prep.lemma, np.case), 'で')
                if particle.endswith('で') and _existence(clause):
                    particle = particle[:-1] + 'に'   # 家にいる・都に住む・机の下にある (存在・居住の動詞の場所)
                parts.append(noun_phrase(np) + particle)
        elif attributive and clause.gap == role:
            continue
        else:
            parts.append(noun_phrase(np) + ROLE_PARTICLES.get(role, 'で'))
    for inner in clause.infinitives:
        parts.append(infinitive(inner, clause))
    for inner in clause.questions:
        parts.append(question(inner))
    if clause.question and clause.question_word and not any(np.interrogative for _, np in clause.args):
        # 直接の疑問文の疑問の副詞は述語の前 (いつ来るか、少女はどこにいるか)
        parts.append('どこに' if clause.question_word == 'ubi' and _existence(clause) else WH.get(clause.question_word, ''))
    for adv in clause.adverbs:
        parts.append(gloss(adv))
    parts += late
    verb = predicate(clause, final)
    if clause.infinitives and clause.verb.lemma == 'possum':
        verb = predicate(clause).replace('〜', '')
    parts.append(verb)
    return ''.join(parts)


EXISTENCE = {'いる', '居る', 'ある', '有る', '在る', '住む', '暮らす', 'とどまる', '泊まる', '滞在する', '居住する'}


def _existence(clause):
    return (clause.copula and not clause.role('complement')) or gloss(clause.verb) in EXISTENCE


def infinitive(inner, governor):
    kind = inner.infinitive_kind
    import dataclasses
    finite = dataclasses.replace(inner, mood='indicative')
    text = clause_text(finite, final=False)
    if kind == 'perception':
        return text + 'のを'
    if kind == 'saying':
        return text + 'と'
    if governor.verb.lemma == 'possum':
        return text + 'ことが'
    if kind == 'command':   # 命じる・頼む (Il demande que tu viennes「君が来るように頼む」)
        return text + 'ように'
    if kind == 'emotion':   # 感情 (Je regrette que tu partes「君が出発することを残念に思う」)
        return text + ('ことが' if governor.copula else 'ことを')
    return text + 'ことを'


def question(inner):
    import dataclasses
    finite = dataclasses.replace(inner, mood='indicative')
    wh = WH.get(inner.question_word, '')
    text = clause_text(finite, final=False)
    has_np = any(np.interrogative for _, np in inner.args)
    return ('' if has_np else wh) + text + 'か'


def _participial(p):
    """分詞句: もとの動詞の訳語を連用の形に (歌いながら、死んで、褒められて)。独立奪格は主語 + が を前に"""
    from .frame import Lex
    verb = gloss(Lex(p.verb.verb, 'verb', p.verb.verb_ja)) if p.verb.verb_ja else gloss(p.verb)
    kind = 'present' if p.tense == 'present' else 'passive' if p.voice == 'passive' else 'active'
    try:
        form = JaVerb(verb).adverbial_form(kind) if re.search('[うくぐすつぬぶむる]$', verb) else verb
    except Exception:
        form = verb
    args = ''.join(noun_phrase(np) + ROLE_PARTICLES.get(role, 'で') for role, np in p.args if role != 'adverb')
    subject = noun_phrase(p.subject) + 'が' if p.subject is not None else ''
    return subject + args + form + ('、' if p.kind == 'absolute' else '')


def _te_form(text):
    """述語の終止形 → 〜て (読んだ → 読んで、来た → 来て)。合わなければ そして でつなぐ"""
    for past, te in (('んだ', 'んで'), ('いだ', 'いで'), ('った', 'って'), ('た', 'て')):
        if text.endswith(past):
            return text[:-len(past)] + te
    return text + '、そして'


def vocative(np):
    """呼びかけ: 名詞 + よ (主よ)。同格のまとまり (名詞句の列) の固有名詞は・でつなぐ (イエス・キリストよ)"""
    group = np if isinstance(np, list) else [np]
    if all(x.head is not None and x.head.proper for x in group):
        return '・'.join(noun_phrase(x) for x in group) + 'よ'
    return '、'.join(noun_phrase(x) + 'よ' for x in group)   # 普通名詞の同格は1つずつ (主よ、独り子よ)


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import split_address, subordinate_first
    clauses = subordinate_first(clauses)
    out = ''
    for i, clause in enumerate(clauses):
        last = i == len(clauses) - 1
        groups, clause = split_address(clause)
        out += ''.join(vocative(group) + '、' for group in groups)   # 呼びかけは文の頭に (主よ、…)
        text = clause_text(clause, final=True)
        if clause.subordinator:
            text = clause_text(clause, final=False) + SUBORDINATORS.get(clause.subordinator, '')
            out += text + '、'
            continue
        if not last and 'et' in clauses[i + 1].connectives:
            out += _te_form(text) + '、'
            continue
        if not last and 'sed' in clauses[i + 1].connectives:
            out += text + 'が、'
            continue
        out += text + ('。' if last else '、')
    return out
