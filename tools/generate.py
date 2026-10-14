#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 解析の結果 (格の枠) から文を作り直す試み: ラテン語 (・古典ギリシア語・ロシア語・サンスクリット・日本語) → 文の枠 →
# ラテン語・英語・ロシア語・サンスクリット・古典ギリシア語・インドネシア語・タガログ語・アラビア語・ヘブライ語・ペルシア語・ヒンディー語・ウルドゥー語・アイヌ語・古典チベット語・日本語・古文
#
#   python3 tools/generate.py "Puella rosam pulchram in hortō videt."
#   python3 tools/generate.py samples/samples.txt
#   python3 tools/generate.py --to=en,ru,sa "…"     作る言語 (既定: en,la と、語の置き換えの表があれば ru,sa,grc,id,tl,ar,he,fa,hi,ur,ain,bo,ja,kobun)
#   python3 tools/generate.py --from=grc "ἡ κόρη τὸ καλὸν ῥόδον βλέπει."   ロシア語 (ru)・サンスクリット (sa)・古典ギリシア語・
#                                         ペルシア語 (fa)・ヒンディー語 (hi)・ウルドゥー語 (ur)・アラビア語 (ar)・ヘブライ語 (he)・
#                                         インドネシア語 (id)・タガログ語 (tl) から
#   python3 tools/generate.py --from=ja "少女が庭で美しい薔薇を見た。"   日本語の文から (MeCab と規則で文の枠に)
#   python3 tools/generate.py --gaps samples/samples.txt   訳語の見つからない語の一覧だけ (生成文は出さない)
#   python3 tools/generate.py --compare "Rosam in hortō vīdit."   要素ごとに各言語の手段を並べる (前置詞と格・語順・助詞、
#                                                                 書かれていない主語を補うか …)
#
# ラテン語に戻した文が元の文と同じ語 (順序は問わない) になれば ✓。違えば、違う語を出す。
# ファイルは1行1文 (# で始まる行は飛ばす。samples/samples.txt の形)
#
import os
import sys
import re
import unicodedata
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.latin import analyzer, latindic
from dragoman.generate import frame, english, latin, russian, sanskrit, greek, indonesian, tagalog, arabic, hebrew, persian, hindi, urdu, ainu, tibetan, japanese, kobun, korean, turkish, mongolian, german, finnish, french


def _word_list(text):
    text = unicodedata.normalize('NFC', text)
    return [w.strip('.,;:!?"“”()').lower() for w in text.split() if w.strip('.,;:!?"“”()')]


def _normal(text):
    """綴りの流儀をそろえる: マクロンを外し、j → i、v → u"""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.replace('j', 'i').replace('J', 'I').replace('v', 'u').replace('V', 'U')


def _spelling(word):
    """綴りの流儀をそろえた語 (比較用): マクロン・j/v・i 語幹の対格複数 -īs (omnīs = omnēs)・ad- の同化 (adfectus = affectus)"""
    word = _normal(word).lower()
    for plain, assimilated in (('adf', 'aff'), ('adc', 'acc'), ('adp', 'app'), ('adl', 'all'), ('inr', 'irr'),
                               ('conl', 'coll'), ('inl', 'ill'), ('adt', 'att')):
        if word.startswith(plain):
            word = assimilated + word[len(plain):]
    word = {'iis': 'eis', 'ii': 'ei', 'isdem': 'eisdem', 'iidem': 'eidem'}.get(word, word)   # is の複数 iīs = eīs
    return word[:-2] + 'es' if word.endswith('is') and len(word) > 4 else word


def _words(text):
    return Counter(_word_list(text))


