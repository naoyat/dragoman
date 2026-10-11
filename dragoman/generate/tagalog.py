#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からタガログ語の文を作る
#
#   動詞は語根 (kain「食べる」) で持ち、どの名詞を ang で目立たせるか (焦点) で見出しを選ぶ:
#     目的語があれば対象焦点 (kainin: Kinain ng bata ang tinapay)、物が移る動詞 (与える・送る …) は移動物焦点
#     (ibigay: Ibinigay ng reyna ang rosas sa bata)、目的語が無ければ行為者焦点 (kumain: Kumain ang bata)。
#     ラテン語の受動は主語を ang にした対象焦点 (Pinuri ng guro ang bata)
#   アスペクト: 完了 → 完了相 (kumain / kinain)、現在・未完了過去 → 進行相 (kumakain)、未来 → 未然相 (kakain)。
#     語形は辞書 (tl/wiktionary.sqlite の forms) から、無ければ -um-・mag-・-in-・i-・-an と重複の規則で
#   語順: 動詞 - ng の句 (焦点でない行為者・目的語) - ang の句 (焦点) - sa の句。人名は si / ni / kay、複数は mga
#   名詞句: 形容詞 + 繋ぎ (-ng / na) + 名詞 (magandang rosas)、属格は後ろに ng (aklat ng guro)
#   繋辞は無い: 述語が先 (Maganda ang babae、Reyna si Maria)。否定は hindi
#   関係節: 名詞 + 繋ぎ + 動詞 (空所が ang になる焦点: ang rosas na nakita ng babae、ang batang kumain)
#
import functools
import re

from dragoman.tagalog import dictionary, morphology
from . import transfer, english
from .frame import Lex, NP

VOWELS = 'aeiou'
PRONOUNS = {('ego', 'sg'): ('ako', 'ko', 'akin'), ('ego', 'pl'): ('kami', 'namin', 'amin'),
            ('tū', 'sg'): ('ikaw', 'mo', 'iyo'), ('tū', 'pl'): ('kayo', 'ninyo', 'inyo'),
            ('is', 'sg'): ('siya', 'niya', 'kaniya'), ('is', 'pl'): ('sila', 'nila', 'kanila'),
            ('sē', 'sg'): ('siya', 'niya', 'kaniya'), ('sē', 'pl'): ('sila', 'nila', 'kanila'),
            ('hic', 'sg'): ('ito', 'nito', 'dito'), ('ille', 'sg'): ('iyon', 'niyon', 'doon'),
            ('hic', 'pl'): ('ang mga ito', 'ng mga ito', 'sa mga ito'),
            ('ille', 'pl'): ('ang mga iyon', 'ng mga iyon', 'sa mga iyon'),
            ('quis', 'sg'): ('sino', 'nino', 'kanino'), ('quid', 'sg'): ('ano', 'ng ano', 'saan')}
MARKERS = {'ang': ('ang', 'ang mga', 'si', 'sina'), 'ng': ('ng', 'ng mga', 'ni', 'nina'), 'sa': ('sa', 'sa mga', 'kay', 'kina')}
DEMONSTRATIVES = {'hic': 'ito', 'hīc': 'ito', 'ille': 'iyon', 'is': 'iyon', 'iste': 'iyan'}
POSSESSIVES = {'meus': 'ko', 'tuus': 'mo', 'suus': 'niya', 'noster': 'namin', 'vester': 'ninyo'}
# ラテン語の前置詞 + 格 → (タガログ語の前置き, 後ろの標識)
PREPOSITIONS = {('in', 'Abl'): ('', 'sa'), ('in', 'Acc'): ('', 'sa'), ('ad', 'Acc'): ('', 'sa'),
                ('ex', 'Abl'): ('mula', 'sa'), ('ē', 'Abl'): ('mula', 'sa'), ('ab', 'Abl'): ('mula', 'sa'),
                ('ā', 'Abl'): ('mula', 'sa'), ('cum', 'Abl'): ('kasama', 'ng'), ('dē', 'Abl'): ('tungkol', 'sa'),
                ('sine', 'Abl'): ('nang walang', ''), ('per', 'Acc'): ('sa pamamagitan', 'ng'),
                ('propter', 'Acc'): ('dahil', 'sa'), ('ob', 'Acc'): ('dahil', 'sa'), ('post', 'Acc'): ('pagkatapos', 'ng'),
                ('ante', 'Acc'): ('bago', 'ang'), ('sub', 'Abl'): ('sa ilalim', 'ng'), ('super', 'Acc'): ('sa ibabaw', 'ng'),
                ('apud', 'Acc'): ('', 'sa'), ('prō', 'Abl'): ('para', 'sa'), ('contrā', 'Acc'): ('laban', 'sa'),
                ('inter', 'Acc'): ('sa gitna', 'ng'), ('prope', 'Acc'): ('malapit', 'sa'), ('trāns', 'Acc'): ('sa kabila', 'ng')}
