# フランス語（作りかけ）

フランス語の文を、spaCy のフランス語モデル（fr_core_news_sm）で品詞・原形・性・数・人称・時制と依存関係を付けてから、
動詞の組（複合過去・受動・話法の助動詞）をまとめ、共通の解析器（格の枠）で日本語に訳します。名詞に格の形は無いので、
格は文の中の役割（前置詞の目的語・主語・目的語）から付けます。訳語は Wiktionary の英語の語義を日本語に直したものです。

```
./dragoman.py fr -e "Le garçon lit un livre à l'école."
  →  少年が / 学校[に,で] / 本を / 読む
./dragoman.py fr -e "Je le lui ai donné hier."
  →  私が / {彼,彼女}に / {彼,それ}を / 昨日 / 与えた
./dragoman.py fr -e "La fille qui chante est ma sœur."
  →  歌う{少女,娘}は / 私の姉妹である
python3 tools/samples.py --lang=fr              # サンプル (samples/french.txt) の訳
./dragoman.py fr samples/french.txt                # 解析の詳細 (-w で語ごとの辞書引きを省く)
```

ラテン文字の文は、フランス語らしい語（le, la, les, est, que, pas …）が2つ以上（ドイツ語・トルコ語らしい語より多く）あるか、
アクセント記号（é・è・ê・à …）・エリジオン（l'・qu'）があればフランス語と推定します。

## 扱うもの

* 語の切り出し: エリジオン（l'école → l' école、qu'il → qu' il）、倒置（dit-il → dit il、a-t-il → a il）。
  aujourd'hui・quelqu'un は1語。
* 格: 前置詞の後ろは前置詞の目的語。それ以外は動詞の前なら主語「が」、後ろなら目的語「を」（être・devenir などの後ろは補語）。
  読点・接続詞・関係代名詞で節を区切る。代名詞は形で格が分かる（je 主格、me 対格・与格、le 対格、lui 与格、moi 前置詞の後ろ）。
  接語が2つ並ぶとき（me le・le lui）は le・la・les が対格、ほかが与格。3人称の代名詞は人にも物にも取れる訳
  （il「{彼,それ}が」、le「{彼,それ}を」、l'「{彼,彼女,それ}を」、lui「{彼,彼女}に」）。主語の代名詞の後ろの nous・vous は目的語、
  文頭・節の頭なら主語。動詞の人称は直前の主語の代名詞から（spaCy の読み誤りを直す）。
  人を表す接語（me・te・se・nous・vous）の格は動詞から: 辞書の語義の印（à を取る「[with à]」・物を人に「something to someone」・
  自動詞だけ）と手作りの表（`french/morphology.py`）で、間接他動詞（parler・répondre・obéir・ressembler …。Il me parle「私に話す」）と
  二重目的語の動詞（donner・dire・montrer …。Il me montre「私に見せる」）は与格、ほか（voir・aimer …）は対格。
  複合過去（Il m'a parlé）は本動詞で決める。
* 代名動詞: 主語と同じ人称の再帰の接語（se・je me・nous nous …）+ 動詞は、辞書の「se + 動詞」の見出し（Wiktionary の reflexive の
  語義から作る）で引き、接語は訳に出さない（Il se lève「起きる」、Je m'appelle Jean「ジャンと呼ばれている」）。再帰の接語 + être +
  過去分詞は複合過去（Elle s'est levée「起きた」）。見出しが無ければ再帰の目的語のまま（Il se lave → se laver があれば「体を洗う」）。
* 人が与格・物が主語の動詞（manquer à・plaire à。`french/morphology.py` の EXPERIENCER_VERBS）は人を主題に
  （Tu me manques「私は / 君が / いなくて寂しい」、Ce livre me plaît「私は / この本が / 気に入っている」）。
  文の枠では人を主語・相手を目的語にした英語の動詞を仲立ちに（manquer → miss: I miss you・Ich vermisse dich・Tē dēsīderō、
  plaire → like: I like this book・Ich mag dieses Buch）、フランス語に戻すときは元の形。
