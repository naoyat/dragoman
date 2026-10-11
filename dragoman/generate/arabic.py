#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 文の枠 (frame.Clause) からアラビア語 (現代標準アラビア語・正則語) の文を作る
#
#   語形は CAMeL Tools の生成器 (解析と同じ形態素の辞書 calima-msa-r13) で、格・数・性・定冠詞の有無を指定して作る。
#   英語 → アラビア語の語は、その辞書の項目の英語の訳語 (gloss) から (見出しがそのまま生成器の見出しになる)
#   語順: 動詞 - 主語 (主格) - 目的語 (対格) - 前置詞句 (属格)。動詞は主語の性に合わせ、主語が後ろなら単数
#     (رَأَتِ البِنْتُ الوَرْدَةَ)。人でない名詞の複数は女性単数として一致させる
#   時制: 完了 → 完了形、現在 → 未完了形 (直説法)、未来 → سَـ + 未完了形、未完了過去 → كانَ + 未完了形。
#     否定は 過去 لَمْ + 要求法、現在 لا、未来 لَنْ + 接続法
#   名詞文: 主語 (定) + 述語 (不定・主格)。否定は لَيْسَ + 対格、過去は كانَ + 対格
#   関係節: الَّذِي・الَّتِي・الَّذِينَ … を先行詞に合わせ、目的語の空所は動詞に代名詞の接尾辞 (رَآها)
#
import functools
import os

from . import english
from .frame import Lex, NP

PREPOSITIONS = {('in', 'Abl'): 'فِي', ('in', 'Acc'): 'إِلَى', ('ad', 'Acc'): 'إِلَى', ('ex', 'Abl'): 'مِنْ',
                ('ē', 'Abl'): 'مِنْ', ('ab', 'Abl'): 'مِنْ', ('ā', 'Abl'): 'مِنْ', ('cum', 'Abl'): 'مَعَ',
                ('dē', 'Abl'): 'عَنْ', ('sine', 'Abl'): 'بِدُونِ', ('per', 'Acc'): 'عَبْرَ', ('post', 'Acc'): 'بَعْدَ',
                ('ante', 'Acc'): 'قَبْلَ', ('sub', 'Abl'): 'تَحْتَ', ('super', 'Acc'): 'فَوْقَ', ('apud', 'Acc'): 'عِنْدَ',
                ('prō', 'Abl'): 'مِنْ أَجْلِ', ('propter', 'Acc'): 'بِسَبَبِ', ('ob', 'Acc'): 'بِسَبَبِ',
                ('contrā', 'Acc'): 'ضِدَّ', ('inter', 'Acc'): 'بَيْنَ', ('prope', 'Acc'): 'قُرْبَ', ('trāns', 'Acc'): 'عَبْرَ'}
# 代名詞: (ラテン語の代名詞, 数) → (独立形, 人称, 性, 数, 目的語の接尾辞の印 (CAMeL の enc0))
PRONOUNS = {('ego', 'sg'): ('أَنا', '1', 'm', 's', '1s_dobj'), ('ego', 'pl'): ('نَحْنُ', '1', 'm', 'p', '1p_dobj'),
            ('tū', 'sg'): ('أَنْتَ', '2', 'm', 's', '2ms_dobj'), ('tū', 'pl'): ('أَنْتُمْ', '2', 'm', 'p', '2mp_dobj'),
            ('is', 'sg'): ('هُوَ', '3', 'm', 's', '3ms_dobj'), ('is', 'pl'): ('هُمْ', '3', 'm', 'p', '3mp_dobj'),
            ('sē', 'sg'): ('نَفْسَهُ', '3', 'm', 's', '3ms_dobj'), ('sē', 'pl'): ('أَنْفُسَهُمْ', '3', 'm', 'p', '3mp_dobj')}
# 前置詞 + 代名詞の接尾辞 (لَنا「私たちに」・بِهِ・عَلَيْنا)。人称・性・数の印は PRONOUNS の接尾辞の印から (1p・3ms …)
SUFFIXES = {'1s': 'ي', '1p': 'نا', '2ms': 'كَ', '2mp': 'كُمْ', '3ms': 'هُ', '3fs': 'ها', '3mp': 'هُمْ'}
SUFFIXED_PREPOSITIONS = {
    'li_prep': ('لِي', 'لَنا', 'لَكَ', 'لَكُمْ', 'لَهُ', 'لَها', 'لَهُمْ'),
    'bi_prep': ('بِي', 'بِنا', 'بِكَ', 'بِكُمْ', 'بِهِ', 'بِها', 'بِهِمْ'),
    'فِي': ('فِيَّ', 'فِينا', 'فِيكَ', 'فِيكُمْ', 'فِيهِ', 'فِيها', 'فِيهِمْ'),
    'إِلَى': ('إِلَيَّ', 'إِلَيْنا', 'إِلَيْكَ', 'إِلَيْكُمْ', 'إِلَيْهِ', 'إِلَيْها', 'إِلَيْهِمْ'),
    'عَلَى': ('عَلَيَّ', 'عَلَيْنا', 'عَلَيْكَ', 'عَلَيْكُمْ', 'عَلَيْهِ', 'عَلَيْها', 'عَلَيْهِمْ'),
    'مِنْ': ('مِنِّي', 'مِنّا', 'مِنْكَ', 'مِنْكُمْ', 'مِنْهُ', 'مِنْها', 'مِنْهُمْ'),
    'عَنْ': ('عَنِّي', 'عَنّا', 'عَنْكَ', 'عَنْكُمْ', 'عَنْهُ', 'عَنْها', 'عَنْهُمْ'),
}
SUFFIX_KEYS = ('1s', '1p', '2ms', '2mp', '3ms', '3fs', '3mp')