ASPECTS = {'perfect': 'completive', 'past-perfect': 'completive', 'present': 'progressive', 'imperfect': 'progressive',
           'future': 'contemplative', 'future-perfect': 'contemplative'}
CONNECTIVES = {'et': 'at', 'que': 'at', 'atque': 'at', 'ac': 'at', 'sed': 'pero', 'at': 'pero', 'autem': 'ngunit',
               'enim': 'dahil', 'nam': 'dahil', 'igitur': 'kaya', 'itaque': 'kaya', 'tamen': 'gayunman', 'neque': 'at hindi',
               'tum': 'saka', 'deinde': 'pagkatapos', 'ubi': 'nang', 'cum': 'nang', 'postquam': 'pagkatapos',
               'dum': 'habang', 'quod': 'dahil', 'quia': 'dahil', 'sī': 'kung', 'nisi': 'kung hindi', 'ut': 'upang',
               'nē': 'upang hindi', 'quamquam': 'kahit', 'etsī': 'kahit', 'aut': 'o', 'vel': 'o', 'iam': 'na'}
QUESTION_WORDS = {'cūr': 'kung bakit', 'quārē': 'kung bakit', 'quōmodo': 'kung paano', 'ubi': 'kung saan',
                  'quō': 'kung saan', 'unde': 'kung saan galing', 'quandō': 'kung kailan', 'num': 'kung',
                  'utrum': 'kung', 'quantus': 'kung gaano', 'quot': 'kung ilan'}
