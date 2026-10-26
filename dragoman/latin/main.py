#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ラテン語のコマンド (python3 dragoman.py --lang=la。ファイルを解析、無ければ対話モード: 変化表・マクロンの推定)
#
import sys
import os
import select
import getopt

import dragoman.latin.textutil as textutil
import dragoman.latin.latin_char as char
import dragoman.latin.latindic as latindic
import dragoman.core.util as util
from dragoman.core import options as option_defs
from dragoman.latin import analyzer
from dragoman.core import render
from dragoman.latin import macronizer

from dragoman.core import speech as speak_latin

def latin_word_notes(options):
    """ノートの語の注 (子孫語・語源)。端末と同じ色 (core.cli.word_notes と同じ形) で"""
    from dragoman.core import ansi_color, descendants, etymology
    if not (options.show_descendants or options.show_etymology):
        return None

    def notes(word):
        lines = []
        if options.show_descendants:
            lines += [ansi_color.fgcolor(ansi_color.CYAN, '%s: %s' % (lemma, text))
                      for lemma, text in descendants.describe_word(word)]
        if options.show_etymology:
            for lemma, ety in etymology.describe_word(word):
                lines.append(ansi_color.fgcolor(ansi_color.MAGENTA, '%s の語源:' % lemma))
                lines.extend('  ' + line for line in ety)
        return lines
    return notes


def latin_kana(analysis, options):
    """文のカタカナ読み (--kana): 解析で選んだ読みの綴り (マクロン付き: 格の決まった Gallia・dīvīsa) を、語ごとに発音から
    (latin/katakana.py)。辞書に無い語はマクロンを推定して"""
    import re
    from .katakana import katakana
    out = []
    for word in analysis.words:
        if not re.search('[A-Za-z]', word.surface):
            continue
        spelling = (word.items[0].attrib('surface') if word.items else None) or word.surface
        if not word.items and not re.search('[āēīōūȳ]', spelling):
            spelling = macronizer.macronize_text(spelling).strip()
        for enclitic in ('que', 'ne', 've'):   # 後接語 (virumque の -que) は解析の綴りに無いので元の語から
            if word.surface.lower().endswith(enclitic) and not spelling.lower().endswith(enclitic) and \
                    len(word.surface) > len(enclitic) + 1:
                spelling += enclitic
                break
        out.append(katakana(spelling, **options.kana_options))
    return ' '.join(out)


def analyse_text(text, options):
    if options.auto_macron_mode:
        # マクロンの無い入力にマクロンを推定して付けてから解析する
        text = macronizer.macronize_text(text)
    for analysis in analyzer.analyze_text(text):
        if options.gaps is not None:   # 穴の一覧だけ (本文は出さない)
            options.gaps.add(analysis)
            continue
        kana_line = latin_kana(analysis, options) if getattr(options, 'kana', False) else None
        if options.notebook is not None:
            options.notebook.add(analysis, word_notes=latin_word_notes(options),
                                 show_word_detail=options.show_word_detail, show_translation=options.show_translation,
                                 kana=kana_line)
            continue
        if getattr(options, 'kana_only', False):   # カタカナ読みだけ
            print(analysis.text)
            print('  カナ: %s' % kana_line)
            continue
        if options.echo_on:
            render.render_sentence_header(analysis.text)
        if kana_line is not None:
            print('  カナ: %s' % kana_line)
        if options.speech_mode:
            speak_latin.say_latin(analysis.text)

        render.render_analysis(analysis, show_word_detail=options.show_word_detail,
                               show_translation=options.show_translation,
                               show_descendants=options.show_descendants,
                               show_etymology=options.show_etymology)

        # 音読モードの場合、読み終わるまでウェイトを入れる
        if options.speech_mode:
            speak_latin.pause_while_speaking()


