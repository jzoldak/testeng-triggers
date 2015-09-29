"""
Tests for the HTTP server
"""
from unittest import TestCase

from mock import patch
import requests

from ..testeng_triggers import TriggerHTTPServer, TriggerHttpRequestHandler


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

    @patch("testeng_triggers.testeng_triggers.TriggerHttpRequestHandler.trigger_jenkins_job")
    def test_github_event(self, mock_trigger):
        mock_trigger.return_value = 'foo'
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


@patch('testeng_triggers.testeng_triggers.HANDLED_REPO', 'foo/bar')
class TriggerHandlerTestCase(TestCase):
    """TestCase class for verifying the trigger handling. """

    def setUp(self):
        super(TriggerHandlerTestCase, self).setUp()
        self.handler = TriggerHttpRequestHandler

    def test_bad_payload(self):
        self.assertRaises(ValueError, self.handler.trigger_jenkins_job, 'foo', {})

    def test_untriggered_repo(self):
        result = self.handler.trigger_jenkins_job('foo', {'repository': {'full_name': 'foo/untriggered'}})
        self.assertEqual(result, None)

    def test_untriggered_event(self):
        result = self.handler.trigger_jenkins_job('foo', {'repository': {'full_name': 'foo/bar'}})
        self.assertEqual(result, None)

    def test_deployment_event(self):
        result = self.handler.trigger_jenkins_job(
            'deployment',
            {'repository': {'full_name': 'foo/bar'}, 'deployment': {}}
        )
        msg = 'Expected MessageID {} to be a 36 digit string'.format(result)
        self.assertEqual(len(result), 36, msg)

    def test_ignored_deployment_status_event(self):
        result = self.handler.trigger_jenkins_job(
            'deployment_status',
            {'repository': {'full_name': 'foo/bar'}, 'deployment': {}, 'deployment_status': {}}
        )
        self.assertEqual(result, None)

    def test_deployment_status_success_event(self):
        result = self.handler.trigger_jenkins_job(
            'deployment_status',
            {'repository': {'full_name': 'foo/bar'}, 'deployment': {}, 'deployment_status': {'state': 'success'}}
        )
        msg = 'Expected MessageID {} to be a 36 digit string'.format(result)
        self.assertEqual(len(result), 36, msg)