def run(text):
    for analysis in analyzer.analyze_text(text):
        print(analysis.text)
        clauses = frame.frames(analysis)
        if not clauses:
            print('  (述語が見つからない)\n')
            continue
        show_frame(clauses)
        if 'en' in TARGETS:
            print('  英語:     ' + english.sentence(clauses))
        for lang, label, module in OTHERS:
            if lang in TARGETS:
                try:
                    print('  %s ' % label + module.sentence(clauses))
                except Exception as e:   # 1つの言語で作れなくても、ほかの言語は出す
                    print('  %s (作れない: %s: %s)' % (label, type(e).__name__, e))
        if 'la' not in TARGETS:
            print()
            continue
        regenerated = latin.sentence(clauses)
        original, again = _words(analysis.text), _words(regenerated)
        spelled = Counter(map(_spelling, _word_list(analysis.text))), Counter(map(_spelling, _word_list(regenerated)))
        if original != again and spelled[0] == spelled[1]:
            mark = '✓ 綴りの違いだけ (マクロン・i/j・u/v・-īs/-ēs・同化)'
        elif original == again:
            mark = '✓ 同じ語' + (' (語順も同じ)' if _word_list(regenerated) == _word_list(analysis.text) else '')
        else:
            # 違う語は綴りの違いを除いて出す
            only_original = [w for w in _word_list(analysis.text) if (spelled[0] - spelled[1])[_spelling(w)] > 0]
            only_again = [w for w in _word_list(regenerated) if (spelled[1] - spelled[0])[_spelling(w)] > 0]
            mark = '✗ 元にだけある語: %s / 作った文にだけある語: %s' % (
                ' '.join(sorted(set(only_original))) or '-', ' '.join(sorted(set(only_again))) or '-')
        print('  ラテン語: ' + regenerated + '   ' + mark)
        print()


TARGETS = ['en', 'la']
COMPARE = []   # --compare: 文の枠の要素ごとに、各言語がどの手段で表すかの表も出す (表に出す言語の符号)


def show_frame(clauses):
    for clause in clauses:
        print(frame.describe(clause))
    if COMPARE:
        from dragoman.generate import compare
        print('  要素ごとの比較:')
        print(compare.text_table(clauses, [lang for lang in compare.LANGS if lang in COMPARE]))
OTHERS = [('ru', 'ロシア語:', russian), ('de', 'ドイツ語:', german), ('fr', 'フランス語:', french), ('fi', 'フィンランド語:', finnish), ('sa', '梵語:    ', sanskrit), ('grc', 'ギリシア語:', greek),
          ('id', 'インドネシア語:', indonesian), ('tl', 'タガログ語:', tagalog), ('ar', 'アラビア語:', arabic),
          ('he', 'ヘブライ語:', hebrew), ('fa', 'ペルシア語:', persian), ('hi', 'ヒンディー語:', hindi),
          ('ur', 'ウルドゥー語:', urdu), ('ain', 'アイヌ語:', ainu), ('tr', 'トルコ語: ', turkish), ('mn', 'モンゴル語:', mongolian), ('ko', '韓国語:  ', korean),
          ('bo', 'チベット語:', tibetan), ('ja', '日本語:  ', japanese),
          ('kobun', '古文:    ', kobun)]


def run_japanese(text):
    """日本語の文 → 文の枠 → 各言語 (ラテン語との往復の比べは無し)"""
    from dragoman.generate import from_japanese
    for sentence in re.split(r'(?<=[。！？])', text.strip()):
        if not sentence.strip():
            continue
        print(sentence.strip())
        clauses = from_japanese.parse(sentence)
        if not clauses:
            print('  (述語が見つからない)\n')
            continue
        show_frame(clauses)
        for lang, label, module in [('ja', '日本語:  ', japanese), ('la', 'ラテン語:', latin),
                                    ('en', '英語:    ', english)] + [o for o in OTHERS if o[0] != 'ja']:
            if lang in TARGETS:
                try:
                    print('  %s ' % label + module.sentence(clauses))
                except Exception as e:
                    print('  %s (作れない: %s: %s)' % (label, type(e).__name__, e))
        print()


# --from の言語 → 解析器のパッケージ
SOURCE_ANALYZERS = {'ru': 'russian', 'sa': 'sanskrit', 'grc': 'greek', 'ar': 'arabic', 'he': 'hebrew', 'fa': 'persian',
                    'hi': 'hindi', 'ur': 'urdu', 'id': 'indonesian', 'tl': 'tagalog', 'ko': 'korean', 'de': 'german', 'fr': 'french',
                    'tr': 'turkish', 'mn': 'mongolian', 'fi': 'finnish'}
