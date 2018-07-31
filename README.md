# athena-add-partition
Add partition to Athena table based on CloudWatch Event

## Abstract

Following [Partitioning Data](https://docs.aws.amazon.com/athena/latest/ug/partitions.html#scenario-2-data-is-not-partitioned) from the [Amazon Athena documentation](https://docs.aws.amazon.com/athena/latest/ug/what-is.html) for ELB Access Logs (Classic and Application) requires partitions to be created manually.

## Architecture

This template creates a Lambda function to add the partition and a CloudWatch Scheduled Event. Logs are sent from the Load Balancer into a S3 bucket. Daily, the CloudWatch Scheduled Event will invoke the Lambda function to add a partition to the Athena table.

![athena-add-partition Architecture](resources/architecture.png)

## Parameters

The Lambda functions takes parameters passed from the CloudWatch Event:

* _Database:_ The name of the database in Athena. Example: `logs`
* _Table:_ The name of the table in Athena. Example: `elb_logs`
* _Location:_ The S3Uri location of the bucket/prefix where the ELB Access Logs are stored. By default, the logs are prefixed with `/AWSLogs/{{AccountId}}/elasticloadbalancing/{{Region}}/`. Include the trailing slash. Example: `s3://elb-access-logs/AWSLogs/123456789012/elasticloadbalancing/us-east-1/`
* _QueryResultLocation:_ This is required for all Athena calls. I suggest using the default provided in **Settings** in the [Athena console](https://console.aws.amazon.com/athena/home). Example: `s3://aws-athena-query-results-{{AccountId}}-{{Region}}/`

## Deploy to AWS

### Prerequisites

The Athena table for Elastic Load Balancing logs needs to be created/altered to include the partitions for _year_, _month_, and _day_. Copy and paste the following snippet into the [Athena console](https://console.aws.amazon.com/athena/home), substituting for `your_log_bucket`, `prefix`, `AWS_account_ID`, and `region`.

#### Classic Load Balancer

```HiveQL
CREATE EXTERNAL TABLE IF NOT EXISTS elb_logs (
  request_timestamp string,
  elb_name string,
  request_ip string,
  request_port int,
  backend_ip string,
  backend_port int,
  request_processing_time double,
  backend_processing_time double,
  client_response_time double,
  elb_response_code string,
  backend_response_code string,
  received_bytes bigint,
  sent_bytes bigint,
  request_verb string,
  url string,
  protocol string,
  user_agent string,
  ssl_cipher string,
  ssl_protocol string
)
PARTITIONED BY(year string, month string, day string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
 'serialization.format' = '1',
 'input.regex' = '([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:\-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \\\"([^ ]*) ([^ ]*) (- |[^ ]*)\\\" (\"[^\"]*\") ([A-Z0-9-]+) ([A-Za-z0-9.-]*)$' )
LOCATION 's3://your_log_bucket/prefix/AWSLogs/AWS_account_ID/elasticloadbalancing/region/';
```

#### Application Load Balancer

```HiveQL
CREATE EXTERNAL TABLE IF NOT EXISTS alb_logs (  
  type string,  
  time string,  
  elb string,  
  client_ip string,  
  client_port int,  
  target_ip string,  
  target_port int,  
  request_processing_time double,  
  target_processing_time double,  
  response_processing_time double,  
  elb_status_code string,  
  target_status_code string,  
  received_bytes bigint,  
  sent_bytes bigint,  
  request_verb string,  
  request_url string,  
  request_proto string,
  user_agent string,  
  ssl_cipher string,  
  ssl_protocol string,  
  target_group_arn string,  
  trace_id string,  
  domain_name string,  
  chosen_cert_arn string,
  matched_rule_priority string,  
  request_creation_time string,
  actions_executed string,
  redirect_url string
)
PARTITIONED BY(year string, month string, day string)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
'serialization.format' = '1',
'input.regex' =
'([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \"([^ ]*) ([^ ]*) (- |[^ ]*)\" \"([^\"]*)\" ([A-Z0-9-]+) ([A-Za-z0-9.-]*) ([^ ]*) \"([^\"]*)\" \"([^\"]*)\" \"([^\"]*)\" ([-.0-9]*) ([^ ]*) \"([^\"]*)\" \"([^ ]*)\"' )
LOCATION 's3://your_log_bucket/prefix/AWSLogs/AWS_account_ID/elasticloadbalancing/region/';
```

### Deploy using CloudFormation
[![Deploy to AWS](resources/deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=AthenaAddPartition&templateURL=https://s3.amazonaws.com/athenaaddpartition/template.json)

### Deploy Manually

_Coming Soon_

## Usage

### Classic Load Balancer

The queries below have been expanded from [Example Queries for Elastic Load Balancing Logs](https://docs.aws.amazon.com/athena/latest/ug/elasticloadbalancer-classic-logs.html#query-elb-logs-examples) to include the partitions. The below examples use July 31, 2018 as the date for the partition.

Use a query similar to this example. It lists the backend application servers that returned a `4XX` or `5XX` error response code. Use the `LIMIT` operator to limit the number of logs to query at a time.

```SQL
SELECT
 request_timestamp,
 elb_name,
 backend_ip,
 backend_response_code
FROM elb_logs
WHERE
  (
    backend_response_code LIKE '4%' OR
    backend_response_code LIKE '5%'
  ) AND
  (
    year = '2018' AND
    month = '07' AND
    day = '31'
  )
LIMIT 100;
```

Use a subsequent query to sum up the response time of all the transactions grouped by the backend IP address and Elastic Load Balancing instance name.

```SQL
SELECT sum(backend_processing_time) AS
 total_ms,
 elb_name,
 backend_ip
FROM elb_logs WHERE backend_ip <> '' AND
  (
    year = '2018' AND
    month = '07' AND
    day = '31'
  )
GROUP BY backend_ip, elb_name
LIMIT 100;
```

### Application Load Balancer

The queries below have been expanded from [Example Queries for ALB Logs](https://docs.aws.amazon.com/athena/latest/ug/application-load-balancer-logs.html#query-alb-logs-examples) to include the partitions. The below examples use July 31, 2018 as the date for the partition.

The following query counts the number of HTTP GET requests received by the load balancer grouped by the client IP address:

```SQL
SELECT COUNT(request_verb) AS
 count,
 request_verb,
 client_ip
FROM alb_logs
WHERE
  year = '2018' AND
  month = '07' AND
  day = '31'
GROUP BY request_verb, client_ip
LIMIT 100;
```

Another query shows the URLs visited by Safari browser users:

```SQL
SELECT request_url
FROM alb_logs
WHERE user_agent LIKE '%Safari%' AND
  (
    year = '2018' AND
    month = '07' AND
    day = '31'
  )
LIMIT 10;
```

The following example shows how to parse the logs by `datetime`:

```SQL
SELECT client_ip, sum(received_bytes)
FROM alb_logs_config_us
WHERE
  (
    parse_datetime(time,'yyyy-MM-DD''T''HH:mm:ss.SSSSSS''Z')
      BETWEEN
        parse_datetime('2018-07-31-00:00:00','yyyy-MM-DD-HH:mm:ss')
        AND
        parse_datetime('2018-08-01-00:00:00','yyyy-MM-DD-HH:mm:ss')
  ) AND
  (
    year = '2018' AND
    month = '07' AND
    day = '31'
  )
GROUP BY client_ip;
```
