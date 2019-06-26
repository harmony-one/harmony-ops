# harmony-ops

Harmony Ops Master Repository.

# Cheat Sheet

**Setup**

`tmux attach-session -t node` or `tmux new-session -s node`

**Monitoring - Capture your system information**
```
curl -OL http://harmony.one/mystatus.sh
chmod u+x ./mystatus.sh
./mystatus.sh all
```

**Wallet - Upgrade to the latest wallet**
```
curl -LO https://harmony.one/wallet.sh
chmod u+x wallet.sh
./wallet.sh -d
./wallet.sh list
```

**Node - Download latest version of [node.sh](https://harmony.one/node.sh) and restart with clean instance**
```
curl -LO https://harmony.one/node.sh
chmod a+x node.sh
sudo ./node.sh -c
```
