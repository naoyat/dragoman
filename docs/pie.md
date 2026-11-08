# 印欧祖語（シュライヒャーの寓話）

August Schleicher が1868年に再建した印欧祖語で書いた寓話「羊と馬」（Avis akvāsas ka）を、語ごとに引いて日本語に訳します。
語には今の再建形（喉音のある表記）と、ラテン語・古典ギリシア語・サンスクリットの同源の語を添えます。

```
./dragoman.py ine samples/schleicher.txt          # pie でも同じ
./dragoman.py ine --kana samples/schleicher.txt
python3 tools/samples.py --lang=ine
```

```
Avis akvāsas ka.
  →  羊と馬
Avis akvabhjams ā vavakat:
  →  羊が / 馬に / 言った
Tat kukruvants avis agram ā bhugat.
  →  羊が / {それを 聞いて} / 野を / 逃げた

   0  Avis     (avi) 羊 [Nom.sg.f]
              今の再建: *h₂ówis  同源: ラテン ovis, 古代ギリシア ὄϊς, サンスクリット ávi-
```

## 本文と辞書

* 本文（`samples/schleicher.txt`）は1868年の原文（Beiträge zur vergleichenden Sprachforschung 5, pp. 206–208。パブリックドメイン）。
  後の研究者の書き直し（Lehmann・Zgusta 1979、Byrd 2013 など）は入れない。
* 辞書（`dragoman/pie/lexicon.py`）は寓話に出てくる語だけを手で書いたもの。データのダウンロードは要らない。
  * `FORMS`: 本文の語形 → 見出し・品詞・格・数・性（動詞は時制・法・態・人称・数）。格などはシュライヒャーの意図した形（羊 avi- は女性）。
  * `LEMMAS`: 見出し → 訳語・今の再建形・同源の語。今の再建形は見出しの形（名詞は単数主格、動詞は語根）だけで、語形ごとの
    今の形は載せない（akvabhjams の与格複数 -bʰyos / -mos のように、説によって違うところが多い）。

## 表記と読み

* シュライヒャーの表記は19世紀の再建: 喉音（*h₁ *h₂ *h₃）が無い、母音は a・i・u が中心（e・o は a に）、v は今の *w、j は *y、
  k は口蓋音（*ḱ）と唇軟口蓋音（*kʷ）を区別しない（akva = *h₁éḱwos、ka = *-kʷe）。
* 動詞の前に離して書いた ā は加音（過去の印: ā ast「あった」、ā vavakat「言った」、ā bhugat「逃げた」）。動詞に含めて、語の解説に
  「加音 ā 付き」と出す。
* 後置の ka「と」（avis akvāsas ka「羊と馬」）は前の語の手前に移して、ラテン語の et と同じ並列に（パーリ語の ca と同じ）。
* 引用の前の「:」で文を分ける（Avis akvabhjams ā vavakat: / kard aghnutai …）。vividvant-svas はハイフンで2語に分けて引く。
* 存在の ast（jasmin varnā na ā ast「その上に羊毛の無かった」）は繋辞にしない（「羊毛ではなかった」にならないように）。
* カタカナ（`pie/katakana.py`）は綴りから: 長母音は「ー」、v は「ヴ」、j はヤ行、有気音 bh・dh・gh は b・d・g と同じ
  （avis → アヴィス、bhāram → バーラム、jasmin → ヤスミン）。

## 今の訳の穴

* 1文目の akvams, tam, …, tam, …, tam「馬たちを、一頭は〜、一頭は〜、一頭は〜」: tam を馬の言い換え（=）にして、分詞（vaghantam
  「引いている」・bharantam「運んでいる」）を後ろの名詞（車・人）に掛けてしまう（本来は tam「その一頭」に掛かる）。
* 関係節の空所の処格（jasmin「その上に」）は訳に出ない。
* agram「野へ」（方向の対格）は「野を」。
* 辞書は寓話の語だけ。ほかの文は引けない語が多い（広げるなら Wiktionary の印欧祖語の項目から）。
