# -*- coding: utf-8 -*-
#
# パーリ語の辞書 ($DRAGOMAN_DATA/pi/pali.sqlite。tools/build_pali_dic.py が Digital Pāḷi Dictionary から作る)
#
#   lookup('dhammā') → [{'pos': 'noun', 'base': 'dhamma', '_': [('Nom', 'pl', 'm'), …], 'ja': '法', …}]
#   deconstruct('sammantīdha') → ['sammanti', 'idha']
#
# 訳語は、表 (TERMS・PRONOUNS・INDECLINABLES) → サンスクリットの仏典の訳語 (sanskrit/buddhist.py の TERMS を
# DPD のサンスクリットの対応語 dhamma → dharma で引く: 法) → DPD の英語の語義 (core/en_ja で日本語に) の順
#
import json
import os
import re
import sqlite3

from dragoman.core import paths

DB = paths.data('pi', 'pali.sqlite')
_con = None

CASES = {'nom': 'Nom', 'acc': 'Acc', 'instr': 'Ins', 'dat': 'Dat', 'abl': 'Abl', 'gen': 'Gen', 'loc': 'Loc',
         'voc': 'Voc'}
GENDERS = {'masc': ('m',), 'fem': ('f',), 'nt': ('n',), 'x': ('m', 'f', 'n'), '1st': ('m', 'f'), '2nd': ('m', 'f'),
           'dual': ('m', 'f', 'n')}
PERSONS = {'1st': 1, '2nd': 2, '3rd': 3}
# 定動詞の品詞 → (時制, 法)
TENSES = {'pr': ('present', 'indicative'), 'aor': ('aorist', 'indicative'), 'fut': ('future', 'indicative'),
          'opt': ('present', 'optative'), 'imp': ('present', 'imperative'), 'cond': ('future', 'subjunctive'),
          'perf': ('perfect', 'indicative'), 'imperf': ('imperfect', 'indicative')}
# 分詞の品詞 → (時制, 態)
PARTICIPLES = {'pp': ('past', 'passive'), 'prp': ('present', 'active'), 'ptp': ('future', 'passive')}
NOUNS = ('masc', 'fem', 'nt')
SKIP = ('letter', 've', 'root', 'suffix', 'cs', 'prefix')   # 字・語尾・語根・接辞の見出し (語としては読まない)

# 代名詞の訳語 (見出し語 → (訳語, 説明))
PRONOUNS = {'ta': ('それ,彼,彼女', '指示代名詞'), 'eta': ('これ', '指示代名詞'), 'ima': ('これ', '指示代名詞'),
            'amu': ('あれ', '指示代名詞'), 'ya': ('〜するところの', '関係代名詞'), 'ka': ('何,誰', None),
            'ahaṃ': ('私', None), 'amha': ('私たち', None), 'mayaṃ': ('私たち', None), 'tvaṃ': ('あなた', None),
            'tumha': ('あなた', None), 'tumhe': ('あなたたち', None), 'sabba': ('すべての', '指示代名詞'),
            'añña': ('ほかの', '指示代名詞'), 'para': ('ほかの', None), 'sayaṃ': ('自ら', None),
            'bhavanta': ('あなた (敬称)', None), 'kiṃ': ('何', None), 'aññatara': ('ある,ある一つの', '指示代名詞')}