def do_command(line, options=None):
    fs = line.split(' ')
    cmd = fs[0]

    def surface_tr():
        surface = ' '.join(fs[1:])
        if options and options.capital_to_macron_mode:
            surface = char.trans(surface)
        return surface

    # マクロンの推定
    if cmd in ('m', 'macron'):
        print(macronizer.macronize_text(' '.join(fs[1:])))

    # 辞書検索
    elif cmd in ('l', 'lookup'):
        surface = surface_tr()
        print("lookup", surface, end=' ')

        items = latindic.lookup(surface) #.decode('utf-8'))
        util.pp(items)

    # 動詞の活用を見る
    elif cmd in ('c', 'conjug'):
        surface_uc = surface_tr() #.decode('utf-8')
        table = {}
        ja = None
        moods = set()
        voices = set()
        tenses = set()
        for word, items in list(latindic.LatinDic.dic.items()):
            for item in items:
                pres1sg = item.get('pres1sg', None)
                if pres1sg == surface_uc:
                    if not ja: ja = item['ja']
                    mood = item.get('mood', '-')
                    moods.add(mood)
                    voice = item.get('voice', '-')
                    voices.add(mood + voice)
                    tense = item.get('tense', '-')
                    tenses.add(mood + voice + tense)
                    person = item.get('person', None)
                    number = item.get('number', None)
                    key = (mood,voice,tense,person,number)
                    item_surface = item['surface']
                    if key in table:
                        table[key].append(item_surface)
                    else:
                        table[key] = [item_surface]

        def surfaces(key):
            if key in table:
                return ', '.join(table[key])
            else:
                return '-'

        print("%s, %s" % (surface_uc, ja))
        for mood in ['indicative', 'subjunctive', 'imperative']:
            if mood not in moods: continue
            print("  %s" % mood)
            for voice in ['active', 'passive']:
                if mood + voice not in voices: continue
                print("    %s" % voice)
                for tense in ['present', 'imperfect', 'future',
                              'perfect', 'past-perfect', 'future-perfect']:
                    if mood + voice + tense not in tenses: continue
                    print("      %s" % tense)
                    for number in ['sg','pl']:
                        print("        %s" % number)
                        for person in [1,2,3]:
                            key = (mood, voice, tense, person, number)
                            if key in table:
                                print("          %d: %s" % (person, surfaces(key)))
        print("  infinitive")
        print("    present: %s" % surfaces(('infinitive','active','present',None,None)))
        print("    perfect: %s" % surfaces(('infinitive','active','perfect',None,None)))
        print("    future: %s" % surfaces(('infinitive','active','future',None,None)))

    # 名詞の変化形を見る
    elif cmd in ('d', 'decl'):
        surface_uc = surface_tr() #.decode('utf-8')
        table = {}
        base = None
        ja = None
        pos = None
        gender = None
        for word, items in list(latindic.LatinDic.dic.items()):
            for item in items:
                item_base = item.get('base', None)
                if item_base == surface_uc:
                    for case, number, item_gender in item['_']:
                        key = (case, number, item_gender)
                        item_surface = item['surface']
                        if key in table:
                            table[key].append(item_surface)
                        else:
                            table[key] = [item_surface]
                        if not pos:
                            pos = item['pos']
                            gender = item['_'][0][2]
                            base = item['base']
                            ja = item['ja']
        def surfaces(key):
            if key in table:
                return ', '.join(table[key])
            else:
                return '-'

        if pos == 'noun':
            print("%s (%s, %s), %s" % (base, pos, gender, ja))
            for number in ['sg', 'pl']:
                print("  %s:" % number)
                for case in ['Nom', 'Voc', 'Acc', 'Gen', 'Dat', 'Abl', 'Loc']:
                    key = (case, number, gender)
                    if key in table:
                        print("    %s: %s" % (case, surfaces(key)))

    else:
        print("COMMAND NOT SUPPORTED: %s, with \"%s\"" % (cmd, surface_tr()))

# read-eval-print loop
def repl(options=None, show_prompt=False):
    while True:
        if show_prompt:
            sys.stdout.write("> ")
            sys.stdout.flush()

        line = sys.stdin.readline()
        if not line: break

        text = line.rstrip()
        if not text: continue
        if text[0] == '.':
            do_command(text[1:], options=options)
        else:
            if options and options.capital_to_macron_mode:
                text = char.trans(text)
            analyse_text(text, options)

    if show_prompt:
        print()



