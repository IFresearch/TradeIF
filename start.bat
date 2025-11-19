@echo off
echo ========================================
echo TradeIF - 量化回测系统
echo ========================================

echo 检查Python环境...
python --version
if %errorlevel% neq 0 (
    echo 错误: 未找到Python环境，请先安装Python
    pause
    exit /b 1
)

echo.
echo 安装依赖包...
pip install -r requirements.txt

echo.
echo 启动后端服务...
echo 访问地址: http://127.0.0.1:8000
echo.
python backend/api/main.py

pause