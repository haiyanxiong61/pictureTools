# pictureTools

在网页里选例子、改数字、下载图表。也可以打成 Windows 软件，对方不用安装 Python。

## 这台 Mac 上怎么用

```bash
cd chartkit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[desktop]"
python -m chartkit desktop
```

浏览器打开 `http://127.0.0.1:8765` 也可以：`python -m chartkit serve`

## 发给 Windows 用户

把代码推到 GitHub 后，打开仓库的 **Actions**，等 `build-windows` 跑完，下载 `pictureTools-windows`，把整个文件夹发给对方。对方解压后双击 `pictureTools.exe` 即可。