DETERMINERS = ('ta', 'eta', 'ima', 'amu', 'sabba', 'añña', 'aññatara', 'ya', 'ka')
# 不変化詞 (見出し語 → (品詞, 訳語))
INDECLINABLES = {
    'ca': ('conj', 'そして,〜と'), 'vā': ('conj', 'または'), 'na': ('adv', '〜ない'), 'mā': ('adv', '〜するな'),
    'no': ('adv', '〜ない'), 'eva': ('adv', 'まさに,〜だけ'), 'va': ('adv', 'まさに,〜のように'),
    'iti': ('conj', '〜と (引用)'), 'ti': ('conj', '〜と (引用)'), 'pi': ('adv', '〜も'), 'api': ('adv', '〜も,さえ'),
    'tu': ('conj', 'しかし'), 'pana': ('conj', 'しかし,さて'), 'hi': ('conj', 'なぜなら,実に'), 'kho': ('adv', '実に'),
    'atha': ('conj', 'さて,そして'), 'iva': ('adv', '〜のように'), 'viya': ('adv', '〜のように'),
    'yathā': ('conj', '〜のように'), 'tathā': ('adv', 'そのように'), 'yadā': ('conj', '〜するとき'),
    'tadā': ('adv', 'そのとき'), 'yadi': ('conj', 'もし'), 'sace': ('conj', 'もし'), 'ce': ('conj', 'もし'),
    'tattha': ('adv', 'そこで'), 'idha': ('adv', 'ここで,この世で'), 'ettha': ('adv', 'ここで'),
    'puna': ('adv', '再び'), 'evaṃ': ('adv', 'このように'), 'kathaṃ': ('adv', 'どのように'),
    'kuhiṃ': ('adv', 'どこに'), 'kuto': ('adv', 'どこから'), 'kadā': ('adv', 'いつ'), 'sadā': ('adv', 'いつも'),
    'tato': ('adv', 'それから,そこから'), 'yato': ('conj', '〜だから'), 'yasmā': ('conj', '〜だから'),
    'tasmā': ('adv', 'それゆえ'), 'saddhiṃ': ('adv', '〜とともに'), 'saha': ('adv', '〜とともに'),
    'vinā': ('adv', '〜なしに'), 'ajja': ('adv', '今日'), 'idāni': ('adv', '今'), 'pubbe': ('adv', '以前に'),
    'yāva': ('adv', '〜まで'), 'tāva': ('adv', 'その間'), 'nāma': ('adv', '〜という名の'), 'atthi': ('verb', 'ある'),
    'kudācanaṃ': ('adv', 'いつか,かつて'), 'sabbadā': ('adv', 'いつも'), 'bho': ('adv', 'おお'),
    'handa': ('adv', 'さあ'), 've': ('adv', '実に'), 'sādhu': ('adv', '善哉,よし'), 'namo': ('adv', '帰命 (礼拝する)'),
}
# パーリ語の仏典の語 (サンスクリットの表に無い語・形の違う語)
TERMS = {
    'bhikkhu': ('比丘', 'noun'), 'bhikkhunī': ('比丘尼', 'noun'), 'bhagavant': ('世尊', 'noun'),
    'bhante': ('尊者よ', 'noun'), 'āvuso': ('友よ', 'noun'), 'nibbāna': ('涅槃', 'noun'),
    'sāvatthī': ('舎衛城', 'name'), 'jetavana': ('祇園', 'name'), 'anāthapiṇḍika': ('給孤独', 'name'),
    'ārāma': ('園,精舎', 'noun'), 'sutta': ('経', 'noun'), 'sīla': ('戒', 'noun'), 'mettā': ('慈', 'noun'),
    'karuṇā': ('悲', 'noun'), 'muditā': ('喜', 'noun'), 'upekkhā': ('捨', 'noun'), 'paññā': ('慧,智慧', 'noun'),
    'samādhi': ('定', 'noun'), 'dukkha': ('苦', 'noun'), 'sukha': ('楽,幸福', 'noun'), 'vera': ('怨み', 'noun'),
    'avera': ('怨みの無いこと', 'noun'), 'mano': ('意,心', 'noun'), 'citta': ('心', 'noun'),
    'kamma': ('業', 'noun'), 'saṅgha': ('僧伽', 'noun'), 'arahant': ('阿羅漢', 'noun'), 'tathāgata': ('如来', 'noun'),
    'sammāsambuddha': ('正等覚者', 'noun'), 'gotama': ('ゴータマ', 'name'), 'ānanda': ('アーナンダ (阿難)', 'name'),
    'sāriputta': ('サーリプッタ (舎利弗)', 'name'), 'moggallāna': ('モッガッラーナ (目連)', 'name'),
    'saraṇa': ('帰依処', 'noun'), 'cakka': ('車輪', 'noun'), 'pada': ('足,足跡,句', 'noun'),
    'chāyā': ('影', 'noun'), 'māra': ('魔', 'noun'), 'satta': ('衆生', 'noun'), 'brāhmaṇa': ('婆羅門', 'noun'), 'samaṇa': ('沙門', 'noun'),
}
_POS_OF_TERM = {'noun': NOUNS, 'name': NOUNS, 'adj': ('adj',), 'verb': ()}


