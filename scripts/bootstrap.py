#!/usr/bin/env python3
"""マルチレポを「1 ツール = 1 リポ」のままローカルに並べて扱うためのスクリプト（Python 3.12+、標準ライブラリのみ）.

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
    install   仮想環境を作り、Python のツールを入れる（各ツールが固定した devtools-common を使う）
              --dev を付けると、devtools-common もローカルの checkout を editable で入れる（開発者向け）
    list      ツール一覧（Markdown の表）
    check-python  取得済みの Python パッケージの requires-python と、setup が求める Python の版（3.12 以上）が
              合っているかを確かめる（合っていなければ 1）

例:
    python scripts/bootstrap.py clone --org my-org
    python scripts/bootstrap.py install            # ../.venv に全ツールを入れる（devtools-common は各ツールの固定 SHA）
    python scripts/bootstrap.py install --dev      # 開発者向け: ローカルの devtools-common で置き換えて入れる
    python scripts/bootstrap.py status
    python scripts/bootstrap.py --only devtools-common,doc-to-markdown clone   # 一部のリポジトリだけ扱う
"""

from __future__ import annotations

import sys

# tomllib を import する前に版を確かめ、古い Python ではトレースバックではなく理由を出して終わる
from python_version import require  # 同じ scripts フォルダ（必要な版の定義はここだけ）

require()

import argparse  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tomllib  # noqa: E402
import venv  # noqa: E402
from dataclasses import dataclass  # noqa: E402
from pathlib import Path  # noqa: E402

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
    ref: str = ""  # clone / pull で取り出すブランチ・タグ・コミット SHA（空なら既定ブランチ）
    # Python のパッケージがサブフォルダにあるときの相対パス（カンマ区切り。空ならリポジトリ直下）
    packages: str = ""

    def package_dirs(self, root: Path) -> list[Path]:
        """pyproject.toml がある（取得済みの）パッケージのフォルダ."""
        rels = [s.strip() for s in self.packages.split(",") if s.strip()] or ["."]
        dirs = [root / self.name / rel if rel != "." else root / self.name for rel in rels]
        return [d for d in dirs if (d / "pyproject.toml").is_file()]


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
        print(f"clone  {r.name}" + (f" @ {r.ref}" if r.ref else ""))
        git(["clone", f"{host}/{org}/{r.name}.git", str(dest)])
        if r.ref:
            git(["checkout", "-q", r.ref], cwd=dest)
    return 0


def cmd_pull(root: Path, repos: list[Repo]) -> int:
    """取得済みのリポジトリを fast-forward で最新にする。手元に変更があるなどで進められないものは知らせて飛ばす."""
    failed = 0
    for r in repos:
        d = root / r.name
        if not (d / ".git").exists():
            continue
        if r.ref:
            p = _update_to_ref(d, r.ref)
            if p.returncode == 0:
                print(f"pull   {r.name}: {r.ref}")
                continue
            failed += 1
            print(f"pull   {r.name}: {r.ref} にできませんでした（手元の変更を確かめてください）: {p.stderr.strip()}")
            continue
        p = subprocess.run(["git", "pull", "--ff-only"], cwd=d, capture_output=True, text=True, check=False)
        if p.returncode == 0:
            print(f"pull   {r.name}: {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else 'ok'}")
        else:
            failed += 1
            print(f"pull   {r.name}: 最新にできませんでした（手元の変更を確かめてください）: {p.stderr.strip()}")
    return 1 if failed else 0


def _update_to_ref(d: Path, ref: str) -> subprocess.CompletedProcess[str]:
    """マニフェストで ref を指定したリポジトリを、その ref にそろえる（ブランチなら fast-forward まで）."""
    for args in (["fetch", "-q", "--tags", "origin"], ["checkout", "-q", ref]):
        p = subprocess.run(["git", *args], cwd=d, capture_output=True, text=True, check=False)
        if p.returncode != 0:
            return p
    if git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=d, check=False) not in ("", "HEAD"):
        p = subprocess.run(["git", "pull", "--ff-only"], cwd=d, capture_output=True, text=True, check=False)
    return p


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


def _dep_name(dep: str) -> str:
    """依存の指定（`name[extra] @ url` / `name>=1` など）から正規化したパッケージ名を取り出す."""
    return re.split(r"[\s\[@<>=!~;]", dep.strip(), maxsplit=1)[0].replace("_", "-").lower()


def _is_common(dep: str) -> bool:
    return _dep_name(dep) == COMMON


def _project(pkg_dir: Path) -> dict:
    return tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})


def _pinned_by_url(deps: list[str]) -> set[str]:
    """`name @ git+…` のように URL で固定した依存の名前."""
    return {_dep_name(d) for d in deps if re.match(r"^[\w.\-\[\], ]+@\s*\S", d.split(";", 1)[0].strip())}


