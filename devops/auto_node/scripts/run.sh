#!/bin/bash
set -e

unset val_acc_private_key bls_private_key network duration name beacon_endpoint active yes clear generate_shard
val_acc_private_key=$1
bls_private_key=''
network=staking
beacon_endpoint="https://api.s0.os.hmny.io/"
active=false
yes=false
clear=false
name=''
duration=0
generate_shard=-1

for i in "${@}"
do
case $i in
    -s=*)
       generate_shard="${i#*=}"
       shift ;;
    -K=*)
       bls_private_key="${i#*=}"
       shift ;;
    -N=*)
       network="${i#*=}"
       shift ;;
    -D=*)
       duration="${i#*=}"
       shift ;;
    -n=*)
       name="${i#*=}"
       shift ;;
    -e=*)
       beacon_endpoint="${i#*=}"
       shift ;;
    -a)
      active=true
      shift ;;
    -y)
      yes=true
      shift ;;
    -c)
      clear=true
      shift ;;
    -h | --help)
      echo '
      == Main node execution help message ==

      Ex:
        ./run.sh 0336e9be71c31d71d086d9f0887d13cb6701bc45d11b70bb7c14200c9feebe22 \
          -K=04014f864cde86a2bee342d6228ffcdcbb8d0ea4e3c4bc7748dfa4b4067c5845 \
          -N=staking -e=https://api.s0.os.hmny.io/ -n=Harmony_Sentry_1 -a -y -c

      Args:
        1) Validator wallet private key

      Options:
        -K=bls-private-key   Private BLS key for this node
        -N=network           Network to connect to (mainnet, testnet, staking, partner, stress, devnet)
                               default: staking
        -D=duration          How long the node is to run in seconds
                               default: infinite
        -s=shard-id          Shard id of generated bls key. Only considered if no private key is given.
        -n=name              The name of the validator that is created (if applicable).
                               Note that this name must NOT contain spaces.
                               default: harmony_sentry_<random number>
        -e=endpoint          Beacon chain endpoint for staking transactions
                               default: https://api.s0.os.hmny.io/
        -a                   Always try to set active when EPOS status is inactive
        -y                   Say yes to all interaction
        -c                   Clean directory before starting node
    '
    exit
      ;;
  esac
done

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Validator wallet private key: ${val_acc_private_key}"
echo "BLS private key: ${bls_private_key}"
echo "Network: ${network}"
echo "Beacon Chain endpoint: ${beacon_endpoint}"
echo "Validator Name: ${name}"
echo "Duration: ${duration}"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""

echo "${val_acc_private_key}}" > /.val_acc_private_key
echo "${bls_private_key}" > /.bls_private_key
echo "${network}" > /.network
echo "${beacon_endpoint}" > /.beacon_endpoint
echo "${duration}" > /.duration
echo "${name}" > /.name
echo "${active}" > /.active
echo "${yes}" > /.yes
echo "${clear}" > /.clear

run_command="python3 -u /root/run.py ${val_acc_private_key} --network ${network} --beacon_endpoint ${beacon_endpoint}"

if [ "${bls_private_key}" != '' ]; then
  run_command="${run_command} --private_bls_key ${bls_private_key}"
fi

if [ "${name}" != '' ]; then
  run_command="${run_command} --name ${name}"
fi

if [ "${duration}" != 0 ]; then
  run_command="${run_command} --duration ${duration}"
fi

if [ "${generate_shard}" != -1 ]; then
  run_command="${run_command} --generate_shard ${generate_shard}"
fi

if [ "${active}" = "true" ]; then
  run_command="${run_command} --active"
fi

if [ "${yes}" = "true" ]; then
  run_command="${run_command} --confirm_all"
fi

if [ "${clear}" = "true" ]; then
  run_command="${run_command} --active"
fi

eval "$run_command"