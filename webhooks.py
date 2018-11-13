import json
from json import JSONDecodeError

import requests

import boto3

import validatesns

from flask import Flask, request, abort
from flow import Flow

from raven.contrib.flask import Sentry

from config import ORG_ID, CHANNEL_MAP, SENTRY_DSN, BOTNAME, BOTPW, TRAVIS_MAP
from utils import parseException

app = Flask(__name__)

try:
    flow = Flow(BOTNAME)
except flow.FlowError:
    flow = Flow()
    flow.create_device(BOTNAME, BOTPW)
    app.logger.info('Device for bot {} created'.format(BOTNAME))


if SENTRY_DSN:
    sentry = Sentry(app, dsn=SENTRY_DSN)


@app.route('/')
def index():
    channel_id = CHANNEL_MAP['semabot']
    flow.send_message(ORG_ID, channel_id, 'botbotbot')
    return 'foo'


@app.route('/error/')
def error():
    return 1 / 0


@app.route('/pong/')
def pong():

    try:
        from deployment import DEPLOYMENT_ID
    except ImportError:
        abort(401)

    return DEPLOYMENT_ID


@app.route('/travis/', methods=['POST'])
def travis():
    data = json.loads(request.form['payload'])

    message = 'Travis build for started by **{committer_name}** for {name} ({branch}) finished with status **{status}**\n'
    message += data['build_url']
    message = message.format(name=data['repository']['name'],
                             branch=data['branch'],
                             status=data['status_message'],
                             committer_name=data['committer_name'])
    try:
        slug = TRAVIS_MAP[data['repository']['name']]
        channel_id = CHANNEL_MAP[slug]
    except KeyError:
        channel_id = CHANNEL_MAP['semabot']

    flow.send_message(ORG_ID, channel_id, message)

    return 'fuup'


@app.route('/sentry/', methods=['POST'])
def sentry_message():

    data = json.loads(request.data.decode('utf-8'))

    message = '**{project_name}**\n\n'.format(**data)
    message += '**{message}**\n{url}'.format(**data)
    event = data['event']

    exception_parsed = False

    for key in ['exception', 'breadcrumbs', 'message']:

        try:
            body = event[key]
            message += '\n```\n{}\n```\n'.format(parseException(body))
            exception_parsed = True
            break
        except KeyError:
            pass

    if not exception_parsed:
        message += '\n```Unable to parse exception```\n'

    try:
        channel_id = CHANNEL_MAP[data['project']]
    except KeyError:
        channel_id = CHANNEL_MAP['semabot']

    flow.send_message(ORG_ID, channel_id, message[:5999])
    return message


@app.route('/errors/', methods=['POST'])
def errors():

    data = json.loads(request.data.decode('utf-8'))

    try:
        validatesns.validate(data)
    except validatesns.ValidationError:
        abort(400)

    message_type = data['Type']

    if message_type == 'SubscriptionConfirmation':
        requests.get(data['SubscribeURL'])

    elif message_type == 'Notification':
        try:
            message_data = json.loads(data['Message'])
        except JSONDecodeError:
            # This handles the case where the notification is not an actual
            # deployment. This happens when you setup a new trigger
            channel_id = CHANNEL_MAP['semabot']
            message = '**{}**\n'.format(data['Subject'])
            message += data['Message']
            flow.send_message(ORG_ID, channel_id, message)
            return 'foop'

        new_state_value = message_data['NewStateValue']
        if new_state_value == 'ALARM':

            metric_name = message_data['Trigger']['MetricName']
            print(metric_name)

    return 'fwip'


@app.route('/deployments/', methods=['POST'])
def deployments():

    data = json.loads(request.data.decode('utf-8'))

    try:
        validatesns.validate(data)
    except validatesns.ValidationError:
        abort(400)

    message_type = data['Type']

    if message_type == 'SubscriptionConfirmation':
        requests.get(data['SubscribeURL'])

    elif message_type == 'Notification':

        try:
            message_data = json.loads(data['Message'])
        except JSONDecodeError:
            # This handles the case where the notification is not an actual
            # deployment. This happens when you setup a new trigger
            channel_id = CHANNEL_MAP['semabot']
            message = '**{}**\n'.format(data['Subject'])
            message += data['Message']
            flow.send_message(ORG_ID, channel_id, message)
            return 'foop'

        deployment_id = message_data['deploymentId']
        instance_id = message_data['instanceId']

        client = boto3.client('codedeploy')

        deployment_instances = client.get_deployment_instance(deploymentId=deployment_id,
                                                              instanceId=instance_id)
        deployment_info = client.get_deployment(deploymentId=deployment_id)['deploymentInfo']

        logs = []

        if message_data['instanceStatus'].lower() == 'failed':

            for event in deployment_instances['instanceSummary']['lifecycleEvents']:
                if event['status'] == 'Failed':
                    logs.append({'event': event['lifecycleEventName'],
                                 'log': event['diagnostics']['logTail']})

        client = boto3.client('ec2')
        instance_info = client.describe_instances(InstanceIds=[instance_id])
        tags = instance_info['Reservations'][0]['Instances'][0]['Tags']
        instance_name = [t['Value'] for t in tags if t['Key'] == 'Name'][0]

        message = '**{status}: AWS CodeDeploy {deployment_id} in {region} to {appname} ({group}) on {instance_name}**'

        message = message.format(status=message_data['instanceStatus'],
                                 group=deployment_info['deploymentGroupName'],
                                 deployment_id=deployment_id,
                                 region=message_data['region'],
                                 appname=deployment_info['applicationName'],
                                 instance_name=instance_name)
        if logs:
            message += '\n\n'
            for log in logs:
                message += '**[Lifecycle Event: {event}]**\n\n```\n{log}\n```'.format(**log)

        try:
            channel_id = CHANNEL_MAP[deployment_info['applicationName']]
        except KeyError:
            channel_id = CHANNEL_MAP['semabot']

        flow.send_message(ORG_ID, channel_id, message)

    return 'foop'


if __name__ == "__main__":
    import sys

    try:
        port = int(sys.argv[1])
    except ValueError:
        port = 5000

    app.run(port=port, debug=True)
