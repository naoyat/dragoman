#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 言語ごとの機能の表 (言語の間の実装の偏りを見つけるための監査)
#
#   python3 tools/audit_languages.py                 表を標準出力に (Markdown)
#   python3 tools/audit_languages.py --write         notes/audit.md にも書き、前回の表との違いを出す
#   python3 tools/audit_languages.py --only=ru,fr    言語を絞る
#
# 表の印: ○ ある・働く / × 無い・働かない (試しの文で構造が出ない) / ・ 試しの文が無い / — その言語の解析器は別の仕組み
#
# 調べること:
#   設定 (コマンドの Command から): カタカナ (--kana)、ルビ (core/ruby.py)、転写 (-r)、語の解説、音読の声の表 (core/speech.py)、
#   生成 (generate/<言語>.py)、説明 (docs/<言語>.md)、テスト (test/<言語>_test.py)
#   働き (試しの文 PROBES を解析して): 疑問文 (文末の ? で述語が疑問に)、副詞節 (従属接続詞の節が主節の従属節に)、
#   関係節、間接疑問、文脈で訳語を選ぶ (CONTEXT)、それに試しの文の語のうち辞書に無いものの数
#
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dragoman import main as dragoman_main   # noqa: E402

OUT = os.path.join(ROOT, 'notes', 'audit.md')

# 試しの文: 言語 → 働き → 文 (自作の短い文)
PROBES = {
    'la': {'question': 'Ubi habitās?', 'adverbial': 'Cum vēnit, eum vīdī.', 'relative': 'Vir quī vēnit mē vīdit.',
           'indirect': 'Rogāvit quis vēnisset.'},
    'grc': {'question': 'ποῦ οἰκεῖς;', 'adverbial': 'ὅτε ἦλθεν, εἶδον αὐτόν.', 'relative': 'ὁ ἀνὴρ ὃς ἦλθεν εἶδέ με.',
            'indirect': 'ἠρώτησε τίς ἔλθοι.'},
    'sa': {'question': 'त्वं कुत्र वससि?', 'adverbial': 'यदा सः आगच्छत् तदा अहं तम् अपश्यम्।',
           'relative': 'यः नरः आगच्छत् सः माम् अपश्यत्।'},
    'ru': {'question': 'Где ты живёшь?', 'adverbial': 'Когда он пришёл, я увидел его.',
           'relative': 'Человек, который пришёл, увидел меня.', 'indirect': 'Я не знаю, где он живёт.',
           'context': 'Она плетёт нить.'},
    'he': {'question': 'מִי אַתָּה?', 'adverbial': 'כַּאֲשֶׁר בָּא רָאִיתִי אֹתוֹ.', 'relative': 'הָאִישׁ אֲשֶׁר בָּא רָאָה אֹתִי.'},
    'ar': {'question': 'أين تسكن؟', 'adverbial': 'عندما جاء رأيته.', 'relative': 'الرجل الذي جاء رآني.',
           'indirect': 'لا أعرف أين يسكن.'},
    'fa': {'question': 'کجا زندگی می‌کنی؟', 'adverbial': 'وقتی آمد او را دیدم.', 'relative': 'مردی که آمد مرا دید.'},
    'hi': {'question': 'तुम कहाँ रहते हो?', 'adverbial': 'जब वह आया, मैंने उसे देखा।', 'relative': 'जो आदमी आया उसने मुझे देखा।',
           'indirect': 'मैं नहीं जानता कि वह कहाँ रहता है।'},
    'ur': {'question': 'تم کہاں رہتے ہو؟', 'adverbial': 'جب وہ آیا، میں نے اسے دیکھا۔', 'relative': 'جو آدمی آیا اس نے مجھے دیکھا۔'},
    'id': {'question': 'Di mana kamu tinggal?', 'adverbial': 'Ketika dia datang, saya melihatnya.',
           'relative': 'Orang yang datang melihat saya.', 'indirect': 'Saya tidak tahu di mana dia tinggal.'},
    'ms': {'question': 'Di mana awak tinggal?', 'adverbial': 'Apabila dia datang, saya melihatnya.',
           'relative': 'Orang yang datang melihat saya.'},
    'tl': {'question': 'Saan ka nakatira?', 'adverbial': 'Nang dumating siya, nakita ko siya.',
           'relative': 'Nakita ako ng lalaking dumating.'},
    'ko': {'question': '어디에 살아요?', 'adverbial': '그가 왔을 때 나는 그를 보았다.', 'relative': '온 사람이 나를 보았다.'},
    'de': {'question': 'Wo wohnst du?', 'adverbial': 'Als er kam, sah ich ihn.', 'relative': 'Der Mann, der kam, sah mich.',
           'indirect': 'Ich weiß nicht, wo er wohnt.'},
    'fr': {'question': 'Où habites-tu ?', 'adverbial': "Quand il est venu, je l'ai vu.", 'relative': "L'homme qui est venu m'a vu.",
           'indirect': 'Je ne sais pas où il habite.'},
    'tr': {'question': 'Nerede yaşıyorsun?', 'adverbial': 'O geldiğinde onu gördüm.', 'relative': 'Gelen adam beni gördü.'},
    'mn': {'question': 'Чи хаана амьдардаг вэ?', 'adverbial': 'Тэр ирэхэд би түүнийг харсан.', 'relative': 'Ирсэн хүн намайг харсан.'},
    'fi': {'question': 'Missä sinä asut?', 'adverbial': 'Kun hän tuli, näin hänet.', 'relative': 'Mies, joka tuli, näki minut.',
           'indirect': 'En tiedä, missä hän asuu.'},
    'ang': {'question': 'Hwær eardast þu?', 'adverbial': 'Siþþan he com, ic hine geseah.', 'relative': 'Se mann þe com geseah me.'},
    'haw': {'question': 'Aia i hea ʻoe e noho ai?'},
    'en': {'question': 'Where do you live?', 'adverbial': 'When he came, I saw him.', 'relative': 'The man who came saw me.',
           'indirect': "I don't know where he lives."},
}
FEATURES = [('question', '疑問文'), ('adverbial', '副詞節'), ('relative', '関係節'), ('indirect', '間接疑問'),
            ('context', '文脈の訳語')]