def _pronoun_key(np):
    """代名詞の名詞句 → 接尾辞の印 (1p・3fs …)。代名詞でなければ None"""
    head = np.head
    if head is None or head.pos != 'pronoun' or (head.lemma, np.number) not in PRONOUNS or np.members:
        return None
    key = PRONOUNS[(head.lemma, np.number)][4].split('_')[0]
    return '3fs' if key == '3ms' and np.gender == 'f' else key


def with_pronoun(prep, np):
    """前置詞 (li_prep・bi_prep・فِي …) + 代名詞の接尾辞 (لَنا)。代名詞でなければ None"""
    key = _pronoun_key(np)
    if key is None:
        return None
    if prep in SUFFIXED_PREPOSITIONS:
        return SUFFIXED_PREPOSITIONS[prep][SUFFIX_KEYS.index(key)]
    if ' ' in prep:   # مِنْ أَجْلِ → مِنْ أَجْلِنا
        head, last = prep.rsplit(' ', 1)
        return head + ' ' + with_pronoun(last, np)
    stem = prep[:-1] if prep.endswith(('َ', 'ِ')) else prep   # بَعْدَ → بَعْدَنا、بَعْدِي
    return stem + ('ِي' if key == '1s' else prep[len(stem):] + SUFFIXES[key])


DEMONSTRATIVES = {('hic', 'm', 's'): 'هٰذا', ('hic', 'f', 's'): 'هٰذِهِ', ('hic', 'm', 'p'): 'هٰؤُلاءِ',
                  ('ille', 'm', 's'): 'ذٰلِكَ', ('ille', 'f', 's'): 'تِلْكَ', ('ille', 'm', 'p'): 'أُولٰئِكَ'}
RELATIVES = {('m', 's'): 'الَّذِي', ('f', 's'): 'الَّتِي', ('m', 'p'): 'الَّذِينَ', ('f', 'p'): 'اللَّواتِي'}
CONNECTIVES = {'et': ('وَ', True), 'que': ('وَ', True), 'atque': ('وَ', True), 'ac': ('وَ', True), 'sed': ('لٰكِنْ', False),
               'at': ('لٰكِنْ', False), 'autem': ('وَ', True), 'enim': ('فَـ', True), 'nam': ('فَـ', True),
               'igitur': ('فَـ', True), 'itaque': ('لِذٰلِكَ', False), 'tamen': ('مَعَ ذٰلِكَ', False),
               'neque': ('وَلا', False), 'tum': ('ثُمَّ', False), 'deinde': ('ثُمَّ', False), 'ubi': ('عِنْدَما', False),
               'cum': ('عِنْدَما', False), 'postquam': ('بَعْدَما', False), 'dum': ('بَيْنَما', False),
               'quod': ('لِأَنَّهُ', False), 'quia': ('لِأَنَّهُ', False), 'sī': ('إِذا', False), 'ut': ('لِكَيْ', False),
               'quamquam': ('مَعَ أَنَّهُ', False), 'aut': ('أَوْ', False), 'vel': ('أَوْ', False)}
QUESTION_WORDS = {'cūr': 'لِماذا', 'quārē': 'لِماذا', 'quōmodo': 'كَيْفَ', 'ubi': 'أَيْنَ', 'quō': 'إِلَى أَيْنَ',
                  'unde': 'مِنْ أَيْنَ', 'quandō': 'مَتَى', 'num': 'هَلْ', 'utrum': 'هَلْ', 'quantus': 'كَمْ', 'quot': 'كَمْ'}
