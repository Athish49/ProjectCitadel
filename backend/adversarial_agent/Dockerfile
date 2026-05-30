FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    TMPDIR=/tmp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py runner.py strategy.py spend.py ./

# /var/spend is mounted as a named volume (adversarial_spend) so the monthly
# spend ledger survives container restarts. Pre-create it here so Docker
# copies the correct ownership into the volume on first mount.
RUN mkdir -p /var/spend && chown 65534:65534 /var/spend

# Run as nobody — matches the pattern used by pdf/image sandboxes.
USER 65534:65534

CMD ["python", "-u", "runner.py"]
