import time

import requests
from raven import Client
import boto3

import flow as flow_module

from config import BOTNAME, BOTPW, ORG_ID, SENTRY_ACCESS_TOKEN, CHANNEL_MAP

try:
    flow = flow_module.Flow(BOTNAME)
except flow_module.Flow.FlowError as e:
    flow = flow_module.Flow()
    flow.create_device(BOTNAME, BOTPW)
    print('Device for bot {} created'.format(BOTNAME))


def print_channels():
    print('\033[1mYour bot "{}" has access to these channels:\033[0m\n'.format(BOTNAME))

    for channel in flow.enumerate_channels(ORG_ID):
        print('\033[91m\033[1m"{name}":\033[0m \033[94m{id}\033[0m'.format(**channel))


def test_sentry(app_name):
    url = 'https://sentry.io/api/0/projects/datamade/{}/keys/'.format(app_name)
    header = {'Authorization': 'Bearer {}'.format(SENTRY_ACCESS_TOKEN)}

    project_keys = requests.get(url, headers=header)
    key = project_keys.json()[0]['dsn']['secret']

    client = Client(key)

    try:
        1 / 0
    except ZeroDivisionError:
        event_id = client.captureException()

    time.sleep(1)

    url = 'https://sentry.io/api/0/projects/datamade/{app_name}/events/{event_id}/'.format(app_name=app_name, event_id=event_id)
    event_json = requests.get(url, headers=header)

    group_id = event_json.json()['groupID']
    id = event_json.json()['id']

    event_url = 'https://sentry.io/datamade/{app_name}/issues/{group_id}/events/{id}/'.format(app_name=app_name, group_id=group_id, id=id)

    print('You should see this Sentry Event: {} in Semaphor'.format(event_url))


def test_error(alarm_name):
    cloudwatch = boto3.client('cloudwatch')
    response = cloudwatch.describe_alarms()
    alarm_names = [a['AlarmName'] for a in response['MetricAlarms']]

    if alarm_name not in alarm_names:
        print('{} is not a valid alarm'.format(alarm_name))
        return

    cloudwatch.set_alarm_state(AlarmName=alarm_name,
                               StateValue='ALARM',
                               StateReason="Threshold Crossed: 1 out of the last 1 datapoints [12.0 (16/05/18 15:04:00)] was greater than or equal to the threshold (1.0) (minimum 1 datapoint for OK -> ALARM transition).")


if __name__ == "__main__":
    import argparse

    channels = list(CHANNEL_MAP.keys())

    parser = argparse.ArgumentParser(description='Various tools for configuring and testing configurations for Semabot')
    parser.add_argument('--test-sentry', type=str, help='Test sentry integration for a given app')
    parser.add_argument('--test-codedeploy', type=str, help='Test CodeDeploy integration for a given app')
    parser.add_argument('--test-travis', type=str, help='Test')
    parser.add_argument('--test-error', type=str, help='Test')

    args = parser.parse_args()

    all_args = {args.test_sentry, args.test_codedeploy, args.test_travis, args.test_error}

    # if all_args == {None}:
    #     parser.print_help()
    #     print_channels()

    # elif all_args.isdisjoint(set(channels)):
    #     message = '"{all_args}" is not a valid application. Please choose a valid application:\n {channels}'
    #     print(message.format(channels='\n'.join(channels),
    #                          all_args=', '.join(a for a in all_args if a)))
    #     sys.exit(0)

    if args.test_sentry:
        test_sentry(args.test_sentry)

    if args.test_codedeploy:
        print('Not yet implemented')

    if args.test_travis:
        print('Not yet implemented')

    if args.test_error:
        test_error(args.test_error)
