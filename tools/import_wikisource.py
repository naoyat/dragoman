#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Wikisource のページごとの翻刻 (Seite:…。action=raw で取った wiki の書式) をつないで、読むためのテキストにする
#
#   python3 tools/import_wikisource.py OUT.txt PAGE.wiki...
#
# 各ページの <section begin=text /> 〜 <section end=text /> の本文を順につなぎ (ページの境の改行は空白に)、
# 書式 ('''太字'''・<poem>・<br/>・{{…}} のテンプレート) を除く。詩 (<poem>) の行は改行のまま、段落は空行で区切る。
# テキストの著作権・ライセンスは元のページに従う (リポジトリには入れず $DRAGOMAN_DATA に置く)
#
import re
import sys


def page_text(wiki):
    m = re.search(r'<section begin=text />(.*?)<section end=text />', wiki, re.S)
    text = m.group(1) if m else re.sub(r'<noinclude>.*?</noinclude>', '', wiki, flags=re.S)
    text = re.sub(r'\{\{LineCenterSize\|[^|]*\|[^|]*\|(.*?)\}\}', r'\1', text, flags=re.S)   # 見出し
    text = re.sub(r'\{\{[^{}]*\}\}', '', text)
    text = re.sub(r"'''?", '', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    return text


def convert(pages):
    joined = ''
    for wiki in pages:
        text = page_text(wiki)
        if joined and not joined.endswith('\n\n') and not text.startswith('\n\n'):
            joined = joined.rstrip('\n') + ' ' + text.lstrip('\n')   # ページの境で続く段落
        else:
            joined += text
    joined = re.sub(r'<poem>\s*(.*?)\s*</poem>', lambda m: '\n' + m.group(1).strip() + '\n', joined, flags=re.S)
    joined = re.sub(r'[ \t]+\n', '\n', joined)
    joined = re.sub(r'\n{3,}', '\n\n', joined)
    return joined.strip() + '\n'


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    text = convert([open(p, encoding='utf-8').read() for p in paths])
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print('%d pages → %s (%d chars)' % (len(paths), out, len(text)))


if __name__ == '__main__':
    main()
