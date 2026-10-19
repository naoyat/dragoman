#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 言語ごとのコマンド (dragoman.py --lang=xx) の共通の骨組み
#
# 各言語は <言語>/command.py に Command を置き、言語ごとに違うところ (見出しの行・語の転写・解説・データの確認・
# 音読の言語・固有のオプション) だけを書く。オプションの解析、テキストの読み込み、音読、表示はここで行う。
#
#   オプションの定義 (名前・値・説明) は core/options.py (共通の COMMON と、言語ごとの Command(options=…))
#
import getopt
import sys
from dataclasses import dataclass, field

from dragoman.core import ansi_color, descendants, etymology, options as option_defs, provenance, render



@dataclass
class Options:
    show_word_detail: bool = True
    show_descendants: bool = False
    show_etymology: bool = False
    speech: bool = False
    tts: str = None
    voice: str = None
    romanize: bool = False
    kana: bool = False              # 見出しの下にカタカナ読み (--kana)
    kana_only: bool = False         # カタカナ読みだけ (--kana-only)
    kana_options: dict = field(default_factory=dict)   # カタカナの設定 (long・wa)
    explain: bool = True
    sentence_per_line: bool = False
    html: str = None                # ノートの HTML の書き出し先
    pdf: str = None                 # ノートの PDF の書き出し先
    marks: bool = False             # ノートに確かさの印
    gaps: bool = False              # 解析の穴の一覧だけを出す (本文は出さない)
    legend: bool = False            # ノートに印の凡例
    provenance: bool = False        # ノートに再現条件
    compare: list = None            # ノートの要素ごとの比較の言語 (--compare=la,grc,ja)
    extra: dict = field(default_factory=dict)  # 言語固有のオプションの値


@dataclass
class Command:
    lang: str                       # 言語の符号 (grc, sa, ru, he, ar, fa, hi)
    name: str                       # 言語の名前 (日本語)
    analyzer: object                # analyze_text(text) を持つモジュール
    dictionary: object              # 子孫語・語源を引く辞書のモジュール
    available: object               # () → データが無いときの案内 (str) / None
    usage: str = ''                 # 説明の先頭 (使い方の例)
    header: object = None           # (analysis, options) → 見出しの行。無ければ語を並べるだけ
    speech_text: object = None      # (analysis, options) → 音読に渡す文
    romanize: object = None         # 語の転写の関数 (-r)
    katakana: object = None         # (analysis, kana_options) → 語ごとのカタカナ読みの列 (--kana)
    explain: object = None          # (word) → 解説の行
    descendant_langs: tuple = ('en', 'ja')
    fallback_langs: tuple = ()
    speech_lang: str = None         # core.speech の言語の符号
    speech_pron: object = None      # (options) → 発音の流儀 (ギリシア語の --pron)
    speech_setup: object = None     # (options, speech) → 音読の前の設定 (ヘブライ語の神の名の読み方)
    options: tuple = ()             # 固有のオプション (core.options.Option の列。説明の表示にも)
    notes: str = ''                 # 説明の表示に添える文 (固有のオプションのほかの注意)
    handle_option: object = None    # (option, arg, options) → 処理したら True。'exit' で終了
    texts_hook: object = None       # (options) → 解析の前に行うこと (表の表示など)。True を返したら終わる
    render: object = None           # (analysis, options) → 解析結果の表示 (既定は core.render。古文は品詞分解と現代語訳)


def help_text(command):
    out = '%s の解析と逐語訳\n\n%s\n\n共通のオプション:\n%s' % (command.name, command.usage.strip('\n'),
                                                         option_defs.help_text(option_defs.COMMON))
    if command.options or command.notes:
        out += '\n\n%s のオプション:' % command.name
        if command.options:
            out += '\n' + option_defs.help_text(command.options)
        if command.notes:
            out += '\n' + command.notes.strip('\n')
    return out