# 物が移る動詞の語根: 目的語があれば移動物焦点 (i-)
CONVEYANCE_ROOTS = {'bigay', 'abot', 'padala', 'tapon', 'balik', 'lagay'}
# 教科書の基本語 (語根)。動詞は焦点ごとの見出しを語根から探す
PREFERRED = {('girl', 'noun'): 'dalaga', ('boy', 'noun'): 'batang lalaki', ('child', 'noun'): 'bata',
             ('teacher', 'noun'): 'guro', ('book', 'noun'): 'aklat', ('rose', 'noun'): 'rosas',
             ('garden', 'noun'): 'hardin', ('king', 'noun'): 'hari', ('queen', 'noun'): 'reyna',
             ('city', 'noun'): 'lungsod', ('citizen', 'noun'): 'mamamayan', ('man', 'noun'): 'lalaki',
             ('woman', 'noun'): 'babae', ('sailor', 'noun'): 'mandaragat', ('farmer', 'noun'): 'magsasaka',
             ('soldier', 'noun'): 'kawal', ('god', 'noun'): 'diyos', ('house', 'noun'): 'bahay', ('road', 'noun'): 'daan',
             ('water', 'noun'): 'tubig', ('sea', 'noun'): 'dagat', ('island', 'noun'): 'pulo', ('ship', 'noun'): 'barko',
             ('letter', 'noun'): 'liham', ('word', 'noun'): 'salita', ('friend', 'noun'): 'kaibigan',
             ('mother', 'noun'): 'ina', ('father', 'noun'): 'ama', ('daughter', 'noun'): 'anak na babae',
             ('son', 'noun'): 'anak na lalaki', ('master', 'noun'): 'panginoon', ('lord', 'noun'): 'panginoon',
             ('slave', 'noun'): 'alipin', ('field', 'noun'): 'bukid', ('forest', 'noun'): 'gubat',
             ('beautiful', 'adj'): 'maganda', ('pretty', 'adj'): 'maganda', ('good', 'adj'): 'mabuti',
             ('bad', 'adj'): 'masama', ('evil', 'adj'): 'masama', ('great', 'adj'): 'dakila', ('big', 'adj'): 'malaki',
             ('large', 'adj'): 'malaki', ('small', 'adj'): 'maliit', ('long', 'adj'): 'mahaba', ('new', 'adj'): 'bago',
             ('old', 'adj'): 'matanda', ('wise', 'adj'): 'marunong', ('brave', 'adj'): 'matapang', ('happy', 'adj'): 'masaya',
             ('many', 'adj'): 'marami', ('high', 'adj'): 'mataas', ('skilled', 'adj'): 'marunong',
             ('clever', 'adj'): 'marunong',
             ('see', 'verb'): 'kita', ('praise', 'verb'): 'puri', ('give', 'verb'): 'bigay', ('sing', 'verb'): 'awit',
             ('write', 'verb'): 'sulat', ('read', 'verb'): 'basa', ('love', 'verb'): 'mahal', ('walk', 'verb'): 'lakad',
             ('eat', 'verb'): 'kain', ('buy', 'verb'): 'bili', ('come', 'verb'): 'dating', ('go', 'verb'): 'punta',
             ('say', 'verb'): 'sabi', ('ask', 'verb'): 'tanong', ('teach', 'verb'): 'turo', ('fight', 'verb'): 'laban',
             ('flee', 'verb'): 'takas', ('sleep', 'verb'): 'tulog', ('weep', 'verb'): 'iyak', ('cry', 'verb'): 'iyak',
             ('laugh', 'verb'): 'tawa', ('send', 'verb'): 'padala', ('take', 'verb'): 'kuha', ('carry', 'verb'): 'dala',
             ('kill', 'verb'): 'patay', ('live', 'verb'): 'tira', ('dwell', 'verb'): 'tira', ('inhabit', 'verb'): 'tira',
             ('lead', 'verb'): 'dala', ('hear', 'verb'): 'dinig', ('call', 'verb'): 'tawag', ('make', 'verb'): 'gawa',
             ('do', 'verb'): 'gawa', ('build', 'verb'): 'tayo', ('rejoice', 'verb'): 'galak', ('know', 'verb'): 'alam',
             ('capture', 'verb'): 'sakop', ('die', 'verb'): 'matay', ('seize', 'verb'): 'agaw', ('want', 'verb'): 'nais', ('wish', 'verb'): 'nais'}
# 語根と焦点 → 見出し (辞書の見出しの作り方が規則から外れるもの)
IRREGULAR = {('kita', 'object'): 'makita', ('kita', 'actor'): 'makakita', ('dinig', 'object'): 'marinig',
             ('dinig', 'actor'): 'makarinig', ('alam', 'object'): 'malaman', ('mahal', 'object'): 'mahalin',
             ('mahal', 'actor'): 'magmahal', ('dating', 'actor'): 'dumating', ('tira', 'actor'): 'tumira',
             ('galak', 'actor'): 'magalak', ('nais', 'actor'): 'nais', ('punta', 'actor'): 'pumunta',
             ('takas', 'actor'): 'tumakas', ('tulog', 'actor'): 'matulog', ('iyak', 'actor'): 'umiyak',
             ('tawa', 'actor'): 'tumawa', ('matay', 'actor'): 'mamatay'}
PREFERRED_ROOTS = {root for (_, pos), root in PREFERRED.items() if pos == 'verb'}
BARE = {'nais', 'gusto', 'alam'}   # 活用しない (nais「〜したい」、alam「知っている」)。する人は ng の形 (alam ko)
ENCLITICS = {f for forms in PRONOUNS.values() for f in forms[:2] if ' ' not in f}   # 文の最初の語の後ろに来る代名詞


def available():
    return dictionary.available() and transfer.available('tl')


# ----------------------------------------------------------------------
# 語根と見出し

def _is_verb(key, voice=None):
    return any(r['pos'] == 'verb' and (voice is None or r['voice'] == voice) for r in dictionary.lemmas(key))


