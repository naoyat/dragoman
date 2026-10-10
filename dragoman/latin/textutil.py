#!/usr/bin/env python
# -*- coding: utf-8 -*-

def load_text_from_file(file):
    buf = ''
    with open(file, "r") as fp:
        for line in fp:
            buf += line.strip() + ' '
    return buf

def _split_parens(word):
    """語の前後に付いた丸括弧を別のトークンにする: '(quī' → '(', 'quī' / 'erat)' → 'erat', ')'"""
    tokens = []
    while word.startswith('('):
        tokens.append('(')
        word = word[1:]
    closes = 0
    while word.endswith(')'):
        closes += 1
        word = word[:-1]
    if word:
        tokens.append(word)
    return tokens + [')'] * closes


# ローマ人の個人名 (praenōmen) の略: C. Caesar (= Gāius)、M. Tullius (= Mārcus)。後ろに名が続けば文の終わりでない
def _abbreviation(word, following):
    """略した個人名 (C. の点) か: 表の略 (latindic.PRAENOMINA) で、次の語が大文字で始まる (C. Caesar)"""
    from .latindic import PRAENOMINA
    return word in PRAENOMINA and following[:1].isupper()


def word_stream_from_text(text):
    in_sentence = False
    words = text.split()
    for i, word in enumerate(words):
        if word[0] in ['"', "'"]:
            yield word[0]
            word = word[1:]

        if word in ('', '---'): continue

        if not in_sentence:
            yield "BOS"
            in_sentence = True

        last_char = word[-1]
        if last_char in ['"', "'"] or (last_char == ')' and len(word) >= 2 and word[-2] in '.;:?!,'):
            end_quote = last_char
            word = word[:-1]
            last_char = word[-1] if word else ''
        else:
            end_quote = None

        if not end_quote and _abbreviation(word, words[i + 1] if i + 1 < len(words) else ''):
            yield word   # C. Caesar: 点は略の印 (文を区切らない)
        elif last_char in ['.', ';', ':', '?', '!']:
            yield from _split_parens(word[:-1])
            yield last_char
            yield "EOS"
            in_sentence = False
        elif last_char in [',']:
            yield from _split_parens(word[:-1])
            yield last_char
        elif word:
            yield from _split_parens(word)

        if end_quote:
            yield end_quote

    if in_sentence:
        yield "EOS"


def sentence_stream(ws):
    sentence = []
    for word in ws:
        if word == 'BOS':
            sentence = []
        elif word == 'EOS':
            yield sentence
            sentence = []
        else:
            sentence.append(word)


#def analyse_text(text, analyser, options=options):
#    for sentence in sentence_stream(word_stream_from_text(text)):
#        analyser(sentence, options)