def available():
    return os.path.exists(DB)


def _db():
    global _con
    if _con is None:
        _con = sqlite3.connect('file:%s?mode=ro' % DB, uri=True)
    return _con


def base(lemma):
    """見出し語の番号を除く (dhamma 1.01 → dhamma)"""
    return re.sub(r' [0-9.]+$', '', lemma)


HEAD_COLUMNS = 'id lemma pos grammar meaning meaning_lit meaning_2 construction sanskrit root plus_case ' \
               'compound_type ebt base'.split()


def _heads(where, args):
    rows = _db().execute('SELECT %s FROM headwords WHERE %s' % (', '.join(HEAD_COLUMNS), where), args).fetchall()
    return [dict(zip(HEAD_COLUMNS, r)) for r in rows]


def form(key):
    """語形 → (見出しの番号の列, 文法の列, 分解の列)。無ければ None"""
    row = _db().execute('SELECT headwords, grammar, deconstructor FROM forms WHERE key = ?', (key,)).fetchone()
    return tuple(json.loads(x) for x in row) if row else None


def headwords_by_base(word):
    return _heads('base = ?', (word,))


def _english(text):
    """DPD の語義 → core/en_ja に渡す形 (「;」区切りをカンマに、括弧の補いを除く)"""
    senses = []
    for s in text.split(';'):
        s = re.sub(r'\([^)]*\)', '', s).strip().strip(',')
        s = re.sub(r'\s+', ' ', s)
        if s and s not in senses:
            senses.append(s)
    return ','.join(senses)


def _verb_base(english):
    """3人称単数の英語 (speaks・goes・does not resent) → 原形 (speak・go・not resent)"""
    out = []
    for sense in english.split(','):
        words = sense.split()
        if words:
            w = words[0]
            if w in ('is', 'are'):
                w = 'be'
            elif w == 'has':
                w = 'have'
            elif w == 'does' and len(words) > 1:
                w = None   # does not … → not …
            elif w == 'does':
                w = 'do'
            elif w.endswith('ies') and len(w) > 4:
                w = w[:-3] + 'y'
            elif re.search(r'(ch|sh|ss|x|o)es$', w):
                w = w[:-2]
            elif w.endswith('s') and not w.endswith('ss'):
                w = w[:-1]
            words = ([w] if w else []) + words[1:]
        out.append(' '.join(words))
    return ','.join(out)


def _meanings(head):
    """英語の語義の候補 (meaning_1・meaning_2・字義。en_ja に渡す形)"""
    out = []
    for m in (head['meaning'], head['meaning_2'], head['meaning_lit']):
        text = _english(m or '')
        if head['pos'] in TENSES or head['pos'] in ('inf',):
            text = _verb_base(text)
        if text and text not in out:
            out.append(text)
    return out


def meaning(head):
    """見出しの英語の語義 (en_ja に渡す形)。日本語に訳せる候補を先に (is calmed → meaning_2 の ceases)"""
    from dragoman.core import en_ja
    candidates = _meanings(head)
    group = 'verb' if head['pos'] in TENSES else ('noun' if head['pos'] in NOUNS else 'adj')
    for text in candidates:
        if en_ja.translate(text, group):
            return text
    return candidates[0] if candidates else ''


