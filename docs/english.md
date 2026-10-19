# 英語（現代英語）

英語は、ほかの言語の「出入口」として扱う: 英語の文を解析して日本語に訳し、英語のカタカナ読み（発音に忠実に）を出す。
ほかの言語の訳語の多くは英語の語義を英和の表（`core/en_ja.py`）で日本語に置き換えているので、その表をそのまま英語の
訳語に使う。

```
./dragoman.py en -e "The boy reads a book."
./dragoman.py en --kana-only -e "I don't know what you're talking about."
```

## 準備

* `pip install spacy && python3 -m spacy download en_core_web_sm`（約 12MB、MIT）
* 英和の表 `$DRAGOMAN_DATA/en-ja.sqlite`（`tools/build_en_ja.py`。ほかの言語と共通）
* カタカナ読み: CMUdict（`$DRAGOMAN_DATA/en/cmudict.dict`、github.com/cmusphinx/cmudict、BSD 系のライセンス。米音）と
  espeak-ng（辞書に無い語と英音）

## 解析（`english/analyzer.py`）

spaCy の品詞（Penn Treebank）・原形・依存関係で語の項目を作り、共通の解析器に渡す。

* 格は依存関係から: 主語（nsubj）・補語（attr）は主格、目的語（dobj）は対格、間接目的語（dative）は与格、前置詞の目的語は
  前置詞の目的語。代名詞は形でも（I・me）。副詞の働きの名詞（tomorrow）は副詞
* 冠詞は名詞に掛けて訳さない。所有格（John's・my）は後ろの名詞に掛ける「〜の」
* 助動詞の組: be + 過去分詞 → 受動、have + 過去分詞 → 完了、be + 現在分詞 → 進行「〜している」、will + 原形 → 未来、
  can・must・should・may など + 原形、否定・疑問の do は時制だけ取る
* 「動詞 + to 不定詞」の一部（want → 〜たい、have / need → 〜なければならない、begin / start → 〜始める、try → 〜ようとする）
  は1つの述語に
* 句動詞（give up）は英和の表に句があればその訳
* there is / are は「〜がある」、not・n't・never は否定、関係代名詞（who・which・that）は関係節
* 疑問文（2026-10-20）: 文末の ? で主節の動詞に「か」（共通の解析器: どの言語も。Do you like cats? → あなたが / 猫を / 好むか）。
  疑問詞のある疑問文の主語は主題「は」（Where do you live? → どこで / あなたは / 住むか）、繋辞の文の疑問詞は補語（Who is
  that man? → その男は / 誰であるか）。how old「何歳」・how many「いくつの」、取り残された前置詞（What are you talking
  about? → 何について）、have been to「〜へ行った」
* 間接疑問: know・ask・wonder・tell など（core/Question.py の QUESTION_VERBS）の目的語の、疑問詞（who・what・where・
  whether …）で始まる節（I don't know what you're talking about → 私が / {あなたが 何について 話している}かを / 知らない、
  whether は「かどうか」）。従属節の最初の語に節の頭の印（clause_start）を付け、共通の解析器が動詞の間の語をそこで分ける

言語の推定: the か、英語らしい語（and, of, to, you, is …）が2つ以上か、John's・don't の形があれば英語。

## カタカナ（`english/katakana.py`）

docs/katakana.md の「英語」を見よ。米音（既定）は CMUdict、英音は `--kana-accent=gb`（espeak-ng）。

## まだできないこと

* 副詞節（when・because …）は節を分けて並べるだけ（〜するとき / 彼女が / 来た）
* 評価（UD English-EWT）はまだ
