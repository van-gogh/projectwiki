FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY whywiki ./whywiki
COPY examples ./examples
RUN pip install --no-cache-dir -e .
ENV WHYWIKI_DATA_DIR=/data
EXPOSE 8080
CMD ["whywiki", "serve", "--host", "0.0.0.0", "--port", "8080"]
