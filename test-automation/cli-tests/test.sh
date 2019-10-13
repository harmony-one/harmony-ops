#!/usr/bin/env bash
go_path=$(go env GOPATH)
cli_path=$go_path/src/github.com/harmony-one/go-sdk
harmony_path=$go_path/src/github.com/harmony-one/harmony
src_dir="$( cd "$(dirname "$0")" ; pwd -P )"
harmony_branch="master"
cli_branch="master"
force_checkout=false

source $go_path/src/github.com/harmony-one/harmony/scripts/setup_bls_build_flags.sh

while getopts hb:f option 
do 
 case "${option}" 
 in 
 b) harmony_branch=${OPTARG};; 
 h) echo "Options:"
    echo "    -b <branch name>   Branch name for main harmony repo. Default is master."
    echo "    -c <branch name>   Branch name for cli repo. Default is master."
    echo "    -f                 Force stash then checkout." 
    echo "    -h                 Help.";; 
 esac 
done 

function pull_and_build_cli(){
    cd $cli_path
    if ! (git checkout $cli_branch); then
        if $force_checkout ; then
            git stash && git checkout $cli_branch
        else
            exit 1
        fi
    elif ! (git pull -r origin $cli_branch); then
        exit 1
    elif ! (make); then
        exit 1
    else 
        cp $cli_path/hmy $src_dir/tests/hmy
    fi
    cd $src_dir
}


function pull_and_build_localnet(){
    cd $harmony_path
    if ! (git checkout $harmony_branch); then 
        if $force_checkout ; then
            git stash && git checkout $harmony_branch
        else
            exit 1
        fi
    elif ! (git pull -r origin $harmony_branch); then 
        exit 1
    elif ! (make); then 
        exit 1
    fi
    cd $src_dir
}

echo "'go-sdk/$cli_branch' repo and 'harmony/$harmony_branch' repo will get rebased. Is this okay? [Y/n]"
read input
if [ "$input" != "Y" ]; then
    exit
fi
pull_and_build_cli
pull_and_build_localnet
cd $harmony_path && bash test/kill_node.sh
rm -rf tmp_log*
./test/deploy.sh $harmony_path/test/configs/local-resharding.txt > /dev/null &
cd $src_dir/tests && bash launch_test.sh
cd $harmony_path && bash test/kill_node.sh
