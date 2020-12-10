FROM balenalib/raspberrypi3-python:latest

RUN apt-get -q update && apt-get -qy install wireless-tools && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY setup.py README.md ./
COPY netswitch/__init__.py netswitch/__init__.py
RUN pip install -e .
COPY netswitch netswitch
COPY config.yml ./

ENTRYPOINT python -m netswitch run
CMD config.yml
