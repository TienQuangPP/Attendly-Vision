# Build with: python -m PyInstaller --noconfirm AttendlyVision.spec
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []
for package in ('insightface', 'onnxruntime'):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h
datas += copy_metadata('insightface')

a = Analysis(
    ['attendance_system/main.py'],
    pathex=['attendance_system'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['openpyxl'],
    excludes=['torch', 'tensorflow', 'keras', 'mxnet', 'IPython',
              'notebook', 'pytest', 'PySide2', 'PySide6', 'PyQt6'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='AttendlyVision', debug=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='AttendlyVision')