# 教科書の基本語 (英語 → CAMeL の見出し, 品詞)
PREFERRED = {('only-begotten', 'adj'): ('وَحِيد', 'adj'), ('girl', 'noun'): ('بِنْت', 'noun'), ('boy', 'noun'): ('وَلَد', 'noun'), ('child', 'noun'): ('وَلَد', 'noun'),
             ('teacher', 'noun'): ('مُعَلِّم', 'noun'), ('book', 'noun'): ('كِتاب', 'noun'), ('rose', 'noun'): ('وَرْد', 'noun'),
             ('garden', 'noun'): ('حَدِيقَة', 'noun'), ('king', 'noun'): ('مَلِك', 'noun'), ('queen', 'noun'): ('مَلِكَة', 'noun'),
             ('city', 'noun'): ('مَدِينَة', 'noun'), ('citizen', 'noun'): ('مُواطِن', 'noun'), ('man', 'noun'): ('رَجُل', 'noun'),
             ('woman', 'noun'): ('اِمْرَأَة', 'noun'), ('sailor', 'noun'): ('بَحّار', 'noun'), ('farmer', 'noun'): ('فَلّاح', 'noun'),
             ('soldier', 'noun'): ('جُنْدِيّ', 'noun'), ('house', 'noun'): ('بَيْت', 'noun'), ('road', 'noun'): ('طَرِيق', 'noun'),
             ('sea', 'noun'): ('بَحْر', 'noun'), ('ship', 'noun'): ('سَفِينَة', 'noun'), ('letter', 'noun'): ('رِسالَة', 'noun'),
             ('daughter', 'noun'): ('اِبْنَة', 'noun'), ('son', 'noun'): ('اِبْن', 'noun'), ('master', 'noun'): ('سَيِّد', 'noun'),
             ('slave', 'noun'): ('عَبْد', 'noun'), ('god', 'noun'): ('إِلٰه', 'noun'), ('friend', 'noun'): ('صَدِيق', 'noun'),
             ('beautiful', 'adj'): ('جَمِيل', 'noun'), ('good', 'adj'): ('جَيِّد', 'adj'), ('bad', 'adj'): ('سَيِّئ', 'adj'),
             ('evil', 'adj'): ('شِرِّير', 'adj'), ('big', 'adj'): ('كَبِير', 'adj'), ('great', 'adj'): ('كَبِير', 'adj'),
             ('large', 'adj'): ('كَبِير', 'adj'), ('small', 'adj'): ('صَغِير', 'adj'), ('long', 'adj'): ('طَوِيل', 'adj'),
             ('new', 'adj'): ('جَدِيد', 'adj'), ('old', 'adj'): ('قَدِيم', 'adj'), ('wise', 'adj'): ('حَكِيم', 'adj'),
             ('brave', 'adj'): ('شُجاع', 'adj'), ('happy', 'adj'): ('سَعِيد', 'adj'),
             ('pity', 'verb'): ('رَحِم', 'verb'), ('feel pity', 'verb'): ('رَحِم', 'verb'),
             ('remove', 'verb'): ('رَفَع', 'verb'), ('take away', 'verb'): ('رَفَع', 'verb'),
             ('see', 'verb'): ('راوَنْد', 'verb'),   # 辞書の見出しの鍵がこの形 (生成すると رَأَى)
             ('praise', 'verb'): ('مَدَح', 'verb'), ('give', 'verb'): ('أَعْطَى', 'verb'),
             ('write', 'verb'): ('كَتَب', 'verb'), ('read', 'verb'): ('قَرَأ', 'verb'), ('sing', 'verb'): ('غَنَّى', 'verb'),
             ('love', 'verb'): ('أَحَبّ', 'verb'), ('walk', 'verb'): ('مَشَى', 'verb'), ('come', 'verb'): ('جاء', 'verb'),
             ('go', 'verb'): ('ذَهَب', 'verb'), ('say', 'verb'): ('قال', 'verb'), ('ask', 'verb'): ('سَأَل', 'verb'),
             ('know', 'verb'): ('عَرَف', 'verb'), ('flee', 'verb'): ('هَرَب', 'verb'), ('sleep', 'verb'): ('نام', 'verb'),
             ('weep', 'verb'): ('بَكَى', 'verb'), ('laugh', 'verb'): ('ضَحِك', 'verb'), ('rejoice', 'verb'): ('فَرِح', 'verb'),
             ('have', 'verb'): ('مَلَك', 'verb'), ('take', 'verb'): ('أَخَذ', 'verb'), ('capture', 'verb'): ('أَخَذ', 'verb'),
             ('send', 'verb'): ('أَرْسَل', 'verb'), ('kill', 'verb'): ('قَتَل', 'verb'), ('die', 'verb'): ('مات', 'verb'),
             ('live', 'verb'): ('سَكَن', 'verb'), ('inhabit', 'verb'): ('سَكَن', 'verb'), ('fight', 'verb'): ('قاتَل', 'verb')}
CASES = {'subject': 'n', 'complement': 'n', 'object': 'a', 'recipient': 'a', 'means': 'g', 'possessor': 'g'}
HUMAN_GLOSS = ('girl', 'boy', 'man', 'woman', 'king', 'queen', 'teacher', 'citizen', 'soldier', 'son', 'daughter',
               'sailor', 'farmer', 'friend', 'master', 'slave', 'people', 'child', 'god')


def _ensure_env():
    """CAMeL Tools のデータの置き場所 ($DRAGOMAN_DATA/ar/camel)。CAMeL Tools を読み込む前に"""
    from dragoman.core import paths
    os.environ.setdefault('CAMELTOOLS_DATA', paths.data('ar', 'camel'))