SETTINGS = [('kana', 'カナ'), ('ruby', 'ルビ'), ('romanize', '転写'), ('explain', '解説'), ('speech', '音読'),
            ('generate', '生成'), ('docs', '説明'), ('tests', 'テスト')]


def _speech_tables():
    from dragoman.core import speech
    return set(speech.LANGUAGE_BACKENDS) | set(speech.MBROLA_LANGUAGES)   # 声を選ぶ表のある言語 (無ければ読まない)


def settings(lang):
    """設定から分かる機能 → ○ / ×"""
    from dragoman.core import ruby
    module = dragoman_main.LANGUAGES[lang]
    out = {}
    if lang == 'la':   # ラテン語の入口は latin/main.py (カタカナ・音読 (MBROLA)・解説を持つ)
        out.update(kana=True, romanize=False, explain=True, speech=True)
    else:
        command = dragoman_main.command_for(lang)
        out['kana'] = command.katakana is not None
        out['romanize'] = command.romanize is not None
        out['explain'] = command.explain is not None
        out['speech'] = (command.speech_lang or lang) in _speech_tables()
    out['ruby'] = ruby.available(lang)
    out['generate'] = os.path.exists(os.path.join(ROOT, 'dragoman', 'generate', module + '.py'))
    out['docs'] = os.path.exists(os.path.join(ROOT, 'docs', module + '.md'))
    out['tests'] = any(re.match(r'%s(_\w+)?_test\.py$' % module, f) for f in os.listdir(os.path.join(ROOT, 'test')))
    return out


def _analyzer(lang):
    import importlib
    if lang == 'la':
        from dragoman.latin import latindic, analyzer
        latindic.load()
        return analyzer
    return importlib.import_module('dragoman.%s.analyzer' % dragoman_main.LANGUAGES[lang])


def _predicates(analysis):
    from dragoman.core.Adverbial import AdverbialClause
    out = []
    for clause in getattr(analysis, 'clauses', None) or []:
        out.append(clause.predicate)
        out += [s.predicate for s in clause.predicate.subordinates if isinstance(s, AdverbialClause)]
    return out


def works(feature, analysis):
    """試しの文の解析で、その働きの構造が出たか"""
    from dragoman.core.Adverbial import AdverbialClause
    trace = getattr(analysis, 'trace', None) or []
    if feature == 'question':
        return any(getattr(p, 'question', False) for p in _predicates(analysis))
    if feature == 'adverbial':
        return any(isinstance(s, AdverbialClause) for c in analysis.clauses for s in c.predicate.subordinates)
    if feature == 'relative':
        return bool(getattr(analysis, 'relatives', None))
    if feature == 'indirect':
        return bool(getattr(analysis, 'questions', None))
    if feature == 'context':
        return any(line.startswith('// CONTEXT') for line in trace)
    raise ValueError(feature)


