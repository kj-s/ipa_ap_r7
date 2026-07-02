# 情報処理技術者試験 過去問アプリ作成手順

この手順は、別の作業フォルダで同じ形式の過去問アプリを作るための再現用メモです。今回と同じく「問題PDF」と「解答PDF」から、1画面に1問ずつ表示される静的HTMLアプリを作る前提です。

## 目的

- 問題PDFから各問を画像として切り出す
- 解答PDFから正解と分野を抽出する
- `index.html` を開くだけで動く静的アプリにする
- 1画面1問、選択肢ボタン、解答表示、前後移動、問題ジャンプ、進捗表示、選択状態保存を実装する
- 依存関係やサーバーを増やさず、できるだけポータブルにする

## 入力ファイル

作業フォルダ直下に次のようなPDFを置く。

```text
2025r07a_ap_am_qs.pdf   # 問題冊子
2025r07a_ap_am_ans.pdf  # 解答例
```

ファイル名が違う場合は、生成スクリプト内の `QUESTION_PDF` と `ANSWER_PDF` を変更する。

## 作るファイル構成

```text
.
├── index.html
├── app.js
├── styles.css
├── questions.js
├── tools/
│   └── generate_questions.py
├── assets/
│   └── questions/
│       ├── q01_1.png
│       ├── q02_1.png
│       └── ...
└── .gitignore
```

`tmp/` や `__pycache__/` は生成物なのでGitには入れない。

## 全体方針

問題PDFはテキスト抽出できないスキャン画像の場合がある。そのため、問題文はOCRしない。PDFページを画像化し、各問の開始位置を検出してPNGに切り出す。

解答PDFはテキスト抽出できることが多いので、`pdfplumber` で `問番号 正解 分野` を抽出して `questions.js` に埋め込む。

フロントエンドはビルド不要のHTML/CSS/JavaScriptにする。これにより、`index.html` をブラウザで開くだけで使える。

## 実装手順

### 1. PDFの状態を確認する

まず、問題PDFと解答PDFのページ数とテキスト抽出可否を確認する。

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import pdfplumber; p='2025r07a_ap_am_qs.pdf'; pdf=pdfplumber.open(p); print(len(pdf.pages)); print(repr((pdf.pages[0].extract_text() or '')[:1000]))"
```

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -X utf8 -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); import pdfplumber; p='2025r07a_ap_am_ans.pdf'; pdf=pdfplumber.open(p); print(len(pdf.pages)); print((pdf.pages[0].extract_text() or '')[:2000])"
```

今回のように、問題PDFからテキストが取れない場合は画像切り出し方式で進める。

### 2. 代表ページを画像化して目視確認する

`pypdfium2` で問題PDFの代表ページを画像化する。

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import pypdfium2 as pdfium; pdf=pdfium.PdfDocument('2025r07a_ap_am_qs.pdf'); page=pdf[3]; img=page.render(scale=2).to_pil(); img.save('tmp/page4.png'); print(img.size)"
```

確認するポイント:

- 問題が始まるページ番号
- 問題が終わるページ番号
- 1ページに何問程度あるか
- 問番号の左端位置がそろっているか
- 末尾にメモ用紙や注意事項ページが含まれていないか

今回のPDFでは、問題はPDFの4ページ目から38ページ目までだった。

### 3. 生成スクリプトを作る

`tools/generate_questions.py` を作る。役割は次の4つ。

- 解答PDFから正解データを抽出する
- 問題PDFの問題ページを画像化する
- 各問の開始位置を検出する
- `assets/questions/qXX_1.png` と `questions.js` を生成する

重要な実装ポイント:

- `SCALE = 2` でレンダリングして読みやすさを確保する
- 問番号の「問」の字形をテンプレートにして、左端の狭い範囲だけ探索する
- 本文中や図中の「問」を誤検出しないよう、探索X座標を絞る
- 検出数が80にならない場合は、ページごとの検出数をログに出して調整する
- 空白だけの切り出し片は、黒画素数で除外する
- 解答データは `window.QUESTIONS = [...]` 形式で出力する

検出数がずれる場合は、まず以下を調整する。

```python
FIRST_QUESTION_PAGE_INDEX = 3
LAST_QUESTION_PAGE_INDEX = 37
```

次に、テンプレート切り出し位置と探索範囲を調整する。

```python
template = np.array(template_page.crop((104, 145, 131, 181))) < 160
for x in range(85, 122):
```

最後に検出閾値を調整する。

```python
if best_score > 0.38:
```

### 4. 画像とデータを生成する

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\generate_questions.py
```

成功時の出力例:

```text
Generated 80 questions in assets\questions
```

