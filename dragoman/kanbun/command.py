#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 漢文のコマンドの設定 (core/cli.py)。表示は返り点・書き下し文・語ごとの読みと語義・現代語訳
#
from dragoman.core import ansi_color, options as option_defs
from dragoman.core.cli import Command
from . import analyzer, kundoku, note, parse, readings

USAGE = '''
  ./dragoman.py lzh -e "學而時習之、不亦說乎。"     (kanbun でも)
  漢文 (白文) に返り点を付け、書き下し文 (送り仮名・歴史的仮名遣い) と現代語訳を作る。
  語の切り分け・品詞・係り受けは UD-Kanbun (pip install udkanbun。MIT)。読む順序・送り仮名・置き字・再読文字は
  dragoman/kanbun/kundoku.py の規則、用言の訓は手作りの表と KANJIDIC2 ($DRAGOMAN_DATA/kanjidic/kanjidic2.xml.gz、
  EDRDG、CC BY-SA 4.0) と JMdict。返り点は UD-Kanbun のもの。音読は macOS の say の日本語音声 (書き下し文を読む)
'''
NOTES = '  句読点 (、。) で句に区切って読む。白文に句読点が無ければ1つの句として読む'

# 品詞 (UD-Kanbun の細分類の2つ目) の名前の簡略
RELATIONS = {'nsubj': '主語', 'obj': '目的語', 'iobj': '間接目的語', 'obl': '補語', 'advmod': '連用修飾', 'amod': '連体修飾',
             'nmod': '連体修飾', 'det': '連体修飾', 'nummod': '数量', 'case': '前置詞', 'mark': '接続', 'cc': '接続',
             'conj': '並列', 'parataxis': '続く節', 'ccomp': '補文', 'xcomp': '補文', 'advcl': '連用節', 'acl': '連体節',
             'aux': '助動詞', 'cop': '繋辞', 'discourse': '文末の助字', 'root': '述語', 'fixed': '熟語', 'flat': '熟語',
             'compound': '熟語', 'vocative': '呼びかけ', 'csubj': '主語の節', 'expl': '目的語', 'dislocated': '提示'}
FUNCTION_NOTES = {
    '而': '置き字 (読まない。前の用言を「〜て」(順接)・「〜ども」(逆接) でつなぐ)',
    '於': '置き字 (読まない。名詞に「に」(場所・相手)・「より」(起点・比較) を送る)',
    '于': '置き字 (於と同じ)', '乎': '文末なら疑問・反語・詠嘆「か・や」。名詞の前なら置き字 (於と同じ)',
    '矣': '置き字 (文末。断定・完了の語気。読まない)', '焉': '文末なら置き字 (読まない)。文頭なら「いづくんぞ」(反語)',
    '兮': '置き字 (韻文の語調。読まない)',
    '未': '再読文字「未だ〜ず」(まだ〜ない)', '將': '再読文字「將に〜んとす」(今にも〜しようとする)',
    '且': '再読文字「且に〜んとす」', '當': '再読文字「當に〜べし」(当然〜すべきだ)', '應': '再読文字「應に〜べし」(きっと〜だろう)',
    '宜': '再読文字「宜しく〜べし」(〜するのがよい)', '須': '再読文字「須らく〜べし」(ぜひ〜する必要がある)',
    '猶': '再読文字「猶ほ〜のごとし」(ちょうど〜のようだ)', '盍': '再読文字「盍ぞ〜ざる」(どうして〜しないのか)',
    '不': '打消の助動詞「ず」', '弗': '打消の助動詞「ず」', '可': '助動詞「べし」(可能・当然)',
    '使': '使役「AをしてBせしむ」(AにBさせる)', '令': '使役「AをしてBせしむ」', '敎': '使役「AをしてBせしむ」',
    '教': '使役「AをしてBせしむ」', '遣': '使役「AをしてBせしむ」',
    '見': '受身「る・らる」(〜される) / 動詞「見る」', '被': '受身「る・らる」(〜される)',
    '勿': '禁止「〜すること勿かれ」(〜してはならない)', '毋': '禁止「〜すること毋かれ」', '莫': '「莫し」(〜するものはない)',
    '非': '「〜に非ず」(〜ではない)', '無': '「無し」(〜がない) / 禁止「無かれ」', '也': '断定「なり」/ 疑問・詠嘆「や」',
    '者': '「者」(〜する人・もの) / 主題「は」', '所': '「所」(〜すること・もの。動詞を名詞にする)', '之': '「の」(連体) / 代名詞「之」(これ) / 動詞「之く」(ゆく)',
    '以': '「以て」(〜で・〜によって)', '與': '「と」(並列) / 文末なら疑問「か」/ 動詞「與ふ」', '自': '「より」(起点)',
    '如': '「如し」(〜のようだ) / 「如かず」(及ばない) / 仮定「如し」', '若': '「如し」と同じ / 二人称「若」(なんぢ)',
    '則': '「則ち」(前の已然形 + ば と組む: 〜すれば則ち)', '雖': '「雖も」(〜といっても)', '欲': '「〜んと欲す」(〜しようと思う)',
    '豈': '反語「豈に〜んや」(どうして〜だろうか)', '曰': '「曰はく」(言うことには)', '哉': '詠嘆「かな」/ 反語「や」',
    '耳': '限定「のみ」', '已': '限定「のみ」/ 副詞「已に」', '爾': '限定「のみ」/ 二人称「爾」',
}


