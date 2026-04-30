FROM python:3.11-slim

WORKDIR /opt/rmtguard

RUN python -m pip install --no-cache-dir --upgrade pip
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir -e ".[scanpy]"

COPY examples ./examples
COPY tests ./tests
COPY scripts ./scripts
COPY metadata ./metadata

CMD ["python", "examples/run_synthetic.py"]
