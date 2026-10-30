#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# テストをファイルごとに並列に走らせる (python3 -m unittest discover -s test -p '*_test.py' と同じテスト)
#
#   python3 tools/run_tests.py            # 並列の数は CPU の数の半分 (最大 6)
#   python3 tools/run_tests.py -j 2       # 並列の数
#   python3 tools/run_tests.py generate   # ファイル名に generate を含むものだけ
#
# - 失敗したファイルはその出力をそのまま出す。最後の行は unittest と同じく OK か FAILED (...)
# - 重いファイル (前回かかった時間の長いもの) から先に始める。時間は test/__pycache__/run_tests.times に
#
import os
import re
import sys
import glob
import json
import time
import getopt
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMES = os.path.join(ROOT, 'test', '__pycache__', 'run_tests.times')
RAN = re.compile(r'^Ran (\d+) tests? in ', re.M)
RESULT = re.compile(r'^(OK|FAILED)(?: \((.*)\))?\s*$', re.M)


def run_file(path):
    start = time.time()
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'test', '-p', os.path.basename(path)],
                            cwd=ROOT, capture_output=True, text=True)
    return path, result, time.time() - start


def load_times():
    try:
        with open(TIMES, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_times(times):
    try:
        os.makedirs(os.path.dirname(TIMES), exist_ok=True)
        with open(TIMES, 'w', encoding='utf-8') as f:
            json.dump(times, f, indent=0, sort_keys=True)
    except OSError:
        pass


def main():
    opts, args = getopt.gnu_getopt(sys.argv[1:], 'j:')
    jobs = min(6, max(1, (os.cpu_count() or 2) // 2))
    for opt, value in opts:
        if opt == '-j':
            jobs = int(value)
    files = sorted(glob.glob(os.path.join(ROOT, 'test', '*_test.py')))
    if args:
        files = [f for f in files if any(a in os.path.basename(f) for a in args)]
    times = load_times()
    files.sort(key=lambda f: -times.get(os.path.basename(f), 0))
    start = time.time()
    tests, failures = 0, []
    with ThreadPoolExecutor(jobs) as pool:
        for path, result, seconds in pool.map(run_file, files):
            name = os.path.basename(path)
            times[name] = round(seconds, 1)
            output = result.stdout + result.stderr
            ran = RAN.findall(output)
            tests += int(ran[-1]) if ran else 0
            status = RESULT.findall(output)
            if result.returncode != 0 or not status or status[-1][0] != 'OK':
                failures.append(name)
                sys.stdout.write('=' * 70 + '\n%s\n' % name + output)
    save_times(times)
    print('-' * 70)
    print('Ran %d tests in %.3fs (%d files, -j %d)' % (tests, time.time() - start, len(files), jobs))
    print()
    print('FAILED (%s)' % ', '.join(failures) if failures else 'OK')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
