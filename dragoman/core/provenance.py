#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# ノートの再現条件: コードの版・使ったデータ・ライブラリの版・オプション
#
#   同じ文の解析結果が変わったとき、実装の変更か辞書の更新かを切り分けられるように、ノートの末尾に記録する。
#   使ったデータは、データの置き場所 ($DRAGOMAN_DATA) の下で実際に開いたファイル。Python の監査フック (open・
#   sqlite3.connect・subprocess.Popen の引数) で集める (データのパスはモジュールごとに組み立てているので、paths.data() だけでは拾いきれない)。
#   C のライブラリが直接読む辞書 (MeCab の UniDic) はライブラリの版で
#
import datetime
import importlib.metadata
import os
import platform
import subprocess
import sys

from . import paths

_used = set()
_started = False
# 版を記録するライブラリ (import 名 → 配布名)。読み込まれたものだけ
LIBRARIES = {'MeCab': 'mecab-python3', 'unidic_lite': 'unidic-lite', 'pymorphy3': 'pymorphy3', 'vidyut': 'vidyut',
             'camel_tools': 'camel-tools', 'botok': 'botok', 'ginza': 'ginza', 'spacy': 'spacy'}


def _hook(event, args):
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        _record(args[0])
    elif event == 'sqlite3.connect' and args:
        _record(args[0])
    elif event == 'subprocess.Popen' and len(args) > 1:   # 外部のプログラム (RFTagger) と、引数のモデルのファイル
        _record(args[0])
        for a in args[1] if isinstance(args[1], (list, tuple)) else [args[1]]:
            if isinstance(a, (str, bytes, os.PathLike)):
                _record(a)


def _record(path):
    try:
        path = os.path.abspath(os.fsdecode(path))
    except (TypeError, ValueError):
        return
    if path.startswith(os.path.abspath(paths.DATA_DIR) + os.sep):
        _used.add(path)


def start():
    """使ったデータの記録を始める (ノートを書き出すときだけ。監査フックは外せないので一度だけ)"""
    global _started
    if not _started:
        sys.addaudithook(_hook)
        _started = True


def used_data():
    """使ったデータ: [(データの置き場所からのパス, 更新日, 大きさ, ファイルの数)]。
    ディレクトリの中の多くのファイル (vidyut-data/…) は2段目のディレクトリにまとめる"""
    base = os.path.abspath(paths.DATA_DIR)
    groups = {}
    for path in _used:
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, base)
        parts = rel.split(os.sep)
        key = os.sep.join(parts[:2]) if len(parts) > 2 else rel
        size, mtime, count = groups.get(key, (0, 0, 0))
        st = os.stat(path)
        groups[key] = (size + st.st_size, max(mtime, st.st_mtime), count + 1)
    return [(key, datetime.date.fromtimestamp(mtime).isoformat(), size, count)
            for key, (size, mtime, count) in sorted(groups.items())]


def code_version():
    """コードの版: git のコミット (未コミットの変更があれば印)。git の外 (wheel) ならパッケージの版"""
    try:
        commit = subprocess.run(['git', '-C', paths.REPO_ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True,
                                text=True, timeout=5)
        if commit.returncode == 0:
            dirty = subprocess.run(['git', '-C', paths.REPO_ROOT, 'status', '--porcelain', '--untracked-files=no'],
                                   capture_output=True, text=True, timeout=5).stdout.strip()
            return 'git %s%s' % (commit.stdout.strip(), ' (未コミットの変更あり)' if dirty else '')
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        return 'dragoman %s' % importlib.metadata.version('dragoman')
    except importlib.metadata.PackageNotFoundError:
        return '不明'


def libraries():
    out = []
    for module, dist in LIBRARIES.items():
        if module in sys.modules:
            try:
                out.append('%s %s' % (dist, importlib.metadata.version(dist)))
            except importlib.metadata.PackageNotFoundError:
                out.append(dist)
    return out


def options(argv):
    """コマンドの引数から、解析の文 (-e TEXT) を除いたもの (オプションの記録)"""
    from dragoman.main import _split_e
    out, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a in ('-e', '--text'):
            skip = True
            continue
        if a.startswith('--text=') or (a.startswith('-e') and not a.startswith('--')):
            continue
        cluster = _split_e(a)   # -we TEXT・-weTEXT: e の前のオプションだけ
        if cluster is not None:
            if cluster[0] != '-':
                out.append(cluster[0])
            skip = not cluster[1]
            continue
        out.append(a)
    env = ['%s=%s' % (k, os.environ[k]) for k in ('LATIN_TAGGER', 'LATIN_WIKTIONARY', 'DRAGOMAN_DATA')
           if k in os.environ]
    return ' '.join(env + out)


def info(lang, argv=None):
    """ノートに載せる再現条件 [(項目, 値)]"""
    rows = [('作成', datetime.datetime.now().strftime('%Y-%m-%d %H:%M')), ('言語', lang),
            ('コード', code_version()),
            ('Python', '%s (%s)' % (platform.python_version(), platform.system())),
            ('オプション', options(sys.argv[1:] if argv is None else argv) or '(なし)'),
            ('データの置き場所', paths.DATA_DIR)]
    libs = libraries()
    if libs:
        rows.append(('ライブラリ', ', '.join(libs)))
    data = used_data()
    rows.append(('使ったデータ', data))
    return rows
