# NLP标注平台

## 环境安装

### 方式一：使用安装脚本（推荐）

```bash
cd backend
chmod +x setup.sh
./setup.sh
```

### 方式二：手动安装

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 启动服务

```bash
cd backend
source venv/bin/activate  # 激活虚拟环境
python app.py
```

服务启动后，访问 http://localhost:8000

## 使用说明

### 初始化账号
首次启动会自动创建测试账号：
- 审核员：`admin` / `123456`
- 标注员：`annotator1`、`annotator2`、`annotator3` / `123456`

### 功能操作
1. **导入数据**：点击"导入数据"，粘贴JSON格式数据
2. **分配任务**：审核员在数据集列表点击"分配"
3. **标注**：标注员进入"标注"页面，点击"有效"或"无效"
4. **审核**：审核员进入"审核"页面进行通过/驳回
5. **导出**：点击数据集"查看"->"导出JSON"

### JSON数据格式
```json
[
  {"id": "1", "source": "twitter", "text": "文本内容", "extra": "额外字段"},
  {"id": "2", "source": "email", "text": "另一条文本", "custom_field": "自定义"}
]
```

## 技术栈
- 后端：Flask + SQLAlchemy + SQLite
- 前端：Vue3 (CDN引入)