#!/usr/bin/env python3
"""kb — AI プロンプトナレッジベースの管理 CLI.

サブコマンド:
  validate            front matter・本文構成・クリーンルーム文言・禁止パターン・カタログ鮮度を検査
  catalog [--check]   docs/prompts/index.md と README.md の収録表を front matter から再生成
  new ID SLUG TITLE   テンプレートから新規プロンプトを作成
  extract ID          プロンプト本文（コードブロックの中身）だけを標準出力へ
  dist                配布パッケージ（zip）を dist/ に作成

ルールはすべて kb.config.yaml（SSOT）から読む。依存は PyYAML のみ。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parent.parent

FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
# ```text / ````text のどちらも許容（本文中に ``` を含む場合は 4 連バッククォートで囲む）
FENCE_RE = re.compile(r"^(?P<fence>`{3,})text[ \t]*\r?\n(?P<body>.*?)^(?P=fence)[ \t]*$", re.S | re.M)
FILENAME_RE = re.compile(r"^(?P<id>\d{2})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

CATALOG_START = "<!-- catalog:start -->"
CATALOG_END = "<!-- catalog:end -->"
GENERATED_NOTE = "<!-- このファイルは scripts/kb.py catalog で自動生成されます。手で編集しないでください。 -->"

SCAN_SUFFIXES = {".md", ".yml", ".yaml", ".json", ".jsonc", ".txt", ".py", ".toml", ".cfg", ".ini"}
SCAN_EXCLUDE_DIRS = {".git", "site", "dist", "node_modules", ".venv", "venv", "__pycache__", ".cache"}


# ---------------------------------------------------------------------------
# モデル
# ---------------------------------------------------------------------------
@dataclass
class Prompt:
    path: Path
    meta: dict
    text: str
    body: str | None  # コードブロック内のプロンプト本文
    fence_count: int

    @property
    def id(self) -> str:
        return str(self.meta.get("id", ""))

    @property
    def title(self) -> str:
        return str(self.meta.get("title", ""))


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def add(self, where: Path | str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# 読み込み
# ---------------------------------------------------------------------------
def load_config(root: Path) -> dict:
    with (root / "kb.config.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def prompts_dir(root: Path, cfg: dict) -> Path:
    return root / cfg.get("prompts_dir", "docs/prompts")


def parse_prompt(path: Path) -> Prompt:
    text = path.read_text(encoding="utf-8")
    meta: dict = {}
    m = FM_RE.match(text)
    if m:
        loaded = yaml.safe_load(m.group(1))
        meta = loaded if isinstance(loaded, dict) else {}
    fences = list(FENCE_RE.finditer(text))
    body = fences[0].group("body").rstrip("\n") + "\n" if fences else None
    return Prompt(path=path, meta=meta, text=text, body=body, fence_count=len(fences))


def load_prompts(root: Path, cfg: dict) -> list[Prompt]:
    return [parse_prompt(p) for p in sorted(prompts_dir(root, cfg).glob("[0-9][0-9]-*.md"))]


def rel(root: Path, p: Path) -> str:
    try:
        return p.relative_to(root).as_posix()
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------
def validate_prompt(p: Prompt, cfg: dict, root: Path, report: Report) -> None:
    where = rel(root, p.path)
    fm_cfg = cfg["front_matter"]

    fm = FILENAME_RE.match(p.path.name)
    if not fm:
        report.add(where, "ファイル名は 'NN-kebab-case.md' 形式にしてください")

    if not p.meta:
        report.add(where, "front matter（--- で囲んだ YAML）がありません")
        return

    for key in fm_cfg["required"]:
        if key not in p.meta:
            report.add(where, f"front matter に必須キー '{key}' がありません")

    if fm and p.id != fm.group("id"):
        report.add(where, f"front matter の id '{p.id}' がファイル名の番号 '{fm.group('id')}' と一致しません")

    status = p.meta.get("status")
    if status is not None and status not in fm_cfg["statuses"]:
        report.add(where, f"status '{status}' は {fm_cfg['statuses']} のいずれかにしてください")

    category = p.meta.get("category")
    if category is not None and category not in cfg["categories"]:
        report.add(where, f"category '{category}' は {list(cfg['categories'])} のいずれかにしてください")

    version = p.meta.get("version")
    if version is not None and not SEMVER_RE.match(str(version)):
        report.add(where, f"version '{version}' は SemVer（例: 1.0.0）にしてください")

    updated = p.meta.get("updated")
    if updated is not None and not isinstance(updated, dt.date):
        report.add(where, f"updated '{updated}' は YYYY-MM-DD 形式にしてください")

    tags = p.meta.get("tags")
    if tags is not None and (not isinstance(tags, list) or not tags):
        report.add(where, "tags は 1 つ以上の要素を持つリストにしてください")

    deps = p.meta.get("depends_on")
    if deps is not None and not isinstance(deps, list):
        report.add(where, "depends_on はリストにしてください（無ければ []）")

    # 本文
    if p.fence_count == 0:
        report.add(where, "プロンプト本文のコードブロック（```text）がありません")
        return
    if p.fence_count > 1:
        report.add(where, f"プロンプト本文のコードブロック（```text）は 1 つにしてください（{p.fence_count} 個）")

    body = p.body or ""
    body_cfg = cfg["prompt_body"]
    for section in body_cfg["required_sections"]:
        if not re.search(rf"^{re.escape(section)}\s*$", body, re.M):
            report.add(where, f"本文に必須見出し '{section}' がありません")
    flat_body = re.sub(r"\s+", "", body)  # 改行で折り返された文言も検出する
    for phrase in body_cfg["required_phrases"]:
        if re.sub(r"\s+", "", phrase) not in flat_body:
            report.add(where, f"本文にクリーンルーム文言 '{phrase}' がありません")

    if not re.search(body_cfg["placeholder_pattern"], body):
        report.add(where, "本文に {{ }} プレースホルダがありません（利用者が埋める前提を明示してください）")
    if body.count("{{") != body.count("}}"):
        report.add(where, "プレースホルダの {{ と }} の数が一致しません")


def validate_cross(prompts: list[Prompt], root: Path, report: Report) -> None:
    ids: dict[str, Path] = {}
    for p in prompts:
        if p.id in ids:
            report.add(rel(root, p.path), f"id '{p.id}' が {rel(root, ids[p.id])} と重複しています")
        ids[p.id] = p.path
    for p in prompts:
        for dep in p.meta.get("depends_on") or []:
            dep = str(dep)
            if dep == p.id:
                report.add(rel(root, p.path), "depends_on に自分自身を含めないでください")
            elif dep not in ids:
                report.add(rel(root, p.path), f"depends_on の '{dep}' に該当するプロンプトがありません")


def iter_scan_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.relative_to(root).parts[:-1])
        if parts & SCAN_EXCLUDE_DIRS:
            continue
        yield path


def validate_repo_hygiene(root: Path, cfg: dict, report: Report) -> None:
    patterns = [(re.compile(f["pattern"], re.I), f["reason"]) for f in cfg.get("forbidden_patterns", [])]
    config_path = (root / "kb.config.yaml").resolve()
    for path in iter_scan_files(root):
        name = path.name
        if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            report.add(rel(root, path), ".env 系ファイルはコミットしないでください（.env.example を使う）")
            continue
        if path.resolve() == config_path or path.suffix.lower() not in SCAN_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for rx, reason in patterns:
                if rx.search(line):
                    report.add(f"{rel(root, path)}:{lineno}", f"禁止パターンに一致: {reason}")


def cmd_validate(root: Path) -> int:
    cfg = load_config(root)
    prompts = load_prompts(root, cfg)
    report = Report()
    if not prompts:
        report.add(rel(root, prompts_dir(root, cfg)), "プロンプトが 1 件もありません")
    for p in prompts:
        validate_prompt(p, cfg, root, report)
    validate_cross(prompts, root, report)
    validate_repo_hygiene(root, cfg, report)
    for target, expected in render_catalog_targets(root, cfg, prompts).items():
        if target.read_text(encoding="utf-8") != expected:
            report.add(rel(root, target), "収録表が古いです。`python scripts/kb.py catalog` を実行してください")

    if report.ok:
        print(f"OK: {len(prompts)} 件のプロンプトを検証しました")
        return 0
    for e in report.errors:
        print(f"ERROR {e}", file=sys.stderr)
    print(f"\n{len(report.errors)} 件のエラー", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# catalog
# ---------------------------------------------------------------------------
def catalog_table(prompts: list[Prompt], cfg: dict, link_prefix: str) -> str:
    lines = ["| # | ファイル | 対象 | 分類 | 状態 | 版 |", "|---|---|---|---|---|---|"]
    for p in prompts:
        cat = cfg["categories"].get(p.meta.get("category"), p.meta.get("category", ""))
        lines.append(
            f"| {p.id} | [{p.path.name}]({link_prefix}{p.path.name}) | {p.title} | {cat} "
            f"| {p.meta.get('status', '')} | {p.meta.get('version', '')} |"
        )
    return "\n".join(lines)


def dependency_mermaid(prompts: list[Prompt]) -> str:
    lines = ["```mermaid", "flowchart LR"]
    for p in prompts:
        label = p.title.replace('"', "'")
        lines.append(f'  P{p.id}["{p.id}. {label}"]')
    for p in prompts:
        for dep in p.meta.get("depends_on") or []:
            lines.append(f"  P{dep} --> P{p.id}")
    lines.append("```")
    return "\n".join(lines)


def render_index(prompts: list[Prompt], cfg: dict) -> str:
    return "\n".join(
        [
            "---",
            "title: プロンプト一覧",
            "description: 収録プロンプトのカタログ（自動生成）",
            "---",
            "",
            GENERATED_NOTE,
            "",
            "# プロンプト一覧",
            "",
            "各プロンプトの **コードブロックの本文** を AI エージェントに投入し、`{{ }}` を自分の実態で埋めて使います。",
            "使い方の詳細は [使い方](../guides/how-to-use.md) を参照してください。",
            "",
            "## 収録",
            "",
            catalog_table(prompts, cfg, ""),
            "",
            "## 推奨順序（依存関係）",
            "",
            "矢印の元を先に実施すると、後続プロンプトの前提が揃います。",
            "",
            dependency_mermaid(prompts),
            "",
        ]
    )


def render_readme(readme_text: str, prompts: list[Prompt], cfg: dict) -> str:
    start = readme_text.find(CATALOG_START)
    end = readme_text.find(CATALOG_END)
    if start == -1 or end == -1 or end < start:
        return readme_text
    block = f"{CATALOG_START}\n{catalog_table(prompts, cfg, cfg.get('prompts_dir', 'docs/prompts') + '/')}\n"
    return readme_text[:start] + block + readme_text[end:]


def render_catalog_targets(root: Path, cfg: dict, prompts: list[Prompt]) -> dict[Path, str]:
    targets = {prompts_dir(root, cfg) / "index.md": render_index(prompts, cfg)}
    readme = root / "README.md"
    if readme.exists():
        targets[readme] = render_readme(readme.read_text(encoding="utf-8"), prompts, cfg)
    return targets


def cmd_catalog(root: Path, check: bool) -> int:
    cfg = load_config(root)
    prompts = load_prompts(root, cfg)
    stale = []
    for target, content in render_catalog_targets(root, cfg, prompts).items():
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == content:
            continue
        stale.append(target)
        if not check:
            target.write_text(content, encoding="utf-8", newline="\n")
            print(f"updated: {rel(root, target)}")
    if check and stale:
        for t in stale:
            print(f"STALE {rel(root, t)}", file=sys.stderr)
        return 1
    if not stale:
        print("catalog is up to date")
    return 0


# ---------------------------------------------------------------------------
# new / extract
# ---------------------------------------------------------------------------
def cmd_new(root: Path, pid: str, slug: str, title: str, category: str) -> int:
    cfg = load_config(root)
    if not re.fullmatch(r"\d{2}", pid):
        print("ID は 2 桁の数字にしてください（例: 09）", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        print("SLUG は半角小文字ケバブケースにしてください（例: api-diff-tool）", file=sys.stderr)
        return 2
    if category not in cfg["categories"]:
        print(f"category は {list(cfg['categories'])} のいずれかにしてください", file=sys.stderr)
        return 2
    existing = {p.id for p in load_prompts(root, cfg)}
    if pid in existing:
        print(f"ID {pid} は既に使われています", file=sys.stderr)
        return 2

    template = (root / "docs" / "templates" / "prompt-template.md").read_text(encoding="utf-8")
    content = (
        template.replace("__ID__", pid)
        .replace("__TITLE__", title)
        .replace("__CATEGORY__", category)
        .replace("__DATE__", dt.date.today().isoformat())
    )
    dest = prompts_dir(root, cfg) / f"{pid}-{slug}.md"
    dest.write_text(content, encoding="utf-8", newline="\n")
    print(f"created: {rel(root, dest)}")
    print("次の手順: 本文を書く → mkdocs.yml の nav に追加 → python scripts/kb.py catalog → validate")
    return 0


def find_prompt(root: Path, cfg: dict, pid: str) -> Prompt | None:
    return next((p for p in load_prompts(root, cfg) if p.id == pid.zfill(2)), None)


def cmd_extract(root: Path, pid: str) -> int:
    cfg = load_config(root)
    p = find_prompt(root, cfg, pid)
    if p is None or p.body is None:
        print(f"ID {pid} のプロンプト本文が見つかりません", file=sys.stderr)
        return 1
    sys.stdout.write(p.body)
    return 0


# ---------------------------------------------------------------------------
# dist
# ---------------------------------------------------------------------------
def _jsonable(v):
    return v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v


def copilot_prompt_file(p: Prompt) -> str:
    desc = str(p.meta.get("description", "")).replace('"', "'")
    return f'---\ndescription: "{desc}"\n---\n\n{p.body}'


def build_dist(root: Path, out_dir: Path | None = None) -> Path:
    cfg = load_config(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    allowed = set(cfg["front_matter"]["distributable_statuses"])
    prompts = [p for p in load_prompts(root, cfg) if p.meta.get("status") in allowed and p.body]
    name = f"{cfg['name']}-{version}"
    out_dir = out_dir or (root / "dist")
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}.zip"

    catalog = {
        "name": cfg["name"],
        "version": version,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "prompts": [
            {
                **{k: _jsonable(v) for k, v in p.meta.items()},
                "files": {
                    "markdown": f"prompts/{p.path.name}",
                    "plain": f"plain/{p.path.stem}.txt",
                    "copilot": f"copilot/.github/prompts/{p.path.stem}.prompt.md",
                },
            }
            for p in prompts
        ],
    }

    dist_readme = "\n".join(
        [
            f"# {cfg['name']} {version}",
            "",
            "AI 活用プロンプト集の配布パッケージです。",
            "",
            "## 中身",
            "",
            "| パス | 用途 |",
            "|---|---|",
            "| `prompts/` | 解説つきの完全版 Markdown（front matter 付き） |",
            "| `plain/` | プロンプト本文のみ。AI チャットへそのまま貼り付け |",
            "| `copilot/.github/prompts/` | VS Code / GitHub Copilot の再利用プロンプト形式。対象リポの `.github/prompts/` へコピー |",
            "| `catalog.json` | メタデータ一覧（ツール連携用） |",
            "",
            "## 使い方",
            "",
            "1. 空のリポジトリ（または新規フォルダ）を用意する。",
            "2. 目的に合うプロンプトの本文を AI エージェント（例: Copilot Agent Mode）へ投入する。",
            "3. `{{ }}` プレースホルダを**自社/自分の実態**で埋める。固有名はプロンプト集側に書かない。",
            "4. 生成物を必ず確認・承認してから次のプロンプトへ進む（工程境界で人がレビュー）。",
            "",
            "## 収録",
            "",
            catalog_table(prompts, cfg, "prompts/"),
            "",
            "## 原則",
            "",
            "- 固有名を入れない / 「差異なき複製」を目的にしない / 権利・許可の書面は保管 / 機密を書かない",
            "",
        ]
    )

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{name}/README.md", dist_readme)
        z.writestr(f"{name}/catalog.json", json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
        principles = root / "docs" / "guides" / "principles.md"
        if principles.exists():
            z.write(principles, f"{name}/PRINCIPLES.md")
        for p in prompts:
            z.writestr(f"{name}/prompts/{p.path.name}", p.text)
            z.writestr(f"{name}/plain/{p.path.stem}.txt", p.body)
            z.writestr(f"{name}/copilot/.github/prompts/{p.path.stem}.prompt.md", copilot_prompt_file(p))
    return zip_path


def cmd_dist(root: Path) -> int:
    rc = cmd_validate(root)
    if rc != 0:
        print("検証エラーがあるため配布パッケージを作成しません", file=sys.stderr)
        return rc
    zip_path = build_dist(root)
    print(f"built: {rel(root, zip_path)}")
    return 0


# ---------------------------------------------------------------------------
# entry
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # Windows コンソールでの文字化け対策
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(prog="kb", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="リポジトリのルート（既定: このスクリプトの親）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="全体を検証")
    c = sub.add_parser("catalog", help="収録表を再生成")
    c.add_argument("--check", action="store_true", help="書き換えずに差分の有無だけ判定（CI 用）")
    n = sub.add_parser("new", help="新規プロンプトを作成")
    n.add_argument("id")
    n.add_argument("slug")
    n.add_argument("title")
    n.add_argument("--category", default="tools")
    e = sub.add_parser("extract", help="本文だけを出力")
    e.add_argument("id")
    sub.add_parser("dist", help="配布 zip を作成")

    args = ap.parse_args(argv)
    root = args.root.resolve()
    if args.cmd == "validate":
        return cmd_validate(root)
    if args.cmd == "catalog":
        return cmd_catalog(root, args.check)
    if args.cmd == "new":
        return cmd_new(root, args.id, args.slug, args.title, args.category)
    if args.cmd == "extract":
        return cmd_extract(root, args.id)
    if args.cmd == "dist":
        return cmd_dist(root)
    return 2


if __name__ == "__main__":
    sys.exit(main())
