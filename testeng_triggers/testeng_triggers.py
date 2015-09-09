#!/usr/bin/env python

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse
import threading
import json
import os

from lazy import lazy
import requests

from logging import getLogger
LOGGER = getLogger(__name__)

JENKINS_BASE = os.environ.get('JENKINS_BASE', 'https://test-jenkins.testeng.edx.org')
JENKINS_JOB = os.environ.get('JENKINS_JOB', '/job/jz-test-project')
JENKINS_BUILD_CMD = os.environ.get('JENKINS_BUILD_CMD', '/buildWithParameters')
JENKINS_TOKEN = os.environ.get('JENKINS_TOKEN', 'token=FOO')
JENKINS_PARAM = os.environ.get('JENKINS_PARAM', 'EXIT_CODE=0')
JENKINS_USER_NAME = os.environ.get('JENKINS_USER_NAME', 'foo')
JENKINS_USER_TOKEN = os.environ.get('JENKINS_USER_TOKEN', 'bar')  # get this from JENKINS_BASE/me/configure
JENKINS_LINK = '{}{}{}?{}&{}'.format(JENKINS_BASE, JENKINS_JOB, JENKINS_BUILD_CMD, JENKINS_TOKEN, JENKINS_PARAM)

class StubHttpRequestHandler(BaseHTTPRequestHandler, object):
    """
    Handler for the stub HTTP service.
    """
    protocol = "HTTP/1.0"

    def log_message(self, format_str, *args):
        """
        Redirect messages to keep the test console clean.
        """
        print self._format_msg(format_str, *args)
        LOGGER.debug(self._format_msg(format_str, *args))

    def log_error(self, format_str, *args):
        """
        Helper to log a server error.
        """
        print self._format_msg(format_str, *args)
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

    # @lazy
    # def post_json(self):
    #     """
    #     Retrieve the request POST parameters from the client as a dictionary.
    #     If no POST parameters can be interpreted, return an empty dict.
    #     """
    #     contents = self.request_content

    #     # The POST dict will contain a list of values for each key.
    #     # None of our parameters are lists, however, so we map [val] --> val
    #     # If the list contains multiple entries, we pick the first one
    #     try:
    #         post_dict = urlparse.parse_qs(contents, keep_blank_values=True)
    #         return {
    #             key: list_val[0]
    #             for key, list_val in post_dict.items()
    #         }

    #     except:
    #         return dict()

    # @lazy
    # def get_params(self):
    #     """
    #     Return the GET parameters (querystring in the URL).
    #     """
    #     query = urlparse.urlparse(self.path).query

    #     # By default, `parse_qs` returns a list of values for each param
    #     # For convenience, we replace lists of 1 element with just the element
    #     return {
    #         key: value[0] if len(value) == 1 else value
    #         for key, value in urlparse.parse_qs(query).items()
    #     }

    # @lazy
    # def path_only(self):
    #     """
    #     Return the URL path without GET parameters.
    #     Removes the trailing slash if there is one.
    #     """
    #     path = urlparse.urlparse(self.path).path
    #     if path.endswith('/'):
    #         return path[:-1]
    #     else:
    #         return path

    def send_response(self, status_code, content=None, headers=None):
        """
        Send a response back to the client with the HTTP `status_code` (int),
        `content` (str) and `headers` (dict).
        """
        self.log_message(
            "Sent HTTP response: {0} with content '{1}' and headers {2}".format(status_code, content, headers)
        )

        if headers is None:
            headers = {
                'Access-Control-Allow-Origin': "*",
            }

        BaseHTTPRequestHandler.send_response(self, status_code)

        for (key, value) in headers.items():
            self.send_header(key, value)

        if len(headers) > 0:
            self.end_headers()

        if content is not None:
            self.wfile.write(content)

    # def send_json_response(self, content):
    #     """
    #     Send a response with status code 200, the given content serialized as
    #     JSON, and the Content-Type header set appropriately
    #     """
    #     self.send_response(200, json.dumps(content), {"Content-Type": "application/json"})

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

    # def do_HEAD(self):
    #     """
    #     Respond to an HTTP HEAD request
    #     """
    #     self.send_response(200)

    # def do_GET(self):
    #     """
    #     Respond to an HTTP GET request
    #     """
    #     self.send_response(200)

    def do_POST(self):
        """
        Respond to an HTTP POST request
        """
        event = self.headers.get('X-GitHub-Event')
        if event == 'issue_comment':
            data = json.loads(self.request_content)
            repo = data.get('repository')
            repo_name = repo.get('full_name')

            resp = requests.get(JENKINS_LINK, auth=(JENKINS_USER_NAME, JENKINS_USER_TOKEN))

        self.send_response(200)

    # def do_PUT(self):
    #     """
    #     Respond to an HTTP PUT request
    #     """
    #     self.send_response(200)


def run(server_class=HTTPServer, handler_class=StubHttpRequestHandler):
    server_address = ('', 8888)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()


if __name__ == "__main__":
    run()
