@echo off
echo ========================================
echo  角色扮演对话总结系统
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖
echo 安装依赖...
pip install -r requirements.txt -q

REM 检查.env文件
if not exist ".env" (
    echo.
    echo 警告: 未找到.env配置文件
    echo 请复制 .env.example 为 .env 并配置
    echo.
    copy .env.example .env
    echo 已创建默认配置文件，请编辑 .env 后重新运行
    notepad .env
    pause
    exit /b 1
)

echo.
echo 启动应用...
echo 访问 http://localhost:7860
echo.

python app.py

pause
