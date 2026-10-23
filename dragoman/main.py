#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# dragoman: 文を辞書引き・構文解析して、日本語の逐語訳を付ける (ラテン語・古典ギリシア語・サンスクリットをはじめ
# 20あまりの言語。下の「対応している言語」・./dragoman.py --languages)
#
#   ./dragoman.py [LANG] [オプション] [ファイル...]     (python3 dragoman.py / python3 -m dragoman でも)
#
#   echo "Agricola in silvā magnam casam aedificat." | ./dragoman.py
#   ./dragoman.py grc FILE...
#   ./dragoman.py hi -e "लड़के ने किताब पढ़ी।"
#   ./dragoman.py la                                   ラテン語の対話モード (変化表・マクロンの推定)
#   ./dragoman.py he --help                            言語ごとのオプション
#   ./dragoman.py --languages                          対応している言語の一覧
#
#   LANG          最初の引数が言語の符号なら言語の指定 (--lang=LANG でも)。省略するか auto なら文字から推定し、
#                 推定した言語を標準エラー出力に出す
#                 (ラテン文字 → la、ギリシア文字 → grc、キリル文字 → ru、ヘブライ文字 → he、
#                 ウルドゥー語の字 (ٹ ڈ ڑ ں ے ھ) のあるアラビア文字 → ur、ペルシア語の字 (پ چ ژ گ ک ی) の多いもの → fa、
#                 ほかのアラビア文字 → ar、デーヴァナーガリーはヒンディー語らしい語 (है, का, की, में …) があれば hi、無ければ sa、
#                 チベット文字 → bo、インドネシア語らしい語 (yang, dan, di, ini, itu …) が2つ以上あるラテン文字 → id
#                 (マレー語らしい語 kerana, sahaja, bahawa … があれば ms)、タガログ語らしい語 (ang, ng, mga, ay …) → tl、
#                 アイヌ語らしい語 (kamuy, kotan, wa, kor, ne …) → ain、ʻokina か長音符とハワイ語の字だけ → haw、
#                 þ・ð・ƿ・ġ・ċ → ang、フランス語らしい語 (le, est, que …) かアクセント記号・エリジオン → fr、
#                 ğ・ı・ş か トルコ語らしい語 → tr、フィンランド語らしい語 (ja, on, ei …) → fi、ドイツ語らしい語
#                 (der, und, ist …) かウムラウト・ß → de、the か英語らしい語 (and, of, you …) → en、
#                 ө・ү のあるキリル文字 → mn、ハングル → ko、かな交じりの日本語 → kobun)
#   -e, --text=TEXT       引数の文を入力にする (何度でも。ファイル・標準入力の代わりに)
#   -L, --languages       対応している言語の一覧を出す
#
# オプションの定義 (共通・ラテン語・言語ごと) は core/options.py と各言語の command.py。
# 説明は ./dragoman.py LANG --help で。
# ラテン語は dragoman/latin/main.py (対話モード・変化表・マクロンの推定などを含む) に渡す
#
import functools
import importlib
import os
import re
import sys
import tempfile

LANGUAGES = {'la': 'latin', 'grc': 'greek', 'sa': 'sanskrit', 'ru': 'russian', 'he': 'hebrew', 'ar': 'arabic',
             'fa': 'persian', 'hi': 'hindi', 'ur': 'urdu', 'bo': 'tibetan', 'id': 'indonesian', 'ms': 'malay',
             'tl': 'tagalog', 'ko': 'korean', 'de': 'german', 'fr': 'french', 'tr': 'turkish', 'mn': 'mongolian', 'fi': 'finnish', 'ang': 'oldenglish', 'haw': 'hawaiian', 'ain': 'ainu', 'kobun': 'kobun', 'en': 'english'}
