"""Python の版の確認（devtools の必要条件を決める唯一の場所）.

setup.sh・scripts/setup.ps1・scripts/install-prereqs.ps1・scripts/bootstrap.py はすべてここを使う。
古い Python（macOS 標準の 3.9 など）でも読めるよう、f 文字列・型注釈・3.x 専用の書き方を使わない。

    python3 scripts/python_version.py           # 3.11 以上なら 0、未満なら理由を表示して 1
    python3 scripts/python_version.py --quiet   # 何も表示せず、終了コードだけ返す（候補の Python を探すとき）
"""

import sys

# bootstrap.py が tomllib（3.11 で標準ライブラリに入った）を使うため 3.11 以上が要る
MIN_VERSION = (3, 11)


def version_text(info=None):
    info = sys.version_info if info is None else info
    return "%d.%d.%d" % (info[0], info[1], info[2])


def problem(info=None):
    """足りなければ利用者向けの理由（文字列）、足りていれば None."""
    info = sys.version_info if info is None else info
    if tuple(info[:2]) >= MIN_VERSION:
        return None
    args = MIN_VERSION + (version_text(info), sys.executable)
    return (
        "Python %d.%d 以上が必要です（今の Python は %s: %s）。"
        "https://www.python.org/downloads/ から 3.12 を入れてください。" % args
    )


def _write(stream, text):
    """出力先の文字コード（CI の cp1252 など）で日本語を書けなくても止まらないようにする."""
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.write(text.encode("ascii", "backslashreplace").decode("ascii"))


def require(info=None):
    """足りなければ理由を標準エラーに出して終了コード 1 で終わる."""
    msg = problem(info)
    if msg:
        _write(sys.stderr, msg + "\n")
        sys.exit(1)


if __name__ == "__main__":
    if "--quiet" in sys.argv[1:]:
        sys.exit(1 if problem() else 0)
    require()
    _write(sys.stdout, "Python %s OK (%s)\n" % (version_text(), sys.executable))
