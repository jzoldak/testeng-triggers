#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from lazy import lazy
import os
import threading
import urlparse

from helpers import SnsError, handle_deployment_event, handle_deployment_status_event

import logging
import sys
LOGGER = logging.getLogger(__name__)

# Send the output to stdout so it will get handled with the Heroku logging service
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger('requests').setLevel(logging.ERROR)  # TODO: this isn't suppressing the logging, not sure why


REPO_ORG = os.environ.get('REPO_ORG', 'jzoldak')
REPO_NAME = os.environ.get('REPO_NAME', 'testeng-triggers')
HANDLED_REPO = '{org}/{name}'.format(org=REPO_ORG, name=REPO_NAME)

PROVISIONING_TOPIC = os.environ.get('PROVISIONING_TOPIC', 'arn:aws:sns:us-east-1:828123747931:edx-test-jenkins')
SITESPEED_TOPIC = os.environ.get('SITESPEED_TOPIC', 'arn:aws:sns:us-east-1:828123747931:edx-test-jenkins')


class TriggerHttpRequestHandler(BaseHTTPRequestHandler, object):
    """
    Handler for the HTTP service.
    """
    protocol = "HTTP/1.0"

    @classmethod
    def trigger_jenkins_job(cls, event, data):
        """Parse the WebHook payload and trigger downstream jenkins jobs.

        Args:
            event (string): GitHub event
            data (dict): payload from the webhook

        Returns:
            None if no downstream action was required
            string: MessageId of the published SNS message if a followon action should be taken

        Raises:
            ValueError when the request does not conform to the GitHub API v3.
        """
        if not event:
            # This is not a valid webhook from GitHub because
            # those all send an X-GitHub-Event header.
            LOGGER.error('The X-GitHub-Event header was not received in the request.')
            raise ValueError()

        repo = data.get('repository')
        if not repo:
            # This is not a valid webhook from GitHub because
            # those all return the repository info in the JSON payload
            LOGGER.error('Invalid webhook payload: {}'.format(data))
            raise ValueError('Invalid webhook payload: {}'.format(data))

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

        # The POST dict will contain a list of values for each key.
        # None of our parameters are lists, however, so we map [val] --> val
        # If the list contains multiple entries, we pick the first one
        try:
            post_dict = urlparse.parse_qs(contents, keep_blank_values=True)
            return {
                key: list_val[0]
                for key, list_val in post_dict.items()
            }

        except:  # pragma: no cover
            return dict()

    def do_POST(self):
        """
        Respond to the HTTP POST request sent by GitHub WebHooks
        """
        event = self.headers.get('X-GitHub-Event')
        try:
            self.trigger_jenkins_job(event=event, data=self.post_json)
            status_code = 200
        except ValueError, err:
            # Send a 400 back because the webhook did not
            # conform to the GitHub API v3.
            LOGGER.error(str(err))
            status_code = 400
        except SnsError, err:   # pragma: no cover
            # Send a 200 back to GitHub but log that there was a problem
            # with the trigger job itself
            LOGGER.error(str(err))
            status_code = 200

        # Send a response back to GitHub
        BaseHTTPRequestHandler.send_response(self, status_code)
        LOGGER.debug("Sent HTTP response: {}".format(status_code))


class TriggerHTTPServer(HTTPServer, object):
    """
    HTTP server implementation.
    """
    def __init__(self, port_num=0):
        """
        Configure the server to listen on localhost.
        Default is to choose an arbitrary open port.
        """
        address = ('0.0.0.0', port_num)
        HTTPServer.__init__(self, address, TriggerHttpRequestHandler)

        # Log the port we're using to help identify port conflict errors
        LOGGER.debug('Starting service on port {0}'.format(self.port))

        # Start the server in a separate thread
        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def shutdown(self):
        """
        Stop the server and free up the port
        """
        LOGGER.info('Shutting down the server')

        # First call superclass shutdown()
        HTTPServer.shutdown(self)

        # We also need to manually close the socket
        self.socket.close()

    @property
    def port(self):
        """
        Return the port that the service is listening on.
        """
        _, port = self.server_address
        return port


def run():  # pragma: no cover
    port = int(os.environ.get('PORT', '0'))
    httpd = TriggerHTTPServer(port_num=port)


if __name__ == "__main__":
    run()  # pragma: no cover