@functools.lru_cache(maxsize=1)
def _db():
    _ensure_env()
    from camel_tools.morphology.database import MorphologyDB
    return MorphologyDB.builtin_db(flags='g')


@functools.lru_cache(maxsize=1)
def _generator():
    db = _db()   # 置き場所の環境変数を入れてから CAMeL Tools を読み込む
    from camel_tools.morphology.generator import Generator
    return Generator(db)


def available():
    try:
        _ensure_env()
        return os.path.exists(os.path.join(os.environ.get('CAMELTOOLS_DATA', ''), 'data', 'morphology_db',
                                           'calima-msa-r13', 'morphology.db'))
    except Exception:
        return False


@functools.lru_cache(maxsize=1)
def _index():
    """英語 → [(見出し, 品詞, 性, よく使う度合い)] (CAMeL の辞書の項目の英語の訳語から)"""
    index = {}
    for lex, entries in _db().lemma_hash.items():
        for e in entries:
            pos = {'noun': 'noun', 'adj': 'adj', 'verb': 'verb', 'adv': 'adv', 'noun_prop': 'name'}.get(e.get('pos'))
            if pos is None:
                continue
            for rank, gloss in enumerate(g.strip().lower() for g in e.get('gloss', '').split(';')):
                if gloss:
                    index.setdefault(gloss, {})
                    key = (lex, pos)
                    score = rank - float(e.get('lex_logprob', -20)) / 4
                    if key not in index[gloss] or score < index[gloss][key][0]:
                        index[gloss][key] = (score, e.get('form_gen', 'm'))
    return index


def np_gender(np, found=None):
    """名詞句の性: 語末が ة なら女性、人を表す語は元の文の性 (puella 女性)、ほかは辞書の項目の性"""
    found = found if found is not None else (to_arabic(np.head, 'noun') if np.head is not None else None)
    if np.head is not None and np.head.lang == 'ar' and np.gender in ('m', 'f'):
        return np.gender   # 元がアラビア語なら元の語の性 (الوَرْدَة「1本のバラ」は女性。集合の وَرْد にしない)
    if found and found[0].endswith('ة'):
        return 'f'
    if is_human(np) and np.gender in ('m', 'f'):
        return np.gender
    return _gender(*found) if found else ('f' if np.gender == 'f' else 'm')


@functools.lru_cache(maxsize=10000)
def _gender(lex, pos):
    entries = _db().lemma_hash.get(lex, [])
    return next((e.get('form_gen') for e in entries if e.get('pos') == pos and e.get('form_gen') in ('m', 'f')), 'm')


def to_arabic(lex, pos=None):
    """語 → (CAMeL の見出し, 品詞)。見つからなければ None"""
    found = candidates(lex, pos)
    return found[0] if found else None


@functools.lru_cache(maxsize=20000)
def _candidates(lemma, lang, pos, en):
    sources = list(dict.fromkeys(en))
    out = []
    for en_ in sources[:1]:
        found = PREFERRED.get((en_.lower(), pos)) or PREFERRED.get((en_.lower().split(' ')[-1], pos))
        if found:
            out.append(found)
    for en_ in sources[:6]:
        for variant in (en_.lower(), en_.lower().split(' ')[-1], en_.lower().replace('to ', '')):
            hits = sorted((score, key) for key, (score, _) in _index().get(variant, {}).items()
                          if key[1] == pos or (pos == 'adj' and key[1] in ('adj', 'noun')))
            out.extend(key for _, key in hits if key not in out)
    return tuple(out[:8])


def candidates(lex, pos=None):
    """語 → [(CAMeL の見出し, 品詞)] (よさそうな順。生成できない見出しがあるので、作れるまで順に試す)"""
    pos = pos or {'participle': 'verb', 'name': 'noun'}.get(lex.pos, lex.pos)
    sources = english.candidates(lex) or ([e for e in (lex.en or '').split(',') if e])
    found = list(_candidates(lex.lemma, lex.lang, pos, tuple(sources)))
    if lex.lang == 'ar' and lex.lemma in _db().lemma_hash:   # 元がアラビア語なら元の見出しを先に (選び直さない)
        found = [(lex.lemma, pos)] + [f for f in found if f[0] != lex.lemma]
    return found


def _bare(text):
    """母音記号を除いた綴り"""
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text) if not unicodedata.combining(c))


def generate(lex, feats, pick=0):
    """語形 (pick: 候補の何番目。要求法は短い形を選ぶので -1)"""
    try:
        out = _generator().generate(lex, feats)
    except Exception:
        return None
    if not out:
        return None
    forms = list(dict.fromkeys(o['diac'] for o in out))
    if feats.get('pos') in ('noun', 'adj') and feats.get('num') == 's' and len(forms) > 1:
        # 単数として返る複数の形 (طَرِيق → الطُرُقُ) より、見出しの綴りを含む形を先に (الطَرِيقُ)
        stem = _bare(lex)
        forms.sort(key=lambda f: stem not in _bare(f))
    if pick == 'short':
        return min(forms, key=len)   # 要求法 (لَمْ يَرَ)
    if pick == 'long':
        return max(forms, key=len)   # 直説法 (يُغَنِّي。要求法の短い形と同じ特徴で返る)
    return forms[0]


