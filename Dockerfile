FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY codeforge ./codeforge
COPY tests ./tests
RUN pip install --no-cache-dir '.[all]'
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "codeforge.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