NAMES = {'la': 'ラテン語', 'grc': '古典ギリシア語', 'sa': 'サンスクリット', 'ru': 'ロシア語',
         'he': '聖書ヘブライ語 (聖書アラム語も)', 'ar': 'アラビア語 (現代標準アラビア語)', 'fa': 'ペルシア語',
         'hi': 'ヒンディー語', 'ur': 'ウルドゥー語', 'bo': '古典チベット語', 'id': 'インドネシア語', 'ms': 'マレー語', 'tl': 'タガログ語', 'ko': '韓国語', 'de': 'ドイツ語', 'fr': 'フランス語', 'tr': 'トルコ語', 'mn': 'モンゴル語', 'fi': 'フィンランド語', 'ang': '古英語', 'haw': 'ハワイ語', 'ain': 'アイヌ語', 'kobun': '古文 (平安の和文。現代語に組み立て直す)', 'en': '英語 (現代英語)'}
CODE = re.compile('^[a-z]{2,5}$')
INDONESIAN_WORDS = {'yang', 'dan', 'di', 'ini', 'itu', 'dengan', 'untuk', 'tidak', 'adalah', 'akan', 'dari', 'ke', 'pada',
                    'saya', 'mereka', 'ada', 'sudah', 'juga', 'dalam', 'oleh', 'bahwa', 'bahawa', 'kami', 'kita'}
AINU_WORDS = {'kamuy', 'kamui', 'aynu', 'ainu', 'kotan', 'ruwe', 'sekor', 'somo', 'anakne', 'orowa', 'cise', 'chise',
              'kor', 'wa', 'ne', 'an', 'oka', 'pirka', 'wen', 'nispa', 'nishpa', 'teeta', 'tane', 'ki', 'kane'}
TAGALOG_WORDS = {'ang', 'ng', 'mga', 'ay', 'si', 'hindi', 'ako', 'ko', 'siya', 'niya', 'ito', 'kay', 'po', 'naman',
                 'lang', 'pero', 'ikaw', 'mo', 'nila', 'sila', 'kami', 'tayo'}
FINNISH_WORDS = {'ja', 'on', 'ei', 'että', 'se', 'hän', 'minä', 'sinä', 'olen', 'oli', 'kun', 'mutta', 'tai', 'kuin',
                 'jos', 'myös', 'tämä', 'joka', 'ovat', 'olla', 'mitä', 'nyt', 'vain', 'minulla', 'sinulla'}
GERMAN_WORDS = {'der', 'die', 'das', 'und', 'ist', 'nicht', 'ich', 'ein', 'eine', 'zu', 'mit', 'sich', 'auf', 'für',
                'von', 'den', 'dem', 'des', 'sie', 'es', 'wir', 'aber', 'auch', 'ich', 'nach', 'wie', 'sind', 'hat',
                'haben', 'wird', 'werden', 'kann', 'nur', 'noch', 'schon', 'sehr', 'mein', 'dein', 'im', 'zum'}
FRENCH_WORDS = {'le', 'la', 'les', 'un', 'une', 'des', 'du', 'et', 'est', 'sont', 'pas', 'je', 'il', 'elle', 'nous',
                'vous', 'ils', 'que', 'qui', 'dans', 'pour', 'avec', 'sur', 'au', 'aux', 'ce', 'cette', 'mais', 'ne',
                'son', 'sa', 'ses', 'mon', 'ma', 'mes', 'très', 'été', 'avait', 'était', 'ont', 'fait'}
TURKISH_WORDS = {'bir', 've', 'bu', 'için', 'ile', 'çok', 'ben', 'sen', 'biz', 'değil', 'var', 'yok', 'gibi', 'daha',
                 'ama', 'çünkü', 'kadar', 'mı', 'mi', 'mu', 'mü'}
MALAY_WORDS = {'kerana', 'sahaja', 'bahawa', 'wang', 'jepun', 'inggeris', 'kerajaan', 'boleh', 'hendak', 'awak'}
OLD_ENGLISH_WORDS = {'and', 'ond', 'se', 'seo', 'þæt', 'wæs', 'is', 'on', 'mid', 'ic', 'he', 'heo', 'hie', 'him', 'his',
                     'ne', 'þa', 'þe', 'swa', 'ac', 'we', 'ge', 'eom', 'sind', 'sindon', 'hwæt', 'þone', 'þæs'}
