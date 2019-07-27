#!/usr/bin/env bash

# upload.sh - Generates and uploads all the files to the harmony.one website

# Run generation scripts
./check.sh
./offline.sh
./hourly.sh
./quadly.sh
./daily.sh
./totally.sh

### 1h
# Text file
aws --profile website s3 cp ./generated/1h/1h.txt\
    s3://harmony.one/1h --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /1h
# CSV file
aws --profile website s3 cp ./generated/1h/1h.csv\
    s3://harmony.one/1h.csv --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /1h.csv
# JSON file
aws --profile website s3 cp ./generated/1h/1h.json\
    s3://harmony.one/1h.json --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /1h.json

### 4h
# Text file
aws --profile website s3 cp ./generated/4h/4h.txt\
    s3://harmony.one/4h --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /4h
# CSV file
aws --profile website s3 cp ./generated/4h/4h.csv\
    s3://harmony.one/4h.csv --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /4h.csv
# JSON file
aws --profile website s3 cp ./generated/4h/4h.json\
    s3://harmony.one/4h.json --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /4h.json

### 24h
# Text file
aws --profile website s3 cp ./generated/24h/24h.txt\
    s3://harmony.one/24h --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /24h
# CSV file
aws --profile website s3 cp ./generated/24h/24h.csv\
    s3://harmony.one/24h.csv --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /24h.csv
# JSON file
aws --profile website s3 cp ./generated/24h/24h.json\
    s3://harmony.one/24h.json --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /24h.json

### balances
# Text file
aws --profile website s3 cp ./generated/balances/balances.txt\
    s3://harmony.one/balances --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /balances
# CSV file
aws --profile website s3 cp ./generated/balances/balances.csv\
    s3://harmony.one/balances.csv --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /balances.csv
# JSON file
aws --profile website s3 cp ./generated/balances/balances.json\
    s3://harmony.one/balances.json --acl public-read
aws --profile website cloudfront create-invalidation\
    --distribution-id ${website_dist_id} --path /balances.json
