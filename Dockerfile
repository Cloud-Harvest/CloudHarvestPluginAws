FROM python:3.11.5-bookworm as python

WORKDIR /src

COPY . .

RUN pip install -r ./requirements.txt

RUN mkdir -pv /etc/harvest.d/

ENTRYPOINT /bin/bash
