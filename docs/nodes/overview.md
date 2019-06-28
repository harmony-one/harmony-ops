# Harmony Ops Monitoring Pipeline
(That is, how we ensure our network is up and running 24/7)

## Design

### Motivation, Goal, *Modus Operandi*

Because system failures are inevitable.  Because we engineers are not omniscient therefore cannot predict all possible ways our system might fail, now or in the future.  Because we are few and adversaries are numerous, and because adversaries are eventually smarter than us.

Because downtimes directly hurt and undermine customer experience and confidence in us.

Because we must therefore minimize, or even try to eliminate, such downtimes.

The last line of defense is: We want to know as soon as a real problem emerges, so that we can fix it ASAP.  But we can, and should, do better.  We want to know as soon as a *potential* problem emerges, so that we can fix it *before* it becomes a real problem.  This is the ultimate goal of our ops pipeline: No real problems = zero impact.

To this end, we want not just evidences of real problems but also *canaries*—early signs of failure.  Again, we want to deal with potential problems before they become real.  We do so by plumbing a pipeline: Data collection → analysis → anomaly detection → alerting.

### Data Collection

We collect various kinds of metrics and logs, into a common database capable of aggregation and searching.

#### System & Process Metrics

We use [Metricbeat](https://www.elastic.co/products/beats/metricbeat).  It supports a wide variety of ready-to-use metric collection methods, named [modules](https://www.elastic.co/guide/en/beats/metricbeat/current/metricbeat-modules.html).  On day one, we use the [System module](https://www.elastic.co/guide/en/beats/metricbeat/current/metricbeat-module-system.html) to monitor CPU and memory saturations, as well as process table.

#### Application Metrics

*[TODO – identify meaningful application metrics to monitor (block height, transaction height, block time, etc.) and make the node software emit them.]*

#### Golang Metrics

*[TODO – [Tuning Go Apps with Metricbeat](https://www.elastic.co/blog/monitor-and-optimize-golang-application-by-using-elastic-stack)]*

#### Logs

*[TODO – consider [Filebeat](https://www.elastic.co/products/beats/filebeat)]*

#### Database

We use [Elasticsearch](https://www.elastic.co/), which functions both as a time-series database and as a full-text search database.  We chose this because 1) it is reasonably fast, 2) it comes up with a wide variety of data search and analysis tools, and 3) it integrates with its own dashboard—Kibana, so it is end-user friendly.

### Anomaly Detection

We use various techniques on the metric/log database, including text searching, metric aggregation, and numeric analysis/comparison, to detect abnormal behaviors of our systems.

We have evaluated various existing solutions, but none of them perfectly fits our use (flexibility or cost).  Plus, we are starting with a few metrics over which we want to quickly iterate, with more to come in explorative fashion.  Therefore, we are starting with a hand-rolled script: We care more about giving those who know what they are doing—including ourselves—with full control, than about making it possible for less technical people to add their own tweaks.  For the latter, we may later roll the logic into an existing FOSS tool that we can use.

### Alerting

When our tool detects anomalies (CPU saturation, memory leaks…), it raises an alert with PagerDuty.  An alert is a signal of something potentially going out of ordinary.
Upon receiving an alert, PagerDuty can turn that into an incident.  An incident is an issue that needs human intervention and resolution.
We use PagerDuty for alert and incident management.  It has an easy-to-use [Events API](https://v2.developer.pagerduty.com/docs/events-api-v2), which our tool uses to post alerts.  Alert-to-incident policy is managed within PagerDuty.

### How-tos

TBD

## FAQ

### “Elasticsearch?  Why not OpenTSDB, InfluxDB, or any other time-series database?”

It is true that a true TSDB is faster than Elasticsearch, but we choose Elasticsearch for three reasons:

* Time-series databases achieve their efficiency by optimizing on the axs of the cardinality of objects to monitor, such as number of hosts.  As the cardinality increases, one of the two degradations occur: 1) Indexing speed of overall documents slow down due to mono-dimensional expansion of the key space (as is the case with OpenTSDB), or 2) the memory consumption increases linearly (as is the case with InfluxDB).  Since our number of nodes is not fixed, and new nodes come and go constantly, the node key space grows unbounded (as the network will always see more node keys, such as hostnames or instance IDs).  Elasticsearch does not suffer from this limitation.
* Time-series databases typically require careful setup of new key (tag) spaces, meaning that every time we need to add a new type of search key such as hostname or network interface name, we need to hand-configure them into the TSDB.  Elasticsearch does not suffer from this limitation: Being an inverted-index database, Elasticsearch avails new fields for searching by default, enabling “just start emitting new fields” operation and simplifying the pipeline.
* We need a searchable log database, for which Elasticsearch has been proven to do its job adequately, so we are using Elasticsearch anyways.  Using it as a TSDB as well makes the overall ops simpler – one product to maintain, and not two.

### “Filebeat?  Not Logstash?”

Logstash as a log emitter is too heavy, because it is highly flexible and comes with a lot of log transformation/enrichment features that we do not need on day one.  Plus, Logstash is written in Java, so it is too heavy to run on often-resource-constrained nodes.

Filebeat, on the other hand, is a simple log shipper, and being written in Go, is much lighter than Logstash.  In general, Filebeat and Metricbeat are members of the Beats family of lightweight agents, specifically designed for being embedded into systems monitored.

### “What’s wrong with existing alerting tools?”

**Cost** – Elastic [X-Pack](https://www.elastic.co/products/stack/alerting) comes with alerting, but it’s not free, and can’t be installed on AWS-hosted Elasticsearch instances.

**Rigidity** – [Yelp/elastalert](https://github.com/Yelp/elastalert) is a popular FOSS alternative to X-Pack, but it cannot use data crunching features of Elasticsearch such as [aggregations](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations.html), which we routinely need to monitor hundreds of hosts at once.