def generate_any(found, feats, pick=0):
    """候補の見出しを順に試して、作れた最初の語形"""
    for lex, pos in found:
        for p in ([pos, 'noun'] if feats.get('pos') == 'adj' else [pos]):   # 形容詞の多くは辞書では名詞の品詞
            form = generate(lex, dict(feats, pos=p if feats.get('pos') != 'verb' else 'verb'), pick)
            if form:
                return form, lex, p
    return None, None, None


def is_human(np):
    if np.animate:
        return True
    return any(g in (english.word(np.head) if np.head else '') for g in HUMAN_GLOSS)


# ----------------------------------------------------------------------
# 名詞句

def noun_phrase(np, case='n', definite=True, prc1='0'):
    """名詞句: 名詞 (格・数・定冠詞) + 形容詞 (性・数・格・定の一致) + 属格 + 関係節"""
    if np.members:
        parts = [noun_phrase(m, case, definite) for m in np.members]
        return ' وَ'.join(parts)
    head = np.head
    if head is None:
        return ''
    if head.pos == 'pronoun' and (head.lemma, np.number) in PRONOUNS:
        if prc1 != '0':   # 前置詞の付いた代名詞は接尾辞に (لَنا)
            return with_pronoun(prc1, np)
        return PRONOUNS[(head.lemma, np.number)][0]
    if head.proper:   # Wiktionary の名前 (Iēsus → يَسُوع)。無ければ綴りのまま
        from .names import localized
        found = localized(head, 'ar')
        return found[0] if found else head.lemma
    found = candidates(head, 'noun')
    if not found:
        return '[%s]' % english.word(head)
    num = 'p' if np.number == 'pl' else 's'
    definite = definite and not np.genitives and np.definite is not False   # 元の文で不定 (冠詞なし) なら不定
    feats = {'pos': 'noun', 'num': num, 'cas': case, 'stt': 'd' if definite else ('c' if np.genitives else 'i')}
    if definite:
        feats['prc0'] = 'Al_det'
    if prc1 != '0':
        feats['prc1'] = prc1
    word = lex = None
    for lex_, pos_ in found:
        gender = np_gender(np, (lex_, pos_))
        word = generate(lex_, dict(feats, pos=pos_, gen=gender)) or generate(lex_, dict(feats, pos=pos_))
        if word:
            lex = lex_
            break
    if word is None:
        lex, gender = found[0][0], np_gender(np, found[0])
        word = lex
    out = [word]
    agree_gender, agree_num = (('f', 's') if num == 'p' and not is_human(np) else (gender, num))   # 人でない複数は女性単数
    for g in np.genitives:
        out.append(noun_phrase(g, 'g'))
    for m in np.modifiers:
        if isinstance(m, NP):
            out.append(' وَ'.join(adjective(x.head, case, agree_gender, agree_num, definite or bool(np.genitives))
                                   for x in m.members))
        elif m.pos == 'pronoun' and m.lemma in ('hic', 'ille'):
            demo = DEMONSTRATIVES.get((m.lemma, agree_gender, agree_num)) or DEMONSTRATIVES[(m.lemma, 'm', 's')]
            out.insert(0, demo)   # هٰذا الكِتابُ
        else:
            out.append(adjective(m, case, agree_gender, agree_num, definite or bool(np.genitives)))
    for r in np.relatives:
        out.append(relative_clause(r, agree_gender, agree_num, definite))
    return ' '.join(w for w in out if w)


def adjective(lex, case, gender, num, definite):
    found = candidates(lex, 'adj')
    if not found:
        return '[%s]' % english.word(lex)
    feats = {'pos': 'adj', 'gen': gender, 'num': num, 'cas': case, 'stt': 'd' if definite else 'i'}
    if definite:
        feats['prc0'] = 'Al_det'
    form, _, _ = generate_any(found, feats)
    return form or found[0][0]


def prepositional(np, passive=False):
    import dataclasses
    inner = dataclasses.replace(np, prep=None)
    if passive and np.prep.lemma in ('ā', 'ab'):
        return with_pronoun('مِنْ قِبَلِ', inner) or 'مِنْ قِبَلِ ' + noun_phrase(inner, 'g')   # 受動の動作主
    prep = PREPOSITIONS.get((np.prep.lemma, np.case), 'فِي')
    inner_text = with_pronoun(prep, inner) or noun_phrase(inner, 'g')
    if not inner_text or not inner_text.strip('[]?'):
        return ''   # 中身の分からない句 (辞書に無い語) は書かない
    return inner_text if inner_text.startswith(prep[:2]) and with_pronoun(prep, inner) else prep + ' ' + inner_text


# ----------------------------------------------------------------------
# 節