def install_plan(
    root: Path, repos: list[Repo], dev: bool = False, extras: str = "dev", notes: list[str] | None = None
) -> list[list[str]]:
    """pip の引数リストを返す.

    既定（利用者向け）: ツールを通常の依存解決で入れる。各ツールが `devtools-common @ git+…@<SHA>` で固定した版を
    pip がそのまま入れるので、手元の devtools-common の checkout（どのコミットか分からない）は使わない。
    同じように、ほかのツールが URL で固定しているパッケージ（review-platform が固定する auto-review など）も
    手元の checkout は入れない（同じ名前を 2 か所から入れると pip が衝突で止まるため）。
    ツールを 1 回の pip にまとめるのは、ツールごとに固定 SHA が食い違ったときに pip に衝突として止めてもらうため。

    dev=True（開発者向け）: devtools-common をローカルの checkout から editable で入れ、ツールは --no-deps で入れて
    Git の固定依存をローカル版で置き換える。共有ライブラリとツールを同時に変更して試すとき用。

    notes にリストを渡すと、利用者に知らせること（手元の checkout を使わないパッケージ）を足す（表示は呼び出し側）。
    """
    plan: list[list[str]] = []
    pkgs: list[tuple[Path, dict]] = [(d, _project(d)) for r in repos if r.python for d in r.package_dirs(root)]
    names = {str(p.get("name", d.name)).replace("_", "-").lower() for d, p in pkgs}
    common = next((d for d, p in pkgs if str(p.get("name", "")).lower() == COMMON), None)
    if not dev:
        pinned: set[str] = set()
        for _, p in pkgs:
            pinned |= _pinned_by_url(p.get("dependencies", []))
        if len(pkgs) > 1:
            pinned.add(COMMON)  # ツールと一緒なら、devtools-common はツールが固定した版だけを入れる（従来どおり）
        chosen = [d for d, p in pkgs if str(p.get("name", d.name)).replace("_", "-").lower() not in pinned]
        if notes is not None:
            notes += [f"{p.get('name', d.name)}: ほかのツールが固定した版を入れる" for d, p in pkgs if d not in chosen]
        if chosen:
            args = ["install"]
            for d in chosen:
                args += ["-e", str(d)]
            plan.append(args)
        return plan
    if common:
        plan.append(["install", "-e", f"{common}[{extras}]"])
    third_party: list[str] = []
    for d, project in pkgs:
        if d == common:
            continue
        deps = project.get("dependencies", []) + project.get("optional-dependencies", {}).get(extras, [])
        # 手元にあるパッケージ（devtools-common・auto-review など）は Git の固定ではなくローカルの checkout を使う
        third_party += [x for x in deps if _dep_name(x) not in names]
        plan.append(["install", "--no-deps", "-e", str(d)])
    if third_party:
        plan.insert(1 if common else 0, ["install", *sorted(set(third_party))])
    return plan