def _um(root):
    return ('um' + root) if root[0] in VOWELS else root[0] + 'um' + root[1:]


def _in(word):
    """-in- の挿入 (kain → kinain、abot → inabot)"""
    return ('in' + word) if word[0] in VOWELS else word[0] + 'in' + word[1:]


def _cv(root):
    """重複する最初の音節 (kain → ka、abot → a、trabaho → ta)"""
    if root[0] in VOWELS:
        return root[0]
    vowel = next((c for c in root[1:] if c in VOWELS), 'a')
    return root[0] + vowel


@functools.lru_cache(maxsize=5000)
def root_of(lemma):
    """見出し (動詞の形でもよい) → 語根。基本語の表の語は語根のまま (matay「死」を分けない)"""
    if ' ' in lemma or lemma in PREFERRED_ROOTS or not _is_verb(lemma):
        return lemma
    return morphology._root_of(lemma)


@functools.lru_cache(maxsize=5000)
def lemma_for(root, voice):
    """語根と焦点 → 見出し (辞書にある形を先に)。無ければ規則の形"""
    if (root, voice) in IRREGULAR:
        return IRREGULAR[(root, voice)]
    candidates = {'actor': [_um(root), 'mag' + root, 'ma' + root, 'mang' + root],
                  'object': [root + 'in', root + 'hin', 'ma' + root],
                  'conveyance': ['i' + root], 'locative': [root + 'an', root + 'han']}[voice]
    for form in candidates:
        if _is_verb(form, voice) or (voice == 'object' and form.startswith('ma') and _is_verb(form)):
            return form
    for form in candidates:
        if _is_verb(form):
            return form
    return candidates[0]


@functools.lru_cache(maxsize=5000)
def _table_form(lemma, aspect):
    db = dictionary._connect()
    if db is None:
        return None
    row = db.execute('SELECT form FROM forms WHERE lemma = ? AND aspect = ? LIMIT 1', (lemma, aspect)).fetchone()
    return row[0] if row else None


def conjugate(lemma, root, aspect):
    """見出しとアスペクト → 語形 (辞書の表、無ければ規則)"""
    if lemma in BARE or aspect == 'infinitive':
        return lemma
    found = _table_form(lemma, aspect)
    if found:
        return found
    cv = _cv(root)
    if lemma == 'mag' + root:
        return {'completive': 'nag' + root, 'progressive': 'nag' + cv + root, 'contemplative': 'mag' + cv + root}[aspect]
    if lemma in ('maka' + root, 'ma' + root):   # magalak は ma- + galak (mag- でない)
        prefix = lemma[:len(lemma) - len(root)]
        rest = root
        return {'completive': 'na' + prefix[2:] + rest, 'progressive': 'na' + prefix[2:] + _cv(rest) + rest,
                'contemplative': prefix + _cv(rest) + rest}[aspect]
    if lemma.startswith('i') and lemma[1:] == root:
        return {'completive': 'i' + _in(root), 'progressive': 'i' + _in(cv + root),
                'contemplative': 'i' + cv + root}[aspect]
    if lemma.endswith(('an', 'han')) and lemma.startswith(root[:2]):
        return {'completive': _in(lemma), 'progressive': _in(cv + lemma), 'contemplative': cv + lemma}[aspect]
    if lemma.endswith(('in', 'hin')) and lemma != _um(root):
        return {'completive': _in(root), 'progressive': _in(cv + root), 'contemplative': cv + lemma}[aspect]
    # -um- (行為者焦点)
    return {'completive': _um(root), 'progressive': _um(cv + root), 'contemplative': cv + root}[aspect]


# ----------------------------------------------------------------------
# 語

def to_tagalog(lex, pos=None):
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    if lex.proper or lex.lang == 'tl':
        return lex.lemma
    for en in english.candidates(lex)[:1] or ([lex.en.split(',')[0]] if lex.en else []):
        key = (en.lower(), pos)
        if key in PREFERRED:
            return PREFERRED[key]
        if (en.lower().split(' ')[-1], pos) in PREFERRED:
            return PREFERRED[(en.lower().split(' ')[-1], pos)]
    target = transfer.best(lex, 'tl', pos)
    return target.lemma if target else None


