FROM ccr.ccs.tencentyun.com/itqm/dataset_finetune_api_base:1.0

# 设置工作目录
WORKDIR /app
ENV TZ=Asia/Shanghai

# 复制 requirements.txt 到工作目录
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt uvicorn gunicorn

# 复制当前目录的内容到工作目录
COPY . .

CMD cp /app/dataset_finetune/config.property /app/.env && \
    gunicorn app:app \
    --bind 0.0.0.0:8000 \
    --workers $$(( $(nproc) * 2 )) \
    --worker-class uvicorn.workers.UvicornWorker \
    --max-requests 1000 \
    --timeout 120 \
    --log-level info