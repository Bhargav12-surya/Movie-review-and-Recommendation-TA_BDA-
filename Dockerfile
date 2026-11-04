FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY . /app
RUN python -m pip install --no-cache-dir -e .
RUN addgroup --system cinescope \
    && adduser --system --ingroup cinescope --home /app cinescope \
    && mkdir -p /app/data/runtime \
    && chown -R cinescope:cinescope /app/data/runtime
USER cinescope
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"]
CMD ["python","-m","uvicorn","cinescope.api:app","--host","0.0.0.0","--port","8000"]
