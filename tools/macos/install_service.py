#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# macOS のサービス (クイックアクション)「dragoman で解析」を作る: どのアプリでも、テキストを選んで右クリックのメニュー
# (「サービス」の下) から dragoman を呼び、解析結果のノート (HTML) をブラウザで開く (tools/macos/dragoman-service.sh)
#
#   python3 tools/macos/install_service.py [--name=NAME] [--python=PYTHON] [--dest=DIR]
#
# 出力: ~/Library/Services/<NAME>.workflow (Automator のクイックアクションの束: Contents/Info.plist と document.wflow)。
# Python は既定でこのスクリプトを実行した Python (conda の環境など。サービスはログインシェルの PATH を引き継がない)。
# 作った後にサービスの一覧を更新する (pbs -update)。キーボードショートカットはシステム設定の
# 「キーボード → キーボードショートカット → サービス」で
#
import getopt
import os
import plistlib
import shlex
import subprocess
import sys
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, 'tools', 'macos', 'dragoman-service.sh')


def info_plist(name):
    return {'NSServices': [{
        'NSMenuItem': {'default': name},
        'NSMessage': 'runWorkflowAsService',
        'NSSendTypes': ['NSStringPboardType'],
    }]}


def document(command):
    """Automator の文書: 「シェルスクリプトを実行」の動作1つ (テキストを標準入力で渡す)"""
    action = {
        'AMAccepts': {'Container': 'List', 'Optional': True, 'Types': ['com.apple.cocoa.string']},
        'AMActionVersion': '2.0.3',
        'AMApplication': ['Automator'],
        'AMParameterProperties': {'COMMAND_STRING': {}, 'CheckedForUserDefaultShell': {}, 'inputMethod': {},
                                  'shell': {}, 'source': {}},
        'AMProvides': {'Container': 'List', 'Types': ['com.apple.cocoa.string']},
        'ActionBundlePath': '/System/Library/Automator/Run Shell Script.action',
        'ActionName': 'シェルスクリプトを実行',
        'ActionParameters': {'COMMAND_STRING': command, 'CheckedForUserDefaultShell': True, 'inputMethod': 0,
                             'shell': '/bin/bash', 'source': ''},
        'BundleIdentifier': 'com.apple.RunShellScript',
        'CFBundleVersion': '2.0.3',
        'CanShowSelectedItemsWhenRun': False,
        'CanShowWhenRun': True,
        'Category': ['AMCategoryUtilities'],
        'Class Name': 'RunShellScriptAction',
        'InputUUID': str(uuid.uuid4()).upper(),
        'Keywords': ['Shell', 'Script', 'Command', 'Run', 'Unix'],
        'OutputUUID': str(uuid.uuid4()).upper(),
        'UUID': str(uuid.uuid4()).upper(),
        'UnlocalizedApplications': ['Automator'],
        'arguments': {},
        'isViewVisible': True,
        'location': '309.000000:253.000000',
        'nibPath': '/System/Library/Automator/Run Shell Script.action/Contents/Resources/Base.lproj/main.nib',
    }
    return {
        'AMApplicationBuild': '523',
        'AMApplicationVersion': '2.10',
        'AMDocumentVersion': '2',
        'actions': [{'action': action, 'isViewVisible': True}],
        'connectors': {},
        'workflowMetaData': {
            'applicationBundleIDsByPath': {},
            'applicationPaths': [],
            'inputTypeIdentifier': 'com.apple.Automator.text',
            'outputTypeIdentifier': 'com.apple.Automator.nothing',
            'presentationMode': 11,
            'processesInput': 0,
            'serviceInputTypeIdentifier': 'com.apple.Automator.text',
            'serviceOutputTypeIdentifier': 'com.apple.Automator.nothing',
            'serviceProcessesInput': 0,
            'systemImageName': 'NSActionTemplate',
            'useAutomaticInputType': 0,
            'workflowTypeIdentifier': 'com.apple.Automator.servicesMenu',
        },
    }


def main():
    opts, _ = getopt.getopt(sys.argv[1:], '', ['name=', 'python=', 'dest='])
    opts = dict(opts)
    name = opts.get('--name', 'dragoman で解析')
    python = opts.get('--python', sys.executable)
    dest = os.path.expanduser(opts.get('--dest', '~/Library/Services'))
    command = 'DRAGOMAN_PYTHON=%s %s' % (shlex.quote(python), shlex.quote(SCRIPT))
    bundle = os.path.join(dest, name + '.workflow', 'Contents')
    os.makedirs(bundle, exist_ok=True)
    with open(os.path.join(bundle, 'Info.plist'), 'wb') as fp:
        plistlib.dump(info_plist(name), fp)
    with open(os.path.join(bundle, 'document.wflow'), 'wb') as fp:
        plistlib.dump(document(command), fp)
    subprocess.run(['/System/Library/CoreServices/pbs', '-update'], check=False)
    print('サービス「%s」→ %s' % (name, os.path.dirname(bundle)))
    print('  コマンド: %s' % command)


if __name__ == '__main__':
    main()
