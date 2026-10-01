---
description: Excel（や Word・PDF の表）を Markdown に変換し、ルールで整合性をチェックして報告する（doc2md → fieldcheck）
agent: agent
argument-hint: チェックしたいファイルのパス
---

次のファイルの表を、整合性チェックしてください。

- ファイル: ${input:file:Excel / Word / PDF のパス}
- ルール: ${input:rules:rules.yaml のパス（無ければ「なし」と入力。守るべきルールを文章で書いてもよい）}

## 手順

1. **変換**: `doc2md "<ファイル>" -d out -f json`
   - コマンドが見つからなければ `../.venv/Scripts/doc2md`（Windows）/ `../.venv/bin/doc2md` を使う（fieldcheck も同様）
   - JSON の `warning`（非表示行・数式の計算結果が無い・変更履歴など）は、チェック結果に影響するので必ず先に伝える
   - 「数式の計算結果が保存されていない」と出たら `--recalc` を付けて変換し直す（LibreOffice が必要）
2. **表の選択**: `out/<名前>.md` の `##` / `###` 見出しを一覧にし、チェックする表を決める
   （複数あって判断できなければ利用者に聞く）
3. **ルール**:
   - ルールファイルがある → そのまま使う
   - 文章のルールだけ → field-validation の `/fieldcheck-write-rules` と同じ手順で `rules.yaml` を作り、
     `fieldcheck check-rules rules.yaml` が通るまで直す（作ったルールは利用者に見せる）
   - どちらも無い → 列名と値を見て、ありそうなルール案を 3〜5 個提案し、使うものを利用者に選んでもらう
4. **検証**: `fieldcheck validate "out/<名前>.md" --table "<見出し名>" -r rules.yaml -f json`
5. **報告**（日本語・初心者向け）:
   - 変換時の注意点（手順 1 の warning）
   - 指摘の表: | 行 | 項目 | 問題 | 今の値 | 期待される値 | 直し方 |（error を優先して 20 件まで）
   - 元の Excel でその行を探すための手がかり（申請ID など、行を特定できる値）

元の Excel ファイルは直接開かないこと。機密の可能性がある値は、指摘のあった行だけ扱うこと。