class Options:
    def __init__(self, args):
        try:
            short, long = option_defs.getopt_spec(option_defs.LATIN)   # 定義は core/options.py の LATIN
            opts, self.args = getopt.gnu_getopt(args, short, long)
        except getopt.GetoptError:
            self.usage()
            sys.exit()

        self.show_word_detail = True
        self.show_translation = True
        self.capital_to_macron_mode = False
        self.auto_macron_mode = False
        self.speech_mode = False
        self.tts_backend = None  # speak_latin の既定 (mbrola、使えなければ espeak)
        self.accent = 'pitch'
        self.echo_on = True
        self.show_descendants = False
        self.show_etymology = False
        self.html = None
        self.pdf = None
        self.marks = self.legend = self.provenance = False
        self.compare = None
        self.notebook = None
        self.gaps = None   # 穴の一覧 (--gaps)
        self.kana = self.kana_only = False   # カタカナ読み (--kana・--kana-only)
        self.kana_options = {}

        for option, arg in opts:
            if option in ('-w', '--no-word-detail'):
                self.show_word_detail = False
            elif option in ('-k', '--kana'):
                self.kana = True
            elif option == '--kana-only':
                self.kana = self.kana_only = True
            elif option == '--kana-long':
                self.kana_options['long'] = arg
            elif option == '--kana-wa':
                self.kana_options['wa'] = arg
            elif option == '--kana-si':
                self.kana_options['si'] = arg
            elif option == '--kana-oe':
                self.kana_options['oe'] = arg
            elif option in ('--kana-accent', '--kana-small', '--kana-kobun', '--kana-hebrew', '--kana-pt'):
                self.kana_options[option[len('--kana-'):]] = arg   # ラテン語では使わない (ほかの言語と同じく受け付ける)
            elif option in ('-q', '--no-translation'):
                self.show_translation = False
            elif option in ('-m', '--capital-to-macron'):
                self.capital_to_macron_mode = True
            elif option in ('-a', '--auto-macron'):
                self.auto_macron_mode = True
            elif option in ('-s', '--speech'):
                self.speech_mode = True
            elif option in ('-t', '--tts'):
                self.speech_mode = True
                self.tts_backend = arg
            elif option == '--no-wiktionary':
                latindic.LatinDic.use_wiktionary = False
            elif option == '--accent':
                self.speech_mode = True
                self.accent = arg
            elif option in ('-D', '--descendants'):
                self.show_descendants = True
            elif option in ('-E', '--etymology'):
                self.show_etymology = True
            elif option == '--html':
                from dragoman.core.cli import check_html_path
                self.html = check_html_path(arg)
            elif option == '--pdf':
                self.pdf = arg
            elif option == '--marks':
                self.marks = True
            elif option == '--gaps':
                from dragoman.core.gaps import Gaps
                self.gaps = Gaps('la')
            elif option == '--legend':
                self.marks = self.legend = True
            elif option == '--provenance':
                self.provenance = True
            elif option == '--compare':
                from dragoman.core.cli import compare_langs
                self.compare = compare_langs(arg)
            elif option in ('-h', '--help'):
                self.usage()
                sys.exit()
        if self.provenance:
            from dragoman.core import provenance
            provenance.start()   # ノートの再現条件: 使ったデータを記録 (辞書を読み込む前に)

    def usage(self):
        print('ラテン語の解析と逐語訳 (ファイルが無ければ対話モード: 変化表・マクロンの推定)\n')
        print('  ./dragoman.py la [オプション] [ファイル...]\n')
        print('オプション:\n' + option_defs.help_text(option_defs.LATIN))

def main(argv=None):
    options = Options(sys.argv[1:] if argv is None else argv)
    if options.speech_mode:
        speak_latin.set_accent(options.accent)
        speak_latin.init_synth(options.tts_backend)

    latindic.load()
    if options.html or options.pdf:
        from dragoman.core.notebook import Notebook
        options.notebook = Notebook('ラテン語 — dragoman', marks=options.marks, legend=options.legend,
                                    compare=options.compare)

    if len(options.args) == 0:
        # repl mode
        if select.select([sys.stdin,],[],[],0.0)[0]:
            # have data from pipe. no prompt.
            repl(options=options)
        else:
            repl(options=options, show_prompt=True)
    else:
        # file mode
        for file in options.args:
            text = textutil.load_text_from_file(file)
            if options and options.capital_to_macron_mode:
                text = char.trans(text)

            analyse_text(text, options)
    if options.notebook is not None:
        from dragoman.core.cli import save_notebook
        save_notebook(options.notebook, options, 'la')
    if options.gaps is not None:
        print(options.gaps.report())

if __name__ == '__main__':
    main()
