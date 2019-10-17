version := $(shell git rev-list --count HEAD)
commit := $(shell git describe --always --long --dirty)
built_at := $(shell date +%FT%T%z)
built_by := ${USER}@harmony.one

flags := -gcflags="all=-N -l -c 2"
ldflags := -X main.version=v${version} -X main.commit=${commit}
ldflags += -X main.builtAt=${built_at} -X main.builtBy=${built_by}
watchdog := blockchain-watchd
watchdog_src := $(wildcard blockchain-watchdog/*.go)

env := GO111MODULE=on

all: watchdog
	./$(watchdog) version

watchdog:
	@ $(env) go build -ldflags="$(ldflags)" \
-o $(watchdog) ${watchdog_src}

iterate:all
	./$(watchdog) monitor --watch ./monitor-testnet.yaml

.PHONY:clean

clean:
	rm -f ${watchdog}
