$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .venv/Scripts/python.exe -m pip install pyinstaller==6.16.0
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller installation failed' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm AttendlyVision.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Copy-Item README.md,THIRD_PARTY_NOTICES.md dist/AttendlyVision
Compress-Archive -Path dist/AttendlyVision -DestinationPath dist/AttendlyVision-Windows-x64.zip -Force
