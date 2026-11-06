# -*- coding: utf-8 -*-
#
# 真言の語と種字の訳語 (解析で辞書より先に引く)
#
# 種字の saḥ・sa・aṃ などはふつうの文では別の語 (saḥ「彼」) なので、種字として引くのは
# 真言の文 (oṃ・hūṃ・svāhā・phaṭ・namaḥ samanta を含む) の中と、種字1字だけの行に限る
#
from . import script

# 真言の語 (どの文でも)
WORDS = {
    'oṃ': '聖音 (真言の始めに唱える)',
}
# 真言の語 (真言の文の中で)
MANTRA_WORDS = {
    'hūṃ': '種字 (阿閦如来・金剛薩埵。五大の風。真言の結びに)',
    'svāhā': '真言の結びの語 (成就あれ)',
    'phaṭ': '真言の語 (摧破)',
    'namaḥ': '帰命 (礼拝する)',
    'namo': '帰命 (礼拝する)',
}
# 種字 (1字で仏・菩薩を表す)
SEEDS = {
    'hrīḥ': '種字 (阿弥陀如来・千手観音)',
    'trāḥ': '種字 (虚空蔵菩薩)',
    'vaṃ': '種字 (金剛界大日如来)',
    'hāṃ': '種字 (不動明王)',
    'maṃ': '種字 (文殊菩薩)',
    'bhaḥ': '種字 (釈迦如来)',
    'saḥ': '種字 (勢至菩薩)',
    'sa': '種字 (聖観音)',
    'aṃ': '種字 (普賢菩薩)',
    'aḥ': '種字 (胎蔵界大日如来)',
    'a': '種字 (胎蔵界大日如来。五大の地)',
    'vi': '種字 (五大の水)',
    'ra': '種字 (五大の火)',
    'khaṃ': '種字 (五大の空)',
    'jaḥ': '種字 (四摂の金剛鉤)',
    'hoḥ': '種字 (四摂の金剛鈴)',
}
MARKERS = ('oṃ', 'hūṃ', 'svāhā', 'phaṭ')   # これを含む文は真言
HOMAGE = ('namaḥ', 'namo')                # namaḥ samanta … も真言


def _key(word):
    """表の鍵 (SLP1): 語末の m・m̐ は ṃ と同じに (hūm = hūṃ)、ॐ (vidyut は AUM に) は oṃ"""
    slp1 = script.to_slp1(word).replace('~', 'M')
    if slp1 == 'AUM':
        return 'oM'
    return slp1[:-1] + 'M' if slp1.endswith('m') else slp1


def _table(d):
    return {_key(w): gloss for w, gloss in d.items()}


_WORDS = _table(WORDS)
_MANTRA = _table(MANTRA_WORDS)
_SEEDS = _table(SEEDS)
_MARKERS = {_key(w) for w in MARKERS}
_HOMAGE = {_key(w) for w in HOMAGE}


def is_mantra(words):
    """語の列 (句読点を除く) が真言か: oṃ などを含むか、namaḥ samanta で始まる部分があるか、種字1字だけか"""
    keys = [_key(w) for w in words]
    if any(k in _MARKERS for k in keys):
        return True
    if any(a in _HOMAGE and b == 'samanta' for a, b in zip(keys, keys[1:])):
        return True
    return len(keys) == 1 and keys[0] in _SEEDS


def gloss(word, mantra):
    """語の訳語 (真言の語・種字)。無ければ None"""
    k = _key(word)
    if k in _WORDS:
        return _WORDS[k]
    if mantra:
        return _MANTRA.get(k) or _SEEDS.get(k)
    return None


def item(word, text):
    """解析の項目 (辞書の項目と同じ形)"""
    iast = script.iast(_key(word))
    return {'surface': iast, 'pos': 'interj', 'base': iast, 'ja': text, 'gloss_lang': 'ja'}
