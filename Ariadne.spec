# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all data files and dynamic submodules
hidden_imports = (
    collect_submodules('ariadne') +
    collect_submodules('dns') +
    collect_submodules('prompt_toolkit') +
    collect_submodules('PIL') +
    collect_submodules('cryptography') +
    [
        'rich',
        'rich.console',
        'rich.panel',
        'rich.table',
        'rich.progress',
        'pydantic',
        'aiohttp',
        'jinja2',
        'yaml',
        'aiofiles',
        'aiosqlite',
        'keyring',
    ]
)

data_files = [
    ('ariadne/assets/banner.txt', 'ariadne/assets'),
    ('ariadne/assets/ariadne.ico', 'ariadne/assets'),
    ('ariadne/cli/locales/*.json', 'ariadne/cli/locales'),
    ('ariadne/plugins/builtin', 'ariadne/plugins/builtin'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Ariadne',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ariadne/assets/ariadne.ico',
)
