#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from . import orthography

from .words import words_path
from . import latin_noun
from . import latin_pronoun
from . import latin_adj
from . import latin_conj
from . import latin_prep
from . import latin_verb_reg
from . import latin_verb_irreg

from dragoman.core import util
from . import wiktionary


class LatinDic:
    dic = {}
    # Wiktionary 由来の補助辞書を使うか (環境変数 LATIN_WIKTIONARY=0 で無効)
    use_wiktionary = os.environ.get('LATIN_WIKTIONARY', '1') != '0'


def register(surface, info):
    if 'pos' not in info: return

    if surface in LatinDic.dic:
        LatinDic.dic[surface].append(info)
    else:
        LatinDic.dic[surface] = [info]


def register_items(items):
    for item in items:
        register(item['surface'], item)


_ortho_index = None


def _orthography_index():
    """綴りの流儀 (i/j, u/v) を同一視したキー → 辞書の表層形"""
    global _ortho_index
    if _ortho_index is None:
        _ortho_index = {}
        for surface in LatinDic.dic:
            _ortho_index.setdefault(orthography.uv(orthography.ij(surface)), []).append(surface)
    return _ortho_index


# 実際にはまず使われない読みを除く語: ita の分詞 (eō の非人称受動の完了分詞 itus の女性形)。副詞「このように」だけに
UNUSED_READINGS = {'ita': ('participle',)}


def lookup_hand(word):
    """手作りの辞書 (dragoman/latin/data/*.def から生成) を引く。
    表記どおりで無ければ、i/j を同一視 → u/v も同一視 (入力に v が無ければ) の順で探す
    (手作りの辞書は juvenis, Jovis のように j で書いている)"""
    items = _drop_unused(word, LatinDic.dic.get(word, None))
    if items:
        return items
    candidates = _orthography_index().get(orthography.uv(orthography.ij(word)), [])
    for allowed in (lambda s: orthography.ij(s) == orthography.ij(word),        # i/j だけ違う
                    lambda s: orthography.may_merge_uv(word)):                  # u/v も違う
        surfaces = [s for s in candidates if allowed(s)]
        if surfaces:
            return _drop_unused(word, [item for s in surfaces for item in LatinDic.dic[s]])
    return None


def lookup_wiktionary(word):
    """Wiktionary 由来の補助辞書を引く (tools/build_wiktionary_dic.py で作成)"""
    if not LatinDic.use_wiktionary:
        return None
    return _drop_unused(word, wiktionary.lookup(word))


def _drop_unused(word, items):
    unused = UNUSED_READINGS.get(word.lower())
    if items and unused:
        items = [item for item in items if item.get('pos') not in unused] or items
    return items


# 個人名 (praenōmen) の略 → (名, 日本語)。碑文・史書の C. Caesar、M. Tullius Cicerō
PRAENOMINA = {'A.': ('Aulus', 'アウルス'), 'Ap.': ('Appius', 'アッピウス'), 'C.': ('Gāius', 'ガイウス'),
              'Cn.': ('Gnaeus', 'グナエウス'), 'D.': ('Decimus', 'デキムス'), 'K.': ('Kaesō', 'カエソ'),
              'L.': ('Lūcius', 'ルキウス'), 'M.': ('Mārcus', 'マルクス'), "M'.": ('Mānius', 'マニウス'),
              'Mam.': ('Māmercus', 'マメルクス'), 'N.': ('Numerius', 'ヌメリウス'), 'P.': ('Pūblius', 'プブリウス'),
              'Q.': ('Quīntus', 'クィントゥス'), 'Ser.': ('Servius', 'セルウィウス'), 'Sex.': ('Sextus', 'セクストゥス'),
              'Sp.': ('Spurius', 'スプリウス'), 'T.': ('Titus', 'ティトゥス'), 'Ti.': ('Tiberius', 'ティベリウス'),
              'V.': ('Vibius', 'ウィビウス')}


