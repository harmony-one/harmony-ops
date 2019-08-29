#!/usr/bin/env bash

# upload.sh - Generates and uploads all the files to the harmony.one website

### Run generation scripts
./online.sh

dump=$(aws --profile website s3 cp ./network.txt\
       s3://harmony.one/pga/network --acl public-read)
dump=$(aws --profile website cloudfront create-invalidation\
       --distribution-id ${website_dist_id} --path /pga/network)
