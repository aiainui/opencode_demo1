# 贡献指南

## 本地开发

### 环境要求
- Python 3.11+
- SQLite3

### 快速开始

```bash
# 克隆项目
git clone https://github.com/aiainui/opencode_demo1.git
cd opencode_demo1

# 使用 Makefile 安装并运行
make install
make run
```

### Docker 部署

```bash
# 构建并运行
make docker-build
make docker-up
```

## 项目结构

```
opencode_demo1/
├── backend/          # Flask 后端
│   ├── app.py       # 主应用
│   ├── models.py    # 数据模型
│   ├── auth.py      # 认证
│   └── ...
├── frontend/        # Vue3 前端
├── Dockerfile       # Docker 配置
└── docker-compose.yml
```

## 功能模块

1. 用户管理 - 登录、权限控制
2. 数据集管理 - 导入、导出
3. 任务分配 - 审核员分配任务给标注员
4. 标注功能 - 有效/无效标注
5. 审核功能 - 审核标注结果
