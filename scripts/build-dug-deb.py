#!/usr/bin/env python3
"""Build the architecture-independent dugout Debian package using Python's stdlib."""

from pathlib import Path
import argparse
import gzip
import io
import tarfile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "dugout-mlb-data-analysis"
VERSION = "0.1.1"
INSTALL_ROOT = f"usr/lib/{PACKAGE}"


def tar_archive(files: list[tuple[str, bytes, int]]) -> bytes:
    stream = io.BytesIO()
    with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as archive:
            directories = {"."}
            for name, _, _ in files:
                parts = name.split("/")
                directories.update("/".join(parts[:index]) for index in range(1, len(parts)))
            for directory in sorted(directories, key=lambda item: (item.count("/"), item)):
                info = tarfile.TarInfo(f"./{directory}/" if directory != "." else "./")
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.mtime = 0
                archive.addfile(info)
            for name, content, mode in files:
                info = tarfile.TarInfo(f"./{name}")
                info.size = len(content)
                info.mode = mode
                info.mtime = 0
                info.uid = info.gid = 0
                archive.addfile(info, io.BytesIO(content))
    return stream.getvalue()


def ar_member(name: str, content: bytes) -> bytes:
    header = f"{name:<16}{0:<12}{0:<6}{0:<6}{0o100644:<8o}{len(content):<10}`\n".encode("ascii")
    return header + content + (b"\n" if len(content) % 2 else b"")


def build(output_dir: Path) -> Path:
    control = (
        f"Package: {PACKAGE}\n"
        f"Version: {VERSION}\n"
        "Section: utils\n"
        "Priority: optional\n"
        "Architecture: all\n"
        "Depends: python3 (>= 3.10)\n"
        "Maintainer: Dugout maintainers <noreply@github.com>\n"
        "Description: MLB data analysis command-line interface\n"
        " Access schedule, game summaries, boxscores, and raw MLB data\n"
        " through a running MLB Analyzer backend.\n"
    ).encode("utf-8")
    launcher = (
        "#!/usr/bin/python3\n"
        "import sys\n"
        f"sys.path.insert(0, '/{INSTALL_ROOT}')\n"
        "from dugout.cli import main\n"
        "raise SystemExit(main())\n"
    ).encode("utf-8")
    data_files = [("usr/bin/dug", launcher, 0o755)]
    for source in sorted((ROOT / "cli" / "dugout").glob("*.py")):
        data_files.append((f"{INSTALL_ROOT}/dugout/{source.name}", source.read_bytes(), 0o644))

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{PACKAGE}_{VERSION}_all.deb"
    path.write_bytes(
        b"!<arch>\n"
        + ar_member("debian-binary", b"2.0\n")
        + ar_member("control.tar.gz", tar_archive([("control", control, 0o644)]))
        + ar_member("data.tar.gz", tar_archive(data_files))
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    print(build(args.output_dir))


if __name__ == "__main__":
    main()