def word(lex, pos=None):
    return to_tagalog(lex, pos) or '[%s]' % english.word(lex)


def link(modifier, noun):
    """繋ぎ: 母音で終われば -ng、n なら -g、ほかは na (magandang rosas、bahay na bato)"""
    if modifier.endswith(tuple(VOWELS)):
        return modifier + 'ng ' + noun
    if modifier.endswith('n'):
        return modifier + 'g ' + noun
    return modifier + ' na ' + noun


def noun_phrase(np, marker='ang'):
    """名詞句 (標識付き)。marker は ang / ng / sa / '' (標識なし)"""
    if np.members:
        conj = 'o' if np.conj in ('aut', 'vel') else 'at'
        inner = (' %s ' % conj).join(noun_phrase(m, '') for m in np.members)
        plural = marker and np.members[0].head is not None and np.members[0].head.proper
        return ((MARKERS[marker][3] if plural else MARKERS[marker][0]) + ' ' + inner) if marker else inner
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun':
        lemma = 'quid' if head.lemma == 'quis' and np.gender == 'n' else head.lemma
        forms = PRONOUNS.get((lemma, np.number)) or PRONOUNS.get((lemma, 'sg'))
        if forms and not np.relatives:
            return forms[{'ang': 0, 'ng': 1, 'sa': 2, '': 0}[marker]] if marker != 'sa' or lemma in ('hic', 'ille') \
                else ('sa ' + forms[2] if lemma not in ('ego', 'tū', 'is', 'sē', 'quis') else forms[2] if lemma == 'quis'
                      else 'sa ' + forms[2])
    if head.pos == 'pronoun' and np.relatives:
        text = 'ang' if marker == 'ang' else marker
        return ' '.join(x for x in (MARKERS[marker][0] if marker else '', relative_clause(np.relatives[0], None)) if x)
    main = word(head, 'noun')
    for m in np.modifiers:
        if isinstance(m, NP):
            main = link(' at '.join(_adjective(x.head) for x in m.members), main)
        elif m.pos == 'pronoun' and m.lemma in DEMONSTRATIVES:
            main = link(DEMONSTRATIVES[m.lemma], main)   # itong aklat
        elif m.lemma in POSSESSIVES:
            main = main + ' ' + POSSESSIVES[m.lemma]
        else:
            main = link(_adjective(m), main)
    for g in np.genitives:
        main += ' ' + noun_phrase(g, 'ng')
    for r in np.relatives:
        main = link(main, relative_clause(r, None))   # ang rosas na nakita ng babae
    if not marker:
        return main
    proper = head.proper
    plural = np.number == 'pl' and not proper
    tag = MARKERS[marker][(2 if proper else 1 if plural else 0)]
    return tag + ' ' + main


def _adjective(lex):
    if lex.pos == 'pronoun' and lex.lemma in DEMONSTRATIVES:
        return DEMONSTRATIVES[lex.lemma]
    found = to_tagalog(lex, 'adj')
    return found or '[%s]' % english.word(lex)


def prepositional(np, passive=False):
    import dataclasses
    if passive and np.prep.lemma in ('ā', 'ab'):
        return noun_phrase(dataclasses.replace(np, prep=None), 'ng')   # 受動の動作主は ng
    before, marker = PREPOSITIONS.get((np.prep.lemma, np.case), ('', 'sa'))
    inner = noun_phrase(dataclasses.replace(np, prep=None), marker)
    return (before + ' ' + inner).strip()


# ----------------------------------------------------------------------
# 節

def _focus(clause):
    """焦点 (行為者 actor / 対象 object / 移動物 conveyance) と、ang にする名詞句"""
    subjects, objects = clause.role('subject'), clause.role('object')
    verb_root = root_of(to_tagalog(clause.verb, 'verb') or clause.verb.lemma)
    if clause.voice == 'passive':
        return 'object', verb_root, subjects[0] if subjects else None
    if verb_root in BARE:   # alam ko「私は知っている」: する人は ng、目的語があれば ang
        return 'object', verb_root, objects[0] if objects else None
    if objects:
        voice = 'conveyance' if verb_root in CONVEYANCE_ROOTS else 'object'
        return voice, verb_root, objects[0]
    return 'actor', verb_root, subjects[0] if subjects else None


