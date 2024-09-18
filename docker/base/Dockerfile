FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /code

RUN apt update &&  \
    apt install -y --assume-yes git postgresql-client-15 && \
    apt-get install libgeos-dev ffmpeg -y

COPY requirements requirements

COPY requirements/base.txt requirements/base.txt
COPY requirements/tests.txt requirements/tests.txt

RUN pip3 install -r requirements/base.txt
# RUN pip3 install -r requirements/tests.txt
RUN pip3 install "git+https://github.com/ytdl-org/youtube-dl.git"