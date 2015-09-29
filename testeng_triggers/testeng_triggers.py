#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse
import threading
import json

from lazy import lazy
import requests

from helpers import trigger_jenkins_job

from logging import getLogger
LOGGER = getLogger(__name__)


class TriggerHttpRequestHandler(BaseHTTPRequestHandler, object):
    """
    Handler for the HTTP service.
    """
    protocol = "HTTP/1.0"

    def _format_msg(self, format_str, *args):
        """
        Format message for logging.
        `format_str` is a string with old-style Python format escaping;
        `args` is an array of values to fill into the string.
        """
        return u"{0} - - [{1}] {2}\n".format(
            self.client_address[0],
            self.log_date_time_string(),
            format_str % args
        )

    def log_message(self, format_str, *args):
        """
        Redirect messages to keep the test console clean.
        """
        LOGGER.debug(self._format_msg(format_str, *args))

    def log_error(self, format_str, *args):
        """
        Helper to log a server error.
        """
        LOGGER.error(self._format_msg(format_str, *args))

    @lazy
    def request_content(self):
        """
        Retrieve the content of the request.
        """
        try:
            length = int(self.headers.getheader('content-length'))

        except (TypeError, ValueError):
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

        except:
            return dict()

    def do_POST(self):
        """
        Respond to the HTTP POST request sent by GitHub WebHooks
        """
        status_code = 400
        event = self.headers.get('X-GitHub-Event')
        if event:
            status_code = trigger_jenkins_job(event=event, data=self.post_json)

        # Send a response back to GitHub
        BaseHTTPRequestHandler.send_response(self, status_code)
        self.log_message("Sent HTTP response: {}".format(status_code))


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


def run():
    port = int(os.environ.get('PORT', '8888'))
    httpd = TriggerHTTPServer(port_num=port)


if __name__ == "__main__":
    run()
