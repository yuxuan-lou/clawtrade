FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-17-jre-headless \
    xvfb \
    python3 \
    python3-pip \
    curl \
    unzip \
    wget \
    gnupg \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (chromium-browser is a non-functional snap stub in Ubuntu 22.04 Docker)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Download ChromeDriver matching the installed Chrome major version
RUN CHROME_MAJOR=$(google-chrome --version | sed 's/[^0-9]*//' | cut -d. -f1) \
    && CHROMEDRIVER_URL=$(curl -sf "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json" \
       | jq -r ".milestones.\"${CHROME_MAJOR}\".downloads.chromedriver[] | select(.platform==\"linux64\") | .url") \
    && wget -q "$CHROMEDRIVER_URL" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/chromedriver \
    && mv /tmp/chromedriver/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver*

RUN pip3 install ibeam requests

# Patch ibeam 0.5.10 bugs
RUN python3 -c "\
import pathlib;\
\
# 1) ibeam_starter.py: try_authenticating() returns 3 values but --authenticate expects 2\n\
p = pathlib.Path('/usr/local/lib/python3.10/dist-packages/ibeam/ibeam_starter.py');\
p.write_text(p.read_text().replace(\
    'success, _ = strategy_handler.try_authenticating()',\
    'success, _, _ = strategy_handler.try_authenticating()'));\
\
# 2) strategy_handler.py: condition_authenticated_true short-circuits on no session,\n\
#    preventing retries after fresh login. Also add validate() + sleep in _post_authentication\n\
p = pathlib.Path('/usr/local/lib/python3.10/dist-packages/ibeam/src/handlers/strategy_handler.py');\
s = p.read_text();\
s = s.replace(\
    'if not status.running or not status.session:\n        return True\n\n    # happy case, wa don',\
    'if not status.running:\n        return True\n\n    # happy case, wa don');\
s = s.replace(\
    '\"\"\"This method double-checks that the authentication was successful, and if not, reauthenticates\"\"\"\n\n        # if we only just logged in',\
    '\"\"\"This method double-checks that the authentication was successful, and if not, reauthenticates\"\"\"\n\n        import time as _time; _time.sleep(5)\n        try:\n            self.http_handler.validate()\n        except Exception:\n            pass\n\n        # if we only just logged in');\
p.write_text(s);\
\
# 3) login_handler.py: increase post-success sleep from 1s to 10s so SSO redirect completes\n\
p = pathlib.Path('/usr/local/lib/python3.10/dist-packages/ibeam/src/handlers/login_handler.py');\
s = p.read_text();\
s = s.replace(\
    \"raise RuntimeError(f'Invalid AttemptException: {e}')\n\n\n            time.sleep(1)\",\
    \"raise RuntimeError(f'Invalid AttemptException: {e}')\n\n\n            time.sleep(10)\");\
p.write_text(s);\
"

WORKDIR /opt/gateway
RUN wget -q https://download2.interactivebrokers.com/portal/clientportal.gw.zip -O gw.zip \
    && unzip gw.zip -d clientportal \
    && rm gw.zip

# Patch conf file: allow Docker bridge traffic
RUN sed -i '/allow:/a\        - 0.0.0.0\n        - 172.*\n        - 10.*' /opt/gateway/clientportal/root/conf.yaml

COPY start.sh /opt/gateway/start.sh
RUN chmod +x /opt/gateway/start.sh

COPY keepalive.py /opt/gateway/keepalive.py

EXPOSE 5000

CMD ["/opt/gateway/start.sh"]
