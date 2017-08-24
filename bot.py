import json

import requests

import boto3

import validatesns

from flask import Flask, request, abort
from flow import Flow

from raven.contrib.flask import Sentry

from config import ORG_ID, CHANNEL_ID, SENTRY_DSN

flow = Flow('botbotbot')
app = Flask(__name__)

if SENTRY_DSN:
    sentry = Sentry(app, dsn=SENTRY_DSN)


@app.route('/')
def index():
    flow.send_message(ORG_ID, CHANNEL_ID, 'botbotbot')
    return 'foo'


@app.route('/pong/')
def pong():

    try:
        from deployment import DEPLOYMENT_ID
    except ImportError:
        abort(401)

    return DEPLOYMENT_ID


@app.route('/deployments/', methods=['POST'])
def deployments():

    data = json.loads(request.data.decode('utf-8'))

    try:
        validatesns.validate(data)
    except validatesns.ValidationError:
        abort(400)

    message_type = data['Type']

    if message_type == 'SubscriptionConfirmation':
        confirmation = requests.get(data['SubscribeURL'])

    elif message_type == 'Notification':

        message_data = json.loads(data['Message'])
        logs = []

        if message_data['status'] == 'FAILED':

            client = boto3.client('codedeploy')
            group = client.get_deployment_group(applicationName=message_data['applicationName'],
                                                deploymentGroupName=message_data['deploymentGroupName'])
            ec2_filters = []
            for setlist in group['deploymentGroupInfo']['ec2TagSet']['ec2TagSetList']:
                for tag in setlist:
                    filters = [
                       {'Name': 'tag-key', 'Values': [tag['Key']]},
                       {'Name': 'tag-value', 'Values': [tag['Value']]}
                    ]
                    ec2_filters.extend(filters)

            client = boto3.client('ec2')
            instances = client.describe_instances(Filters=ec2_filters)

            instance_ids = []
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_ids.append(instance['InstanceId'])

            client = boto3.client('codedeploy')

            for instance in instance_ids:
                deployment_instances = client.get_deployment_instance(deploymentId=message_data['deploymentId'],
                                                                      instanceId=instance)
                for event in deployment_instances['instanceSummary']['lifecycleEvents']:
                    if event['status'] == 'Failed':
                        logs.append({'event': event['lifecycleEventName'], 
                                     'log': event['diagnostics']['logTail']})


        message = '**{subject} ({group})**'.format(subject=data['Subject'],
                                                   group=message_data['deploymentGroupName'])
        if logs:
            message += '\n\n'
            for log in logs:
                message += '**[Lifecycle Event: {event}]**\n\n```\n{log}\n```'.format(**log)

        flow.send_message(ORG_ID, CHANNEL_ID, message)

    return 'foop'


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1])
    app.run(port=port, debug=True)
