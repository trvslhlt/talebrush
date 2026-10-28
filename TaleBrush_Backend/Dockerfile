# Claude-backed model server (server_llm.py). The original GPT-Neo + GeDi
# server (server_code.py) needs a GPU and model files that are no longer available.
FROM python:3.12-slim
WORKDIR /app
COPY requirements_llm.txt ./
RUN pip install --no-cache-dir -r requirements_llm.txt
COPY server_llm.py ./

ENV PORT=5001
EXPOSE 5001
CMD ["python", "server_llm.py"]
