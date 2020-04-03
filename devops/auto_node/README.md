# Docker image for sentry node deployment

On any machine with docker (install [here](https://docs.docker.com/install/)) one could run a node, create a validator, and maintain it will 1 command.

## Setup

Download the `auto_node.sh` shell script:
```
curl -O https://raw.githubusercontent.com/harmony-one/harmony-ops/master/devops/auto_node/scripts/auto_node.sh && chmod +x ./auto_node.sh && ./auto_node.sh --help
```
> For help on the parameters of `auto_node.sh` use the help option with `./auto_node.sh --help` 

## Usages

1. To run a node, use the `run` param of `auto_node.sh`. For example:
```bash
$ ./auto_node.sh run --clean --auto-active --auto-interaction 
```
> For help or details of the parameters use the `run` help option with `./auto_node.sh run --help`.
>
> Note that keys from the CLI keystore are used to create a validator.

2. Safely kill the node with `./auto_node.sh kill`.

3. Manually activate a node for EPOS with `./auto_node.sh activate`.

4. Get validator information of the account associated with the node with `./auto_node.sh info`.

5. Get latest header of the node with `./auto_node.sh header`.

6. Export the validator private key and BLS key associated with the node with `./auto_node.sh export`.

7. Attach to the docker image (to look around / debug) with `./auto_node.sh attach`.

8. Call the CLI with the node as localhost with `./auto_node.sh hmy <cli args>`.

9. Kill and remove a node's docker container and shared directory with `./auto_node.sh clean`.

### A note on BLS keys

With the `--bls-private-key <BLS PRIVATE KEY>` run option, one could give the private BLS key one wishes to use for their node. 
However, one could also generate the BLS for a specific shard as needed with the `--shard <SHARD ID>` run option.  

## Advanced `run` usage

**It is important to note that the CLI used in the docker image shares the keystore with the host machine.**

* One can define the validator information used in the create validator tx by setting the 
fields in the `validator_config.json` file (which is in the same directory as `auto_node.sh`). 
**Note that this is where you define the wallet linked to the auto_node. Moreover, the defined wallet MUST 
be in the CLI's keystore.**
* If a custom passphrase is needed for the wallet, specify a passphrase toggle with `--wallet-passphrase` run option. 
This will toggle an interactive session and ask for the passphrase when needed. Alternatively, one can specify the
passphrase as a string with the `--wallet-passphrase-string <PASSPHRASE>` run option (this is a less secure option).
* If a validator is already created, auto node will ask to add the BLS key to the validator.
* One can skip all interactions (except for passphrase) with the `--auto-interaction` run option. It will automatically
say yes to creating a validator or adding the BLS key to an existing validator.
* Note that the node files are shared with the host machine and can be inspected / debugged as needed.
* One can define the container name with the `--container=<name>` **PRE-OPTION**. So the run command will now be:
```
./auto_node.sh --container=test123 run --clean --auto-active --auto-interaction
``` 

### `run` help message for reference:
```
== Run a Harmony node & validator automagically ==

optional arguments:
  -h, --help            Show this help message and exit
  --auto-active         Always try to set active when EPOS status is inactive.
  --auto-interaction    Say yes to all interaction (except wallet pw).
  --clean               Clean shared node directory before starting node.
  --wallet-passphrase   Toggle specifying a passphrase interactively
                          If not toggled, default CLI passphrase will be used.
  --wallet-passphrase-string WALLET_PASSPHRASE_STRING
                        Specify passphrase string for validator's wallet.
                          The passphrase may be exposed on the host machine.

  --bls-private-key BLS_PRIVATE_KEY
                        Private BLS key to be used by this node.
                          Note that this is a temp solution and will be removed once the
                          CLI manages the BLS keys.
                          If none provided, a BLS key will be generated with the default CLI passphrase.
  --shard SHARD         Specify shard of generated bls key.
                          Only used if bls private key is not provided.
  --network NETWORK     Network to connect to (staking, partner, stress).
                          Default: 'staking'.
  --duration DURATION   Duration of how long the node is to run in seconds.
                          Default is forever.
  --beacon-endpoint ENDPOINT
                        Beacon chain (shard 0) endpoint for staking transactions.
                          Default is https://api.s0.os.hmny.io/
```

  