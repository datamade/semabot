import time

import requests
from raven import Client

from flow import Flow

from config import BOTNAME, BOTPW, ORG_ID, SENTRY_ACCESS_TOKEN, CHANNEL_MAP

try:
    flow = Flow(BOTNAME)
except flow.FlowError as e:
    flow = Flow()
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


if __name__ == "__main__":
    import argparse

    channels = list(CHANNEL_MAP.keys())

    parser = argparse.ArgumentParser(description='Various tools for configuring and testing configurations for Semabot')
    parser.add_argument('--list-channels', action='store_true', help='List channels that Semabot has access to')
    parser.add_argument('--test-sentry', choices=channels, help='Test sentry integration for a given app')
    parser.add_argument('--test-codedeploy', choices=channels, help='Test CodeDeploy integration for a given app')
    parser.add_argument('--test-travis', choices=channels, help='Test')

    args = parser.parse_args()

    if args.list_channels:
        print_channels()

    if args.test_sentry:
        test_sentry(args.test_sentry)

    if args.test_codedeploy:
        print('Not yet implemented')

    if args.test_travis:
        print('Not yet implemented')

