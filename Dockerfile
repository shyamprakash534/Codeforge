FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY codeforge ./codeforge
COPY tests ./tests
RUN pip install --no-cache-dir '.[dev]'
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
CMD ["codeforge", "--help"]