def _unknown(analysis):
    """辞書に無い語 (訳の無い語: 項目が無いか、どの項目の訳も表層形のままのもの。句読点は除く)"""
    out = []
    for w in getattr(analysis, 'words', []) or []:
        glosses = [i.attrib('ja') for i in (getattr(w, 'items', None) or [])]
        if re.search(r'\w', w.surface) and not any(g and g.lower() != w.surface.lower() for g in glosses):
            out.append(w.surface)
    return out


def probe(lang):
    """働き → ○ / × / ・ / —、辞書に無い語の列、エラーの列"""
    from dragoman.core.analyzer import SentenceAnalysis
    out, unknown, errors = {}, [], []
    try:
        analyzer = _analyzer(lang)
    except Exception as e:   # データの無い言語など
        return {f: '!' for f, _ in FEATURES}, [], ['%s: %s' % (type(e).__name__, e)]
    for feature, _ in FEATURES:
        text = PROBES.get(lang, {}).get(feature)
        if text is None:
            out[feature] = '・'
            continue
        try:
            analyses = list(analyzer.analyze_text(text))
        except Exception as e:
            out[feature] = '!'
            errors.append('%s %r: %s: %s' % (feature, text, type(e).__name__, e))
            continue
        if not analyses or not isinstance(analyses[0], SentenceAnalysis):
            out[feature] = '—'
            continue
        out[feature] = '○' if any(works(feature, a) for a in analyses) else '×'
        for a in analyses:
            unknown += [w for w in _unknown(a) if w not in unknown]
    return out, unknown, errors


def mark(value):
    return {True: '○', False: '×'}.get(value, value)


def table(langs):
    head = ['言語'] + [name for _, name in SETTINGS] + [name for _, name in FEATURES] + ['辞書に無い語']
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    notes = []
    for lang in langs:
        s = settings(lang)
        p, unknown, errors = probe(lang)
        row = ['%s %s' % (lang, dragoman_main.NAMES[lang].split(' ')[0])] + [mark(s[k]) for k, _ in SETTINGS] + \
            [p[k] for k, _ in FEATURES] + [' '.join(unknown[:6]) + (' …' if len(unknown) > 6 else '')]
        lines.append('| ' + ' | '.join(row) + ' |')
        notes += ['- %s: %s' % (lang, e) for e in errors]
    return lines, notes


def summary(lines):
    """機能ごとの ○ の数 (表の行から)"""
    rows = [[c.strip() for c in line.strip('|').split('|')] for line in lines[2:]]
    head = [c.strip() for c in lines[0].strip('|').split('|')]
    out = []
    for k, name in enumerate(head[1:-1], 1):
        yes = sum(1 for r in rows if r[k] == '○')
        known = sum(1 for r in rows if r[k] in ('○', '×'))
        out.append('%s %d/%d' % (name, yes, known))
    return '、'.join(out)


def _cells(text):
    """前回の表 → {(言語, 列): 印}"""
    lines = [line for line in text.splitlines() if line.startswith('| ') and not line.startswith('| 言語')]
    head = next((line for line in text.splitlines() if line.startswith('| 言語')), None)
    if head is None:
        return {}
    names = [c.strip() for c in head.strip('|').split('|')]
    out = {}
    for line in lines:
        cells = [c.strip() for c in line.strip('|').split('|')]
        for name, cell in zip(names[1:], cells[1:]):
            out[(cells[0], name)] = cell
    return out


def changes(old, new):
    a, b = _cells(old), _cells(new)
    return ['- %s %s: %s → %s' % (lang, name, a[(lang, name)], cell) for (lang, name), cell in b.items()
            if (lang, name) in a and a[(lang, name)] != cell]


def main(argv):
    langs = list(dragoman_main.LANGUAGES)
    for arg in argv:
        if arg.startswith('--only='):
            langs = [l for l in arg.split('=', 1)[1].split(',') if l in dragoman_main.LANGUAGES]
    t0 = time.time()
    lines, notes = table(langs)
    text = '# 言語ごとの機能の表 (%s)\n\n' % time.strftime('%Y-%m-%d') + \
        '○ ある・働く / × 無い・働かない / ・ 試しの文が無い / — 別の仕組みの解析器 / ! エラー\n\n' + \
        '\n'.join(lines) + '\n\n' + summary(lines) + '\n'
    if notes:
        text += '\nエラー:\n' + '\n'.join(notes) + '\n'
    print(text)
    if '--write' in argv:
        if os.path.exists(OUT):
            diff = changes(open(OUT, encoding='utf-8').read(), text)
            print('前回からの変化:\n' + ('\n'.join(diff) if diff else '(なし)'))
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write(text)
        print('-> %s' % OUT, file=sys.stderr)
    print('(%.0fs)' % (time.time() - t0), file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
