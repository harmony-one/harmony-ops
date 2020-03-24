#!/bin/bash

container_name="harmony_node"

if [ "$EUID" = 0 ]
  then echo "Do not run as root, exiting..."
  exit
fi

case "${1}" in
  "run")
    if [ "$(docker inspect -f '{{.State.Running}}' $container_name)" = "true" ]; then
      docker kill "${container_name}"
    fi
    if [ "$(docker ps -a | grep $container_name)" ]; then
      docker rm "${container_name}"
    fi
    rm -rf ./."${container_name}"
    mkdir ./."${container_name}"
    echo ""
    echo "[!] Storing node files on host machine at: $(pwd)/.${container_name}"
    echo ""
    eval docker run --name "${container_name}" -v "$(pwd)/.${container_name}:/root/node" -it harmonyone/sentry "${@:2}"
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
      == Sentry node deployment help message ==

      Param:                 Help:

      run <main params>      Main execution to run a sentry node.
                                If errors are given for other params, this needs to be ran.
      activate               Make validator associated with sentry elegable for election in next epoch
      info                   Fetch information for validator associated with sentry
      header                 Fetch the latest header for the node
      export                 Export the private keys associated with this sentry
      attach                 Attach to the docker image to take a look around
      hmy <CLI params>       Call the CLI where the localhost is the current node
      clean                  Kills and remove the node's docker container and shared directory
    "
    exit
    ;;
esac