# ---------------------------------------------------------------------------
# requires-python と setup が求める版（python_version.MIN_VERSION）の整合
# ---------------------------------------------------------------------------
def _ver(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


def requires_python_lower_bound(spec: str) -> tuple[int, ...]:
    """requires-python（`>=3.12` / `>=3.10,<4` / `~=3.11`）の下限. 下限が無ければ ()."""
    lows = [_ver(v) for op, v in re.findall(r"(>=|~=|==|>)\s*([\d.]+)", spec)]
    return max(lows) if lows else ()


def accepts(spec: str, version: tuple[int, ...]) -> bool:
    """requires-python が version（major, minor の組）を受け付けるか（major.minor で比べる）."""
    v = version[:2]
    for op, raw in re.findall(r"(>=|<=|~=|==|!=|>|<)\s*([\d.*]+)", spec):
        w = _ver(raw)[:2]
        ok = {
            ">=": v >= w,
            "~=": v >= w,
            ">": v > w or (len(_ver(raw)) > 2 and v >= w),
            "<": v < w,
            "<=": v <= w,
            "==": v == w,
            "!=": v != w,
        }[op]
        if not ok:
            return False
    return True


def check_python(root: Path, repos: list[Repo], minimum: tuple[int, ...]) -> list[str]:
    """取得済みのパッケージの requires-python と、setup が求める最低版 minimum のずれ（無ければ空）.

    - minimum を受け付けないパッケージがあれば誤り（setup が通しても pip がそのツールを入れられない）
    - minimum が、パッケージの下限のうち最も高いものと一致しなければ誤り
      （低ければ setup が古い Python を「OK」と言ってしまい、高ければ不要に新しい Python を求めてしまう）
    """
    problems: list[str] = []
    bounds: list[tuple[tuple[int, ...], str]] = []
    for r in repos:
        if not r.python:
            continue
        for d in r.package_dirs(root):
            spec = str(_project(d).get("requires-python", ""))
            rel = d.relative_to(root / r.name).as_posix()
            label = r.name if rel == "." else f"{r.name}/{rel}"
            if not spec:
                problems.append(f"{label}: requires-python がありません")
                continue
            if not accepts(spec, minimum):
                want = ".".join(map(str, minimum))
                problems.append(f"{label}: requires-python {spec!r} が Python {want} を受け付けません")
            bounds.append((requires_python_lower_bound(spec), label))
    if bounds:
        highest, who = max(bounds)
        if highest[:2] != tuple(minimum[:2]):
            problems.append(
                f"setup の最低版 {'.'.join(map(str, minimum))} が、requires-python の下限のうち最も高い "
                f"{'.'.join(map(str, highest))}（{who}）と合いません（scripts/python_version.py の MIN_VERSION を直す）"
            )
    return problems


def cmd_check_python(root: Path, repos: list[Repo]) -> int:
    from python_version import MIN_VERSION

    checked = [d for r in repos if r.python for d in r.package_dirs(root)]
    problems = check_python(root, repos, MIN_VERSION)
    for p in problems:
        print(f"NG     {p}", file=sys.stderr)
    if not problems:
        want = ".".join(map(str, MIN_VERSION))
        print(f"ok     {len(checked)} 個のパッケージの requires-python が Python {want} 以上と合っています")
    return 1 if problems else 0


def cmd_install(root: Path, repos: list[Repo], venv_dir: Path | None, dry_run: bool, dev: bool = False) -> int:
    python = sys.executable
    if venv_dir is not None:
        if not dry_run and not venv_dir.exists():
            print(f"venv   {venv_dir}")
            venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = str(venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    if dev:
        print("mode   開発者向け（--dev）: devtools-common はローカルの checkout を editable で使います")
    notes: list[str] = []
    plan = install_plan(root, repos, dev=dev, notes=notes)
    for n in notes:
        print(f"note   {n}（手元の checkout は使わない）")
    for args in plan:
        cmd = [python, "-m", "pip", *args]
        print("$", " ".join(cmd))
        if not dry_run:
            subprocess.run(cmd, check=True)
    if venv_dir is not None and not dry_run:
        activate = venv_dir / ("Scripts\\activate" if sys.platform == "win32" else "bin/activate")
        print(f"\n完了。有効化: {activate}")
    return 0


def select_repos(repos: list[Repo], only: str | None) -> list[Repo]:
    """--only（カンマ区切りのリポジトリ名）で絞り込む。マニフェストにない名前は誤りとして止める."""
    if not only:
        return repos
    names = [n.strip() for n in only.split(",") if n.strip()]
    known = {r.name for r in repos}
    unknown = [n for n in names if n not in known]
    if unknown:
        print(f"repos.yaml にないリポジトリです: {', '.join(unknown)}", file=sys.stderr)
        raise SystemExit(2)
    return [r for r in repos if r.name in names]


def cmd_list(repos: list[Repo]) -> int:
    print("| リポジトリ | 役割 | CLI | 説明 |")
    print("|---|---|---|---|")
    for r in repos:
        print(f"| {r.name} | {r.role} | {f'`{r.cli}`' if r.cli else ''} | {r.description} |")
    return 0


def _safe_stdio() -> None:
    """出力先の文字コード（CI の cp1252 など）で日本語を書けなくても止まらないようにする."""
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    _safe_stdio()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--root",
        type=Path,
        default=HERE.parent,
        help="リポジトリを並べる親フォルダ（既定: このリポの親）",
    )
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--only", help="扱うリポジトリをカンマ区切りで指定（既定: repos.yaml の全部）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clone")
    c.add_argument("--org")
    sub.add_parser("pull")
    sub.add_parser("status")
    i = sub.add_parser("install")
    i.add_argument("--venv", type=Path, help="仮想環境の場所（既定: <root>/.venv）")
    i.add_argument("--no-venv", action="store_true", help="今の Python 環境に入れる")
    i.add_argument("--dry-run", action="store_true")
    i.add_argument(
        "--dev",
        action="store_true",
        help="開発者向け: 各ツールの devtools-common の固定を外し、ローカルの checkout を editable で入れる",
    )
    sub.add_parser("list")
    sub.add_parser("check-python", help="requires-python と setup が求める Python の版が合っているか")
    args = ap.parse_args(argv)

    top, repos = load_manifest(args.manifest)
    repos = select_repos(repos, args.only)
    root = args.root.resolve()
    if args.cmd == "clone":
        return cmd_clone(root, top, repos, args.org)
    if args.cmd == "pull":
        return cmd_pull(root, repos)
    if args.cmd == "status":
        return cmd_status(root, repos)
    if args.cmd == "install":
        venv_dir = None if args.no_venv else (args.venv or root / ".venv")
        return cmd_install(root, repos, venv_dir, args.dry_run, dev=args.dev)
    if args.cmd == "check-python":
        return cmd_check_python(root, repos)
    return cmd_list(repos)


if __name__ == "__main__":
    sys.exit(main())