def lookup_abbreviation(word):
    """個人名の略 (C. → Gāius)。略は変化しないので格は名に合わせて決まる (どの格の候補も持つ)"""
    if word not in PRAENOMINA:
        return None
    base, ja = PRAENOMINA[word]
    return [{'pos': 'noun', 'base': base, 'ja': ja, 'surface': word, 'desc': '個人名の略', 'proper': True,
             '_': [(case, 'sg', 'm') for case in ('Nom', 'Gen', 'Dat', 'Acc', 'Abl', 'Voc')]}]


def lookup(word):
    """手作りの辞書を優先し、無ければ Wiktionary 由来の補助辞書を引く。個人名の略 (C.) は表から"""
    return lookup_abbreviation(word) or lookup_hand_deponent(word) or lookup_wiktionary(word)


def lookup_hand_deponent(word):
    """手作りの辞書を引き、同じ形の形式受動態動詞の読みを Wiktionary から足す (_with_deponent)"""
    hand = lookup_hand(word)
    return _with_agent_noun(word, _with_deponent(word, _without_vocative_participle(hand))) if hand else hand


def _with_agent_noun(word, hand):
    """手作りの辞書では受動の動詞の形 (cantor: cantō の受動の1人称単数) としか読めない -or の語に、Wiktionary の
    名詞の読み (行為者名詞 cantor「歌い手」・amātor「恋する人」) を足す。手作りの辞書に名詞が無い語だけ"""
    if not word.lower().endswith('or') or not all(item.get('pos') == 'verb' and item.get('voice') == 'passive'
                                                  for item in hand):
        return hand
    nouns = [item for item in (lookup_wiktionary(word) or []) if item.get('pos') == 'noun']
    return hand + nouns


def _without_vocative_participle(items):
    """動詞の読み (vocāte: 命令法 2複) と同じ形の、呼格だけの分詞の読み (vocātus の呼格) は外す
    (分詞の呼格はまれで、残すと動詞が見つからない)"""
    if not any(item.get('pos') == 'verb' and item.get('mood') for item in items):
        return items
    def vocative_only(item):
        cases = item.get('_') or []
        return item.get('pos') == 'participle' and cases and all(c[0] == 'Voc' for c in cases)
    return [item for item in items if not vocative_only(item)] or items


def _with_deponent(word, hand):
    """手作りの辞書の受動の読み (miserēre: misereō の受動の命令法) と同じ形の、同じ語根の形式受動態動詞
    (misereor「憐れむ」の能動の命令法) が Wiktionary にあれば、その読みを先に加える (訳語は手作りの辞書の語)。
    手作りの辞書の活用は形式受動態を作らない"""
    passive = {item.get('pres1sg'): item for item in hand if item.get('pos') == 'verb' and item.get('voice') == 'passive'}
    if not passive:
        return hand
    deponents = {lemma[:-1] + 'or': item for lemma, item in passive.items() if lemma and lemma.endswith('ō')}
    found = [item for item in (lookup_wiktionary(word) or []) if item.get('pos') == 'verb' and
             item.get('voice') == 'active' and item.get('pres1sg') in deponents]
    if not found:
        return hand
    added = [dict(item, ja=deponents[item['pres1sg']]['ja'], gloss_lang='ja') for item in found]
    return added + hand


def dump():
    for k, v in list(LatinDic.dic.items()):
        print(util.render2(k, v))


def load_def(file, tags={}):
    items = []

    with open(file, 'r') as fp:
        for line in fp:
            if len(line) == 0: continue
            if line[0] == '#': continue

            fs = line.rstrip().split('\t')
            if len(fs) < 3: continue

            surface = fs[0] #.decode('utf-8')
            pos = fs[1]
            ja = fs[2]

            items.append(util.aggregate_dicts({'surface':surface, 'pos':pos, 'ja':ja}, tags))

    return items


def load():
    global _ortho_index
    _ortho_index = None

    items = []

    items += latin_noun.load()
    items += latin_pronoun.load()
    items += latin_adj.load()
    items += latin_conj.load()
    items += latin_prep.load()
    items += latin_verb_reg.load()
    items += latin_verb_irreg.load()

    items += load_def(words_path('adv.def'), {'pos':'adv'})
    items += load_def(words_path('other.def'))

    register_items(items)

    # return ld


if __name__ == '__main__':
#    for k, v in dic.items():
#        print util.render(k), util.render(v)
    pass
