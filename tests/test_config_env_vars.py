"""
Tests for environment variable expansion in configuration loading (Issue 011).
"""

import os
from travelbot.daemon import TravelBotDaemon


class TestExpandEnvVars:
    """Tests for TravelBotDaemon._expand_env_vars."""

    def test_simple_string_expansion(self):
        """${VAR} in a string value should be replaced with the env var."""
        os.environ['TEST_API_KEY'] = 'secret-key-123'
        try:
            result = TravelBotDaemon._expand_env_vars('${TEST_API_KEY}')
            assert result == 'secret-key-123'
        finally:
            del os.environ['TEST_API_KEY']

    def test_string_with_surrounding_text(self):
        """${VAR} embedded in a larger string should be expanded in place."""
        os.environ['TEST_HOST'] = 'example.com'
        try:
            result = TravelBotDaemon._expand_env_vars('https://${TEST_HOST}/api')
            assert result == 'https://example.com/api'
        finally:
            del os.environ['TEST_HOST']

    def test_missing_env_var_left_unchanged(self):
        """${VAR} referencing an unset variable should remain as the literal string."""
        # Make sure the var doesn't exist
        os.environ.pop('NONEXISTENT_VAR_12345', None)
        result = TravelBotDaemon._expand_env_vars('${NONEXISTENT_VAR_12345}')
        assert result == '${NONEXISTENT_VAR_12345}'

    def test_nested_dict_expansion(self):
        """Environment variables in nested dicts should all be expanded."""
        os.environ['TEST_KEY'] = 'my-key'
        os.environ['TEST_PASS'] = 'my-pass'
        try:
            config = {
                'openai': {'api_key': '${TEST_KEY}'},
                'smtp': {'password': '${TEST_PASS}'},
            }
            result = TravelBotDaemon._expand_env_vars(config)
            assert result['openai']['api_key'] == 'my-key'
            assert result['smtp']['password'] == 'my-pass'
        finally:
            del os.environ['TEST_KEY']
            del os.environ['TEST_PASS']

    def test_list_expansion(self):
        """Environment variables inside lists should be expanded."""
        os.environ['TEST_KEYWORD'] = 'flight'
        try:
            result = TravelBotDaemon._expand_env_vars(['${TEST_KEYWORD}', 'hotel'])
            assert result == ['flight', 'hotel']
        finally:
            del os.environ['TEST_KEYWORD']

    def test_non_string_values_unchanged(self):
        """Integers, booleans, and None should pass through unchanged."""
        config = {
            'port': 587,
            'enabled': True,
            'optional': None,
        }
        result = TravelBotDaemon._expand_env_vars(config)
        assert result == config

    def test_plain_string_unchanged(self):
        """A string with no ${} pattern should be returned as-is."""
        result = TravelBotDaemon._expand_env_vars('just a normal string')
        assert result == 'just a normal string'

    def test_multiple_vars_in_one_string(self):
        """Multiple ${VAR} references in a single string should all expand."""
        os.environ['TEST_USER'] = 'admin'
        os.environ['TEST_DOMAIN'] = 'example.com'
        try:
            result = TravelBotDaemon._expand_env_vars('${TEST_USER}@${TEST_DOMAIN}')
            assert result == 'admin@example.com'
        finally:
            del os.environ['TEST_USER']
            del os.environ['TEST_DOMAIN']
