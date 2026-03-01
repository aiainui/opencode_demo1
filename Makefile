.PHONY: install run docker-build docker-up docker-down clean test

# 安装依赖
install:
	cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# 运行开发服务器
run:
	cd backend && source venv/bin/activate && python app.py

# Docker 构建
docker-build:
	docker build -t nlp-annotation-platform .

# Docker 运行
docker-up:
	docker-compose up -d

# Docker 停止
docker-down:
	docker-compose down

# 清理缓存
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf backend/data/*.db