# (チベット語・アイヌ語の解析器は節の構造 (述語と格の枠) を作らないので、文の枠に写せない)


def run_other(text, source):
    """ロシア語・サンスクリット・古典ギリシア語の文 → 文の枠 → 各言語。元の言語に戻した文と元の文を比べる"""
    import importlib
    analyzer_module = importlib.import_module('dragoman.%s.analyzer' % SOURCE_ANALYZERS[source])
    modules = {'la': ('ラテン語:', latin), 'en': ('英語:    ', english), 'ru': ('ロシア語:', russian),
               'sa': ('梵語:    ', sanskrit), 'grc': ('ギリシア語:', greek), 'id': ('インドネシア語:', indonesian),
               'tl': ('タガログ語:', tagalog), 'ar': ('アラビア語:', arabic), 'he': ('ヘブライ語:', hebrew), 'fa': ('ペルシア語:', persian), 'hi': ('ヒンディー語:', hindi),
               'ur': ('ウルドゥー語:', urdu), 'ain': ('アイヌ語:', ainu), 'bo': ('チベット語:', tibetan), 'ja': ('日本語:  ', japanese),
               'ko': ('韓国語:  ', korean), 'tr': ('トルコ語: ', turkish), 'mn': ('モンゴル語:', mongolian), 'de': ('ドイツ語:', german), 'fr': ('フランス語:', french), 'fi': ('フィンランド語:', finnish),
               'kobun': ('古文:    ', kobun)}
    for analysis in analyzer_module.analyze_text(text):
        print(analysis.text)
        clauses = frame.frames(analysis)
        if not clauses:
            print('  (述語が見つからない)\n')
            continue
        show_frame(clauses)
        for lang in ['ja', 'kobun', 'la', 'en', 'ru', 'de', 'fr', 'fi', 'sa', 'grc', 'id', 'tl', 'ar', 'he', 'fa', 'hi', 'ur', 'tr', 'mn', 'ko', 'ain', 'bo']:
            if lang not in TARGETS and lang != source:
                continue
            label, module = modules[lang]
            try:
                out = module.sentence(clauses)
            except Exception as e:
                out = '(作れない: %s: %s)' % (type(e).__name__, e)
            mark = ''
            if lang == source:
                first = out.split('\n')[0]
                # 解析の表示の文は標識 (ng・ang) を落としたり冠詞・前置詞を切り離したり (הַ מֶּלֶךְ) するので、
                # インドネシア語・タガログ語・ヘブライ語・韓国語 (助詞を切り離す)・トルコ語・モンゴル語 (副動詞の印を足す)・フランス語 (エリジオンを切る) は入力の文と比べる
                original = _source_words(text if source in ('id', 'tl', 'he', 'ko', 'tr', 'mn', 'fr') else analysis.text, source)
                mark = '   ✓ 同じ語' if original == _source_words(first, source) else '   ✗'
            first, _, rest = out.partition('\n')
            print('  %s %s%s%s' % (label, first, mark, ('\n' + rest) if rest else ''))
        print()


def _source_words(text, lang):
    """元の言語の文の語 (比べる用。サンスクリットは SLP1 に、ロシア語は小文字・ё → е)"""
    words = [w.strip('.,;:!?।"“”·;׃׀') for w in text.split() if not w.startswith('(')]   # (كان) は解析で補った語
    words = [w.strip('()') for w in words if w]
    if lang == 'sa':
        from dragoman.sanskrit import script
        return Counter(re.sub('[sr]$', 'H', script.to_slp1(w)) for w in words)   # rāmas = rāmaḥ (語末の連声)
    if lang == 'grc':   # 重アクセント = 鋭アクセント、前接語の前の2つめのアクセントは除く、語末の ν (ἔδωκεν = ἔδωκε)
        words = [unicodedata.normalize('NFD', w.lower()).replace('\u0300', '\u0301') for w in words]
        words = [w[:w.rfind('\u0301')] + w[w.rfind('\u0301') + 1:] if w.count('\u0301') + w.count('\u0342') > 1 else w
                 for w in words]   # 前接語の前で足したアクセント (ταῦτά ἐστιν)
        words = [unicodedata.normalize('NFC', w) for w in words]
        words = [{'ἐστί': 'ἐστι', 'ἐστίν': 'ἐστιν', 'εἰσί': 'εἰσι', 'εἰσίν': 'εἰσιν'}.get(w, w) for w in words]   # 前接語
        return Counter(unicodedata.normalize('NFC', re.sub('(?<=[ει])([\u0300-\u036f]*)ν$', r'\1',
                                                           unicodedata.normalize('NFD', w))) for w in words)
    if lang in ('ar', 'he', 'fa', 'ur'):   # 母音記号・格語尾の有無は問わない (البنت = البِنْتُ)。句読点 ، も除く
        words = [''.join(c for c in unicodedata.normalize('NFD', w) if not unicodedata.combining(c)).strip('،۔')
                 for w in words]
        return Counter(w for w in words if w)
    return Counter(w.lower().replace('ё', 'е') for w in words)