* 冠詞（le・un・des）は名詞に掛けて訳さない。所有形容詞・指示形容詞（mon・ce・tout …）は「私の」「この」「すべての」。
  前置詞と冠詞の縮約形（au・aux・du・des）は前置詞。動詞のすぐ後ろの du・des は部分冠詞（manger du pain「パンを食べる」）。
  de を取る動詞（parler de「〜について」、venir de「〜から」…）の後ろは前置詞のまま。
* 名詞 + de + 名詞は属格（la maison de mon père「私の父の家」）。
* 動詞の組を助動詞の位置の1語にまとめる: avoir + 過去分詞 → 複合過去「〜した」（avait + 過去分詞 → 大過去）、
  être + 過去分詞 → 移動・変化の動詞（aller・venir・partir …）なら複合過去、ほかは受動（par + 名詞は「〜によって」）、
  話法の助動詞 + 不定詞（pouvoir「〜できる」・vouloir「〜したい」・devoir「〜なければならない」）、aller + 不定詞 → 近い未来。
  不定詞の目的語は不定詞の後ろ（言語の設定 `infinitive_objects_follow`: Nous voulons lire un livre「本を読みたい」）。
* 否定 ne … pas（ne の無い pas も）、ne … jamais「決して」、ne … rien「何も」・personne ne …「誰も」（冠詞の無い personne・rien は
  否定の代名詞。動詞の前なら主語、後ろなら目的語。助詞は「も」）、il y a + 名詞「〜がある」。
* 前置詞・副詞 + que の接続詞（sans que「〜することなく」、avant que・bien que・pour que・parce que・pendant que …）は1語に。
  s'en・n'en・m'y の en・y は接語（spaCy が前置詞と読むのを直す: s'en aperçoive「それに気づく」）。
  en（de + それ）の助詞は動詞から（s'en apercevoir「それに」、parler「それについて」、ほかは「それを」）。
* de + 名詞が目的語にあたる動詞（s'apercevoir de・se souvenir de・se moquer de …）は de を外して目的語に（日本語は動詞ごとの助詞:
  Il s'aperçoit de son erreur「誤りに気づく」= He realizes his error）。フランス語に戻すときは de を付ける。
* 代名動詞の見出しの表示は省略形（s'apercevoir・s'appeler。辞書の鍵は se apercevoir）。
* 関係代名詞 qui・que は共通の解析器の関係節に。que・si・quand … の従属節。
* spaCy の小さいモデルの読み誤りを辞書の語形の表で直す: 主語・関係代名詞 qui の後ろの動詞の形（Le garçon lit … の lit を
  前置詞と、qui chante の chante を形容詞と読む）、動詞の前の接語の代名詞（le lui を冠詞と名詞と読む）、文頭の命令形、
  主語・目的語の位置の形容詞の形（a trouvé preneur）。
* 人名はフランス語の読みのカタカナ（Jean → ジャン、Camus → カミュ、Claude → クロード。英語の名前 John の訳にしない）、
  地名は辞書の訳（Londres → ロンドン）。

## 文の生成 (出口)

ほかの言語の文の枠からフランス語の文を作ります（`generate/french.py`）。比較の表（`tools/generate.py --compare`）にも出ます。

```
python3 tools/generate.py --to=fr "Puella rosam in hortō vīdit."
  フランス語: La fille a vu la rose dans le jardin.
python3 tools/generate.py --to=fr "Ego tē amō. Agricola est. Via longa et lāta est."
  フランス語: Je t'aime.  /  Il y a un agriculteur.  /  La route est longue et large.
python3 tools/generate.py --from=fr "Je le lui ai donné hier."      # 入口から: ラテン語 Eī eum here dedī.
```

