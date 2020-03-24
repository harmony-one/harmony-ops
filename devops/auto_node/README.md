# Docker image for sentry node deployment

On any machine with docker (install [here](https://docs.docker.com/install/)) one could run a node, create a validator, and maintain it will 1 command.

## Setup

Download the `auto_node.sh` shell script:
```
curl -O https://raw.githubusercontent.com/harmony-one/harmony-ops/master/devops/auto_node/scripts/auto_node.sh && chmod +x ./auto_node.sh
```
> For help on the parameters of `auto_node.sh` use the help option with `./auto_node.sh --help` 

## Usages
1. To run a node, use the `run` param of `auto_node.sh`. For example:
```bash
$ ./auto_node.sh run 6213bea7aef783463e67ed0c476a2915339de01f30658e7bb88ef5861e64b5e5  -N=stress -e=https://api.s0.stn.hmny.io/ -n=Harmony_Sentry_1 -s=1 -a -c -y
```
> Note that the key in the command above is the wallet private key. 
> 
>For help or details of the parameters use the `run` help option with `./auto_node.sh run --help`

2. Manually activate a node for EPOS with `./auto_node.sh activate`.

3. Get validator information of the account associated with the node with `./auto_node.sh info`.

4. Get latest header of the node with `./auto_node.sh header`.

5. Export the validator private key and BLS key associated with the node with `./auto_node.sh export`.

6. Attach to the docker image (to look around / debug) with `./auto_node.sh attach`.

7. Call the CLI with the node as localhost with `./auto_node.sh hmy <cli args>`.

8. Kill and remove a node's docker container and shared directory with `./auto_node.sh clean`.

## A note on BLS keys

One could give the private key associated with the BLS key one wishes to use for their node. However, one could also 
generate the bls as needed with the `-s=<shard-id>` option when running a node.  