def main():
    import getopt
    latindic.load()
    opts, args = getopt.gnu_getopt(sys.argv[1:], '', ['to=', 'from=', 'compare', 'gaps'])
    TARGETS[:] = ['en', 'la'] + [lang for lang, _, module in OTHERS if module.available()]
    source = 'la'
    for opt, value in opts:
        if opt == '--to':
            TARGETS[:] = value.split(',')
        elif opt == '--from':
            source = value
        elif opt == '--compare':
            COMPARE.append(True)
        elif opt == '--gaps':
            GAPS.append(True)
    if COMPARE:   # 比べる言語: 作る言語と元の言語
        COMPARE[:] = list(dict.fromkeys(TARGETS + [source] + (['la'] if source != 'la' else [])))
    global run
    if source in SOURCE_ANALYZERS:
        def run(text, source=source):
            run_other(text, source)
    if source == 'ja':
        run = run_japanese
        if 'ja' not in TARGETS:
            TARGETS.insert(0, 'ja')   # 日本語からなら訳し戻しも
    if not args:
        print(__doc__ if __doc__ else 'usage: generate.py TEXT|FILE')
        return
    texts = []
    for arg in args:
        if os.path.exists(arg):
            with open(arg, encoding='utf-8') as f:
                texts += [line for line in f if line.strip() and not line.startswith('#')]   # 1行1文。# の行は飛ばす
        else:
            texts.append(arg)
    if GAPS:
        print(gaps_report(texts))
        return
    for text in texts:
        run(text)


GAPS = []   # --gaps: 生成文は出さず、言語ごとに訳語の見つからない語 ([英語] のまま残った語) の一覧だけ
LANGUAGE_LINE = re.compile(r'^  (\S[^:：]*?):\s')
UNTRANSLATED = re.compile(r'\[\[?([^\[\]]+?)\]?\]')


def gaps_report(texts):
    '''言語ごとの訳語の見つからない語 (重複を除き並べ替え。生成文・元の文・文中の位置は出さない) と作れなかった文の数'''
    import io
    import contextlib
    words, failed, sentences = {}, Counter(), 0
    for text in texts:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            run(text)
        current = None
        for line in buffer.getvalue().splitlines():
            if line and not line.startswith(' '):
                sentences += 1
                continue
            m = LANGUAGE_LINE.match(line)
            if not m or m.group(1) == '述語':
                continue   # 文の枠の行と、転写・仮名の行 (同じ語を2度数えない)
            current = m.group(1)
            if '(作れない' in line:
                failed[current] += 1
            for word in UNTRANSLATED.findall(line):
                words.setdefault(current, Counter())[word.strip()] += 1
    lines = ['# generate.py --gaps: %d 文。生成文・元の文は含まない (語は言語ごとに重複を除き並べ替え)' % sentences]
    for lang in sorted(set(words) | set(failed)):
        counter = words.get(lang, Counter())
        lines.append('%s 訳語の見つからない語 %d%s' % (lang, len(counter),
                                                 '、作れなかった文 %d' % failed[lang] if failed[lang] else ''))
        for word in sorted(counter, key=str.lower):
            lines.append('  %s%s' % (word, '  ×%d' % counter[word] if counter[word] > 1 else ''))
    if len(lines) == 1:
        lines.append('穴は見つからなかった')
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