* 語は英語を仲立ちにした置き換え（解析器の訳語の表 GLOSSES の語を先に: soldat を drille より）。名詞の性と、名詞・形容詞・動詞の
  語形は辞書の語形の表から（無ければ規則: 複数 -s・-x・-aux、女性 -e、-er 動詞の活用）。
* 名詞句: 定冠詞 le / la / l' / les（元の言語の不定冠詞なら un / une / des）、前に置く形容詞（beau・petit・grand …）と後ろに置く
  形容詞（性・数の一致）、所有形容詞・指示形容詞（mon / ma / mes、ce / cet / cette / ces）、de + 属格、エリジオン（l'école・d'ami）、
  前置詞と冠詞の縮約（au・aux・du・des）。町の名前は à（à Rome）。
* 語順: 主語 - ne - 接語の代名詞（me・te・le・la・lui・leur …。me le・le lui の順）- 動詞 - pas - 過去分詞 - 目的語 - à + 受け手 -
  前置詞句。関係節は qui（主語の空所）・que（目的語の空所）。
* 時制: 現在、完了は複合過去（avoir + 過去分詞。移動・変化の動詞は être + 過去分詞で主語に一致: Elle est allée）、未完了は半過去、
  大過去、単純未来。受動は être + 過去分詞（par + 動作主）。否定 ne … pas。存在の文は il y a + 不定冠詞。
* 入口 (--from=fr) から: 冠詞の定・不定を枠に渡し、元の前置詞（à l'école）は元の言語に戻すときそのまま使う。

## 1990年の綴りの改革

1990年の綴りの改革（rectifications orthographiques）で綴りが変わった語は、語ごとの詳細にもう一方の綴りを出します:

```
./dragoman.py fr -e "Le coût est élevé."
   0  coût   (coût (le)) 代価,価格 [Nom.sg.m]
            1990年の新しい綴りでは cout
./dragoman.py fr -e "Il connait cet événement."
   … connait   1990年の新しい綴り (従来の綴りは connaît)
   … événement 1990年の新しい綴りでは évènement
```

* 対応は辞書の語義「post-1990 spelling of coût」から（292 語: î・û の記号を省く coût → cout・boîte → boite、é → è の événement →
  évènement …）。見出しの新旧が î・û の記号だけの違いなら活用形にも同じ規則で（connaît → connait、plaît → plait）。
  記号で別の語と区別する語（dû・sûr・mûr）は変わらないので出ない。
* 新しい綴りで書いた語は従来の綴りの語義で訳す（cout → 代価,価格）。文の生成は従来の綴り（plaît）。
* 連結符の改革（week-end → weekend、vingt et un → vingt-et-un）・二重子音の簡略化（ruisselle → ruissèle）は辞書の語義にある語だけ。

## 法と動詞の組

* 接続法: 語形の表でその人称に直説法の読みが無い形（parte・viennes）か、接続法を求める que の後ろ（主節が falloir・vouloir・
  souhaiter …、sans que・pour que・bien que …）で接続法の読みのある形（aille・parle）は接続法。条件法は「〜だろう」。
* il faut que + 接続法は1つの節に（Il faut que je parte「私が / 出発しなければならない」）。文の枠では oportet + 主語のある
  不定詞の節（Mē abīre oportet・I have to leave・Ich muss abfahren）、フランス語に戻すと il faut que + 接続法。
* 話法の助動詞・使役（pouvoir・vouloir・devoir・il faut・faire・laisser + 不定詞）は、文の枠ではラテン語と同じ「話法の動詞 +
  不定詞の節」（possum legere）。近い過去 venir de は完了 + modo「たった今」。
