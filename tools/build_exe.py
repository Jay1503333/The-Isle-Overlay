"""Build a PyInstaller bundle (single folder) on Windows or Linux.

Windows:  py tools/build_exe.py        -> dist/TheIsleCompanion/ and dist/TheIsleCompanion-<version>-windows.zip
The output folder includes HOW_TO_RUN.txt, MAP_DATA.md, CHANGELOG.md and VERSION.txt.
PyInstaller cannot cross-compile: the .exe must be built on Windows.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.version import APP_NAME, APP_VERSION, MAP_DATA_VERSION  # noqa: E402


def _clean_native_search_path() -> None:
    """Prevent unrelated developer tools on PATH from leaking DLLs into the bundle."""

    if os.name != "nt":
        return
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = [
        Path(sys.executable).resolve().parent,
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        Path(sys.base_prefix).resolve() / "DLLs",
        windows / "System32",
        windows,
    ]
    unique: list[str] = []
    for candidate in candidates:
        value = str(candidate)
        if value.casefold() not in {item.casefold() for item in unique}:
            unique.append(value)
    os.environ["PATH"] = os.pathsep.join(unique)


def write_version_file(path: Path) -> None:
    """Write a PyInstaller Windows version resource (shown in file Properties)."""

    parts = [int(x) for x in APP_VERSION.split(".")] + [0] * 4
    tup = tuple(parts[:4])
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Community project'),
      StringStruct('FileDescription', '{APP_NAME} - external map and minimap overlay'),
      StringStruct('FileVersion', '{APP_VERSION}'),
      StringStruct('InternalName', 'TheIsleCompanion'),
      StringStruct('OriginalFilename', 'TheIsleCompanion.exe'),
      StringStruct('ProductName', '{APP_NAME}'),
      StringStruct('ProductVersion', '{APP_VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def write_icon(path: Path) -> bool:
    """Render the in-app icon to a multi-size .ico. Returns False if unsupported."""

    try:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtGui import QGuiApplication

        from app import create_app_icon

        _app = QGuiApplication.instance() or QGuiApplication([])
        pixmap = create_app_icon().pixmap(256, 256)
        return bool(pixmap.save(str(path), "ICO"))
    except Exception as exc:  # noqa: BLE001 - icon is cosmetic
        print(f"icon skipped: {exc}")
        return False


def build_arguments(
    platform_name: str | None = None,
    *,
    version_file: Path | None = None,
    icon: Path | None = None,
) -> list[str]:
    """Return platform-correct PyInstaller arguments without personal config data."""

    platform_name = os.name if platform_name is None else platform_name
    data_separator = ";" if platform_name == "nt" else ":"
    arguments = [
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "TheIsleCompanion",
        "--contents-directory",
        ".",
        "--add-data",
        f"data{data_separator}data",
        "--add-data",
        f"assets/map{data_separator}assets/map",
        "--add-data",
        f"assets/icons{data_separator}assets/icons",
    ]
    if platform_name == "nt":
        arguments.extend(
            [
                "--add-data",
                f"core/windows_ocr.ps1{data_separator}core",
            ]
        )
    if platform_name == "nt":
        if version_file is not None:
            arguments.extend(["--version-file", str(version_file)])
        if icon is not None:
            arguments.extend(["--icon", str(icon)])
    arguments.append("app.py")
    return arguments


def package_output(root: Path) -> Path | None:
    """Copy user docs into the built folder and zip it for sharing."""

    out = root / "dist" / "TheIsleCompanion"
    if not out.is_dir():
        return None
    shutil.copy2(root / "packaging" / "HOW_TO_RUN.txt", out / "HOW_TO_RUN.txt")
    shutil.copy2(root / "docs" / "MAP_DATA.md", out / "MAP_DATA.md")
    shutil.copy2(root / "CHANGELOG.md", out / "CHANGELOG.md")
    (out / "VERSION.txt").write_text(
        f"{APP_NAME} {APP_VERSION}\nMap data: {MAP_DATA_VERSION}\n", encoding="utf-8"
    )
    (out / "config").mkdir(exist_ok=True)
    (out / "config" / "README.md").write_text(
        (root / "config" / "README.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    tag = "windows" if os.name == "nt" else "linux"
    archive = shutil.make_archive(
        str(root / "dist" / f"TheIsleCompanion-{APP_VERSION}-{tag}"), "zip",
        root_dir=root / "dist", base_dir="TheIsleCompanion",
    )
    return Path(archive)


def main() -> int:
    try:
        from PyInstaller.__main__ import run
    except ImportError:
        print("PyInstaller is not installed. Run: py -m pip install -r requirements-dev.txt")
        return 1

    project_root = Path(__file__).resolve().parents[1]
    os.chdir(project_root)
    _clean_native_search_path()
    work = project_root / "build"
    work.mkdir(exist_ok=True)
    version_file = work / "version_info.txt"
    write_version_file(version_file)
    icon = work / "app.ico"
    run(build_arguments(version_file=version_file, icon=icon if write_icon(icon) else None))
    archive = package_output(project_root)
    if archive is not None:
        print(f"Built: {project_root / 'dist' / 'TheIsleCompanion'}\nZip:   {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
