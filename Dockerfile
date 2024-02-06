FROM python:3.12-bookworm as python

WORKDIR /src

COPY . .

RUN pip install -r ./requirements.txt

RUN mkdir -p /etc/harvest.d/

# copy the default harvest.yaml unless it already exists (previously mounted)
RUN cp -vn /src/harvest/harvest.yaml /etc/harvest.d/harvest.yaml

RUN chmod 600 /etc/harvest.d/*

ENTRYPOINT python harvest