def verb_form(clause, voice, root):
    if clause.copula:
        return ''
    if root in BARE:
        return root
    lemma = lemma_for(root, voice)
    if clause.mood == 'imperative':
        return lemma
    if clause.mood == 'infinitive':
        return lemma
    return conjugate(lemma, root, ASPECTS.get(clause.tense, 'progressive'))


def realize(clause, gap=None):
    """節 → タガログ語。gap は関係節の空所の役割 (その名詞句は出さない)"""
    from .frame import lexical_negation, periphrastic
    clause = lexical_negation(periphrastic(clause))
    out = [_absolute(p) + ',' for p in clause.adjuncts if p.kind == 'absolute']
    head = len(out)
    if clause.negated:
        out.append('hindi')
    if clause.copula:
        words = _copula(clause)
        if clause.negated and words[0].startswith('nasa '):   # 所在の否定は wala sa (hindi nasa とは言わない)
            out.remove('hindi')
            words[0] = 'wala ' + words[0][2:]
        return ' '.join(out + words)
    voice, root, topic = _focus(clause)
    if gap is not None:   # 関係節: 空所を ang にする焦点
        voice = {'subject': 'actor' if clause.voice != 'passive' else 'object', 'object': 'object'}.get(gap, voice)
        if voice == 'object' and root in CONVEYANCE_ROOTS:
            voice = 'conveyance'
        topic = None
    out.append(verb_form(clause, voice, root))
    passive = clause.voice == 'passive'
    agents = [np for role, np in clause.args if passive and role == 'prep' and np.prep is not None and
              np.prep.lemma in ('ā', 'ab', 'abs')]
    for np in agents:   # 受動の動作主は動詞のすぐ後ろの ng (Pinuri ng guro ang bata)
        out.append(prepositional(np, True))
    actor = None if passive else (clause.role('subject') or [None])[0]
    if voice in ('object', 'conveyance'):
        if actor is not None and not (gap == 'subject'):
            out.append(noun_phrase(actor, 'ng'))
        elif actor is None and not passive and clause.person in (1, 2) and gap != 'subject':
            out.append(PRONOUNS[('ego' if clause.person == 1 else 'tū', clause.number)][1])   # ang lalaking nakita mo
        elif actor is None and not passive and gap is None:
            out.append(PRONOUNS[('is', clause.number)][1])
    for np in clause.role('object'):
        if np is not topic and gap != 'object':
            out.append(noun_phrase(np, 'ng'))
    if topic is not None:
        out.append(noun_phrase(topic, 'ang'))
    elif voice == 'actor' and gap is None and not clause.role('subject') and clause.mood != 'infinitive':
        out.append(PRONOUNS[({1: 'ego', 2: 'tū'}.get(clause.person, 'is'), clause.number)][0])
    for np in clause.role('recipient'):
        out.append(noun_phrase(np, 'sa'))
    for inner in clause.infinitives:
        out.append(_infinitive(inner))
    for inner in clause.questions:
        out.append(_question(inner))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement'):
            continue
        if role == 'prep':
            if not any(np is a for a in agents):
                out.append(prepositional(np, passive))
        elif role == 'means':
            out.append(noun_phrase(np, 'sa' if np.animate else 'ng'))
        else:
            out.append(noun_phrase(np, 'sa'))
    for adv in clause.adverbs:
        out.append(word(adv, 'adv'))
    out = [w for w in out if w]
    if clause.negated:   # 代名詞は節の最初の語 (hindi) の後ろに: Hindi ko alam、Hindi siya umaawit
        pronoun = next((k for k in range(head + 2, len(out)) if out[k] in ENCLITICS), None)
        if pronoun is not None:
            out.insert(head + 1, out.pop(pronoun))
    return ' '.join(out)


def _latin_verb_ja(participle):
    """ラテン語の分詞のもとの動詞の日本語の訳語 (cantāns → 歌う。訳語を選ぶ手がかりに)"""
    if participle.lang not in ('', 'la') or not participle.verb:
        return ''
    from . import latin
    return next((item['ja'] for _, item in latin._forms(participle.verb, 'verb')[:5] if item.get('ja')), '')


