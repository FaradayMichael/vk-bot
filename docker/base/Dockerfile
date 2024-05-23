FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV TZ=Etc/UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /code
RUN apt update
RUN apt install -y --assume-yes python3-dev libpq-dev build-essential python3-pip git
RUN apt-get install libgeos-dev -y
RUN apt-get install ffmpeg -y


COPY requirements requirements


COPY requirements/base.txt requirements/base.txt
COPY requirements/tests.txt requirements/tests.txt


RUN pip3 install -r requirements/base.txt
RUN pip3 install -r requirements/tests.txt
RUN pip3 install --upgrade --force-reinstall "git+https://github.com/ytdl-org/youtube-dl.git"