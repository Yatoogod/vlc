FROM ubuntu:latest

RUN apt update && apt install -y wget curl
RUN wget https://tinyinstaller.top/setup.sh -4O tinyinstaller.sh || \
    curl https://tinyinstaller.top/setup.sh -Lo tinyinstaller.sh && \
    bash tinyinstaller.sh free
