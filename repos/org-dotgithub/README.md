# .github（組織共通リポジトリ）

組織内の全リポジトリに適用される既定ファイルと、ツール群が共通で使う **再利用可能ワークフロー** を置くリポジトリです。
リポジトリ名は必ず `.github` にします（GitHub の仕様）。

| パス | 役割 |
|---|---|
| `.github/workflows/python-ci.yml` | 共通 CI：ruff（lint/format）→ pytest（複数 Python）→ bandit（SAST）・pip-audit（依存脆弱性） |
| `.github/workflows/python-release.yml` | 共通リリース：タグと `pyproject.toml` の version 一致を検査 → wheel/sdist を GitHub Release へ |
| `workflow-templates/` | Actions 画面の「New workflow」に出る組織テンプレート |
| `CONTRIBUTING.md` / `SECURITY.md` / `pull_request_template.md` / `ISSUE_TEMPLATE/` | 各リポに個別ファイルが無い場合の既定 |

## 版管理

再利用ワークフローはタグで固定して呼び出します（`@v1`）。

- 互換性のある修正: `v1.x.y` タグを打ち、`v1` タグを最新に付け替える
  （`git tag -f v1 && git push -f origin v1`）
- 呼び出し側の入力を壊す変更: `v2` を切り、各リポへは Dependabot（github-actions）経由で更新 PR を出す

## 各ツールリポからの呼び出し

```yaml
jobs:
  ci:
    uses: <your-org>/.github/.github/workflows/python-ci.yml@v1
    with:
      extra-apt-packages: "libreoffice-writer-nogui"   # 必要な場合のみ
    secrets: inherit   # 非公開の依存（devtools-common）を読む DEPS_TOKEN を渡す
```

### 設定が必要なもの

- 組織 Secrets に `DEPS_TOKEN`（`devtools-common` を含む非公開リポの **読み取り専用** fine-grained token）。
  公開リポジトリ構成なら不要です。
- Settings → Actions → General → 「Access」で、このリポのワークフローを組織内から呼べるようにする（非公開リポの場合）。
