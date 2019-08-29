#!/usr/bin/env bash

# upload.sh - Generates and uploads all the files to the harmony.one website

### Run generation scripts
./check.sh
./offline.sh
./hourly.sh
./quadly.sh
./daily.sh
./totally.sh

### 1h
# Text file
dump=$(aws --profile website s3 cp ./generated/1h/1h.txt\
       s3://harmony.one/pga/1h --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/1h)
# CSV file
dump=$(aws --profile website s3 cp ./generated/1h/1h.csv\
       s3://harmony.one/pga/1h.csv --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/1h.csv)
# JSON file
dump=$(aws --profile website s3 cp ./generated/1h/1h.json\
       s3://harmony.one/pga/1h.json --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/1h.json)

### 4h
# Text file
dump=$(aws --profile website s3 cp ./generated/4h/4h.txt\
       s3://harmony.one/pga/4h --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/4h)
## CSV file
dump=$(aws --profile website s3 cp ./generated/4h/4h.csv\
       s3://harmony.one/pga/4h.csv --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/4h.csv)
## JSON file
dump=$(aws --profile website s3 cp ./generated/4h/4h.json\
       s3://harmony.one/pga/4h.json --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/4h.json)

### 24h
# Text file
dump=$(aws --profile website s3 cp ./generated/24h/24h.txt\
       s3://harmony.one/pga/24h --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/24h)
# CSV file
dump=$(aws --profile website s3 cp ./generated/24h/24h.csv\
       s3://harmony.one/pga/24h.csv --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/24h.csv)
# JSON file
dump=$(aws --profile website s3 cp ./generated/24h/24h.json\
       s3://harmony.one/pga/24h.json --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/24h.json)

### balances
# Text file
dump=$(aws --profile website s3 cp ./generated/balances/balances.txt\
       s3://harmony.one/pga/balances --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/balances)
# CSV file
dump=$(aws --profile website s3 cp ./generated/balances/balances.csv\
       s3://harmony.one/pga/balances.csv --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/balances.csv)
# JSON file
dump=$(aws --profile website s3 cp ./generated/balances/balances.json\
       s3://harmony.one/pga/balances.json --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/balances.json)