ENGLISH_WORDS = {'the', 'and', 'of', 'to', 'that', 'it', 'you', 'was', 'for', 'are', 'with', 'this', 'have', 'not',
                 'be', 'they', 'what', 'i', 'my', 'we', 'she', 'there', 'can', 'will', 'from', 'your', 'were', 'has',
                 'would', 'about', 'which', 'their', 'been', 'an', 'or', 'but', 'by', 'at', 'on', "don't", "it's",
                 'he', 'his', 'her', 'him', 'them', 'our', 'is', 'very', 'gave', 'does', 'did', 'had', 'said', 'do', 'like',
                 'please', 'some', 'give', 'want', 'go', 'how', 'why', 'where', 'who', 'when', 'if', 'yes', 'know'}
HINDI_WORDS = {'है', 'हैं', 'का', 'की', 'के', 'में', 'नहीं', 'को', 'से', 'ने', 'था', 'थी', 'और', 'पर', 'भी'}


def detect(text):
    """文字から言語を推定する (分からなければ None)"""
    counts = {
        'grc': len(re.findall('[Ͱ-Ͽἀ-῿]', text)),
        'ru': len(re.findall('[Ѐ-ӿ]', text)),
        'he': len(re.findall('[֐-׿]', text)),
        'arabic-script': len(re.findall('[؀-ۿ]', text)),
        'deva': len(re.findall('[ऀ-ॿ]', text)),
        'bo': len(re.findall('[\u0f00-\u0fff]', text)),
        'ko': len(re.findall('[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]', text)) * 3,  # ハングル
        'la': len(re.findall('[A-Za-zāēīōūȳĀĒĪŌŪ]', text)),
        'kobun': len(re.findall('[\u3040-\u30ff]', text)) * 2,  # かな (日本語の文は古文として)
    }
    best = max(counts, key=counts.get)
    if counts[best] == 0:
        return None
    if best == 'kobun' and re.search('[\u31f0-\u31ff]', text):
        return 'ain'   # アイヌ語のカタカナの小書きの文字 (ㇰ・ㇼ・ㇷ゚ …。音節末の子音) があればアイヌ語
    if best == 'ru' and re.search('[өүӨҮ]', text):
        return 'mn'  # キリル文字のモンゴル語 (ө・ү)
    if best == 'arabic-script':
        if re.search('[\u0679\u0688\u0691\u06ba\u06d2\u06d3\u06be]', text):
            return 'ur'  # ٹ ڈ ڑ ں ے ۓ ھ
        persian = len(re.findall('[پچژگکی‌]', text))
        return 'fa' if persian > len(re.findall('[كي]', text)) else 'ar'
    if best == 'la':
        words = set(re.findall('[a-z]+', text.lower()))
        if len(words & AINU_WORDS) >= 3 and len(words & AINU_WORDS) > len(words & TAGALOG_WORDS):
            return 'ain'  # ラテン文字のアイヌ語 (kamuy, kotan, wa, kor, ne …)
        if len(words & TAGALOG_WORDS) >= 2 and len(words & TAGALOG_WORDS) >= len(words & INDONESIAN_WORDS):
            return 'tl'  # ラテン文字のタガログ語 (ang, ng, mga, ay …)
        if re.search('ʻ', text) or re.search("[āēīōū]", text.lower()) and \
                not re.search('[^aeiouāēīōūhklmnpwʻ\'\s.,;:!?"“”()-]', text.lower()):
            return 'haw'  # ハワイ語 (ʻokina、または長音符とハワイ語の字 a e i o u h k l m n p w だけ)
        oe = set(re.findall('[a-zæþðƿāēīōūȳǣġċ]+', text.lower()))
        if re.search('[þðƿȜȝ]|[ġċ]', text.lower()) or 'æ' in text.lower() and len(oe & OLD_ENGLISH_WORDS) >= 2:
            return 'ang'  # 古英語 (þ ð ƿ ġ ċ、æ と and・se・wæs …。ラテン語の æ (Cæsar) は除く)
        whole = set(re.findall(r"[a-zà-öø-ÿāēīōūȳœæ]+", text.lower()))   # 長音符の字で切らない (dīvīsa の sa を数えない)
        french = len(whole & FRENCH_WORDS)
        if french >= 2 and french > len(words & GERMAN_WORDS) and french > len(words & TURKISH_WORDS) or \
                re.search("[éèêàœùâîôû]|\\b[ldjmtsnc]'|\\bqu'", text.lower()) and not re.search('[äöüğış]', text.lower()):
            return 'fr'  # ラテン文字のフランス語 (le, la, est, que … か é・è・l')
        if re.search('[ğışİĞŞçÇ]', text) or len(words & TURKISH_WORDS) >= 2:
            return 'tr'  # ラテン文字のトルコ語 (ğ ı ş İ か bir, ve, bu, için …)
        if len(words & FINNISH_WORDS) >= 2 or re.search(r'(?:ää|öö|yy|ssa|ssä|sta|stä|lla|llä)\b', text) and \
                len(words & FINNISH_WORDS) >= 1:
            return 'fi'  # ラテン文字のフィンランド語 (ja, on, ei, että … か格の語尾 -ssa・-lla …)
        if len(words & GERMAN_WORDS) >= 2 or re.search('[äöüßÄÖÜ]', text):
            return 'de'  # ラテン文字のドイツ語 (der, die, das, und, ist … かウムラウト・ß)
        english = set(re.findall(r"[a-z']+", text.lower())) & ENGLISH_WORDS | \
            set(re.findall(r"[a-z]'(?:s|t|re|ll|ve|d|m)\b", text.lower()))   # John's・don't
        if ('the' in english or len(english) >= 2) and len(english) > len(words & GERMAN_WORDS) and len(english) > len(words & INDONESIAN_WORDS):
            return 'en'  # ラテン文字の英語 (the, and, of, to, that …)
        if len(words & INDONESIAN_WORDS) >= 2:
            return 'ms' if words & MALAY_WORDS else 'id'  # ラテン文字のインドネシア語・マレー語
    if best == 'deva':
        words = set(re.findall('[ऀ-ॣ०-ॿ]+', text))
        return 'hi' if words & HINDI_WORDS else 'sa'
    return best


