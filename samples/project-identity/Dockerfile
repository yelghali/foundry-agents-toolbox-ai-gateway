FROM python:3.13-slim
WORKDIR /app
RUN pip install --no-cache-dir fastmcp==2.14.1 mcp==1.27.2 "pydantic-settings>=2.11,<3" "PyJWT[crypto]>=2.10,<3" "uvicorn>=0.30,<1" \
    && python -c "from fastmcp import FastMCP; import jwt, uvicorn"
COPY custom_server.py .
EXPOSE 8000
CMD ["python", "custom_server.py"]
