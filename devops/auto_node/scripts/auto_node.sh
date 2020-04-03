#!/bin/bash

if [ "$EUID" = 0 ]
  then echo "Do not run as root, exiting..."
  exit
fi

validator_config_path="./validator_config.json"
container_name="harmony_node"
case $1 in
  --container=*)
    container_name="${1#*=}"
    shift;;
esac

if [ ! -f "$validator_config_path" ]; then
    echo '{
     "validator-addr": null,
     "name": "harmony_autonode",
     "website": "harmony.one",
     "security-contact": "Daniel-VDM",
     "identity": "auto-node",
     "amount": 10100,
     "min-self-delegation": 10000,
     "rate": 0.1,
     "max-rate": 0.75,
     "max-change-rate": 0.05,
     "max-total-delegation": 1000000.0,
     "details": "None"
}' > $validator_config_path
fi

case "${1}" in
  "run")
    if [ ! -d "${HOME}/.hmy_cli" ]; then
      echo "CLI keystore not found at ~/.hmy_cli. Create or import a wallet using the CLI before running autonode.sh"
      exit
    fi
    if [ "$(docker inspect -f '{{.State.Running}}' "$container_name")" = "true" ]; then
      echo "[!!] Killing existing docker container with name: $container_name"
      docker kill "${container_name}"
    fi
    if [ "$(docker ps -a | grep $container_name)" ]; then
      echo "[!!] Removing existing docker container with name: $container_name"
      docker rm "${container_name}"
    fi
    if [ ! -d "$(pwd)/.$container_name}" ]; then
      mkdir "$(pwd)/.$container_name"
    fi
    cp $validator_config_path "$(pwd)/.${container_name}/validator_config.json"

    echo ""
    echo "[!] Using validator config at: $validator_config_path"
    echo "[!] Sharing node files on host machine at: $(pwd)/.${container_name}"
    echo "[!] Sharing CLI files on host machine at: ${HOME}/.hmy_cli"
    echo ""

    # Warning: Assumption about CLI files, might have to change in the future...
    eval docker run --name "${container_name}" -v "$(pwd)/.${container_name}:/root/node" \
     -v "${HOME}/.hmy_cli/:/root/.hmy_cli" -it harmonyone/sentry "${@:2}"
    ;;
  "activate")
    docker exec -it "${container_name}" /root/activate.sh
    ;;
  "info")
    docker exec -it "${container_name}" /root/info.sh
    ;;
  "header")
    docker exec -it "${container_name}" /root/header.sh
    ;;
  "export")
    docker exec -it "${container_name}" /root/export.sh
    ;;
  "attach")
    docker exec -it "${container_name}" /bin/bash
    ;;
  "kill")
    docker exec -it "${container_name}" /bin/bash -c "killall harmony"
    docker kill "${container_name}"
    ;;
  "hmy")
    docker exec -it "${container_name}" /root/bin/hmy "${@:2}"
    ;;
  "clean")
    docker kill "${container_name}"
    docker rm "${container_name}"
    rm -rf ./."${container_name}"
    ;;
  *)
    echo "
      == Harmony auto-node deployment help message ==

      Optional:            Param:             Help:

      [--container=<name>] run <run params>   Main execution to run a sentry node. If errors are given
                                                for other params, this needs to be ran. Use '-h' for run help msg.
      [--container=<name>] activate           Make validator associated with sentry elegable for election in next epoch
      [--container=<name>] info               Fetch information for validator associated with sentry
      [--container=<name>] header             Fetch the latest header for the node
      [--container=<name>] export             Export the private keys associated with this sentry
      [--container=<name>] attach             Attach to the docker image to take a look around
      [--container=<name>] hmy <CLI params>   Call the CLI where the localhost is the current node
      [--container=<name>] clean              Kills and remove the node's docker container and shared directory
    "
    exit
    ;;
esac