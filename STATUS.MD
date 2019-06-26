# HARMONY RELEASE STATUS PAGE

## CURRENT RELEASE

**Release Date -** Tuesday June 25th 19:00 Pacific Time

**Release Type -** Rolling Upgrade

**Release Version -** v3768-r3_20190626-0-g12bb1d44

**Release Detail -** Harmony (C) 2018. harmony, version v3768-r3_20190626-0-g12bb1d44 (jenkins@ 2019-06-26T02:45:49+0000)


## ACTION REQUIRED
**Auto Upgrade -** None
**Manual Upgrade -**  Manually restart node.sh

## PLANNED RELEASES

## PREVIOUS RELEASES

## Additional Information

**Checking your version -** `./mystatus.sh`

**Ensuring you have the latest version of the software**

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


