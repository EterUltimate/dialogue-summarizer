#!/bin/bash
echo "========================================"
echo " 角色扮演对话总结系统"
echo "========================================"
echo

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python 3.9+"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt -q

# 检查.env文件
if [ ! -f ".env" ]; then
    echo
    echo "警告: 未找到.env配置文件"
    echo "请复制 .env.example 为 .env 并配置"
    echo
    cp .env.example .env
    echo "已创建默认配置文件，请编辑 .env 后重新运行"
    exit 1
fi

echo
echo "启动应用..."
echo "访问 http://localhost:7860"
echo

python app.py
