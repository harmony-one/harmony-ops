### harmony-monitoring

##### Step 1

set config in `.env` file

```
MODE=mainnet // or testnet
GIT_TOKEN=<your github token>
MIN_STORAGE_SPACE=5
PROMETHEUS_SCRAPE_INTERVAL=5
```



##### Step 2

run the python script to download latest ip list and create grafana & prometheus configs

```bash
python ./update_db_config.py
```

it will create configs under `prometheus` and `grafana/dashboards`



##### Step3

build docker images

```bash
docker-compose build
```

perhaps, you need to clear old imgae volumes before build as follows

```bash
docker volume rm harmony-monitoring_prometheus_data &&
docker volume rm harmony-monitoring_grafana_data
```

otherwise, this configuration will not take effect



##### Step 4

run the containers by docker compose

```bash
docker-compose up
```

