#!/usr/bin/env python3
"""マルチレポを「1 ツール = 1 リポ」のままローカルに並べて扱うためのスクリプト（Python 3.11+、標準ライブラリのみ）.

レイアウト（このリポジトリの親フォルダに兄弟として並べる。フォルダ共有・サブモジュールは使わない）:

    devtools/                 ← 親フォルダ（リポジトリではない）
    ├── devtools-workspace/   ← このリポジトリ
    ├── devtools-common/
    ├── doc-to-markdown/
    └── ...

サブコマンド:
    clone     マニフェスト（repos.yaml）のリポジトリのうち、未取得のものを clone
    pull      取得済みのリポジトリを git pull --ff-only
    status    各リポジトリのブランチ・未コミット変更・最新タグ
    install   仮想環境を作り、Python リポジトリを editable で入れる（devtools-common はローカル版を使う）
    list      ツール一覧（Markdown の表）

例:
    python scripts/bootstrap.py clone --org my-org
    python scripts/bootstrap.py install            # ../.venv を作成して全ツールを editable インストール
    python scripts/bootstrap.py status
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
import venv
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
MANIFEST = HERE / "repos.yaml"
COMMON = "devtools-common"


# ---------------------------------------------------------------------------
# マニフェスト（依存を増やさないため、repos.yaml の単純なサブセットだけを読む）
# ---------------------------------------------------------------------------
@dataclass
class Repo:
    name: str
    role: str = ""
    description: str = ""
    python: bool = False
    cli: str = ""
    prompt: str = ""


def _scalar(v: str) -> str | bool:
    v = v.strip()
    if v in ("true", "false"):
        return v == "true"
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def load_manifest(path: Path = MANIFEST) -> tuple[dict[str, str], list[Repo]]:
    top: dict[str, str] = {}
    repos: list[Repo] = []
    cur: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip():
            continue
        if m := re.match(r"^(\w+):\s*(.*)$", line):
            if m.group(2):
                top[m.group(1)] = str(_scalar(m.group(2)))
            continue
        if m := re.match(r"^\s+-\s+(\w+):\s*(.*)$", line):
            cur = {m.group(1): _scalar(m.group(2))}
            repos.append(cur)  # type: ignore[arg-type]
            continue
        if (m := re.match(r"^\s+(\w+):\s*(.*)$", line)) and cur is not None:
            cur[m.group(1)] = _scalar(m.group(2))
    return top, [Repo(**r) for r in repos]  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
def git(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed in {cwd}: {r.stderr.strip()}")
    return r.stdout.strip()


def cmd_clone(root: Path, top: dict[str, str], repos: list[Repo], org: str | None) -> int:
    org = org or top.get("org", "")
    if not org or org.startswith("<"):
        raise SystemExit("--org を指定するか、repos.yaml の org を設定してください")
    host = top.get("host", "https://github.com").rstrip("/")
    for r in repos:
        dest = root / r.name
        if dest.exists():
            print(f"skip   {r.name}（取得済み）")
            continue
        print(f"clone  {r.name}")
        git(["clone", f"{host}/{org}/{r.name}.git", str(dest)])
    return 0


def cmd_pull(root: Path, repos: list[Repo]) -> int:
    for r in repos:
        d = root / r.name
        if (d / ".git").exists():
            print(f"pull   {r.name}: {git(['pull', '--ff-only'], cwd=d, check=False) or 'ok'}")
    return 0


def cmd_status(root: Path, repos: list[Repo]) -> int:
    print(f"{'repo':22} {'branch':16} {'changes':8} latest-tag")
    for r in repos:
        d = root / r.name
        if not (d / ".git").exists():
            print(f"{r.name:22} {'(未取得)':16}")
            continue
        branch = git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=d, check=False) or "-"
        dirty = len([ln for ln in git(["status", "--porcelain"], cwd=d, check=False).splitlines() if ln])
        tag = git(["describe", "--tags", "--abbrev=0"], cwd=d, check=False) or "-"
        print(f"{r.name:22} {branch:16} {dirty:<8} {tag}")
    return 0


def install_plan(root: Path, repos: list[Repo], extras: str = "dev") -> list[list[str]]:
    """pip の引数リストを返す。ツールは --no-deps で入れ、Git タグ依存の devtools-common をローカル版で代替する."""
    plan: list[list[str]] = []
    py = [r for r in repos if r.python and (root / r.name / "pyproject.toml").is_file()]
    common = next((r for r in py if r.name == COMMON), None)
    if common:
        plan.append(["install", "-e", f"{root / common.name}[{extras}]"])
    third_party: list[str] = []
    for r in py:
        if r.name == COMMON:
            continue
        project = tomllib.loads((root / r.name / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        deps = project.get("dependencies", []) + project.get("optional-dependencies", {}).get(extras, [])
        third_party += [d for d in deps if not d.replace("_", "-").startswith(COMMON)]
        plan.append(["install", "--no-deps", "-e", str(root / r.name)])
    if third_party:
        plan.insert(1 if common else 0, ["install", *sorted(set(third_party))])
    return plan


def cmd_install(root: Path, repos: list[Repo], venv_dir: Path | None, dry_run: bool) -> int:
    python = sys.executable
    if venv_dir is not None:
        if not dry_run and not venv_dir.exists():
            print(f"venv   {venv_dir}")
            venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = str(venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    for args in install_plan(root, repos):
        cmd = [python, "-m", "pip", *args]
        print("$", " ".join(cmd))
        if not dry_run:
            subprocess.run(cmd, check=True)
    if venv_dir is not None and not dry_run:
        activate = venv_dir / ("Scripts\\activate" if sys.platform == "win32" else "bin/activate")
        print(f"\n完了。有効化: {activate}")
    return 0


def cmd_list(repos: list[Repo]) -> int:
    print("| リポジトリ | 役割 | CLI | 元プロンプト | 説明 |")
    print("|---|---|---|---|---|")
    for r in repos:
        print(f"| {r.name} | {r.role} | {f'`{r.cli}`' if r.cli else ''} | {r.prompt} | {r.description} |")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--root",
        type=Path,
        default=HERE.parent,
        help="リポジトリを並べる親フォルダ（既定: このリポの親）",
    )
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clone")
    c.add_argument("--org")
    sub.add_parser("pull")
    sub.add_parser("status")
    i = sub.add_parser("install")
    i.add_argument("--venv", type=Path, help="仮想環境の場所（既定: <root>/.venv）")
    i.add_argument("--no-venv", action="store_true", help="今の Python 環境に入れる")
    i.add_argument("--dry-run", action="store_true")
    sub.add_parser("list")
    args = ap.parse_args(argv)

    top, repos = load_manifest(args.manifest)
    root = args.root.resolve()
    if args.cmd == "clone":
        return cmd_clone(root, top, repos, args.org)
    if args.cmd == "pull":
        return cmd_pull(root, repos)
    if args.cmd == "status":
        return cmd_status(root, repos)
    if args.cmd == "install":
        venv_dir = None if args.no_venv else (args.venv or root / ".venv")
        return cmd_install(root, repos, venv_dir, args.dry_run)
    return cmd_list(repos)


if __name__ == "__main__":
    sys.exit(main())
