# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
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
]

# Collect only what's strictly necessary
datas += collect_data_files('xgboost')
tmp_ret = collect_all('uvicorn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('apscheduler')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Heavy libraries we explicitly DO NOT want bundled
_big_excludes = [
    # Deep learning frameworks (hundreds of MB each)
    'tensorflow', 'tensorflow_core', 'tensorboard', 'tensorflow_estimator',
    'keras', 'keras_core',
    'torch', 'torchvision', 'torchaudio',
    'jax', 'jaxlib', 'flax',
    'onnx', 'onnxruntime',
    # Numba / LLVM (not used in our app)
    'numba', 'llvmlite',
    # Arrow / Big-data (not needed at runtime for a FastAPI app)
    'pyarrow',
    # Plotting libraries (server has no display)
    'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair',
    # GUI frameworks
    'tkinter', '_tkinter', 'wx', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
    # Browser automation
    'playwright', 'selenium',
    # Game engines
    'pygame', 'OpenGL',
    # IPython / Jupyter (dev tools only)
    'IPython', 'ipykernel', 'jupyter', 'notebook', 'nbformat', 'nbconvert',
    'ipywidgets', 'traitlets',
    # Test frameworks
    'pytest',
    # CV
    'cv2',
]

a = Analysis(
    ['run_backend.py'],
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
    name='backend-x86_64-pc-windows-msvc',
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
)