def _sanskrit_term(head):
    """サンスクリットの対応語の仏典の訳語 (dhamma → dharma → 法)"""
    from dragoman.sanskrit import buddhist
    sk = (head['sanskrit'] or '').split('[')[0].strip()
    if not sk or '+' in sk or ',' in sk:
        return None
    return buddhist.TERMS.get(sk)


def gloss(head):
    """見出し → (訳語, 訳語の言語, 固有名詞か)"""
    b = head['base']
    if b in TERMS and head['pos'] in _POS_OF_TERM[TERMS[b][1]]:
        ja, kind = TERMS[b]
        return ja, 'ja', kind == 'name'
    term = _sanskrit_term(head)
    if term and head['pos'] in _POS_OF_TERM.get(term[1], ()):
        return term[0], 'ja', term[1] == 'name'
    if head['pos'] in TENSES and re.search(r'\b(?:aor|fut|opt|imp|cond|perf|imperf) of ', head['grammar'] or ''):
        verb = _verb_of(head)   # アオリストなどの見出し (akkocchi「aor of akkosati」) は現在形の動詞の語義で
        if verb and verb is not head and verb['pos'] == 'pr':
            return gloss(verb)
    english = meaning(head) or b
    return english, 'en', 'name' in (head['grammar'] or '').split(', ') or english.startswith('name of ')


def _verb_of(head):
    """分詞・絶対分詞・不定詞の元の動詞 (grammar の「pp of bhamati」) の見出し"""
    m = re.search(r'\b(?:of|from) (\S+)', head['grammar'] or '')
    if not m:
        return None
    verb = m.group(1).strip(',').lstrip('√')
    heads = [h for h in headwords_by_base(verb) if h['pos'] in TENSES]
    return max(heads, key=lambda h: h['ebt']) if heads else None


def _absolutive_gloss(head, verb):
    from dragoman.core import en_ja
    english = meaning(verb) if verb else re.sub(r'^having ', '', meaning(head).split(',')[0])
    ja = en_ja.translate(english, 'verb') if verb else None
    if ja:
        from dragoman.core.japanese import JaVerb
        try:
            return JaVerb(ja.split(',')[0]).adverbial_form('active'), 'ja'
        except Exception:
            pass
    return '%s[絶対分詞]' % english.split(',')[0], 'en' if not verb else 'ja'


def _cngs(entries):
    out = []
    for desc in entries:
        parts = desc.split()
        gender = [p for p in parts if p in GENDERS]
        case = [CASES[p] for p in parts if p in CASES]
        number = [p for p in parts if p in ('sg', 'pl')]
        if not case or not number:
            continue
        for g in GENDERS[gender[0]] if gender else ('m', 'f', 'n'):
            cng = (case[0], number[0], g)
            if cng not in out:
                out.append(cng)
    out.sort(key=lambda cng: cng[0] == 'Voc')   # 呼格は後ろに
    return out


