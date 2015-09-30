"""
Tests for the HTTP server
"""
from unittest import TestCase

from mock import Mock, patch
import requests

from ..testeng_triggers import TriggerHTTPServer


class TriggerServerTestCase(TestCase):
    """TestCase class for verifying the HTTP server that
    is servicing the webhooks from GitHub.
    """
    def setUp(self):
        """These tests start the server to test it. """
        super(TriggerServerTestCase, self).setUp()
        self.server = TriggerHTTPServer()
        self.addCleanup(self.server.shutdown)
        self.url = "http://127.0.0.1:{port}".format(port=self.server.port)

    @patch("testeng_triggers.testeng_triggers.trigger_jenkins_job", Mock(return_value=200))
    def test_github_event(self):
        headers = {'X-GitHub-Event': 'foo'}
        response = requests.post(self.url, headers=headers, data={})
        self.assertEqual(response.status_code, 200)

    def test_bad_github_event(self):
        response = requests.post(self.url, data={})
        self.assertEqual(response.status_code, 400)

    def test_get_request(self):
        """ Test that GET requests are not implemented, only POSTs are. """
        response = requests.get(self.url, data={})
        self.assertEqual(response.status_code, 501)
