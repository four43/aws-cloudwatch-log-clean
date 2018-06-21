#!/usr/bin/env python3
import argparse
import boto3

client = boto3.client('logs')


def get_log_group_config(log_group_name):
    log_groups_result = client.describe_log_groups(
        logGroupNamePrefix=log_group_name,
        limit=2
    )
    log_groups = log_groups_result['logGroups']
    if len(log_groups) == 0:
        # No log group found
        raise Exception("No log groups found by name: " + log_group_name)
    elif len(log_groups) > 1:
        # Still okay if it matches exactly.
        if log_groups[0]['logGroupName'] != log_group_name:
            # Too many log groups found
            raise Exception("More than one log group found, be more specific: {}\n"
                            " - Nuking a log group is pretty destructive, we'll just do one at a time for now"
                            .format(log_group_name))

    log_group_config = log_groups[0]

    if log_group_config['logGroupName'] != log_group_name:
        # Name wasn't an exact match
        raise Exception("Log group found a single match but it wasn't quite right.\n"
                        "Did you mean: " + log_group_config['logGroupName'] + " ?")
    return log_group_config


def get_log_group_metric_filters(log_group_name, next_token=None):
    opts = {
        'logGroupName': log_group_name,
        'limit': 50  # Maximum
    }
    if next_token:
        opts['nextToken'] = next_token

    metric_filters_response = client.describe_metric_filters(**opts)
    if metric_filters_response:
        for metric_filter in metric_filters_response['metricFilters']:
            yield metric_filter
        # Exhausted, try to loop with paging token
        if 'nextToken' in metric_filters_response:
            yield from get_log_group_metric_filters(log_group_name, metric_filters_response['nextToken'])


def get_log_group_subscription_filters(log_group_name, next_token=None):
    opts = {
        'logGroupName': log_group_name,
        'limit': 50  # Maximum
    }
    if next_token:
        opts['nextToken'] = next_token

    subscription_filters_response = client.describe_subscription_filters(**opts)
    if subscription_filters_response:
        for subscription_filter in subscription_filters_response['subscriptionFilters']:
            yield subscription_filter
        # Exhausted, try to loop with paging token
        if 'nextToken' in subscription_filters_response:
            yield from get_log_group_subscription_filters(log_group_name, subscription_filters_response['nextToken'])


def main(log_group_name, dry_run=False):
    log_group_config = get_log_group_config(log_group_name)

    log_group_tags = client.list_tags_log_group(
        logGroupName=log_group_name
    )['tags']

    # Fully pump our generator, we're deleting this resource so make sure we have everything first.
    log_group_metric_filters = []
    for metric_filter in get_log_group_metric_filters(log_group_name):
        log_group_metric_filters.append(metric_filter)

    # Fully pump our generator, we're deleting this resource so make sure we have everything first.
    log_group_subscription_filters = []
    for subscription_filter in get_log_group_subscription_filters(log_group_name):
        log_group_subscription_filters.append(subscription_filter)

    # Delete log group
    if dry_run:
        print("Would delete: {} (but --dry-run is set)".format(log_group_name))
    else:
        print("Deleting: {}".format(log_group_name))
        client.delete_log_group(
            logGroupName=log_group_name
        )

    # Create new log group
    create_opts = {
        'logGroupName': log_group_name
    }
    if 'kmsKeyId' in log_group_config:
        create_opts['kmsKeyId'] = log_group_config['kmsKeyId']
    if len(log_group_tags):
        create_opts['tags']: {
            **log_group_tags
        }

    if dry_run:
        print("Would create new log group: " + log_group_name + " (but --dry-run is set)")
    else:
        print("Creating: {}".format(log_group_name))
        client.create_log_group(**create_opts)

    # Put everything back
    # Expire
    if dry_run:
        print(
            "Would put new retention policy of {} days (but --dry-run is set)"
                .format(log_group_config['retentionInDays'])
        )
    else:
        print("Setting expiration to: {} days".format(log_group_config['retentionInDays']))
        client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=log_group_config['retentionInDays']
        )

    # Metric Filter
    for metric_filter in log_group_metric_filters:
        if dry_run:
            print("Would put metric filter {} (but --dry-run is set)".format(metric_filter['filterName']))
        else:
            print("Putting metric filter {}".format(metric_filter['filterName']))
            del metric_filter['creationTime']
            client.put_metric_filter(
                **metric_filter
            )

    # Subscriptions
    for subscription_filter in log_group_subscription_filters:
        if dry_run:
            print("Would put subscription filter for {} (but --dry-run is set)"
                  .format(subscription_filter['destinationArn']))
        else:
            print("Putting subscription filter for {}".format(subscription_filter['destinationArn']))
            del subscription_filter['creationTime']
            client.put_subscription_filter(
                **subscription_filter
            )


def get_arg_parser():
    parser = argparse.ArgumentParser(description="Removes a log group and will replace it with a new empty one with "
                                                 "the same settings")
    parser.add_argument("--dry-run",
                        dest="dry_run",
                        action="store_true",
                        help="Just print what we're going to do, don't actually do it."
                        )
    parser.add_argument(dest="log_group_name",
                        help="The log group to clean and replace. Example: '/aws/lambda/my-app'"
                        )
    return parser


if __name__ == "__main__":
    args = get_arg_parser().parse_args()
    main(args.log_group_name, args.dry_run)
