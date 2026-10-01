# セキュリティポリシー（組織既定）

## 脆弱性の報告

公開 Issue には書かず、リポジトリの **Security → Report a vulnerability**（Private vulnerability reporting）
または `<your-security-contact>` へ連絡してください。

## ツール開発の既定

- 秘密情報は環境変数（または `.env`。コミットしない）から読む。
- 機密文書の本文・データ値をログに出さない（`devtools_common.log` を使う）。
- 一時ファイルは `devtools_common.tempfiles.secure_tempdir()` で作成し、例外時も削除する。
- 外部 API 呼び出しは `devtools_common.httpclient` を使い、レート制限・リトライを守る。
- CI で bandit（SAST）と pip-audit（依存脆弱性）を必須チェックにする。
