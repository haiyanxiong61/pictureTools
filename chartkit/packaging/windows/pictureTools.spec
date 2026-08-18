# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

project = Path(SPECPATH).resolve().parents[1]
src = project / "src"

datas = collect_data_files("chartkit")
webapp = src / "chartkit" / "webapp"
if webapp.exists():
    datas.append((str(webapp), "chartkit/webapp"))
binaries = []
hiddenimports = []

for package in ("matplotlib", "flask", "yaml", "numpy", "wordcloud", "jieba", "PIL"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += [
    "chartkit",
    "chartkit.web",
    "chartkit.desktop",
    "chartkit.api",
    "chartkit.render",
    "chartkit.fonts",
    "chartkit.presets",
    "chartkit.paths",
    "chartkit.config",
    "chartkit.themes",
    "chartkit.spec",
    "chartkit.demo",
    "chartkit.clouds",
    "webview",
    "tkinter",
]

a = Analysis(
    [str(Path(SPECPATH) / "launch.py")],
    pathex=[str(src)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="pictureTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="pictureTools",
)