def word_notes(command, options):
    def notes(word):
        lines = []
        if options.explain and command.explain:
            lines += [ansi_color.fgcolor(ansi_color.GREEN, line) for line in command.explain(word)]
        if options.show_descendants:
            for lemma, line in descendants.describe_word(word, command.descendant_langs, command.dictionary,
                                                          command.fallback_langs):
                lines.append(ansi_color.fgcolor(ansi_color.CYAN, '%s: %s' % (lemma, line)))
        if options.show_etymology:
            for lemma, ety in etymology.describe_word(word, command.dictionary):
                lines.append(ansi_color.fgcolor(ansi_color.MAGENTA, '%s の語源:' % lemma))
                lines.extend('  ' + line for line in ety)
        return lines
    wanted = options.show_descendants or options.show_etymology or (options.explain and command.explain)
    return notes if wanted else None


def parse(command, argv):
    short, long = option_defs.getopt_spec(option_defs.COMMON + tuple(command.options))
    opts, args = getopt.gnu_getopt(argv, short, long)
    options = Options()
    for option, arg in opts:
        if command.handle_option:
            handled = command.handle_option(option, arg, options)
            if handled == 'exit':
                return None, None
            if handled:
                continue
        if option in ('-w', '--no-word-detail'):
            options.show_word_detail = False
        elif option in ('-D', '--descendants'):
            options.show_descendants = True
        elif option in ('-E', '--etymology'):
            options.show_etymology = True
        elif option in ('-s', '--speech'):
            options.speech = True
        elif option in ('-t', '--tts'):
            options.speech, options.tts = True, arg
        elif option in ('-r', '--romanize'):
            options.romanize = True
        elif option in ('-k', '--kana'):
            options.kana = True
        elif option == '--kana-only':
            options.kana = options.kana_only = True
        elif option == '--kana-long':
            options.kana_options['long'] = arg
        elif option == '--kana-wa':
            options.kana_options['wa'] = arg
        elif option == '--kana-si':
            options.kana_options['si'] = arg
        elif option == '--no-explain':
            options.explain = False
        elif option == '--sentence-per-line':
            options.sentence_per_line = True
        elif option == '--html':
            options.html = check_html_path(arg)
        elif option == '--pdf':
            options.pdf = arg
        elif option == '--marks':
            options.marks = True
        elif option == '--gaps':
            options.gaps = True
        elif option == '--legend':
            options.marks = options.legend = True
        elif option == '--provenance':
            options.provenance = True
            provenance.start()   # 使ったデータの記録を始める (辞書を読み込む前に)
        elif option == '--compare':
            options.compare = compare_langs(arg)
        elif option == '--english-glosses':
            from dragoman.core import en_ja
            en_ja.ENABLED = False
        elif option in ('-h', '--help'):
            print(help_text(command))
            return None, None
    return options, args


def split_lines(text):
    """1行1文: 行ごとに分ける。行末がカンマ・セミコロン・コロン (、，) なら次の行に続ける"""
    chunks, current = [], []
    for line in text.splitlines():
        if not line.strip():
            if current:
                chunks.append(' '.join(current))
                current = []
            continue
        current.append(line.strip())
        if not line.rstrip().endswith((',', ';', ':', '、', '，', '،', '؛')):
            chunks.append(' '.join(current))
            current = []
    if current:
        chunks.append(' '.join(current))
    return chunks


def read_texts(args):
    """ファイル (無ければ標準入力) のテキスト。# で始まる行は注釈として除く"""
    texts = [open(path, encoding='utf-8').read() for path in args] if args else [sys.stdin.read()]
    return ['\n'.join(l for l in t.splitlines() if not l.lstrip().startswith('#')) for t in texts]