def _agreement(clause):
    """動詞の人称・性・数 (主語が名詞なら3人称で性だけ合わせる。人でない複数は女性単数)"""
    subjects = clause.role('subject')
    if subjects and subjects[0].members:   # 並列の主語: 動詞が前なら最初の要素に一致 (単数。غَنَّى الوَلَدُ وَالبِنْتُ)
        first = subjects[0].members[0]
        if first.head is not None and first.head.pos != 'pronoun':
            return '3', np_gender(first) if not first.head.proper else ('f' if first.gender == 'f' else 'm'), 's', True
    if subjects and subjects[0].head is not None and subjects[0].head.pos != 'pronoun':
        np = subjects[0]
        gender = np_gender(np) if not np.head.proper else ('f' if np.gender == 'f' else 'm')
        if np.number == 'pl' and not is_human(np):
            gender = 'f'
        return '3', gender, 's', True   # 主語が動詞の後ろ: 単数
    if subjects and subjects[0].head is not None and (subjects[0].head.lemma, subjects[0].number) in PRONOUNS:
        _, per, gen, num, _ = PRONOUNS[(subjects[0].head.lemma, subjects[0].number)]
        return per, ('f' if subjects[0].gender == 'f' and per != '1' else gen), num, False
    return str(clause.person), 'f' if False else 'm', 'p' if clause.number == 'pl' else 's', False


def verb_form(clause, enc0='0', per=None, gen=None, num=None):
    """動詞の語形 (時制・法・態・否定の語を含む語の列)"""
    found = [f for f in candidates(clause.verb, 'verb') if f[1] == 'verb']
    if not found:
        return ['[%s]' % english.word(clause.verb)]
    a_per, a_gen, a_num, _ = _agreement(clause)
    per, gen, num = per or a_per, gen or a_gen, num or a_num
    vox = 'p' if clause.voice == 'passive' else 'a'
    base = {'pos': 'verb', 'per': per, 'gen': gen, 'num': num, 'vox': vox}
    if enc0 != '0':
        base['enc0'] = enc0

    def form(feats, pick=0):
        word, _, _ = generate_any(found, feats, pick)
        return word or found[0][0]
    tense = clause.tense
    if clause.mood == 'imperative':   # 命令形は要求法の2人称から (辞書の生成器は命令形を作らない)。禁止は لا + 要求法
        jussive = form(dict(base, asp='i', per='2'), 'short')
        return ['لا', jussive] if clause.negated else [imperative(jussive)]
    if clause.negated:
        if tense in ('perfect', 'past-perfect', 'imperfect'):
            return ['لَمْ', form(dict(base, asp='i'), 'short')]   # 要求法 (短い形)
        if tense in ('future', 'future-perfect'):
            return ['لَنْ', form(dict(base, asp='i'), 'long')]
        return ['لا', form(dict(base, asp='i'), 'long')]
    if tense in ('perfect', 'past-perfect'):
        return [form(dict(base, asp='p'))]
    if tense in ('future', 'future-perfect'):
        return [form(dict(base, asp='i', prc1='sa_fut'), 'long')]
    if tense == 'imperfect':
        kana = generate('كان', {'pos': 'verb', 'asp': 'p', 'per': per, 'gen': gen, 'num': num, 'vox': 'a'}) or 'كانَ'
        return [kana, form(dict(base, asp='i'), 'long')]
    return [form(dict(base, asp='i'), 'long')]


FATHA, DAMMA, KASRA, SUKUN = '\u064e', '\u064f', '\u0650', '\u0652'


def imperative(jussive):
    """要求法の2人称 → 命令形: 接頭辞 تَـ / تُـ を外し、子音の連続で始まれば語頭に母音を
    (تَكْتُبْ → اُكْتُبْ、تَرْحَمْ → اِرْحَمْ、第4型 تُكْرِمْ → أَكْرِمْ、تُعَلِّمْ → عَلِّمْ、تَقُلْ → قُلْ)"""
    import unicodedata
    word = unicodedata.normalize('NFD', jussive)
    if not word.startswith('ت') or len(word) < 3 or word[1] not in (FATHA, DAMMA):
        return jussive
    prefix_vowel, rest = word[1], word[2:]
    if len(rest) > 1 and rest[1] == SUKUN:
        if prefix_vowel == DAMMA:
            rest = 'أَ' + rest   # 第4型 (أَفْعَلَ)
        else:
            stem_vowel = next((c for c in rest[2:] if c in (FATHA, DAMMA, KASRA)), KASRA)
            rest = ('اُ' if stem_vowel == DAMMA else 'اِ') + rest
    return unicodedata.normalize('NFC', rest)


def passive_possible(clause):
    """受動の形が辞書で作れるか (作れなければ能動に組み替える)"""
    found = [f for f in candidates(clause.verb, 'verb') if f[1] == 'verb']
    feats = {'pos': 'verb', 'asp': 'p', 'per': '3', 'gen': 'm', 'num': 's', 'vox': 'p'}
    return any(generate(lex, feats) for lex, _ in found[:3])


