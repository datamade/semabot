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

# The way that the Flow object works is to configure a "device" for the account
# that you're logging in with. You can think of this as an account logging in
# with their phone first and then adding a laptop and maybe some other
# workstation. Each place where the account logs in needs to be configured as
# a "device". That's what this stuff below is all about. If the machine that is
# running the code is not configured as a "device" for the botbotbot account,
# then it configures it and moves on.

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
    '''
    This is mostly a route that is setup to make sure that, once you have the
    Flow stuff working above, you're actually able to send messages to Semaphor
    '''
    channel_id = CHANNEL_MAP['semabot']
    flow.send_message(ORG_ID, channel_id, 'botbotbot')
    return 'foo'


@app.route('/error/')
def error():
    '''
    This is setup to make sure that sentry logging is working. It'll always
    raise an error.
    '''
    return 1 / 0


@app.route('/pong/')
def pong():
    '''
    The classic "pong" route from our zero downtime deployment strategy.
    '''
    try:
        from deployment import DEPLOYMENT_ID
    except ImportError:
        abort(401)

    return DEPLOYMENT_ID


@app.route('/travis/', methods=['POST'])
def travis():
    '''
    This route handles the webhook posts from Travis. To get a sense of what
    that looks like, check out:
    https://docs.travis-ci.com/user/notifications/#webhooks-delivery-format
    '''

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
    '''
    Handler for the webhooks from Sentry.
    '''

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

    '''
    This is the beginngings of a handler for Cloudwatch notifications. To use
    this, we would just have to setup a metric that we'd like to track (so, CPU
    or memory use on a server, for example), create and Alarm for it (so, CPU
    greater than 75% for more than a minute or something) and add the SNS topic
    for this Semabot endpoint (which is called "errors") as a notification
    channel.
    '''

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
    '''
    Handler for the CodeDeploy deployments.
    '''

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

        # In order for this to work, you need to have AWS credentials configured
        # for the user that is running the script or, in the case of an EC2
        # instance, you can also add a server level policy that allows these
        # calls to happen. More here:
        # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#configuring-credentials

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

        # See comment above about configuring the client.

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
