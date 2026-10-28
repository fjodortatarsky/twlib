FROM ubuntu:23.10

RUN apt-get update
RUN apt-get install -y idzebra-2.0

RUN mkdir /zebra
WORKDIR /zebra

EXPOSE 9999

CMD zebrasrv -l zebrasrv.log -f config/yazgfs.xml 

