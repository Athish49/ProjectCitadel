FROM python:3.13-slim-bookworm

# Never write .pyc files and always flush stdout immediately — keeps the
# sandbox lean and ensures JSON output reaches the parent process without
# buffering delays.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    TMPDIR=/tmp

WORKDIR /

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY parse.py /parse.py

# Run as nobody (uid=65534) — matches --user=65534:65534 on the docker run
# call.  The RUN above runs as root so pip installs succeed; after that the
# runtime drops privileges.
USER 65534:65534

ENTRYPOINT ["python", "-u", "/parse.py"]
