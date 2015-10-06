"""
Tests for the helper methods
"""
import json
from unittest import TestCase

from boto import connect_sns
from mock import patch
from moto import mock_sns
from ..helpers import publish_sns_messsage, SnsError, compose_sns_message


@mock_sns
class HelperTestCase(TestCase):
    """TestCase class for verifying the helper methods. """

    def test_nonexistent_sns_topic_arn(self):
        # There are no topics yet in the mocked SNS, so using
        # any arn will raise an error
        self.assertRaisesRegexp(SnsError, 'BotoServerError: 404 Not Found.*', publish_sns_messsage, 'arn', 'msg')

    def test_publish_to_topic(self):
        # Create a mocked connection and create the topic then
        # publish a message to that topic
        conn = connect_sns()
        conn.create_topic("some-topic")
        topics_json = conn.get_all_topics()
        topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']
        msg_id = publish_sns_messsage(topic_arn=topic_arn, message='foo')
        self.assertIsNotNone(msg_id)

    def test_compose_message(self):
        msg = compose_sns_message('org', 'repo')
        self.assertEqual(
            msg,
            {'default': '{"owner": {"name": "org"}, "url": "https://github.com/org/repo", "name": "repo"}'}
        )
