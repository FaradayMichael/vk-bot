# base image
FROM --platform=linux/amd64 python:3.11-slim as base
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
# # disable apt cache
COPY docker/selenium/apt_settings /etc/apt/apt.conf.d/02settings
# # disable docs
COPY docker/selenium/dpkg_nodocs /etc/dpkg/dpkg.cfg.d/01_nodoc
ENV	TZ=Europe/Moscow
RUN cp /usr/share/zoneinfo/$TZ /etc/localtime
RUN  apt update \
     && apt install -y curl libcurl4-openssl-dev libssl-dev gcc \
     && apt-get update \
     && apt-get install -y python3.11-dev

COPY requirements /requirements

RUN pip3 install --no-cache-dir -r /requirements/base.txt



# database image without selenium and curl
FROM --platform=linux/amd64 base as db
RUN pip3 install --no-cache-dir -r /requirements/db.txt


# base selenium image
FROM --platform=linux/amd64 base as selenium

RUN apt update \
    && apt install -y curl wget xvfb libgtk-3-0 libx11-xcb1  libnss3 libxss1 libasound2 fonts-liberation xdg-utils libgbm1 libu2f-udev libvulkan1 python3-tk

RUN curl --silent --show-error --fail https://mirror.cs.uchicago.edu/google-chrome/pool/main/g/google-chrome-stable/google-chrome-stable_114.0.5735.90-1_amd64.deb --output google-chrome.deb \
    && dpkg -i google-chrome.deb \
    && rm google-chrome.deb \
    && apt remove -y curl \
    && apt-get autoremove -y \
    && apt-get autoclean -y \
    && apt-get clean -y \
    && apt-get purge -y --auto-remove \
    && touch /root/.Xauthority

ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

COPY bin/chromedriver /usr/bin/chromedriver
COPY docker/selenium/run_parser.sh /usr/bin/run_parser
RUN chmod +x /usr/bin/run_parser \
    && chmod a+x /usr/bin/chromedriver \
    && sed -i -e 's/\r$//' /usr/bin/run_parser

RUN pip3 install --no-cache-dir -r /requirements/selenium.txt

#base selenium firefox image
FROM --platform=linux/amd64 base as selenium_firefox

RUN apt update \
    && apt install -y curl wget xvfb libgtk-3-0 libx11-xcb1  libnss3 libxss1 libasound2 fonts-liberation xdg-utils libgbm1 libu2f-udev libvulkan1 python3-tk bzip2 libxtst6 libx11-xcb-dev libdbus-glib-1-2 libxt6 libpci-dev && rm -rf /var/lib/apt/lists/*
RUN wget https://ftp.mozilla.org/pub/firefox/releases/118.0.1/linux-x86_64/en-GB/firefox-118.0.1.tar.bz2  \
    && tar xvf firefox-118.0.1.tar.bz2 \
    && mv firefox/ /usr/lib/firefox \
    && ln -s /usr/lib/firefox/firefox /usr/bin/firefox \
    && apt-get autoremove -y \
    && apt-get autoclean -y \
    && apt-get clean -y \
    && apt-get purge -y --auto-remove \
    && touch /root/.Xauthority

ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

COPY bin/geckodriver /usr/bin/geckodriver
COPY docker/selenium/run_parser.sh /usr/bin/run_parser
RUN chmod +x /usr/bin/run_parser \
    && chmod a+x /usr/bin/geckodriver  \
    && chmod a+x /usr/bin/firefox \
    && sed -i -e 's/\r$//' /usr/bin/run_parser

RUN pip3 install --no-cache-dir -r /requirements/selenium.txt


# base test image
FROM --platform=linux/amd64 selenium as base_tests
COPY requirements /requirements
COPY docker/selenium/run_tests.sh /usr/bin/run_tests
RUN pip3 install --no-cache-dir -r /requirements/tests.txt -r /requirements/db.txt -r /requirements/selenium.txt \
    && rm -rf /requirements \
    && chmod +x /usr/bin/run_tests \
    && sed -i -e 's/\r$//' /usr/bin/run_tests