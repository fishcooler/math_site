@echo off
chcp 65001 >nul
echo ========================================
echo   幼小衔接数学练习 - 启动脚本
echo ========================================
echo.

:: 检查 Python 是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.7+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 正在安装依赖...
pip install flask flask-sqlalchemy -q
echo.

echo [2/3] 正在启动服务器...
echo.
echo ========================================
echo   启动成功！请在浏览器中打开：
echo   http://localhost:5000
echo ========================================
echo.
echo 按 Ctrl+C 可停止服务器
echo.

cd /d "%~dp0"
python app.py
pause
