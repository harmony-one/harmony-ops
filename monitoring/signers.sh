for x in `curl -s https://raw.githubusercontent.com/harmony-one/harmony/master/internal/genesis/foundational.go | grep Address | cut -d'"' -f4`; do grep $x ./latest/validator*.log; done > fn-signers
for x in `curl -s https://github.com/harmony-one/harmony/blob/master/internal/genesis/genesis.go | grep Address | cut -d'"' -f4`; do grep $x ./latest/validator*.log; done > genesis-signers