def run(command, argv=None, texts=None):
    options, args = parse(command, sys.argv[1:] if argv is None else argv)
    if options is None:
        return
    if command.texts_hook and command.texts_hook(options):
        return
    missing = command.available()
    if missing:
        sys.exit(missing)
    notes = word_notes(command, options)
    speech = None
    if options.speech:
        from dragoman.core import speech
        speech.set_language(command.speech_lang or command.lang,
                            command.speech_pron(options) if command.speech_pron else None)
        if command.speech_setup:
            command.speech_setup(options, speech)
        if speech.init_synth(options.tts, options.voice) is None:
            speech = None
    texts = texts if texts is not None else read_texts(args)
    if options.sentence_per_line:
        texts = [chunk for text in texts for chunk in split_lines(text)]
    notebook = None
    if options.html or options.pdf:
        from dragoman.core.notebook import Notebook
        notebook = Notebook('%s — dragoman' % command.name, marks=options.marks, legend=options.legend,
                            compare=options.compare)
    if options.gaps:   # 穴の一覧だけ (本文は出さない)
        from dragoman.core.gaps import Gaps
        gaps = Gaps(command.lang)
        for text in texts:
            for analysis in command.analyzer.analyze_text(text):
                gaps.add(analysis)
        print(gaps.report())
        return
    if options.kana and command.katakana is None:
        print('(%s のカタカナ読みはまだありません)' % command.name, file=sys.stderr)
    for text in texts:
        for analysis in command.analyzer.analyze_text(text):
            line = command.header(analysis, options) if command.header else ' '.join(analysis.surfaces)
            kana_line = kana_text(command, analysis, options)
            if options.kana_only:   # カタカナ読みだけ
                print(line)
                print('  カナ: %s' % kana_line if kana_line is not None else '  (カタカナ読みはまだありません)')
                continue
            if notebook is not None:
                rendered = None
                if command.render:   # 独自の表示の言語 (古文など): 表示をそのままノートに
                    import contextlib
                    import io
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        command.render(analysis, options)
                    rendered = buffer.getvalue()
                notebook.add(analysis, header=line, word_notes=notes, show_word_detail=options.show_word_detail,
                             romanize=command.romanize if options.romanize else None, rendered=rendered)
                continue
            render.render_sentence_header(line)
            if kana_line is not None:
                print('  カナ: %s' % kana_line)
            if speech:
                speech.say_latin(command.speech_text(analysis, options) if command.speech_text
                                 else ' '.join(analysis.surfaces))
            if command.render:
                command.render(analysis, options)
            else:
                render.render_analysis(analysis, show_word_detail=options.show_word_detail, word_notes=notes,
                                       romanize=command.romanize if options.romanize else None)
            if getattr(analysis, 'literal', None):   # 語順のままの訳 (韓国語)
                print('  ≒  %s  (語順のまま)' % analysis.literal)
            if speech:
                speech.pause_while_speaking()
    if notebook is not None:
        save_notebook(notebook, options, command.lang)


def kana_text(command, analysis, options):
    """文のカタカナ読み (語ごとに空白で区切る)。--kana が無いか、言語のカタカナ読みが無ければ None"""
    if not options.kana or command.katakana is None:
        return None
    return ' '.join(k for k in command.katakana(analysis, dict(options.kana_options)) if k)


def compare_langs(value):
    """--compare の値を言語の符号の列に。知らない符号なら解析の前に止める"""
    from dragoman.generate import compare
    try:
        return compare.parse_langs(value)
    except ValueError as e:
        sys.exit(str(e))


def check_html_path(path):
    """--html の書き出し先: .pdf なら解析の前に止める (既存の PDF を HTML で上書きしない)"""
    if path.lower().endswith('.pdf'):
        sys.exit('--html の書き出し先が .pdf: %s (PDF は --pdf=FILE で)' % path)
    return path


def save_notebook(notebook, options, lang):
    if options.provenance:
        notebook.provenance = provenance.info(lang)   # 再現条件 (コードの版・使ったデータ・オプション)
    if options.html:
        notebook.write(options.html)
        print('ノート: %s' % options.html, file=sys.stderr)
    if options.pdf:
        notebook.write_pdf(options.pdf)
        print('ノート (PDF): %s' % options.pdf, file=sys.stderr)


def main(command):
    run(command)
