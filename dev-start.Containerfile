FROM docker.io/library/ubuntu:24.04


RUN apt update && apt upgrade -y &&\
    apt install -y openjdk-8-jdk-headless ant wget unzip python3 python-is-python3 python3-pip &&\
    apt clean

COPY . /src

WORKDIR /src

RUN cd /src && ./dev.sh setup

ENV WEB_BINDADDRESS=0.0.0.0
ENV CODESERVER_BINDADDRESS=0.0.0.0

EXPOSE 8000
EXPOSE 9876
EXPOSE 5000

# New Portion for RAG

RUN pip3 install --no-cache-dir --break-system-packages -r add/requirements.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
