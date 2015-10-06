#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import json
import os
import urlparse

from helpers import SnsError, handle_deployment_event, handle_deployment_status_event
from helpers import parse_webhook_payload, is_valid_gh_event

import logging
import sys
LOGGER = logging.getLogger(__name__)

# Send the output to stdout so it will get handled with the Heroku logging service
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger('requests').setLevel(logging.ERROR)  # TODO: this isn't suppressing the logging, not sure why
logging.getLogger('boto').setLevel(logging.ERROR)


class TriggerHttpRequestHandler(BaseHTTPRequestHandler):
    """
    Handler for the HTTP service.
    """
    protocol = "HTTP/1.1"

    def do_POST(self):
        """
        Respond to the HTTP POST request sent by GitHub WebHooks
        """
        # Send a response back to the webhook
        LOGGER.debug("Sending a 200 HTTP response back to the webhook")
        self.send_response(200)
        self.end_headers()

        # Retrieve the request POST json from the client as a dictionary.
        # If no POST json can be interpreted, don't do anything.
        try:
            length = int(self.headers.getheader('content-length'))
            contents = self.rfile.read(length)
            data = json.loads(contents)
        except (TypeError, ValueError):
            LOGGER.error("Could not interpret the POST request.")
            return

        event = self.headers.get('X-GitHub-Event')
        LOGGER.debug("Received GitHub event: {}".format(event))

        if is_valid_gh_event(event=event, data=data):
            try:
                parse_webhook_payload(event=event, data=data)

            except SnsError, err:
                LOGGER.error(str(err))


def run(server_class=HTTPServer, handler_class=TriggerHttpRequestHandler):  # pragma: no cover
    port = int(os.environ.get('PORT', '0'))
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)

    LOGGER.debug('Starting service on port {0}'.format(httpd.server_port))
    httpd.serve_forever()


if __name__ == "__main__":
    run()  # pragma: no cover
