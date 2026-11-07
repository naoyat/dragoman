#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ベトナム語の辞書 ($DRAGOMAN_DATA/vi/vietnamese.sqlite) を Wiktionary (kaikki.org の抽出データ) と Unihan から作る
#
#   python3 tools/build_vietnamese_dic.py
#
#   words    見出し語 (小文字) ごとの品詞・英語の語義 (日本語には実行時に core/en_ja.py で直す)・漢越語の漢字
#            (語源の「Sino-Vietnamese word from 生員」から。音節の数と字の数が合うものだけ)・字喃 / 漢字の表記・量詞・
#            「〜の別の綴り」などのつながり・ハノイの発音 (IPA)
#   hanviet  漢字 → 漢越音 (Wiktionary の「chữ Hán form of học」と Unihan の kVietnamese)
#
# 入力: $DRAGOMAN_DATA/vi/kaikki.org-dictionary-Vietnamese.jsonl (https://kaikki.org/dictionary/Vietnamese/。CC BY-SA)、
#       $DRAGOMAN_DATA/vi/unihan/Unihan_Readings.txt (https://www.unicode.org/Public/UCD/latest/ucd/Unihan.zip。
#       Unicode License v3)
# 出力: $DRAGOMAN_DATA/vi/vietnamese.sqlite (データは Wiktionary 由来 (CC BY-SA)。出力ファイルもその条件に従う)
#
# 解析には別に Stanza (pip install stanza。Apache 2.0) のベトナム語モデルが要る (約330MB。学習データは
# UD Vietnamese-VTB、CC BY-SA 4.0)。全部入りの default.zip (520MB) でなく、使うものだけを $DRAGOMAN_DATA/vi/stanza に:
#   python3 -c "import stanza, os; d = os.path.expanduser('~/.local/share/dragoman-data/vi/stanza');
#     stanza.download('vi', model_dir=d, processors='tokenize,pos,depparse');
#     stanza.download('vi', model_dir=d, processors={'tokenize': 'vtb_charlm'}, package=None)"
#
import os
import re
import sys
import json
import sqlite3
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths
from dragoman.core.wiktionary_import import english_glosses

POS = {'noun': 'noun', 'name': 'name', 'adj': 'adj', 'num': 'num', 'pron': 'pronoun', 'det': 'det', 'verb': 'verb',
       'adv': 'adv', 'conj': 'conj', 'particle': 'particle', 'prep': 'preposition', 'intj': 'intj',
       'classifier': 'classifier', 'counter': 'classifier', 'phrase': 'phrase', 'proverb': 'phrase',
       'prefix': 'prefix', 'suffix': 'suffix'}
LINKS = re.compile(r'^(?:traditional |modern )?(tone placement spelling|alternative form|alternative spelling|obsolete spelling|obsolete form|misspelling|'
                   r'eye dialect spelling|pronunciation spelling|rare form|dialectal form|clipping|abbreviation|'
                   r'initialism|ellipsis|superseded spelling|synonym) of ([^,;:()“”"]+)', re.I)
HAN = re.compile(r'[㐀-䶿一-鿿豈-﫿\U00020000-\U0003FFFF]')
SINO = re.compile(r'Sino-Vietnamese word from ([^\s,.;:()“”"]+)')
HAN_FORM = re.compile(r'^chữ Hán form of ([^\s(“]+(?: [^\s(“]+)*?)(?: \(|$)')


def _han(entry):
    """漢越語の漢字 (音節と字の数が合うもの)"""
    m = SINO.search(entry.get('etymology_text') or '')
    if not m:
        return None
    han = m.group(1)
    if not all(HAN.match(c) for c in han) or len(han) != len(entry['word'].split()):
        return None
    return han


def _ipa(entry):
    for sound in entry.get('sounds', []):
        if 'Hà-Nội' in (sound.get('tags') or []) and sound.get('ipa'):
            return sound['ipa'].strip('[]/')
    return None


def entries(path, readings):
    with open(path, encoding='utf-8') as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get('word', '')
            if entry.get('pos') == 'character':
                for sense in entry.get('senses', []):
                    for gloss in sense.get('glosses', [])[:1]:
                        m = HAN_FORM.match(gloss)
                        if m and len(word) == 1:
                            readings.add((word, m.group(1).lower(), 'wiktionary'))
                continue
            pos = POS.get(entry.get('pos'))
            if pos is None or not word:
                continue
            link = None
            for sense in entry.get('senses', []):
                for gloss in sense.get('glosses', [])[:1]:
                    m = LINKS.match(gloss)
                    if m:
                        link = (m.group(1).lower(), m.group(2).strip().rstrip('.').lower())
                        break
                if link:
                    break
            senses = [s for s in entry.get('senses', []) if not any(LINKS.match(g) for g in s.get('glosses', [])[:1])]
            en = english_glosses(entry, senses=senses, limit=4) if senses else ''
            forms = entry.get('forms', [])
            nom = ''.join(f['form'] for f in forms if 'CJK' in (f.get('tags') or []))[:12] or None
            classifiers = ','.join(f['form'] for f in forms if 'classifier' in (f.get('tags') or [])) or None
            yield (word.lower(), word, pos, en, _han(entry), nom, classifiers, link[0] if link else None,
                   link[1] if link else None, len(senses), _ipa(entry))


def unihan(path, readings):
    if not os.path.exists(path):
        print('missing:', path)
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            if '\tkVietnamese\t' not in line:
                continue
            code, _, values = line.rstrip('\n').split('\t')
            char = chr(int(code[2:], 16))
            for v in values.split():
                readings.add((char, v.lower(), 'unihan'))


def main():
    t0 = time.time()
    src = paths.data('vi', 'kaikki.org-dictionary-Vietnamese.jsonl')
    if not os.path.exists(src):
        sys.exit('missing: %s (https://kaikki.org/dictionary/Vietnamese/)' % src)
    out = paths.data('vi', 'vietnamese.sqlite')
    tmp = out + '.tmp'
    if os.path.exists(tmp):
        os.unlink(tmp)
    db = sqlite3.connect(tmp)
    db.executescript('''
        CREATE TABLE words (key TEXT, word TEXT, pos TEXT, en TEXT, han TEXT, nom TEXT, classifiers TEXT,
                            link TEXT, target TEXT, senses INTEGER, ipa TEXT);
        CREATE TABLE hanviet (char TEXT, reading TEXT, source TEXT);
    ''')
    readings = set()
    db.executemany('INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?)', entries(src, readings))
    unihan(paths.data('vi', 'unihan', 'Unihan_Readings.txt'), readings)
    db.executemany('INSERT INTO hanviet VALUES (?,?,?)', sorted(readings))
    db.executescript('''
        CREATE INDEX words_key ON words (key);
        CREATE INDEX hanviet_char ON hanviet (char);
        CREATE INDEX hanviet_reading ON hanviet (reading);
    ''')
    db.commit()
    n = db.execute('SELECT count(*) FROM words').fetchone()[0]
    h = db.execute('SELECT count(*) FROM words WHERE han IS NOT NULL').fetchone()[0]
    r = db.execute('SELECT count(DISTINCT char) FROM hanviet').fetchone()[0]
    db.execute('VACUUM')
    db.close()
    os.replace(tmp, out)
    print('%s: %d 語 (漢越語の漢字 %d)、漢越音 %d 字 (%.1fs)' % (out, n, h, r, time.time() - t0))


if __name__ == '__main__':
    main()
