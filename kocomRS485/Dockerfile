#ARG BUILD_FROM="alpine:latest"
FROM python:3

ENV LANG C.UTF-8

# Copy data for add-on
COPY run.sh makeconf.sh grex.py kocom.py main.py rs485.py settings.py strings.py utility.py /

# Install requirements for add-on
RUN apt-get update && apt-get -y install jq vim
RUN python3 -m pip install pyserial && \
        python3 -m pip install paho-mqtt

WORKDIR /share

RUN chmod a+x /makeconf.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

