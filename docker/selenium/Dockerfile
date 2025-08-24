FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /code

RUN apt update &&  \
    apt install -y --assume-yes postgresql-client-17 && \
    apt install -y git && \
    apt-get install libgeos-dev ffmpeg -y

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-dev \
    xvfb \
    xauth \
    fluxbox \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libxss1 \
    libpci3 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/* \
#    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
#    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \

ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

COPY docker/selenium/run_selenium.sh /usr/bin/run_selenium
RUN chmod +x /usr/bin/run_selenium

ENV DISPLAY=:99
ENV RESOLUTION=1920x1080x24

COPY requirements requirements

COPY requirements/base.txt requirements/base.txt
COPY requirements/tests.txt requirements/tests.txt
COPY requirements/selenium.txt requirements/selenium.txt

RUN pip3 install --upgrade pip
RUN pip3 install --upgrade setuptools
RUN pip3 install -r requirements/base.txt
RUN pip3 install -r requirements/selenium.txt
RUN pip3 install "git+https://github.com/ytdl-org/youtube-dl.git"

