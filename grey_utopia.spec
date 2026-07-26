# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the offline GREY UTOPIA desktop build.

Bundles the pywebview shell (desktop.py) around the existing server.py
engine, plus the read-only data/ and web/ asset trees. Writable state
(saves, legacy.json) is never bundled -- it's created at runtime in
%APPDATA%/GreyUtopia via engine/paths.py.

Build: pyinstaller grey_utopia.spec --noconfirm
"""
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH)


def collect_data_files(src_root: Path, dest_prefix: str, exclude_rel=()):
    exclude_rel = {Path(p) for p in exclude_rel}
    entries = []
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src_root)
        if any(rel == ex or ex in rel.parents for ex in exclude_rel):
            continue
        dest_dir = dest_prefix if rel.parent == Path(".") else str(Path(dest_prefix) / rel.parent)
        entries.append((str(path), dest_dir))
    return entries


datas = []
# data/assets/originals are pre-crop source art, never served -- skip them.
datas += collect_data_files(PROJECT_ROOT / "data", "data", exclude_rel=["assets/originals"])
datas += collect_data_files(PROJECT_ROOT / "web", "web")

a = Analysis(
    ["desktop.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GreyUtopia",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
