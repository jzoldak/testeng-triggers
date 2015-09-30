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
        code = trigger_jenkins_job('foo', {})
        self.assertEqual(code, 400)

    def test_untriggered_repo(self):
        code = trigger_jenkins_job('foo', {"repository": {"full_name": "foo/untriggered"}})
        self.assertEqual(code, 200)

    def test_untriggered_event(self):
        code = trigger_jenkins_job('foo', {"repository": {"full_name": "foo/bar"}})
        self.assertEqual(code, 200)
