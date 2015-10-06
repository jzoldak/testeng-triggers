#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from lazy import lazy
import os
import urlparse

from helpers import SnsError, handle_deployment_event, handle_deployment_status_event

import logging
import sys
LOGGER = logging.getLogger(__name__)

# Send the output to stdout so it will get handled with the Heroku logging service
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger('requests').setLevel(logging.ERROR)  # TODO: this isn't suppressing the logging, not sure why


REPO_ORG = os.environ.get('REPO_ORG', 'foo')
REPO_NAME = os.environ.get('REPO_NAME', 'bar')
HANDLED_REPO = '{org}/{name}'.format(org=REPO_ORG, name=REPO_NAME)

PROVISIONING_TOPIC = os.environ.get('PROVISIONING_TOPIC', 'insert_sns_arn_here')
SITESPEED_TOPIC = os.environ.get('SITESPEED_TOPIC', 'insert_sns_arn_here')


class TriggerHttpRequestHandler(BaseHTTPRequestHandler, object):
    """
    Handler for the HTTP service.
    """
    protocol = "HTTP/1.0"

    @classmethod
    def parse_webhook_payload(cls, event, data):
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
            LOGGER.debug('Deployment event received.')
            msg_id = handle_deployment_event(
                PROVISIONING_TOPIC,
                REPO_ORG,
                REPO_NAME,
                data.get('deployment')
            )

        # Handle deployment status events
        elif event == 'deployment_status':
            LOGGER.debug('Deployment status event received.')
            msg_id = handle_deployment_status_event(
                SITESPEED_TOPIC,
                REPO_ORG,
                REPO_NAME,
                data.get('deployment'),
                data.get('deployment_status')
            )

        return msg_id

    @lazy
    def request_content(self):
        """
        Retrieve the content of the request.
        """
        try:
            length = int(self.headers.getheader('content-length'))

        except (TypeError, ValueError):  # pragma: no cover
            return ""
        else:
            return self.rfile.read(length)

    @lazy
    def post_json(self):
        """
        Retrieve the request POST parameters from the client as a dictionary.
        If no POST parameters can be interpreted, return an empty dict.
        """
        contents = self.request_content
        try:
            return urlparse.parse_qs(contents, keep_blank_values=True)
        except:  # pragma: no cover
            return dict()

    def _is_valid_gh_event(cls, event, data):
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

    def do_POST(self):
        """
        Respond to the HTTP POST request sent by GitHub WebHooks
        """
        event = self.headers.get('X-GitHub-Event')
        data = self.post_json

        if self._is_valid_gh_event(event=event, data=data):
            # Send a 200 back to GitHub regardless
            status_code = 200

            try:
                self.parse_webhook_payload(event=event, data=data)

            except SnsError, err:   # pragma: no cover
                LOGGER.error(str(err))

        else:
            status_code = 400

        # Send a response back to GitHub
        BaseHTTPRequestHandler.send_response(self, status_code)
        LOGGER.debug("Sent HTTP response: {}".format(status_code))


def run(server_class=HTTPServer, handler_class=TriggerHttpRequestHandler):  # pragma: no cover
    port = int(os.environ.get('PORT', '0'))
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    LOGGER.debug('Starting service on port {0}'.format(port))
    httpd.serve_forever()


if __name__ == "__main__":
    run()  # pragma: no cover
