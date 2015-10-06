"""
Helper methods for triggering the next step in the deployment pipeline
"""
import json
import os

from boto import connect_sns
from boto.exception import BotoServerError


class SnsError(Exception):
    """ Error in the communication with SNS. """
    pass


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
        raise SnsError('Could not publish message. Response was: {}'.format(publish_response))  # pragma: no cover
    return message_id


def compose_sns_message(repo_org, repo_name):
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
    msg_id = publish_sns_messsage(topic_arn=topic, message=compose_sns_message(repo_org, repo_name))
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
    state = deployment_status.get('state')

    if state == 'success':
        # Continue the next job in the pipeline by publishing an SNS message that will trigger
        # the sitespeed job.
        msg_id = publish_sns_messsage(topic_arn=topic, message=compose_sns_message(repo_org, repo_name))
        return msg_id

    return None
