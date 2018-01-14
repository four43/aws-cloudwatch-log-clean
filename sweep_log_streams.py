#!/usr/bin/env python3
import argparse
from datetime import datetime, timedelta
from dateutil import tz

import boto3

client = boto3.client('logs')


def print_log_group(log_group, message):
    print("[{}] {}".format(log_group['logGroupName'], message))


def get_log_groups(prefix, next_token=None):
    opts = {
        'logGroupNamePrefix': prefix,
        'limit': 50  # Maximum
    }
    if next_token:
        opts['nextToken'] = next_token
    log_groups_response = client.describe_log_groups(**opts)
    if log_groups_response:
        for log_group in log_groups_response['logGroups']:
            yield log_group
        # Exhausted, try to loop with paging token
        if 'nextToken' in log_groups_response:
            yield from get_log_groups(prefix, log_groups_response['nextToken'])


def get_streams(log_group, next_token=None):
    opts = {
        'logGroupName': log_group['logGroupName'],
        'limit': 50  # Max
    }
    if next_token:
        opts['nextToken'] = next_token

    response = client.describe_log_streams(**opts)

    if response:
        for stream in response['logStreams']:
            yield stream
        if 'nextToken' in response:
            yield from get_streams(log_group, response['nextToken'])


def delete_old_streams(log_group, dry_run=False):
    """
    Delete old log streams that are empty. Events get cleaned up by log_group['retentionInDays'] but the streams don't.
    """
    print_log_group(log_group, "Checking for old streams...")

    now = datetime.utcnow().replace(tzinfo=tz.tzutc())
    if 'retentionInDays' in log_group:
        oldest_valid_event = now - timedelta(days=log_group['retentionInDays'])
    else:
        # Log group has no expiration set, we're done here.
        print_log_group(log_group, "Log Group has no expiration set, skipping.")
        return

    print(" - Streams in group: " + log_group['logGroupName'])
    for stream in get_streams(log_group):

        # lastEventTimestamp doesn't update right away sometimes or if the stream was created with no events
        # it is missing
        if 'lastEventTimestamp' in stream:
            stream_time = datetime.fromtimestamp(stream['lastEventTimestamp'] / 1000, tz=tz.tzutc())
        else:
            # Assume stream creation if we don't have a lastEventTimestamp
            stream_time = datetime.fromtimestamp(stream['creationTime'] / 1000, tz=tz.tzutc())

        if stream_time < oldest_valid_event:
            if dry_run:
                print_log_group(log_group, "Would delete stream: " + stream['logStreamName'] + " (--dry-run set)")
            else:
                print_log_group(log_group, "Deleting stream: " + stream['logStreamName'])
                delete_result = client.delete_delete_log_stream(
                    logGroupName=log_group['logGroupName'],
                    logStreamName=stream['logStreamName']
                )
                print(delete_result)
                print_log_group(log_group, "Deleted stream: " + stream['logStreamName'])
        else:
            print_log_group(log_group, "Checked stream, keeping: " + stream['logStreamName'])


def get_arg_parser():
    parser = argparse.ArgumentParser(description="Cleans up old and empty log streams from log groups matching a "
                                                 "provided pattern")

    parser.add_argument("--dry-run",
                        dest="dry_run",
                        action="store_true",
                        help="Just print what we're going to do, don't actually do it."
                        )

    parser.add_argument("prefix",
                        help="The log group prefix to filter for. Example: '/aws/lambda/app-staging-'"
                        )
    return parser


def main(prefix, dry_run=False):
    for log_group in get_log_groups(prefix):
        delete_old_streams(log_group, dry_run)
    print("Done")


if __name__ == "__main__":
    args = get_arg_parser().parse_args()
    main(args.prefix, args.dry_run)
