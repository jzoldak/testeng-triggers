"""
Tests for the helper methods
"""
from unittest import TestCase
from mock import Mock, patch
from ..helpers import trigger_jenkins_job


@patch("testeng_triggers.helpers.HANDLED_REPO", 'foo/bar')
class TriggerHelpersTestCase(TestCase):
    """TestCase class for verifying the helper methods. """

    def test_bad_payload(self):
        self.assertRaises(ValueError, trigger_jenkins_job, 'foo', {})

    def test_untriggered_repo(self):
        result = trigger_jenkins_job('foo', {"repository": {"full_name": "foo/untriggered"}})
        self.assertEqual(result, None)

    def test_untriggered_event(self):
        result = trigger_jenkins_job('foo', {"repository": {"full_name": "foo/bar"}})
        self.assertEqual(result, None)

    def test_deployment_event(self):
        result = trigger_jenkins_job(
            'deployment',
            {"repository": {"full_name": "foo/bar"}, "deployment": {}}
        )
        self.assertEqual(result, None)

