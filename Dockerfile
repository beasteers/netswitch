FROM balenalib/raspberry-pi

WORKDIR /app
COPY setup.py .
COPY netswitch/__init__.py netswitch/__init__.py
RUN pip install -e .
COPY netswitch netswitch
COPY config.yml .

ENTRYPOINT python -m netswitch monitor
CMD config.yml