def _item(head, grammar, surface):
    """見出しと、その見出しに当たる文法の列 → 解析の項目 (無ければ None)"""
    pos, b = head['pos'], head['base']
    ja, lang, name = gloss(head)
    item = {'surface': surface, 'base': b, 'ja': ja, 'gloss_lang': lang, 'source': 'dpd', 'dpd': head['lemma']}
    if pos in NOUNS or pos in ('adj', 'card', 'ordin', 'pron', 'pp', 'prp', 'ptp'):
        cngs = _cngs(grammar)
        if not cngs:
            return None
        item['_'] = cngs
        if pos == 'pron':
            if b in PRONOUNS:
                item.update(ja=PRONOUNS[b][0], gloss_lang='ja')
                if PRONOUNS[b][1]:
                    item['desc'] = PRONOUNS[b][1]
            item['pos'] = 'pronoun'
        elif pos in PARTICIPLES:
            verb = _verb_of(head)
            if verb:
                tense, voice = PARTICIPLES[pos]
                vja, vlang, _ = gloss(verb)
                own = dict(item, pos='adj')   # 分詞の語自身の語義 (paduṭṭha「悪い」) も形容詞の読みに
                item.update(pos='participle', base=verb['base'], pres1sg=verb['base'], tense=tense, voice=voice,
                            ja=vja, gloss_lang=vlang)
                return [item, own] if own['ja'] != b else item
            else:
                item['pos'] = 'adj'
        else:
            item['pos'] = 'noun' if pos in NOUNS else 'adj'
            if name:
                item['name'] = True
        return item
    if pos in TENSES:
        verbs = [g for g in grammar if g.split()[-2:-1] and g.split()[-2] in PERSONS]
        if not verbs:
            return None
        parts = verbs[0].split()
        tense, mood = TENSES.get(parts[-3], TENSES[pos]) if len(parts) >= 3 else TENSES[pos]
        voice = 'passive' if 'pass' in (head['grammar'] or '').split(', ')[0].split() else 'active'
        item.update(pos='verb', pres1sg=b, tense=tense, mood=mood, voice=voice, person=PERSONS[parts[-2]],
                    number=parts[-1])
        if len(verbs) > 1:   # 同じ形で人称・数の違う読み (cond 1st sg = 2nd sg) は1つ目を
            item['alt'] = verbs[1:]
        if all(g.startswith('reflx') or 'opt' in g.split() for g in verbs):
            item['rare'] = True   # 反射態・願望法だけの読み (veraṃ: vāti の reflx opt 3pl) はほかの読みの後ろに
        return item
    if pos in ('abs', 'ger'):
        verb = _verb_of(head)
        ja, lang = _absolutive_gloss(head, verb)
        item.update(pos='adv', base=verb['base'] if verb else b, pres1sg=verb['base'] if verb else b, ja=ja,
                    gloss_lang=lang)
        return item
    if pos == 'inf':
        verb = _verb_of(head)
        vja, vlang, _ = gloss(verb) if verb else (meaning(head), 'en', False)
        item.update(pos='verb', mood='infinitive', pres1sg=verb['base'] if verb else b, ja=vja, gloss_lang=vlang)
        return item
    if pos in ('ind', 'idiom', 'sandhi'):
        if b in INDECLINABLES:
            p, ja = INDECLINABLES[b]
            item.update(pos=p, ja=ja, gloss_lang='ja', source='table')
        else:
            item['pos'] = 'conj' if 'conj' in (head['grammar'] or '') else 'adv'
        return item
    return None


