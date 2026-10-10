#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# 手作りの辞書ファイル (dragoman/latin/data/*.def) の場所。パッケージの中に置き、wheel にも同梱する (pyproject.toml)
#
import os

WORDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def words_path(name):
    return os.path.join(WORDS_DIR, name)