def to_active(clause):
    """受動の文 → 能動 (動作主 ā + 奪格を主語に、元の主語を目的語に。動作主が無ければ3人称複数の「人々が」)"""
    import dataclasses
    agent = next((np for role, np in clause.args if role == 'prep' and np.prep is not None and
                  np.prep.lemma in ('ā', 'ab', 'abs')), None)
    args = []
    for role, np in clause.args:
        if np is agent:
            continue
        args.append(('object', np) if role == 'subject' else (role, np))
    if agent is not None:
        args.insert(0, ('subject', dataclasses.replace(agent, prep=None, case='Nom')))
        return dataclasses.replace(clause, voice='active', args=args)
    return dataclasses.replace(clause, voice='active', args=args, person=3, number='pl')


def realize(clause, gap=None, antecedent=None):
    """節 → アラビア語の語の列。gap は関係節の空所の役割 (目的語なら動詞に代名詞の接尾辞)"""
    from .frame import lexical_negation, periphrastic, dative_as_object
    clause = dative_as_object(lexical_negation(periphrastic(clause)), 'ar')
    if clause.voice == 'passive' and not clause.copula and gap is None and not passive_possible(clause):
        clause = to_active(clause)   # 受動の形が無い動詞 (مَدَح): مَدَحَ المُعَلِّمُ الوَلَدَ
    out = []
    for p in clause.adjuncts:
        if p.kind == 'absolute':
            out.append(_absolute(p) + '،')
    if clause.copula:
        return ' '.join(out + _nominal(clause, gap))
    subjects = clause.role('subject')
    enc0 = '0'
    if gap == 'object' and antecedent is not None:
        enc0 = '3%s%s_dobj' % antecedent   # الوَرْدَة الَّتِي رَآها (目的語の空所の代名詞)
    objects = [np for np in clause.role('object') if gap != 'object']
    pronoun_object = objects and objects[0].head is not None and objects[0].head.pos == 'pronoun' and \
        (objects[0].head.lemma, objects[0].number) in PRONOUNS
    if pronoun_object:
        enc0 = PRONOUNS[(objects[0].head.lemma, objects[0].number)][4]
        objects = objects[1:]
    if gap == 'subject' and antecedent is not None:
        out += verb_form(clause, enc0, '3', antecedent[0], antecedent[1])
    else:
        out += verb_form(clause, enc0)
    for np in subjects:
        if gap == 'subject' or (np.head is not None and np.head.pos == 'pronoun'):
            continue   # 代名詞の主語は動詞の人称で分かる (書かない)
        out.append(noun_phrase(np, 'n'))
    for np in objects:
        out.append(noun_phrase(np, 'a'))
    for np in clause.role('recipient'):
        out.append(noun_phrase(np, 'g', prc1='li_prep'))
    for inner in clause.infinitives:
        out.append(_infinitive(inner))
    for inner in clause.questions:
        out.append(_question(inner))
    for role, np in clause.args:
        if role in ('subject', 'object', 'recipient', 'complement'):
            continue
        if role == 'prep':
            out.append(prepositional(np, clause.voice == 'passive'))
        elif role == 'means':   # 与格と奪格の同形: 人なら受け手 لِـ、ほかは手段 بِـ
            out.append(noun_phrase(np, 'g', prc1='li_prep' if np.animate else 'bi_prep'))
        else:
            text = noun_phrase(np, 'g')
            if text.strip('[]?'):   # 中身の分からない句は書かない
                out.append('فِي ' + text)
    for adv in clause.adverbs:
        found = to_arabic(adv, 'adv')
        out.append(found[0] if found else '[%s]' % english.word(adv))
    return ' '.join(w for w in out if w)


def _nominal(clause, gap=None):
    """名詞文: 主語 (定・主格) + 述語 (不定・主格)。否定は لَيْسَ + 対格、過去は كانَ + 対格"""
    subjects = clause.role('subject')
    complements = clause.role('complement') + clause.role('object')
    subject = subjects[0] if subjects else None
    per, gen, num, _ = _agreement(clause)
    if subject is not None and subject.head is not None and subject.head.pos != 'pronoun':
        gen = np_gender(subject) if not subject.head.proper else ('f' if subject.gender == 'f' else 'm')
        num = 'p' if subject.number == 'pl' and is_human(subject) else 's'
        if subject.number == 'pl' and not is_human(subject):
            gen = 'f'
    past = clause.tense in ('perfect', 'imperfect', 'past-perfect')
    case = 'a' if past or clause.negated else 'n'
    out = []
    if past or clause.negated:
        aux_lex = 'لَيْس' if clause.negated and not past else 'كان'
        aux = generate(aux_lex, {'pos': 'verb', 'asp': 'p', 'per': per, 'gen': gen, 'num': num, 'vox': 'a'}) or \
            ('لَيْسَ' if aux_lex == 'لَيْس' else 'كانَ')
        out.append(('لَمْ ' + (generate('كان', {'pos': 'verb', 'asp': 'i', 'mod': 'j', 'per': per, 'gen': gen,
                                                'num': num, 'vox': 'a'}) or 'يَكُنْ')) if clause.negated and past else aux)
    if subject is not None and gap != 'subject':
        out.append(noun_phrase(subject, 'n') if subject.head is None or subject.head.pos != 'pronoun' else
                   PRONOUNS.get((subject.head.lemma, subject.number), ('هُوَ',))[0])
    if not complements:
        return out + ['مَوْجُود']
    np = complements[0]
    from .frame import adjective_members
    if adjective_members(np):   # 形容詞の並列 (طَوِيلٌ وَعَرِيضٌ): 主語に一致
        out.append(' وَ'.join(adjective(m.head, case, gen, num, False) for m in adjective_members(np)))
    elif np.head is not None and np.head.pos in ('adj', 'participle') and not np.members:
        out.append(adjective(np.head, case, gen, num, False))
    else:
        out.append(noun_phrase(np, case, definite=False))
    return out


