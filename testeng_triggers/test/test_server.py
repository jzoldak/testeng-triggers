"""
Tests for the HTTP server
"""
from BaseHTTPServer import HTTPServer
from unittest import TestCase, skip

from boto import connect_sns
import json
from mock import patch
from moto import mock_sns
import requests
import threading

from ..testeng_triggers import TriggerHttpRequestHandler


class ThreadedHTTPServer(HTTPServer, object):
    """ HTTP server implementation for testing.

    Configure the server to listen on an arbitrary open port on localhost.
    Start it up in a separate thread so that it can be shutdown by another thread.
    """
    def __init__(self):
        """
        """
        address = ('0.0.0.0', 0)
        HTTPServer.__init__(self, address, TriggerHttpRequestHandler)

        server_thread = threading.Thread(target=self.serve_forever)
        server_thread.daemon = True
        server_thread.start()

    def shutdown(self):
        """
        Stop the server and free up the port
        """
        HTTPServer.shutdown(self)
        self.socket.close()

    @property
    def port(self):
        """
        Return the port that the service is listening on.
        """
        _, port = self.server_address
        return port


class TriggerServerTestCase(TestCase):
    """TestCase class for verifying the HTTP server that
    is servicing the webhooks from GitHub.
    """
    def setUp(self):
        """These tests start the server to test it. """
        super(TriggerServerTestCase, self).setUp()
        self.server = ThreadedHTTPServer()
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:{port}".format(port=self.server.port)

    @patch("testeng_triggers.testeng_triggers.TriggerHttpRequestHandler.parse_webhook_payload")
    def test_github_event(self, mock_downstream):
        mock_downstream.return_value = 'foo'
        headers = {'X-GitHub-Event': 'foo', 'content-type': 'application/json'}
        payload = {'repository': 'bar'}
        response = requests.post(self.url, headers=headers, data=json.dumps(payload))
        self.assertEqual(response.status_code, 200)

    def test_bad_github_event(self):
        response = requests.post(self.url, data={})
        self.assertEqual(response.status_code, 400)

    def test_get_request(self):
        """ Test that GET requests are not implemented, only POSTs are. """
        response = requests.get(self.url, data={})
        self.assertEqual(response.status_code, 501)

    def test_empty_payload(self):
        headers = {'X-GitHub-Event': 'foo'}
        response = requests.post(self.url, headers=headers, data='{}')
        self.assertEqual(response.status_code, 400)

    def test_bad_payload(self):
        headers = {'X-GitHub-Event': 'foo'}
        response = requests.post(self.url, headers=headers, data="{'foo': }")
        self.assertEqual(response.status_code, 400)


@patch('testeng_triggers.testeng_triggers.HANDLED_REPO', 'foo/bar')
class TriggerHandlerTestCase(TestCase):
    """TestCase class for verifying the trigger handling. """

    def setUp(self):
        super(TriggerHandlerTestCase, self).setUp()
        self.handler = TriggerHttpRequestHandler

    @classmethod
    def create_topic(cls):
        """ Create a topic so that we can publish to it. """
        conn = connect_sns()
        conn.create_topic("some-topic")
        topics_json = conn.get_all_topics()
        topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']
        return topic_arn

    def test_untriggered_repo(self):
        result = self.handler.parse_webhook_payload('foo', {'repository': {'full_name': 'foo/untriggered'}})
        self.assertEqual(result, None)

    def test_untriggered_event(self):
        result = self.handler.parse_webhook_payload('foo', {'repository': {'full_name': 'foo/bar'}})
        self.assertEqual(result, None)

    @mock_sns
    def test_deployment_event(self):
        with patch('testeng_triggers.testeng_triggers.PROVISIONING_TOPIC', self.create_topic()):
            result = self.handler.parse_webhook_payload(
                'deployment',
                {'repository': {'full_name': 'foo/bar'}, 'deployment': {}}
            )
            msg = 'Expected MessageID {} to be a 36 digit string'.format(result)
            self.assertEqual(len(result), 36, msg)

    def test_ignored_deployment_status_event(self):
        result = self.handler.parse_webhook_payload(
            'deployment_status',
            {'repository': {'full_name': 'foo/bar'}, 'deployment': {}, 'deployment_status': {}}
        )
        self.assertEqual(result, None)

    @mock_sns
    def test_deployment_status_success_event(self):
        with patch('testeng_triggers.testeng_triggers.SITESPEED_TOPIC', self.create_topic()):
            result = self.handler.parse_webhook_payload(
                'deployment_status',
                {'repository': {'full_name': 'foo/bar'}, 'deployment': {}, 'deployment_status': {'state': 'success'}}
            )
            msg = 'Expected MessageID {} to be a 36 digit string'.format(result)
            self.assertEqual(len(result), 36, msg)
