"""
Helper methods for triggering jenkins jobs
"""
import os

JENKINS_BASE = os.environ.get('JENKINS_BASE', 'https://test-jenkins.testeng.edx.org')
JENKINS_JOB = os.environ.get('JENKINS_JOB', '/job/jz-test-project')
JENKINS_BUILD_CMD = os.environ.get('JENKINS_BUILD_CMD', '/buildWithParameters')
JENKINS_TOKEN = os.environ.get('JENKINS_TOKEN', 'FOO')
JENKINS_PARAM = os.environ.get('JENKINS_PARAM', 'EXIT_CODE=0')
JENKINS_USER_NAME = os.environ.get('JENKINS_USER_NAME', 'foo')
JENKINS_USER_TOKEN = os.environ.get('JENKINS_USER_TOKEN', 'bar')  # get this from JENKINS_BASE/me/configure
JENKINS_LINK = '{}{}{}?token={}&{}'.format(JENKINS_BASE, JENKINS_JOB, JENKINS_BUILD_CMD, JENKINS_TOKEN, JENKINS_PARAM)

HANDLED_REPO = 'jzoldak/testeng-triggers'

def trigger_jenkins_job(event, data):
    """Parse the WebHook payload and trigger
    downstream jenkins jobs.

    Args:
        event (string): GitHub event
        data (dict): payload from the webhook

    Returns:
        None

    Raises:
        ValueError when the request does not conform to the GitHub API v3.
    """
    if not event:
        # This is not a valid webhook from GitHub because
        # those all send an X-GitHub-Event header.
        raise ValueError('The X-GitHub-Event header was not received in the request.')

    repo = data.get('repository')
    if not repo:
        # This is not a valid webhook from GitHub because
        # those all return the repository info in the JSON payload
        raise ValueError('Invalid payload: {}'.format(data))

    repo_name = repo.get('full_name')
    if repo_name != HANDLED_REPO:
        # We only want to take action on a specific repo, so
        # even if another repo gets configured to send webhooks
        # to this app send back a 200 to GitHub
        return None

    # Handle deployment events.
    if event == 'deployment':
        handle_deployment_event(data.get('deployment'))

    # Handle deployment events.
    elif event == 'deployment_status':
        handle_deployment_status_event(data.get('deployment_status'))

    return None


def handle_deployment_event(deployment):
    """Handle the deployment event.

    This webhook is triggered by jenkins creating a deployment event
    after a successful quality build of master.

    Args:
        deployment (dict): deployment object from the webhook payload

    Returns:
        None

    Raises:
        ValueError when the request does not conform to the GitHub API v3.
    """
    # from nose.tools import set_trace; set_trace()
    # print "deployment: {}".format(deployment)
    # self.log_message(
    #     "Sending GET request to: {0} with credentials '{1}:{2}'".format(JENKINS_LINK, JENKINS_USER_NAME, JENKINS_USER_TOKEN)
    # )
    # resp = requests.get(JENKINS_LINK, auth=(JENKINS_USER_NAME, JENKINS_USER_TOKEN))


def handle_deployment_status_event(deployment_status):
    """Handle the deployment status event.

    This webhook is triggered by jenkins creating a deployment status event
    after a successful quality build of master.

    Args:
        deployment_status (dict): deployment status object from the webhook payload

    Returns:
        None

    Raises:
        ValueError when the request does not conform to the GitHub API v3.
    """
    # from nose.tools import set_trace; set_trace()
    # print "deployment_status: {}".format(deployment_status)
    # self.log_message(
    #     "Sending GET request to: {0} with credentials '{1}:{2}'".format(JENKINS_LINK, JENKINS_USER_NAME, JENKINS_USER_TOKEN)
    # )
    # resp = requests.get(JENKINS_LINK, auth=(JENKINS_USER_NAME, JENKINS_USER_TOKEN))

