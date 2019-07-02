#!/bin/bash

PUB_IP=$(dig @resolver1.opendns.com ANY myip.opendns.com +short)
PORT=9000

sudo ./soldier -ip $PUB_IP -port $PORT
