#!/bin/bash

# 文本标注平台 - 环境安装脚本

echo "=== 创建虚拟环境 ==="
cd "$(dirname "$0")"

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "=== 安装依赖包 ==="
pip install -r requirements.txt

echo "=== 环境安装完成 ==="
echo ""
echo "激活虚拟环境命令: source venv/bin/activate"
echo "启动后端命令: python app.py"
echo ""
echo "默认测试账号:"
echo "  审核员: admin / 123456"
echo "  标注员: annotator1 / 123456"