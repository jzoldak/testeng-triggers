"""
Helper methods for triggering the next step in the deployment pipeline
"""
import json
import os

from boto import connect_sns
from boto.exception import BotoServerError

import logging
LOGGER = logging.getLogger(__name__)

REPO_ORG = os.environ.get('REPO_ORG', 'foo')
REPO_NAME = os.environ.get('REPO_NAME', 'bar')
HANDLED_REPO = '{org}/{name}'.format(org=REPO_ORG, name=REPO_NAME)

PROVISIONING_TOPIC = os.environ.get('PROVISIONING_TOPIC', 'insert_sns_arn_here')
SITESPEED_TOPIC = os.environ.get('SITESPEED_TOPIC', 'insert_sns_arn_here')


class SnsError(Exception):
    """ Error in the communication with SNS. """
    pass


def parse_webhook_payload(event, data):
    """Parse the WebHook payload and trigger downstream jobs.

    Args:
        event (string): GitHub event
        data (dict): payload from the webhook

    Returns:
        None if no downstream action was required
        string: MessageId of the published SNS message if a followon action should be taken
    """
    repo = data.get('repository')
    repo_name = repo.get('full_name')
    if repo_name != HANDLED_REPO:
        # We only want to take action on a specific repo, so
        # even if another repo gets configured to send webhooks
        # to this app send back a 200 to GitHub
        LOGGER.debug('Unhandled repo: {}'.format(repo_name))
        return None

    msg_id = None

    # Handle deployment events
    if event == 'deployment':
        LOGGER.debug('Deployment event passed to the handler.')
        msg_id = handle_deployment_event(
            PROVISIONING_TOPIC,
            REPO_ORG,
            REPO_NAME,
            data.get('deployment')
        )

    # Handle deployment status events
    elif event == 'deployment_status':
        LOGGER.debug('Deployment status event passed to the handler.')
        msg_id = handle_deployment_status_event(
            SITESPEED_TOPIC,
            REPO_ORG,
            REPO_NAME,
            data.get('deployment'),
            data.get('deployment_status')
        )

    else:
        LOGGER.debug('This event type does not need to be handled.')

    return msg_id


def is_valid_gh_event(event, data):
    """ Verify that the webhook sent conforms to the GitHub API v3. """
    if not event:
        # This is not a valid webhook from GitHub because
        # those all send an X-GitHub-Event header.
        LOGGER.error('The X-GitHub-Event header was not received in the request.')
        return False

    repo = data.get('repository')
    if not repo:
        # This is not a valid webhook from GitHub because
        # those all return the repository info in the JSON payload
        LOGGER.error('Invalid webhook payload: {}'.format(data))
        return False

    return True


def publish_sns_messsage(topic_arn, message):
    """ Publish a message to SNS that will trigger jenkins jobs listening via SQS subscription.

    Args:
        topic_arn (string): The arn representing the topic
        message (string): The message to send

    Returns:
        string: The MessageId of the published message

    Raises:
        SnsError when publising was unsuccessful
    """
    try:
        LOGGER.debug('Publishing to {}. Message is {}'.format(topic_arn, message))
        conn = connect_sns()
        response = conn.publish(topic=topic_arn, message=message)

    except BotoServerError as err:
        raise SnsError(err)

    # A successful response will be something like this:
    # {u'PublishResponse':
    #     {u'PublishResult':
    #         {u'MessageId': u'46c3689d-9ca0-425e-a9a7-1ec036eec857'},
    #          u'ResponseMetadata': {u'RequestId': u'384ac68d-3775-11df-8963-01868b7c937a'
    #         }
    #     }
    # }
    publish_response = response.get('PublishResponse')
    publish_result = publish_response and publish_response.get('PublishResult')
    message_id = publish_result.get('MessageId')

    if not message_id:
        raise SnsError('Could not publish message. Response was: {}'.format(publish_response))

    LOGGER.debug('Successfully published MessageId {}'.format(message_id))
    return message_id


def _compose_sns_message(repo_org, repo_name):
    """ Compose the message to publish to the SNS topic.

    Note that an SQS queue must be subscribed to the SNS topic, the Jenkins main configuration
    must be set up to be listening to that queue. The Jenkins SQS plugin will then consume messages
    from the SQS Queue and trigger any jobs that have a matching github repository configuration.

    """
    message = {}
    repo = {}
    repo['name'] = repo_name
    repo['owner'] = {'name': '{org}'.format(org=repo_org)}
    repo['url'] = 'https://github.com/{org}/{name}'.format(org=repo_org, name=repo_name)
    message['default'] = "{}".format(json.dumps(repo))

    return message


def handle_deployment_event(topic, repo_org, repo_name, deployment):
    """Handle the deployment event webhook.

    Technical implementation notes:
        * A successful quality build of master sends a request to create a deployment
          with required contexts. After the required contexts all pass,
          GitHub will send the DeploymentEvent webhook.
        * The Jenkins SQS plugin will look to trigger a build for any job that is configured
          with a Git backed (either directly or through a multi-SCM choice) repo that
          matches the URL, name, and owner specified in the message.
        * It will then look for unbuilt changes in that repo, as Jenkins does for any triggered build

    Args:
        repo_org (string): Org of the repo to use in the message
        repo_name (string): Name of the repo to use in the message
        deployment (dict): deployment object from the webhook payload

    Returns:
        string: the message ID of the published message
    """
    # Start up the pipeline by publishing an SNS message that will trigger the provisioning job.
    # At the moment we don't need any conditional logic for this. That is, for any
    # deployment event that is created, trigger the provisioning job.
    #
    # The provisioning job will need to post a deployment status event with 'state' equal to
    # 'success' in order to trigger the next job in the pipeline.
    LOGGER.info('Received deployment event')
    LOGGER.debug(deployment)

    msg_id = publish_sns_messsage(topic_arn=topic, message=_compose_sns_message(repo_org, repo_name))
    return msg_id


def handle_deployment_status_event(topic, repo_org, repo_name, deployment, deployment_status):
    """Handle the deployment status event.

    This webhook is triggered by jenkins creating a deployment status event
    after a successful build provisioning the target sandbox.

    Args:
        repo_org (string): Org of the repo to use in the message
        repos_name (string): Name of the repo to use in the message
        deployment (dict): deployment object from the webhook payload
        deployment_status (dict): deployment status object from the webhook payload

    Returns:
        None if no action was required or
        string: the message ID of the published message
    """
    LOGGER.info('Received deployment status event')
    LOGGER.debug(deployment_status)

    state = deployment_status.get('state')

    if state == 'success':
        # Continue the next job in the pipeline by publishing an SNS message that will trigger
        # the sitespeed job.
        msg_id = publish_sns_messsage(topic_arn=topic, message=_compose_sns_message(repo_org, repo_name))
        return msg_id

    return None
