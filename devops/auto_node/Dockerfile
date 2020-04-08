FROM ubuntu:18.04

SHELL ["/bin/bash", "-c"]

WORKDIR /root

RUN apt update && apt upgrade -y && apt install psmisc dnsutils curl python3 python3-pip -y

RUN mkdir -p /root/node

RUN python3 -m pip install pyhmy

RUN python3 -m pip install requests

COPY run.py /root

COPY utils.py /root

RUN chmod +x /root/run.py

COPY scripts/info.sh /root

RUN chmod +x /root/info.sh

COPY scripts/activate.sh /root

RUN chmod +x /root/activate.sh

COPY scripts/deactivate.sh /root

RUN chmod +x /root/deactivate.sh

COPY scripts/balances.sh /root

RUN chmod +x /root/balances.sh

COPY scripts/export.sh /root

RUN chmod +x /root/export.sh

COPY scripts/header.sh /root

RUN chmod +x /root/header.sh

COPY scripts/headers.sh /root

RUN chmod +x /root/headers.sh

COPY scripts/version.sh /root

RUN chmod +x /root/version.sh

ENTRYPOINT ["/root/run.py"]