def lookup(word):
    """語形 (ローマ字) → 解析の項目のリスト (良いものから)"""
    found = form(word)
    if not found and word in INDECLINABLES:
        p, ja = INDECLINABLES[word]
        return [{'surface': word, 'pos': p, 'base': word, 'ja': ja, 'gloss_lang': 'ja', 'source': 'table'}]
    if not found:
        return []
    ids, grammar, _ = found
    if not ids:
        return []
    heads = _heads('id IN (%s)' % ','.join('?' * len(ids)), ids)
    # 頻度の高い見出しから。同じ語幹・品詞の見出し (dhamma 1.01・1.02 …) は最初の1つ
    heads.sort(key=lambda h: (-(h['ebt'] or 0), h['lemma']))
    items, seen = [], set()
    for head in heads:
        if head['pos'] in SKIP:
            continue
        kind = 'noun' if head['pos'] in NOUNS else head['pos']
        if (head['base'], kind) in seen:
            continue
        coarse = {'noun': ('noun',), 'adj': ('adj',), 'card': ('card', 'adj'), 'ordin': ('ordin', 'adj'),
                  'pron': ('pron',), 'pp': ('pp',), 'prp': ('prp',), 'ptp': ('ptp',)}.get(kind, ('verb',))
        entries = [g[2] for g in grammar if g[0] == head['base'] and g[1] in coarse]
        item = _item(head, entries, word)
        if item:
            seen.add((head['base'], kind))
            items += item if isinstance(item, list) else [item]
    if word in INDECLINABLES and not any(i['base'] == word and i['pos'] in ('adv', 'conj') for i in items):
        p, ja = INDECLINABLES[word]
        items.insert(0, {'surface': word, 'pos': p, 'base': word, 'ja': ja, 'gloss_lang': 'ja', 'source': 'table'})
    # 代名詞・不変化詞の読みを先に (taṃ「それを」、na「〜ない」)
    nouns = {i['base'] for i in items if i['pos'] == 'noun'}
    # 仏典の訳語のある名詞 (buddha「仏」・dhamma「法」) と同じ語幹の形容詞の読みは除く (Buddhaṃ saraṇaṃ を
    # 「目覚めた帰依処を」と読まない)
    termed = {i['base'] for i in items if i['pos'] == 'noun' and i['gloss_lang'] == 'ja'}
    items = [i for i in items if not (i['pos'] == 'adj' and i['base'] in termed)]
    # 表の不変化詞・代名詞を先に (taṃ「それを」、na「〜ない」)。同じ語幹の名詞と形容詞 (dhamma) は名詞を先に
    # 固有名詞の読み (manomaya「意から成る」と独覚の名前) は後ろに
    # 仏典の訳語のある名詞 (sattā「衆生」) は、頻度の高い別の読み (sajjati の過去分詞) より先に
    items.sort(key=lambda i: (i.get('source') != 'table', bool(i.get('rare')), i['pos'] != 'pronoun',
                              i['base'] not in termed or i['pos'] != 'noun', bool(i.get('name')),
                              i['pos'] == 'adj' and i['base'] in nouns))
    return items


def deconstruct(word):
    """連声・複合語の分解 (DPD の deconstructor の最初の案) → 語の列。無ければ []"""
    found = form(word)
    if not found or not found[2]:
        return []
    return [p.strip() for p in found[2][0].split('+')]


def stem_items(word):
    """複合語の要素 (語幹) の項目 (格の無い名詞・形容詞として。mano → 意)"""
    heads = [h for h in headwords_by_base(word) if h['pos'] in NOUNS + ('adj', 'pron', 'card', 'ordin')]
    heads.sort(key=lambda h: (-(h['ebt'] or 0), h['lemma']))
    if not heads:
        return []
    h = heads[0]
    ja, lang, name = gloss(h)
    return [{'surface': word, 'pos': 'noun' if h['pos'] in NOUNS else 'adj', 'base': h['base'], 'ja': ja,
             'gloss_lang': lang, 'source': 'dpd', 'dpd': h['lemma'], 'desc': '複合語の要素', '_': []}]


def verb_items(lemma):
    """動詞の見出し語 → 訳語の項目 (分詞の元の動詞の訳語に)"""
    heads = [h for h in headwords_by_base(lemma) if h['pos'] in TENSES]
    out = []
    for h in sorted(heads, key=lambda h: -(h['ebt'] or 0))[:1]:
        ja, lang, _ = gloss(h)
        out.append({'pos': 'verb', 'ja': ja, 'gloss_lang': lang})
    return out


def etymology(lemma):
    """語源 (core/etymology の形): サンスクリットの対応語・語根・成り立ち"""
    out = []
    for h in sorted(headwords_by_base(lemma), key=lambda h: -(h['ebt'] or 0))[:1]:
        ancestors = []
        if h['sanskrit']:
            ancestors.append(('der', 'sa', h['sanskrit'], ''))
        if h['root']:
            ancestors.append(('root', 'pi', h['root'], ''))
        text = ('成り立ち: ' + h['construction'].replace('\n', ' / ')) if h['construction'] else ''
        if ancestors or text:
            out.append({'ancestors': ancestors, 'cognates': [], 'text': text})
    return out


def descendants(lemma):
    return []
