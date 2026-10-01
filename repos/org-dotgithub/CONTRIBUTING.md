# CONTRIBUTING（組織既定）

各リポジトリに個別の CONTRIBUTING.md が無い場合に適用されます。

## ブランチと PR

- `main` は保護ブランチ（直 push 禁止・CI 必須・レビュー 1 名以上）。
- ブランチ名: `feat/<topic>` / `fix/<topic>` / `docs/<topic>` / `chore/<topic>`
- コミットは [Conventional Commits](https://www.conventionalcommits.org/ja/v1.0.0/)（例: `feat(cli): add --strict`）。
- PR は小さく。1 PR = 1 目的。スクリーンショットや実行例を添える。

## レビュー観点

| 観点 | 確認内容 |
|---|---|
| 責務 | 1 ツール = 1 責務を守っている（変換と検証を混ぜない等） |
| 互換性 | CLI オプション・終了コード・出力形式（JSON）を壊していない。壊すなら MAJOR |
| テスト | 新しい振る舞いにテストがある。ゴールデンの差分は意図どおり |
| 安全性 | 秘密情報を書いていない。機密本文をログに出していない。一時ファイルを消している |
| ドキュメント | README の使用例・CHANGELOG を更新した |

## 秘密情報

`.env` はコミットしない。必要な値は `.env.example` に `<your-token>` のような形で書く。