def command_for(lang):
    return importlib.import_module('dragoman.%s.command' % LANGUAGES[lang]).COMMAND


def language_list():
    """対応している言語の一覧 (符号・名前・説明の文書)"""
    return '\n'.join(['  %-4s %s  (docs/%s.md)' % (code, NAMES[code], LANGUAGES[code]) for code in LANGUAGES] +
                     ['  auto 文字から推定する'])


@functools.lru_cache(maxsize=1)
def value_options():
    """値を取るオプション (言語ごとのコマンドに渡すもの)。値を言語の符号・入力ファイルと取り違えないように
    (-t say を言語 say と、--html note.html を入力と読まない)。定義 (core/options.py の COMMON・LATIN・LANGUAGE) から"""
    from dragoman.core import options
    names = options.value_names(options.COMMON + options.LATIN)
    for extra in options.LANGUAGE.values():   # 言語のコマンド (解析器) は読み込まない (任意の依存が無くても動くように)
        names |= options.value_names(extra)
    return frozenset(names)


def value_short():
    """値を取る短いオプションの字 (t, v)"""
    return {name[1] for name in value_options() if len(name) == 2}


KANA_VALUE_OPTIONS = {'--kana-long': 'long', '--kana-wa': 'wa', '--kana-si': 'si', '--kana-oe': 'oe',
                      '--kana-accent': 'accent', '--kana-small': 'small', '--kana-kobun': 'kobun'}