def relative_clause(r, gender, num, definite):
    """関係節: 先行詞が定なら الَّذِي など (性・数を合わせる)。目的語の空所は動詞に代名詞の接尾辞"""
    gap = r.gap if r.gap in ('subject', 'object') else None
    pronoun = RELATIVES.get((gender, num)) if definite else ''
    return ' '.join(w for w in (pronoun, realize(r, gap=gap or 'subject', antecedent=(gender, num))) if w)


def _infinitive(inner):
    import dataclasses
    finite = dataclasses.replace(inner, mood='indicative', infinitive_kind='')
    if inner.infinitive_kind in ('saying', 'perception') and inner.role('subject'):
        return 'أَنَّ ' + ' '.join(_nominal_from(finite))
    return 'أَنْ ' + realize(dataclasses.replace(finite, args=[(r, np) for r, np in finite.args if r != 'subject']))


def _nominal_from(clause):
    """أَنَّ の後ろ: 主語 (対格) を先に、述語を後ろに"""
    subjects = clause.role('subject')
    rest = realize(clause, gap='subject') if subjects else realize(clause)
    if subjects and subjects[0].head is not None and subjects[0].head.pos != 'pronoun':
        return [noun_phrase(subjects[0], 'a'), rest]
    return [rest]


def _question(inner):
    """間接疑問: مَنْ・ماذا・لِماذا・أَيْنَ … + 節 (主語の疑問は مَنْ + 動詞)"""
    import dataclasses
    from .frame import interrogative_np, without_interrogative
    owner, role, wh = interrogative_np(inner)
    finite = dataclasses.replace(inner, mood='indicative', question_word='')
    if wh is None:
        return QUESTION_WORDS.get(inner.question_word, 'هَلْ') + ' ' + realize(finite)
    pronoun = 'مَنْ' if inner.question_word in ('quis', 'quem', 'cui', 'cūius', 'cuius') and wh.gender != 'n' \
        else 'ماذا'
    return pronoun + ' ' + realize(without_interrogative(finite), gap=role if role in ('subject', 'object') else None)


def _absolute(p):
    """独立奪格・属格独立: بَعْدَ أَنْ + 受動の完了 (بَعْدَ أَنْ أُخِذَتِ المَدِينَةُ)、現在は بَيْنَما + 未完了"""
    if not p.verb.verb or p.subject is None:
        return ''
    from .frame import Clause
    clause = Clause(Lex(p.verb.verb, 'verb', p.verb.verb_ja or _latin_verb_ja(p.verb), lang=p.verb.lang),
                    tense='present' if p.tense == 'present' else 'perfect',
                    voice='passive' if p.voice == 'passive' else 'active', args=[('subject', p.subject)])
    return ('بَيْنَما ' if p.tense == 'present' else 'بَعْدَ أَنْ ') + realize(clause)


def _latin_verb_ja(participle):
    if participle.lang not in ('', 'la') or not participle.verb:
        return ''
    from . import latin
    return next((item['ja'] for _, item in latin._forms(participle.verb, 'verb')[:5] if item.get('ja')), '')


def wrap(text, clause):
    for key in reversed(clause.connectives + ([clause.subordinator] if clause.subordinator else [])):
        if key in CONNECTIVES:
            word, attached = CONNECTIVES[key]
            text = (word.rstrip('ـ') + text) if attached else (word + ' ' + text)   # وَ・فَـ は次の語に付ける
    return text


def transliterate(text):
    from dragoman.arabic import script
    return ' '.join(script.translit(w) if script.is_arabic(w) else w for w in text.split(' '))


def vocative(np):
    """呼びかけ: يا + 冠詞もタンウィーンも無い主格 (يا رَبُّ)"""
    return 'يا ' + noun_phrase(np, 'n', False).replace('ٌ', 'ُ')


def sentence(clauses):
    """アラビア文字 (と転写の行)"""
    if not clauses:
        return ''
    import unicodedata
    from .frame import with_address
    text = unicodedata.normalize('NFC', '، '.join(wrap(with_address(c, realize, vocative, '، ', 'يا '), c)
                                                 for c in clauses) + '.')   # 記号の並びをそろえる
    return '%s\n            %s' % (text, transliterate(text))
