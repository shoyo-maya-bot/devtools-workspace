#!/usr/bin/env python3
"""マルチレポを「1 ツール = 1 リポ」のままローカルに並べて扱うためのスクリプト（Python 3.12+、標準ライブラリのみ）.

レイアウト（このリポジトリの親フォルダに兄弟として並べる。フォルダ共有・サブモジュールは使わない）:

    devtools/                 ← 親フォルダ（リポジトリではない）
    ├── devtools-workspace/   ← このリポジトリ
    ├── devtools-common/
    ├── doc-to-markdown/
    └── ...

サブコマンド:
    clone     マニフェスト（repos.yaml）のリポジトリのうち、未取得のものを clone（空のフォルダにも clone する。
              中身があって Git のリポジトリでないフォルダは知らせて 1）
    pull      取得済みのリポジトリを git pull --ff-only
    status    各リポジトリのブランチ・未コミット変更・最新タグ
    install   仮想環境を作り、Python のツールを入れる（各ツールが固定した devtools-common を使う）。
              未取得のリポジトリは知らせて飛ばす。フォルダはあるのに pyproject.toml が無いもの
              （空のフォルダなど）があれば、黙って外さずに 1
              --dev を付けると、devtools-common もローカルの checkout を editable で入れる（開発者向け）
    list      ツール一覧（Markdown の表）
    check-python  取得済みの Python パッケージの requires-python と、setup が求める Python の版（3.12 以上）が
              合っているかを確かめる（合っていなければ 1）
    check-pins    取得済みの Python パッケージが URL（git+…@<SHA>）で固定した devtools-common などの版が、
              ツールどうしで食い違っていないかを確かめる（食い違えば、どのツールの固定をそろえるかを表示して 1）。
              setup は一括インストールの前にこれを流す

例:
    python scripts/bootstrap.py clone --org my-org
    python scripts/bootstrap.py install            # ../.venv に全ツールを入れる（devtools-common は各ツールの固定 SHA）
    python scripts/bootstrap.py install --dev      # 開発者向け: ローカルの devtools-common で置き換えて入れる
    python scripts/bootstrap.py status
    python scripts/bootstrap.py check-pins     # 各ツールの devtools-common の固定 SHA がそろっているか
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


class ManifestError(ValueError):
    """マニフェスト（repos.yaml）を読めない（このスクリプトが読むサブセットの外の書き方・誤り）."""


_FIELDS = set(Repo.__dataclass_fields__)


def _strip_comment(raw: str) -> str:
    """行末コメント（空白の後の `#`）を除く。値が引用符（' / "）で始まるときは、閉じる引用符までを値として残す.

    YAML と同じく、引用符が意味を持つのは値の先頭だけ（`a 'b' # c` の `'` はただの文字）。
    引用符が閉じていない・閉じた後にコメント以外が続く行は誤り（ValueError）。
    """
    m = re.match(r"^(\s*(?:-\s+)?\w+:\s*)(['\"])", raw)
    if m:
        quote = m.group(2)
        end = raw.find(quote, m.end())
        if end < 0:
            raise ValueError(f"引用符 {quote} が閉じていません")
        rest = raw[end + 1 :]
        if rest.strip() and not re.match(r"^\s+#", rest):
            raise ValueError(f"閉じた引用符の後に余計な文字があります: {rest.strip()}")
        return raw[: end + 1]
    if raw.lstrip().startswith("#"):
        return ""
    m = re.search(r"\s#", raw)
    return (raw[: m.start()] if m else raw).rstrip()


def _scalar(v: str) -> str | bool:
    v = v.strip()
    if v in ("true", "false"):
        return v == "true"
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def load_manifest(path: Path = MANIFEST) -> tuple[dict[str, str], list[Repo]]:
    """repos.yaml の単純なサブセット（`key: value`、`repos:` の下の `- name: …` と字下げした `key: value`）を読む.

    行末の ` # コメント` は除く（引用符の中の `#` は残す）。読めない行・知らない項目・name の無い項目・
    重複した name は、黙って読み飛ばさず ManifestError（ファイル名と行番号付き）にする。
    """
    top: dict[str, str] = {}
    repos: list[dict] = []
    cur: dict | None = None
    for no, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):

        def bad(msg: str, no: int = no) -> ManifestError:
            return ManifestError(f"{path}:{no}: {msg}")

        try:
            line = _strip_comment(raw)
            if not line.strip():
                continue
            if m := re.match(r"^(\w+):\s*(.*)$", line):
                if m.group(2):
                    top[m.group(1)] = str(_scalar(m.group(2)))
                cur = None
                continue
            if m := re.match(r"^\s+-\s+(\w+):\s*(.*)$", line):
                cur = {m.group(1): _scalar(m.group(2)), "_line": no}
                repos.append(cur)
            elif m := re.match(r"^\s+(\w+):\s*(.*)$", line):
                if cur is None:
                    raise ValueError("リポジトリの項目（`  - name: …`）の外にあります")
                if m.group(1) in cur:
                    raise ValueError(f"{m.group(1)} が 2 回あります")
                cur[m.group(1)] = _scalar(m.group(2))
            else:
                raise ValueError(f"読めない行です: {raw.strip()}")
            if m.group(1) not in _FIELDS:
                raise ValueError(f"知らない項目です: {m.group(1)}（使えるのは {', '.join(sorted(_FIELDS))}）")
        except ValueError as e:
            raise bad(str(e)) from None
    result: list[Repo] = []
    seen: set[str] = set()
    for r in repos:
        no = r.pop("_line")
        name = r.get("name")
        if not isinstance(name, str) or not name:
            raise ManifestError(f"{path}:{no}: name がありません")
        if name in seen:
            raise ManifestError(f"{path}:{no}: {name} が 2 回あります")
        if not isinstance(r.get("python", False), bool):
            raise ManifestError(f"{path}:{no}: python は true / false で書きます")
        seen.add(name)
        result.append(Repo(**r))
    return top, result


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
    failed = 0
    for r in repos:
        dest = root / r.name
        if (dest / ".git").exists():
            print(f"skip   {r.name}（取得済み" + ("。ref には pull でそろえる）" if r.ref else "）"))
            continue
        if dest.exists() and not _is_empty_dir(dest):
            # 中身のあるフォルダを「取得済み」とみなすと、install が黙ってそのリポジトリを外してしまう
            failed += 1
            print(
                f"NG     {r.name}: {dest} はありますが Git のリポジトリではありません"
                "（中身を確かめて、別の場所へ移すか消してから、もう一度実行してください）",
                file=sys.stderr,
            )
            continue
        # 空のフォルダ（作っただけ・clone の途中で止まったもの）には、そのまま clone する
        into_empty = "（空のフォルダに取得）" if dest.exists() else ""
        print(f"clone  {r.name}" + (f" @ {r.ref}" if r.ref else "") + into_empty)
        git(["clone", f"{host}/{org}/{r.name}.git", str(dest)])
        if r.ref:
            p = subprocess.run(["git", "checkout", "-q", r.ref], cwd=dest, capture_output=True, text=True, check=False)
            if p.returncode != 0:
                # clone は残る（次の setup では skip される）が、install は HEAD が ref と違うリポジトリがあれば止まる
                raise SystemExit(f"clone  {r.name}: {r.ref} を取り出せませんでした: {p.stderr.strip()}")
    return 1 if failed else 0


def _is_empty_dir(d: Path) -> bool:
    return d.is_dir() and next(d.iterdir(), None) is None


def missing_packages(root: Path, repos: list[Repo]) -> tuple[list[str], list[str]]:
    """Python のリポジトリのうち、入れられないもの: (フォルダはあるが pyproject.toml が無いもの, 未取得のもの).

    package_dirs() は pyproject.toml のあるフォルダだけを返すので、空のフォルダや別物のフォルダを
    そのまま install に渡すと、そのリポジトリが黙って外れて終了コード 0 になってしまう。install の前にこれで確かめる。
    """
    broken: list[str] = []
    absent: list[str] = []
    for r in repos:
        if not r.python:
            continue
        d = root / r.name
        if not d.exists():
            absent.append(r.name)
            continue
        rels = [s.strip() for s in r.packages.split(",") if s.strip()] or ["."]
        for rel in rels:
            pkg = d if rel == "." else d / rel
            if not (pkg / "pyproject.toml").is_file():
                label = r.name if rel == "." else f"{r.name}/{rel}"
                why = "空のフォルダ" if _is_empty_dir(d) else "pyproject.toml がありません"
                broken.append(f"{label}: {why}（{pkg}）")
    return broken, absent


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


def ref_mismatches(root: Path, repos: list[Repo]) -> list[str]:
    """マニフェストで ref を指定したリポジトリのうち、手元の HEAD がその ref のコミットと違うもの（無ければ空）.

    clone の直後の checkout や pull で ref にそろえられなかったまま install すると、既定ブランチなど
    意図しない版が入ってしまう。install の前にこれで確かめて止める。
    """
    problems: list[str] = []
    for r in repos:
        if not r.ref:
            continue
        d = root / r.name
        if not (d / ".git").exists():
            continue  # 未取得のものは install_plan が扱う（ここでは版のずれだけを見る）
        want = git(["rev-parse", "--verify", "-q", f"{r.ref}^{{commit}}"], cwd=d, check=False)
        head = git(["rev-parse", "--verify", "-q", "HEAD"], cwd=d, check=False)
        if not want:
            problems.append(f"{r.name}: ref {r.ref} が手元にありません（今の HEAD は {head[:12] or '不明'}）")
        elif want != head:
            problems.append(f"{r.name}: HEAD {head[:12] or '不明'} が ref {r.ref}（{want[:12]}）と違います")
    return problems


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


_CLAUSE = re.compile(r"^(~=|===|==|!=|<=|>=|<|>)\s*(\d+(?:\.\d+)*)(\.\*)?$")


def _pad(v: tuple[int, ...], n: int) -> tuple[int, ...]:
    return v + (0,) * (n - len(v))


def _clause_ok(op: str, w: tuple[int, ...], wildcard: bool, v: tuple[int, ...]) -> bool:
    """PEP 440 の比較 1 つ（リリース番号だけ。プレリリースなどは requires-python に書かない前提）."""
    if wildcard:  # ==3.12.* / !=3.12.*: 先頭の一致
        hit = _pad(v, len(w))[: len(w)] == w
        return hit if op == "==" else not hit
    n = max(len(v), len(w))
    a, b = _pad(v, n), _pad(w, n)
    if op == "~=":  # ~=3.12.1 は >=3.12.1, ==3.12.*（最後の桁だけ上がってよい）
        return a >= b and _pad(v, len(w))[: len(w) - 1] == w[:-1]
    return {
        "==": a == b,
        "===": a == b,
        "!=": a != b,
        ">=": a >= b,
        "<=": a <= b,
        ">": a > b,
        "<": a < b,
    }[op]


def accepts(spec: str, version: tuple[int, ...]) -> bool:
    """requires-python（PEP 440 の指定子のカンマ区切り）が version を受け付けるか.

    依存を増やさないよう packaging の SpecifierSet と同じ判定をリリース番号の範囲で実装している
    （`~=3.12.1` は 3.13 を受け付けない、`>3.12` は 3.12.1 以降を受け付ける など）。
    version が (major, minor) だけのときは、その系列（3.12 なら 3.12.x）のどれかを受け付ければ True。
    読めない指定（`~=3` のような 1 桁の ~= や、数字でない版）は受け付けない（False）として扱う.
    """
    clauses: list[tuple[str, tuple[int, ...], bool]] = []
    for raw in spec.split(","):
        raw = raw.strip()
        if not raw:
            continue
        m = _CLAUSE.match(raw)
        if m is None:
            return False
        op, w, wildcard = m.group(1), tuple(int(x) for x in m.group(2).split(".")), bool(m.group(3))
        if (op == "~=" and len(w) < 2) or (wildcard and op not in ("==", "!=")):
            return False
        clauses.append((op, w, wildcard))
    if len(version) >= 3:
        candidates = [tuple(version)]
    else:
        # 系列の中で境目になりうる版（.0、指定に出てくるパッチ番号とその前後、十分大きいパッチ）を試す
        series = tuple(version[:2])
        patches = {0, 10**6}
        for _, w, _ in clauses:
            if w[:2] == series and len(w) > 2:
                patches |= {w[2], w[2] + 1, max(w[2] - 1, 0)}
        candidates = [(*series, p) for p in sorted(patches)]
    return any(all(_clause_ok(op, w, wc, v) for op, w, wc in clauses) for v in candidates)


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


# ---------------------------------------------------------------------------
# URL で固定した依存（devtools-common @ git+…@<SHA> など）がツールどうしでそろっているか
# ---------------------------------------------------------------------------
_URL_PIN = re.compile(r"^\s*([\w.\-]+)\s*(?:\[[^\]]*\])?\s*@\s*(\S+)")


def url_pin(dep: str) -> tuple[str, str, str] | None:
    """`name[extra] @ git+https://host/org/repo.git@<ref>#subdirectory=x ; marker` → (name, リポジトリの URL, ref).

    URL で固定していない依存は None。ref の無い URL は ref を空にする.
    """
    m = _URL_PIN.match(dep.split(";", 1)[0])
    if not m:
        return None
    url = m.group(2).split("#", 1)[0]
    base, ref = url, ""
    # `scheme://[user@]host/path[@ref]`。ユーザー名の @（git+ssh://git@github.com/…）は host の前、
    # ref の @ はパスの後ろにある。パス（最初の / より後ろ）にある @ だけを ref の区切りとみなす
    scheme, sep, rest = url.partition("://")
    if sep:
        authority, slash, path = rest.partition("/")
        if slash and "@" in path:
            path, ref = path.rsplit("@", 1)
        base = f"{scheme}://{authority}{slash}{path}"
    elif "@" in url:
        base, ref = url.rsplit("@", 1)
    return m.group(1).replace("_", "-").lower(), base.removesuffix(".git").rstrip("/"), ref


def collect_pins(root: Path, repos: list[Repo]) -> dict[str, dict[tuple[str, str], list[str]]]:
    """{依存の名前: {(URL, ref): [固定しているパッケージの表示名]}}.

    見るのは `dependencies` だけ（setup の一括インストールで pip が解決するもの）。optional-dependencies は
    setup では入れないので、食い違っていても一括インストールは止まらない（各ツールの CI が見る）.
    """
    pkgs = [(r, d, _project(d)) for r in repos if r.python for d in r.package_dirs(root)]
    # ほかのツールが URL で固定しているパッケージ（review-platform → auto-review）は、手元の checkout ではなく
    # 固定した版が入る（install_plan と同じ）。手元の checkout の固定は使われないので見ない
    pinned_elsewhere: set[str] = set()
    for _, _, p in pkgs:
        pinned_elsewhere |= _pinned_by_url(p.get("dependencies", []))
    pins: dict[str, dict[tuple[str, str], list[str]]] = {}
    for r, d, project in pkgs:
        if str(project.get("name", d.name)).replace("_", "-").lower() in pinned_elsewhere:
            continue
        rel = d.relative_to(root / r.name).as_posix()
        label = r.name if rel == "." else f"{r.name}/{rel}"
        for dep in project.get("dependencies", []):
            pin = url_pin(dep)
            if pin is None:
                continue
            users = pins.setdefault(pin[0], {}).setdefault(pin[1:], [])
            if label not in users:
                users.append(label)
    return pins


def check_pins(root: Path, repos: list[Repo], names: tuple[str, ...] | None = None) -> list[str]:
    """URL で固定した依存の版がパッケージどうしで食い違っていれば、その説明（無ければ空）.

    names を渡すと、その依存だけを見る（既定はすべて。devtools-common のほか、auto-review・doc-to-markdown など）。
    食い違いは pip の一括インストールで衝突として止まるので、その前に「どのツールの固定をどの SHA にそろえるか」を示す。
    そろえる先は、最も多くのツールが使っている固定（同数なら、表示の先頭）.
    """
    problems: list[str] = []
    for dep, by_pin in sorted(collect_pins(root, repos).items()):
        if names is not None and dep not in names:
            continue
        if len(by_pin) < 2:
            continue
        ranked = sorted(by_pin.items(), key=lambda kv: -len(kv[1]))
        (url, ref), majority = ranked[0]
        lines = [f"{dep} の固定がツールごとに違います:"]
        for (u, r), users in ranked:
            lines.append(f"    {r or '(ref なし)'} {u}  ← {', '.join(users)}")
        to_fix = [u for _, users in ranked[1:] for u in users]
        lines.append(
            f"  そろえる: {', '.join(to_fix)} の pyproject.toml の {dep} の固定を {ref or url} にする"
            f"（{', '.join(majority)} と同じ。新しい版にそろえるなら、ほかのツールを上げる）"
        )
        problems.append("\n".join(lines))
    return problems


def cmd_check_pins(root: Path, repos: list[Repo]) -> int:
    problems = check_pins(root, repos)
    for p in problems:
        print(f"NG     {p}", file=sys.stderr)
    if problems:
        print(
            "       食い違ったままでは一括インストールで pip が衝突として止まります。"
            "固定をそろえてから setup をやり直してください",
            file=sys.stderr,
        )
        return 1
    pins = collect_pins(root, repos)
    common = next(iter(pins.get(COMMON, {})), None)
    detail = f"（{COMMON} は {common[1]}）" if common else ""
    print(f"ok     URL で固定した依存 {len(pins)} 個の版がツールどうしでそろっています{detail}")
    return 0


def pip_failure_hint(code: object, dev: bool = False) -> str:
    """pip が失敗したときの案内（トレースバックの代わりに出す）."""
    lines = [
        f"\nインストールに失敗しました（pip の終了コード: {code}）。"
        "上の pip の表示の最後のエラーを確かめてください。よくある原因:",
        "  - ネットワーク・社内プロキシ: PyPI と GitHub（git+https の固定依存）に届くか。"
        "プロキシが要るなら HTTPS_PROXY を設定する",
        "  - 固定の食い違い: `python scripts/bootstrap.py check-pins` で、"
        "ツールどうしの devtools-common などの固定 SHA を確かめる"
        "（ResolutionImpossible・conflicting dependencies と出たとき）",
        "  - Python の版: `python scripts/bootstrap.py check-python`",
        "  - 一時的な失敗なら、もう一度 setup を実行する（取得済みのリポジトリはそのまま使う）",
    ]
    if not dev:
        lines.append(
            "  - devtools-common を変更しながら試しているなら、開発者向けの --dev（ローカルの checkout を使う）"
        )
    return "\n".join(lines)


def cmd_install(root: Path, repos: list[Repo], venv_dir: Path | None, dry_run: bool, dev: bool = False) -> int:
    python = sys.executable
    if venv_dir is not None:
        if not dry_run and not venv_dir.exists():
            print(f"venv   {venv_dir}")
            venv.EnvBuilder(with_pip=True).create(venv_dir)
        python = str(venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))
    mismatched = ref_mismatches(root, [r for r in repos if r.python])
    if mismatched:
        for m in mismatched:
            print(f"NG     {m}", file=sys.stderr)
        print(
            "マニフェストの ref にそろっていないリポジトリがあるため、インストールを止めました。"
            "手元の変更を確かめてから `bootstrap.py pull` で ref にそろえ、もう一度実行してください",
            file=sys.stderr,
        )
        return 1
    broken, absent = missing_packages(root, repos)
    for name in absent:
        print(f"skip   {name}（未取得。入れるには先に `bootstrap.py clone`）", file=sys.stderr)
    if broken:
        for b in broken:
            print(f"NG     {b}", file=sys.stderr)
        print(
            "取得できていない Python のリポジトリがあるため、インストールを止めました。"
            "空のフォルダなら消してから `bootstrap.py clone`（setup をやり直す）で取得してください",
            file=sys.stderr,
        )
        return 1
    if dev:
        print("mode   開発者向け（--dev）: devtools-common はローカルの checkout を editable で使います")
    notes: list[str] = []
    plan = install_plan(root, repos, dev=dev, notes=notes)
    for n in notes:
        print(f"note   {n}（手元の checkout は使わない）")
    for args in plan:
        cmd = [python, "-m", "pip", *args]
        print("$", " ".join(cmd))
        if dry_run:
            continue
        try:
            subprocess.run(cmd, check=True)
        except (subprocess.CalledProcessError, OSError) as e:
            code = e.returncode if isinstance(e, subprocess.CalledProcessError) else e
            print(pip_failure_hint(code, dev=dev), file=sys.stderr)
            return 1
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
    sub.add_parser("check-pins", help="各ツールが URL で固定した devtools-common などの版がそろっているか")
    args = ap.parse_args(argv)

    try:
        top, repos = load_manifest(args.manifest)
    except ManifestError as e:
        print(f"マニフェストを読めません: {e}", file=sys.stderr)
        return 2
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
    if args.cmd == "check-pins":
        return cmd_check_pins(root, repos)
    return cmd_list(repos)


if __name__ == "__main__":
    sys.exit(main())