def kana_json(lang, args, texts):
    """--kana-json: 入力の1行ごとに {"text": 行, "ruby": [{text, start, end, kana}]} を1行の JSON で (core/ruby.py)"""
    import json
    from dragoman.core import cli, ruby
    options, liaison, files = {}, 'next', []
    k = 0
    while k < len(args):
        arg = args[k]
        name, eq, value = arg.partition('=')
        if name in KANA_VALUE_OPTIONS or name == '--kana-liaison':
            if not eq:
                k += 1
                value = args[k] if k < len(args) else ''
            if name == '--kana-liaison':
                liaison = value
            else:
                options[KANA_VALUE_OPTIONS[name]] = value
        elif not arg.startswith('-'):
            files.append(arg)
        k += 1
    if not ruby.available(lang):
        sys.exit('ルビのカタカナが無い言語: %s' % lang)
    for text in texts if texts is not None else cli.read_texts(files):
        for line in text.splitlines():
            if line.strip():
                print(json.dumps({'text': line, 'ruby': ruby.ruby(line, lang, liaison=liaison, **options)},
                                 ensure_ascii=False))


def _take_flag(args, short, long):
    """値を取らないオプション (-l / --sentence-per-line) を引数から除く。短いオプションのまとまり (-kl) の中の字も。
    返り値: (あったか, 残りの引数)"""
    found, out = False, []
    values = value_short()
    skip_next = False
    for arg in args:
        if skip_next:
            out.append(arg)
            skip_next = False
            continue
        if arg == long:
            found = True
            continue
        if _short_cluster(arg) and arg != '-':
            letters = ''
            for k, ch in enumerate(arg[1:]):
                if ch in values:   # 値を取る字の後ろは値 (-tsay)
                    letters += arg[1 + k:]
                    break
                if ch == short:
                    found = True
                    continue
                letters += ch
            if letters:
                out.append('-' + letters)
            skip_next = takes_next('-' + letters) if letters else False
            continue
        out.append(arg)
        skip_next = takes_next(arg)
    return found, out


def _short_cluster(arg):
    """短いオプションのまとまり (-wt、-wtsay、-we) か"""
    return arg.startswith('-') and not arg.startswith('--') and len(arg) > 1


def takes_next(arg):
    """この引数の次の引数がオプションの値か: -t / --html / まとまりの最後が値を取る字 (-wt)。
    値がくっついていれば (-tsay、-wtsay、--html=FILE) 次は値でない。getopt と同じ規則"""
    if arg in value_options():
        return True
    if not _short_cluster(arg):
        return False
    for k, c in enumerate(arg[1:], 1):
        if c in value_short():
            return k == len(arg) - 1
    return False


def _split_e(arg):
    """まとまりの中の -e (-we TEXT、-weTEXT): (e の前のオプション, e の後ろの文 (無ければ '')) か None。
    e より前に値を取る字があれば (-te …) e はその値の一部"""
    if not _short_cluster(arg) or arg.startswith('-e'):
        return None
    for k, c in enumerate(arg[1:], 1):
        if c in value_short():
            return None
        if c == 'e':
            return arg[:k], arg[k + 1:]
    return None


def parse_args(argv):
    """(言語, 言語に渡す引数, -e の文のリスト)。言語は --lang=LANG か、最初の引数が言語の符号のとき"""
    lang, args, texts = None, [], []
    positional_seen = False
    i = 0
    while i < len(argv):
        arg = argv[i]
        cluster_e = _split_e(arg)
        if cluster_e is not None:   # -we TEXT・-weTEXT: e の前のオプションは言語のコマンドへ、文は -e と同じく
            options, text = cluster_e
            if options != '-':
                args.append(options)
            if text:
                texts.append(text)
            elif i + 1 < len(argv):
                texts.append(argv[i + 1])
                i += 1
            i += 1
            continue
        if takes_next(arg) and i + 1 < len(argv):
            args += [arg, argv[i + 1]]   # オプションと値はそのまま言語のコマンドへ (-t say、-wt say、--html FILE)
            i += 2
            continue
        if arg.startswith('--lang='):
            lang = arg.split('=', 1)[1]
        elif arg == '--lang' and i + 1 < len(argv):
            lang = argv[i + 1]
            i += 1
        elif arg.startswith('--text='):
            texts.append(arg.split('=', 1)[1])
        elif arg in ('-e', '--text') and i + 1 < len(argv):
            texts.append(argv[i + 1])
            i += 1
        elif arg.startswith('-e') and len(arg) > 2:
            texts.append(arg[2:])
        elif not arg.startswith('-') and not positional_seen and lang is None and not os.path.exists(arg) \
                and CODE.match(arg):
            lang = arg  # ./dragoman.py grc …
            positional_seen = True
        else:
            if not arg.startswith('-'):
                positional_seen = True
            args.append(arg)
        i += 1
    return lang, args, texts


