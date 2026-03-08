FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    chromium-browser \
    chromium-chromedriver \
    xvfb \
    python3 \
    python3-pip \
    curl \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install ibeam requests

WORKDIR /opt/gateway
RUN wget -q https://download2.interactivebrokers.com/portal/clientportal.gw.zip \
    && unzip clientportal.gw.zip -d clientportal \
    && rm clientportal.gw.zip

COPY start.sh /opt/gateway/start.sh
RUN chmod +x /opt/gateway/start.sh

COPY keepalive.py /opt/gateway/keepalive.py

EXPOSE 5000

CMD ["/opt/gateway/start.sh"]