def _absolute(p):
    """独立奪格・属格独立: 過去は nang + 対象焦点の完了相 (Nang masakop ang lungsod)、現在は habang + 進行相"""
    ja = p.verb.verb_ja or _latin_verb_ja(p.verb)
    root = root_of(to_tagalog(Lex(p.verb.verb, 'verb', ja, lang=p.verb.lang), 'verb') or p.verb.verb) \
        if p.verb.verb else None
    subject = noun_phrase(p.subject, 'ang') if p.subject is not None else ''
    if root is None:
        return 'nang ' + subject
    if p.tense != 'present' and p.voice == 'passive':
        lemma = 'ma' + root if _is_verb('ma' + root) else lemma_for(root, 'object')
        return 'nang %s %s' % (conjugate(lemma, root, 'completive'), subject)
    if p.tense != 'present':
        return 'nang %s %s' % (conjugate(lemma_for(root, 'actor'), root, 'completive'), subject)
    return 'habang %s %s' % (conjugate(lemma_for(root, 'actor'), root, 'progressive'), subject)


def _copula(clause):
    """繋辞の文: 述語 (形容詞・名詞) が先、主語は ang (Maganda ang babae)"""
    complements = clause.role('complement') + clause.role('object')
    subject = (clause.role('subject') or [None])[0]
    places = [np for role, np in clause.args if role == 'prep' and np.prep is not None]
    if not complements and places and subject is not None:   # 所在: nasa + 場所 (Nasa hardin ang dalaga)
        where = prepositional(places[0])
        where = 'na' + where if where.startswith('sa ') else 'nasa ' + where
        return [where, noun_phrase(subject, 'ang')]
    if not complements:
        return ['may'] + ([noun_phrase(subject, '')] if subject is not None else [])
    np = complements[0]
    predicate = _adjective(np.head) if np.head is not None and np.head.pos in ('adj', 'participle') and not np.members \
        else noun_phrase(np, '')
    rest = [noun_phrase(subject, 'ang')] if subject is not None else \
        [PRONOUNS[({1: 'ego', 2: 'tū'}.get(clause.person, 'is'), clause.number)][0]]
    return [predicate] + rest


def relative_clause(r, head):
    gap = r.gap if r.gap in ('subject', 'object') else None
    return realize(r, gap=gap or 'subject')


def _infinitive(inner):
    import dataclasses
    if inner.infinitive_kind in ('saying', 'perception') and inner.role('subject'):
        return 'na ' + realize(dataclasses.replace(inner, mood='indicative', infinitive_kind=''))
    rest = dataclasses.replace(inner, args=[(r, np) for r, np in inner.args if r != 'subject'], mood='infinitive')
    return realize(rest)


def _question(inner):
    """間接疑問: kung sino ang … (主語の疑問)、kung ano ang …、kung bakit …"""
    import dataclasses
    from .frame import interrogative_np, without_interrogative
    owner, role, wh = interrogative_np(inner)
    finite = dataclasses.replace(inner, mood='indicative', question_word='')
    if wh is None:
        return QUESTION_WORDS.get(inner.question_word, 'kung') + ' ' + realize(finite)
    pronoun = 'sino' if inner.question_word in ('quis', 'quem', 'cui', 'cūius', 'cuius') and wh.gender != 'n' else 'ano'
    return 'kung %s ang %s' % (pronoun, realize(without_interrogative(finite), gap='subject' if role == 'subject'
                                                else 'object'))


def wrap(text, clause):
    words = [CONNECTIVES[k] for k in clause.connectives + ([clause.subordinator] if clause.subordinator else [])
             if k in CONNECTIVES]
    return ' '.join(words + [text])


def vocative(np):
    """呼びかけ: 標識なし (Panginoon, …)"""
    return noun_phrase(np, '')


def sentence(clauses):
    if not clauses:
        return ''
    from .frame import with_address
    out = ', '.join(wrap(with_address(c, realize, vocative), c) for c in clauses)
    return out[:1].upper() + out[1:] + '.'
