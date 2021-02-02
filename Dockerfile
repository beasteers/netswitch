FROM python:slim

RUN apt-get -q update && apt-get -qy install wireless-tools net-tools && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY setup.py README.md ./
COPY netswitch/__init__.py netswitch/__init__.py
RUN pip install -e .
COPY netswitch netswitch
COPY config.yml ./

ENTRYPOINT python -m netswitch run config.yml
