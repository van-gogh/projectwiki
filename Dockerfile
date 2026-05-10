FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY projectwiki ./projectwiki
COPY examples ./examples
RUN pip install --no-cache-dir -e .
ENV PROJECTWIKI_DATA_DIR=/data
EXPOSE 8080
CMD ["projectwiki", "serve", "--host", "0.0.0.0", "--port", "8080"]