* que 節は主節の補文に（文の枠ではラテン語の対格不定詞と同じ不定詞の節）: 言う・思う・知る動詞は saying（Je sais que tu viens →
  Tē venīre sciō・I know that you come・「君が来ると知っている」）、望む・命じる動詞（vouloir・demander …）は command（Je veux que tu
  viennes → Volō tē venīre・I want you to come・「君に来てほしい」）。フランス語に戻すと que 節（command は接続法）。ラテン語の対格不定詞
  からも que 節（Dīcit puerum venīre → Il dit que le garçon vient。補文の主語の sē は主節の主語を指す代名詞: qu'elle aime）。
  感情の動詞・形容詞（regretter・craindre、être content・triste …）の que 節は emotion（接続法。Je suis content que tu viennes
  「君が来ることがうれしい」・She is sad that you leave）。補文を取るときの主節の動詞の日本語は補文の種類で選ぶ（demander que「頼む」）。
* 疑問文（倒置 Viens-tu・est-ce que・文末の ?）は文の枠の疑問の印に（生成の文末は ?、日本語は「〜か。」）。
* 命令文（主語の無い文頭の動詞。Donne-moi の接語）、1人称の命令は「〜よう」（Parlons「話そう」）。
* ジェロンディフ en + 現在分詞「〜しながら」、比較 plus / aussi / moins … que「〜より」「〜と同じくらい」「〜ほど…ない」、
  非人称の il（il faut・il pleut）。

## 準備

```
pip install spacy && python3 -m spacy download fr_core_news_sm      # 約16MB (LGPL-LR。UD French-Sequoia・WikiNER で学習)
mkdir -p ~/.local/share/dragoman-data/fr/ud
curl -sL -o ~/.local/share/dragoman-data/fr/kaikki.org-dictionary-French.jsonl https://kaikki.org/dictionary/French/kaikki.org-dictionary-French.jsonl
python3 tools/build_french_dic.py ~/.local/share/dragoman-data/fr/kaikki.org-dictionary-French.jsonl
```

Wiktionary のフランス語の抽出データ（CC BY-SA）は約 580MB（`~/.local/share/dragoman-data/fr/` に置いておくと作り直しが速い。
標準入力から流すこともできる: `curl … | python3 tools/build_french_dic.py -`）。必要なものだけを sqlite に残します（`~/.local/share/dragoman-data/fr/wiktionary.sqlite`、約 90MB。見出し語 8.6 万・語形 60 万）。
見出し語ごとの品詞・英語の語義（古い・まれな語義は後ろに、訳語は6つまで: partir は to share より to leave を先に）・名詞の性・動詞の語義の印（他動・自動・再帰と à）、代名動詞の見出し（se lever …）と、語形の表（動詞は単純時制の形だけ。複合時制は avoir / être + 過去分詞で作る）です。

評価用に UD French-GSD（CC BY-SA 4.0）の `fr_gsd-ud-test.conllu` を `~/.local/share/dragoman-data/fr/ud/` に置きます
（spaCy のモデルの学習に使ったのは Sequoia なので、GSD とは重ならない）。

## 評価

```
python3 tools/ud_eval.py --lang=fr
```

UD French-GSD のテスト（416 文）で、述語の検出 93%、主語の再現率 79%、目的語の再現率 69%、代名詞の格 92%（2026-10-15）。
il y a + 名詞は訳では「〜がある」の主語なので、主語として数える。

## まだのこと

* pour・sans + 不定詞「〜するために」「〜せずに」を不定詞の節の接続詞に（今は行き場の無い語句になる）。
* 倒置の主語（a expliqué Véronique、Que dit l'Eglise ?）、疑問文の est-ce que。
* 人が与格の構文は manquer・plaire だけ（convenir・importer・falloir も同じ形にできる）。ロシア語の出口の miss（скучать по + 与格）・
  like（нравиться + 与格）はまだ。
* 出口: 否定の文の部分冠詞（ne mange pas de pain）、主語の倒置・疑問文。接続法は sans que・bien que・pour que・avant que の後ろの
  現在だけ。ne … personne・ne … rien は枠では否定の代名詞（nēmō・nihil）で、節の否定にしない（二重否定にしない）。
