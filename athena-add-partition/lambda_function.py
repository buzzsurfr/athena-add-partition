import datetime
import logging
import boto3

print("Loading function")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

athena = boto3.client("athena")


def lambda_handler(event, context):
    # Get data from CloudWatch Scheduled Event
    database = event["database"]
    table = event["table"]
    location = event["location"]
    query_result_location = event["query_result_location"]
    dt = datetime.datetime.now()

    # Format Request
    query_string = f"ALTER TABLE {table}  ADD PARTITION (year=\"{dt.strftime('%Y')}\", month=\"{dt.strftime('%m')}\", day=\"{dt.strftime('%d')}\") LOCATION \"{location}{dt.strftime('%Y')}/{dt.strftime('%m')}/{dt.strftime('%d')}/\""
    logger.debug("query_string: " + query_string)
    query_execution_context = {"Database": database}
    result_configuration = {"OutputLocation": query_result_location}

    # Create new partition in Athena table
    result = athena.start_query_execution(
        QueryString=query_string,
        QueryExecutionContext=query_execution_context,
        ResultConfiguration=result_configuration,
    )

    # Log Query Execution Id
    logger.info("QueryExecutionId: " + result["QueryExecutionId"])

    return