def input_files(args):
    """言語に渡す引数のうち入力ファイル (オプションの値は除く)"""
    files, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif takes_next(a):
            skip = True
        elif not a.startswith('-') and os.path.exists(a):
            files.append(a)
    return files


def _without(args, files):
    """args から入力ファイルを除く (オプションの値は、同じ名前のファイルでも残す)"""
    out, skip, rest = [], False, list(files)
    for a in args:
        if skip:
            out.append(a)
            skip = False
        elif takes_next(a):
            out.append(a)
            skip = True
        elif a in rest:
            rest.remove(a)
        else:
            out.append(a)
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '-L' in argv or '--languages' in argv:
        print('対応している言語:\n' + language_list())
        return
    lang, args, texts = parse_args(argv)
    if lang == 'auto':
        lang = None  # 文字から推定する
    if lang is not None and lang not in LANGUAGES:
        sys.exit('知らない言語: %s\n対応している言語:\n%s' % (lang, language_list()))
    if lang is None and ('-h' in args or '--help' in args):
        header = open(__file__, encoding='utf-8').read().split('\nimport')[0].split('\n')[2:]   # #! と coding の行は除く
        print('\n'.join(line[2:] if line.startswith('# ') else line.lstrip('#') for line in header))
        from dragoman.core import options as option_defs
        print('共通のオプション (どの言語でも。ラテン語の入口はその一部と独自のもの: ./dragoman.py la --help):')
        print(option_defs.help_text(option_defs.COMMON))
        print()
        print('対応している言語:\n' + language_list())
        return
    texts = texts or None
    if lang is None:
        # 言語を推定するためにテキストを先に読む (ファイルの指定はオプションでない引数)
        from dragoman.core import cli
        if texts is None:
            files = input_files(args)
            texts = cli.read_texts(files)
            args = _without(args, files)
        detected = detect('\n'.join(texts))
        lang = detected or 'la'
        # 推定した言語を標準エラー出力に (解析結果の出力は汚さない)
        print('推定した言語: %s (%s)%s' % (lang, NAMES[lang], '' if detected else '。文字から推定できないのでラテン語に'),
              file=sys.stderr)
    if '--kana-json' in args:   # ルビ用のカタカナ (解析はしない。どの言語も同じ入口で)
        return kana_json(lang, args, texts)
    per_line, stripped = _take_flag(args, 'l', '--sentence-per-line') if lang == 'la' else (False, args)
    if per_line:
        # ラテン語の入口 (latin/main.py) はファイルを自分で読むので、行の区切りに句点を補った一時ファイルにして渡す
        from dragoman.core import cli
        args = stripped
        if texts is None:
            files = input_files(args)
            texts = cli.read_texts(files)
            args = _without(args, files)
        texts = [chunk if chunk.rstrip().endswith(('.', '!', '?', ';', ':')) else chunk + '.'
                 for text in texts for chunk in cli.split_lines(text)]
    if lang == 'la':
        from dragoman.latin import main as latin_main
        if texts is None:
            latin_main.main(args)
            return
        # 文はラテン語のコマンドに一時ファイルで渡す。終わったら (例外でも) 消す
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as fp:
            fp.write('\n'.join(texts) + '\n')
        try:
            latin_main.main(args + [fp.name])
        finally:
            os.unlink(fp.name)
        return
    from dragoman.core import cli
    cli.run(command_for(lang), args, texts)


if __name__ == '__main__':
    main()
