#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 古英語の音読用の espeak-ng の音素表 (ang) を作る
#
#   python3 tools/build_oldenglish_espeak.py [PHSOURCE]
#
# espeak-ng の音素はテキストの定義 (ソースの phsource/) からコンパイルしたデータ (phontab・phondata …) で、
# 言語の表はほかの表を引き継げる。古英語の表はドイツ語の表 (de。基本の表 base1 の θ・ð・w・ɣ も持つ) を引き継ぎ:
#   - b・d・g・v・z をドイツ語の語末の無声化の無い定義に (基本の表の定義を呼ぶだけ: gōd の d を t にしない)
#   - [æ] (&)・[æː] (&:) を足す (espeak-ng の母音のフォルマント vowel/& を使う)
#   音声 ang の言語の設定は en (ドイツ語の設定は音素表とは別に語末の無声化をする)
# 入力: espeak-ng のソース (https://github.com/espeak-ng/espeak-ng、GPL-3.0) の phsource/。インストールしてある
#       espeak-ng と同じ版 (コンパイルしたデータの形式が版ごとに違う)。既定は
#       $DRAGOMAN_DATA/espeak-src/espeak-ng-<版>/phsource (ほかの言語の表を作るときも共用)
# 出力: $DRAGOMAN_DATA/ang/espeak-ng-data (インストールしてある espeak-ng のデータの写しに、古英語の表と音声 ang を
#       足してコンパイルし直したもの。espeak-ng-data 由来 (GPL-3.0)。インストールしてあるデータには触れない)
#   使い方: espeak-ng --path=$DRAGOMAN_DATA/ang -v ang "[[hw'&t]]"
#
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dragoman.core import paths

# 古英語の表 (自前の定義。基本の表の定義を呼ぶ)
PH_OLDENGLISH = '''// Old English (dragoman: tools/build_oldenglish_espeak.py)
// German phonemes without final devoicing, plus [ae] and [ae:]

phoneme b
  vcd blb stp
  voicingswitch p
  CALL base1/b
endphoneme

phoneme d
  vcd alv stp
  voicingswitch t
  CALL base1/d
endphoneme

phoneme g
  vcd vel stp
  voicingswitch k
  CALL base1/g
endphoneme

phoneme v
  vcd lbd frc
  voicingswitch f
  CALL base1/v
endphoneme

phoneme z
  vcd alv frc sib
  voicingswitch s
  CALL base1/z
endphoneme

phoneme &
  vwl starttype #a endtype #a
  length 120
  FMT(vowel/&)
endphoneme

phoneme &:
  vwl starttype #a endtype #a
  length 210
  FMT(vowel/&)
endphoneme
'''
# 言語の設定は en (de・nl の設定は語末の有声音を無声にする。音素の列 [[…]] で渡すので訳語の辞書は使わない)
VOICE = '''name Old English (dragoman)
language en
phonemes ang
tunes s4 c1 q4 e1
'''


def espeak_version_and_data():
    out = subprocess.run(['espeak-ng', '--version'], capture_output=True, text=True).stdout
    m = re.search(r'text-to-speech: (\S+)\s+Data at: (.+)', out)
    if not m:
        sys.exit('espeak-ng が見つからない')
    return m.group(1), m.group(2).strip()


def main():
    version, installed = espeak_version_and_data()
    root = paths.data('ang')
    src = sys.argv[1] if len(sys.argv) > 1 else paths.data('espeak-src', 'espeak-ng-%s' % version, 'phsource')
    if not os.path.isdir(src):
        sys.exit('no phsource: %s (espeak-ng %s のソースを展開しておく)' % (src, version))
    data = os.path.join(root, 'espeak-ng-data')
    work = os.path.join(root, 'espeak-phsource')
    for d in (data, work):
        if os.path.exists(d):
            shutil.rmtree(d)
    shutil.copytree(installed, data)
    shutil.copytree(src, work)
    with open(os.path.join(work, 'ph_oldenglish'), 'w') as fp:
        fp.write(PH_OLDENGLISH)
    with open(os.path.join(work, 'phonemes'), 'a') as fp:
        fp.write('\n\nphonemetable ang de\ninclude ph_oldenglish\n')
    os.makedirs(os.path.join(data, 'lang', 'gmw'), exist_ok=True)
    with open(os.path.join(data, 'lang', 'gmw', 'ang'), 'w') as fp:
        fp.write(VOICE)
    env = dict(os.environ, ESPEAK_DATA_PATH=root)
    result = subprocess.run(['espeak-ng', '--path=%s' % root, '--compile-phonemes=%s' % work], env=env,
                            capture_output=True, text=True)
    print((result.stdout + result.stderr).strip()[-2000:])
    shutil.rmtree(work)   # 作業用の写しは消す (元の phsource は残す)
    check = subprocess.run(['espeak-ng', '--path=%s' % root, '-v', 'ang', '-q', '--ipa', "[[hw'&t g'o:d]]"],
                           capture_output=True, text=True)
    print('ang: %s' % (check.stdout.strip() or check.stderr.strip()))


if __name__ == '__main__':
    main()
