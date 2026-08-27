# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all
import os

datas = [
    ('backend/app', 'backend/app'),
    ('frontend/dashboard/public', 'frontend/dashboard/public')
]
binaries = []

hiddenimports = [
    'fastapi',
    'pydantic',
    'sqlalchemy',
    'passlib',
    'jose',
    'python-multipart',
    'python-dotenv',
    'yfinance',
    'xgboost',
    'sklearn',
    'sklearn.tree._utils',
    'sklearn.neighbors._typedefs',
    'app.api.router',
    'app.outperform.router',
    'app.core.config',
    'app.scheduler.jobs',
    'app.alerts.bot_listener',
    'app.domain.contracts',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'multiprocessing',
    'multiprocessing.pool',
    'multiprocessing.managers',
    'webview',
    'pywebview',
]

# Collect only what's strictly necessary
datas += collect_data_files('xgboost')

for pkg in ['uvicorn', 'apscheduler', 'fastapi', 'pydantic_settings', 'pydantic', 'sqlalchemy', 'yfinance', 'tenacity']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Heavy libraries we explicitly DO NOT want bundled
_big_excludes = [
    'tensorflow', 'tensorflow_core', 'tensorboard', 'tensorflow_estimator',
    'keras', 'keras_core',
    'torch', 'torchvision', 'torchaudio',
    'jax', 'jaxlib', 'flax',
    'onnx', 'onnxruntime',
    'numba', 'llvmlite',
    'pyarrow',
    'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair',
    'tkinter', '_tkinter', 'wx', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    'playwright', 'selenium',
    'pygame', 'OpenGL',
    'IPython', 'ipykernel', 'jupyter', 'notebook', 'nbformat', 'nbconvert',
    'ipywidgets', 'traitlets',
    'pytest',
    'cv2',
]

a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_big_excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AlphaHunter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Hide the terminal window for production
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
