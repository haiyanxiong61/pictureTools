@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."

echo [1/4] 安装打包依赖...
python -m pip install -U pip
python -m pip install -e ".[build]"
if errorlevel 1 (
  echo 安装失败。请先安装 Python 3.10 或更高，并勾选 Add python.exe to PATH。
  pause
  exit /b 1
)

echo [2/4] 正在打包，可能需要几分钟...
if exist "dist\pictureTools" rmdir /s /q "dist\pictureTools"
python -m PyInstaller packaging\windows\pictureTools.spec --noconfirm --clean --distpath dist --workpath build
if errorlevel 1 (
  echo 打包失败。
  pause
  exit /b 1
)

echo [3/4] 写入使用说明...
copy /Y "packaging\windows\发给对方.txt" "dist\pictureTools\使用说明.txt" >nul

echo [4/4] 打成 zip...
if exist "dist\pictureTools.zip" del /f /q "dist\pictureTools.zip"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\pictureTools\*' -DestinationPath 'dist\pictureTools.zip' -Force"

echo.
echo 完成。
echo 文件夹：%cd%\dist\pictureTools
echo 压缩包：%cd%\dist\pictureTools.zip
echo 把 zip 发给对方，解压后双击 pictureTools.exe 即可。
echo.
pause
