# Build with: python -m PyInstaller --noconfirm AttendlyVision.spec
from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata

datas, binaries, hiddenimports = [], collect_dynamic_libs('onnxruntime'), []
datas += copy_metadata('insightface')

a = Analysis(
    ['attendance_system/main.py'],
    pathex=['attendance_system'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ['openpyxl'],
    excludes=['torch', 'tensorflow', 'keras', 'mxnet', 'IPython',
              'notebook', 'pytest', 'PySide2', 'PySide6', 'PyQt6',
              'insightface.gui', 'insightface.commands', 'insightface.app.mask_renderer',
              'insightface.thirdparty.face3d', 'onnx.reference',
              'onnxruntime.quantization', 'onnxruntime.transformers',
              'sklearn', 'matplotlib', 'pip'],
    noarchive=False,
)
# Third-party sample models, photos and reports are not application assets.
a.datas = [entry for entry in a.datas
           if not entry[0].lower().endswith(('.onnx', '.jpg', '.jpeg', '.pdf', '.xlsx'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='AttendlyVision', debug=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='AttendlyVision')