def word_line(analysis, t, width):
    if t.upos == 'PUNCT':
        return None
    x = t.x
    pos = x[1] + ('・' + x[2] if len(x) > 2 and x[2] not in ('*', '') else '')
    rel = RELATIONS.get(t.rel, t.rel)
    reading = analysis.reading_of(t)
    gloss = _gloss_ja(t)
    parts = ['  %s' % t.form.ljust(width, '　'), pos, rel]
    if t.gloss and not t.gloss.startswith('['):
        parts.append(t.gloss + ('「%s」' % gloss if gloss else ''))
    if reading and reading != t.form:
        parts.append('→ ' + reading)
    elif not reading and t.form in kundoku.SILENT:
        parts.append('(読まない)')
    return '  '.join(parts)


def _gloss_ja(t):
    from dragoman.core import en_ja
    if not t.gloss or t.gloss.startswith('[') or not en_ja.available() or \
            t.upos not in ('VERB', 'NOUN', 'ADJ') or t.form in FUNCTION_NOTES:
        return ''   # 助字・副詞・代名詞は語義の訳を出さない (解説の表で)
    pos = {'VERB': 'verb', 'NOUN': 'noun', 'ADV': 'adv', 'ADJ': 'adj', 'PRON': 'pronoun', 'PROPN': 'name'}.get(t.upos, 'noun')
    try:
        return en_ja.translate(t.gloss.replace('-', ' '), pos) or ''
    except Exception:
        return ''


def explain(t):
    return FUNCTION_NOTES.get(t.form, '')


def render(analysis, options):
    if not (options.html or options.pdf):   # ノートでは返り点は縦書きの訓点付きの本文に (note.py)
        print('  返り点   ' + analysis.kaeriten)
    print('  書き下し ' + analysis.kakikudashi)
    if analysis.yomi:
        print('  読み     ' + analysis.yomi)
    if options.show_word_detail:
        print()
        width = max([len(t.form) for t in analysis.tokens] + [1])
        for t in analysis.tokens:
            line = word_line(analysis, t, width)
            if line is None:
                continue
            note = explain(t) if options.explain else ''
            print(line + (ansi_color.fgcolor(ansi_color.GREEN, '  ' + note) if note else ''))
    print()
    print('  →  ' + analysis.modern)
    print()


def handle_option(option, arg, options):
    if option == '--wa':
        kundoku.TOPIC_WA = True
        return True
    return False


def available():
    if not parse.available():
        return 'no UD-Kanbun (pip install udkanbun)'
    if not readings.kanjidic_available():
        return ('no KANJIDIC2 (curl -O http://www.edrdg.org/kanjidic/kanjidic2.xml.gz into '
                '$DRAGOMAN_DATA/kanjidic/)')
    return None


COMMAND = Command(lang='lzh', name='漢文 (訓読)', analyzer=analyzer, dictionary=None, available=available,
                  usage=USAGE, header=lambda a, o: a.text, speech_text=lambda a, o: a.reading,
                  speech_lang='ja', render=render, notes=NOTES,
                  note_html=note.html_of, options=option_defs.LANGUAGE['lzh'], handle_option=handle_option)