生成後に確認する。

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import json,re,pathlib; s=pathlib.Path('questions.js').read_text(encoding='utf-8'); data=json.loads(re.sub(r'^window\\.QUESTIONS = |;\\s*$', '', s)); assert len(data)==80; assert all(q['images'] for q in data); print('questions ok', len(data), sum(len(q['images']) for q in data))"
```

期待値:

```text
questions ok 80 80
```

代表的な画像も目視する。

- `assets/questions/q01_1.png`
- `assets/questions/q40_1.png`
- `assets/questions/q80_1.png`

確認するポイント:

- 問題文の先頭が切れていない
- 図表が入っている
- 選択肢が最後まで入っている
- 次の問題が混ざっていない

### 5. 静的アプリを作る

`index.html` は次を読み込む。

```html
<link rel="stylesheet" href="styles.css" />
<script src="questions.js"></script>
<script src="app.js"></script>
```

画面要素:

- ヘッダー: 試験名、進捗
- 問題エリア: 問番号、分野バッジ、問題画像
- 回答エリア: ア/イ/ウ/エボタン、結果表示
- ナビゲーション: 前へ、問題ジャンプ、次へ

`app.js` の機能:

- `window.QUESTIONS` を読み込む
- 現在の問題番号を `localStorage` に保存する
- 選択済み回答を `localStorage` に保存する
- 解答表示ボタンで正解を表示する
- 正解、不正解のボタン色を切り替える
- 左右キーで前後移動する
- ア/イ/ウ/エキーでも選択できる

`styles.css` の方針:

- 業務ツール寄りの落ち着いたUIにする
- 問題画像を最大幅で表示して読みやすくする
- モバイルではヘッダーと回答欄を縦積みにする
- ボタンやカードの角丸は控えめにする
- 単色に寄りすぎない配色にする

### 6. 検証する

JavaScript構文確認:

```powershell
node --check app.js
```

データ整合確認:

```powershell
C:\Users\j-kazama\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -c "import json,re,pathlib; s=pathlib.Path('questions.js').read_text(encoding='utf-8'); data=json.loads(re.sub(r'^window\\.QUESTIONS = |;\\s*$', '', s)); assert len(data)==80; assert all(q['images'] for q in data); print('questions ok', len(data), sum(len(q['images']) for q in data))"
```

ブラウザ確認:

- `index.html` を直接開く
- 問1が表示される
- ア/イ/ウ/エを押せる
- 解答表示で正解が出る
- 次へ/前へが動く
- 問題ジャンプが動く
- リロード後も選択状態が残る
- スマートフォン幅でも文字やボタンが重ならない

### 7. Git管理とプッシュ

`.gitignore` を作る。

```gitignore
tmp/
__pycache__/
```

初期化する。

```powershell
git init -b main
git add .
git commit -m "Add IPA AP past exam app"
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin main
```

もし `__pycache__` を誤ってコミットに入れたら、プッシュ前に外す。

```powershell
git rm --cached tools/__pycache__/generate_questions.cpython-312.pyc
git add .gitignore
git commit --amend --no-edit
```

## 別年度・別試験で調整する箇所

### PDFファイル名

```python
QUESTION_PDF = ROOT / "..."
ANSWER_PDF = ROOT / "..."
```

### 問題数

応用情報午前は通常80問。別試験で問題数が違う場合は、検出数チェックを変更する。

```python
if len(answers) != 80:
if len(starts) != 80:
```

### 問題ページ範囲

```python
FIRST_QUESTION_PAGE_INDEX = 3
LAST_QUESTION_PAGE_INDEX = 37
```

PDFページ番号は0始まりなので注意する。PDF表示上の4ページ目は `3`。

### 問番号テンプレート

問題冊子のスキャン位置が違う場合は、代表ページをレンダリングして「問」の位置を見直す。

```python
template = np.array(template_page.crop((104, 145, 131, 181))) < 160
```

### 探索範囲

本文中の「問」を拾う場合はX範囲を狭める。問番号を取りこぼす場合は少し広げる。

```python
for x in range(85, 122):
```

### 切り出し範囲

左右や上下が欠ける場合は調整する。

```python
content_left = 70
content_right = 960
content_top = 90
content_bottom = 1300
```

### 空白除外

ページまたぎ判定で空白画像が混ざる場合は黒画素数の閾値を上げる。必要な2枚目が消える場合は下げる。

```python
dark_pixels < 2500
```

## 品質基準

完成扱いにする前に、最低限これを満たす。

- `questions.js` に全問分のデータがある
- 各問に画像が1枚以上ある
- 正解が全問分入っている
- 問1、中間、最終問の画像を目視して問題文と選択肢が欠けていない
- `node --check app.js` が通る
- `index.html` を直接開いて基本操作ができる
- `tmp/` と `__pycache__/` はGitに含めない

## Pythonパッケージについて

追加インストールが必要な場合は、必ず `uv` を使う。

```powershell
uv pip install pdfplumber pypdfium2 pillow numpy
```

`pip install` や `pip3 install` は使わない。

ただし、今回の環境では同梱Pythonに `pdfplumber`、`pypdfium2`、Pillow、NumPyが入っていたため、追加インストールは不要だった。
