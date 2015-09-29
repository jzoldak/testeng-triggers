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


def trigger_jenkins_job(event, data):
    """Parse the WebHook payload and trigger
    downstream jenkins jobs.

    Args:
        event (string): GitHub event
        data (string): json payload from the webhook

    Returns:
        int: HTTP status code to send back to GitHub
    """
    repo = data.get('repository')
    if not repo:
        # This isn't a valid webhook from GitHub because
        # they all return the repository info in the JSON
        return 400

    repo_name = repo.get('full_name')
    if repo_name is not 'jzoldak/testeng-triggers':
        # We only want to take action on a specific repo, so
        # even if another repo gets configured to send webhooks
        # to this app
        return 200

    if event == 'issue_comment':
        self.log_message(
            "Sending GET request to: {0} with credentials '{1}:{2}'".format(JENKINS_LINK, JENKINS_USER_NAME, JENKINS_USER_TOKEN)
        )
        # resp = requests.get(JENKINS_LINK, auth=(JENKINS_USER_NAME, JENKINS_USER_TOKEN))

    return 200
