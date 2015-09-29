"""
Tests for the helper methods
"""
import json
from unittest import TestCase, skip

from boto import connect_sns
from mock import patch
from moto import mock_sns
from ..helpers import publish_sns_messsage, SnsError


@mock_sns
class SnsTestCase(TestCase):
    """TestCase class for verifying the sns communication. """

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

    # I can't figure out how to test no permissions, because remove_permissions is not implemented
    # and setting all permissions to Deny as below is not denying publishing permissions as I had hoped,
    # perhaps because it knows that the account running the tests is the owner...
    @skip
    def test_not_permitted_to_publish_to_topic(self):
        # Create a mocked connection and create the topic then
        # publish a message to that topic
        conn = connect_sns('key_foo', 'secret_bar')
        conn.create_topic("some-topic")
        topics_json = conn.get_all_topics()
        topic_arn = topics_json["ListTopicsResponse"]["ListTopicsResult"]["Topics"][0]['TopicArn']
        response = conn.get_topic_attributes(topic_arn).get(u'GetTopicAttributesResponse')
        policy = response.get(u'GetTopicAttributesResult').get(u'Attributes').get(u'Policy')
        policy_id = json.loads(policy).get("Id")
        # resp = conn.remove_permission(topic=topic_arn, label=policy_id)
        # resp = conn.add_permission(topic=topic_arn, label='foo', account_ids='xyz', actions='deny')
        resp = conn.get_topic_attributes(topic=topic_arn)
        policy = resp.get('GetTopicAttributesResponse').get('GetTopicAttributesResult').get('Attributes').get('Policy')
        resp = conn.set_topic_attributes(topic_arn, 'Policy', policy.replace('Allow', 'Deny'))
        msg_id = conn.publish_sns_messsage(topic_arn=topic_arn)
        self.assertIsNotNone(msg_id)
