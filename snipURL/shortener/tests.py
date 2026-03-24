"""
Comprehensive tests for URL shortener.
"""
from django.test import TestCase, Client
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from rest_framework.test import APITestCase
from rest_framework import status

from .models import ShortenedURL
from .utils import (
    encode_base62,
    decode_base62,
    normalize_url,
    validate_custom_code,
    generate_qr_code
)
from .cache import (
    cache_url,
    get_cached_url,
    increment_click_redis,
    get_buffered_clicks,
    read_and_clear_clicks_atomic
)


class Base62TestCase(TestCase):
    """Test base62 encoding/decoding."""

    def test_encode_zero(self):
        self.assertEqual(encode_base62(0), '0')

    def test_encode_small_numbers(self):
        self.assertEqual(encode_base62(1), '1')
        self.assertEqual(encode_base62(10), 'a')
        self.assertEqual(encode_base62(61), 'Z')

    def test_encode_large_number(self):
        result = encode_base62(1000000)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_decode_matches_encode(self):
        """Test that decode reverses encode."""
        for num in [0, 1, 10, 100, 1000, 999999]:
            encoded = encode_base62(num)
            decoded = decode_base62(encoded)
            self.assertEqual(decoded, num)


class URLNormalizationTestCase(TestCase):
    """Test URL normalization."""

    def test_lowercase_hostname(self):
        url = normalize_url('https://EXAMPLE.COM/path')
        self.assertEqual(url, 'https://example.com/path')

    def test_remove_default_http_port(self):
        url = normalize_url('http://example.com:80/path')
        self.assertEqual(url, 'http://example.com/path')

    def test_remove_default_https_port(self):
        url = normalize_url('https://example.com:443/path')
        self.assertEqual(url, 'https://example.com/path')

    def test_keep_non_default_port(self):
        url = normalize_url('https://example.com:8080/path')
        self.assertEqual(url, 'https://example.com:8080/path')

    def test_remove_utm_parameters(self):
        url = normalize_url('https://example.com/path?utm_source=test&utm_medium=email&foo=bar')
        self.assertNotIn('utm_source', url)
        self.assertNotIn('utm_medium', url)
        self.assertIn('foo=bar', url)

    def test_reject_invalid_scheme(self):
        with self.assertRaises(ValueError):
            normalize_url('ftp://example.com')

    def test_preserve_path_and_query(self):
        url = normalize_url('https://example.com/path/to/page?query=value')
        self.assertIn('/path/to/page', url)
        self.assertIn('query=value', url)


class CustomCodeValidationTestCase(TestCase):
    """Test custom code validation."""

    def test_valid_alphanumeric_code(self):
        self.assertTrue(validate_custom_code('abc123'))
        self.assertTrue(validate_custom_code('MyCustomCode'))

    def test_reject_empty_code(self):
        with self.assertRaises(ValueError):
            validate_custom_code('')

    def test_reject_too_long_code(self):
        long_code = 'a' * 33
        with self.assertRaises(ValueError):
            validate_custom_code(long_code)

    def test_reject_special_characters(self):
        with self.assertRaises(ValueError):
            validate_custom_code('my-code')
        with self.assertRaises(ValueError):
            validate_custom_code('my_code')
        with self.assertRaises(ValueError):
            validate_custom_code('my.code')


class QRCodeTestCase(TestCase):
    """Test QR code generation."""

    def test_generate_qr_code(self):
        qr_base64 = generate_qr_code('https://example.com')
        self.assertIsInstance(qr_base64, str)
        self.assertGreater(len(qr_base64), 0)

    def test_qr_code_is_base64(self):
        import base64
        qr_base64 = generate_qr_code('https://example.com')
        try:
            base64.b64decode(qr_base64)
        except Exception:
            self.fail('QR code is not valid base64')


class UrlModelTestCase(TestCase):
    """Test Url model."""

    def test_create_url(self):
        url = Url.objects.create(
            code='test123',
            original_url='https://example.com'
        )
        self.assertEqual(url.code, 'test123')
        self.assertEqual(url.original_url, 'https://example.com')
        self.assertTrue(url.is_active)

    def test_is_expired_false_when_no_expiry(self):
        url = Url.objects.create(
            code='test',
            original_url='https://example.com'
        )
        self.assertFalse(url.is_expired())

    def test_is_expired_false_when_future(self):
        future = timezone.now() + timedelta(days=1)
        url = Url.objects.create(
            code='test',
            original_url='https://example.com',
            expires_at=future
        )
        self.assertFalse(url.is_expired())

    def test_is_expired_true_when_past(self):
        past = timezone.now() - timedelta(days=1)
        url = Url.objects.create(
            code='test',
            original_url='https://example.com',
            expires_at=past
        )
        self.assertTrue(url.is_expired())


class URLStatsModelTestCase(TestCase):
    """Test URLStats model."""

    def test_create_stats(self):
        url = Url.objects.create(
            code='test',
            original_url='https://example.com'
        )
        stats = URLStats.objects.create(url=url)
        self.assertEqual(stats.total_clicks, 0)
        self.assertEqual(stats.url, url)

    def test_increment_clicks(self):
        url = Url.objects.create(
            code='test',
            original_url='https://example.com'
        )
        stats = URLStats.objects.create(url=url)
        stats.total_clicks += 10
        stats.save()
        self.assertEqual(stats.total_clicks, 10)


class CacheTestCase(TestCase):
    """Test Redis caching functions."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_cache_and_get_url(self):
        url_data = {
            'url_id': 1,
            'original_url': 'https://example.com',
            'expires_at': None,
            'is_active': True
        }
        cache_url('test123', url_data)

        cached = get_cached_url('test123')
        self.assertIsNotNone(cached)
        self.assertEqual(cached['url_id'], 1)
        self.assertEqual(cached['original_url'], 'https://example.com')

    def test_get_cached_url_miss(self):
        cached = get_cached_url('nonexistent')
        self.assertIsNone(cached)

    def test_increment_click_redis(self):
        increment_click_redis(1)
        increment_click_redis(1)
        increment_click_redis(2)

        buffered = get_buffered_clicks()
        self.assertEqual(buffered.get(1), 2)
        self.assertEqual(buffered.get(2), 1)

    def test_read_and_clear_clicks_atomic(self):
        increment_click_redis(1)
        increment_click_redis(1)
        increment_click_redis(2)

        clicks = read_and_clear_clicks_atomic()
        self.assertEqual(clicks.get(1), 2)
        self.assertEqual(clicks.get(2), 1)

        # Should be cleared
        buffered = get_buffered_clicks()
        self.assertEqual(len(buffered), 0)


class ShortenURLAPITestCase(APITestCase):
    """Test the shorten URL API endpoint."""

    def test_shorten_url_basic(self):
        data = {'url': 'https://example.com'}
        response = self.client.post('/shorten', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('code', response.data)
        self.assertIn('short_url', response.data)
        self.assertIn('qr_base64', response.data)

    def test_shorten_url_with_custom_code(self):
        data = {
            'url': 'https://example.com',
            'custom': 'mycode'
        }
        response = self.client.post('/shorten', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'mycode')

    def test_shorten_url_duplicate_custom_code(self):
        data = {
            'url': 'https://example.com',
            'custom': 'mycode'
        }
        self.client.post('/shorten', data, format='json')

        # Try to create again with same custom code
        response = self.client.post('/shorten', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shorten_url_with_expiration(self):
        future = (timezone.now() + timedelta(days=1)).isoformat()
        data = {
            'url': 'https://example.com',
            'expires_at': future
        }
        response = self.client.post('/shorten', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_shorten_url_invalid_url(self):
        data = {'url': 'not-a-url'}
        response = self.client.post('/shorten', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_shorten_url_missing_url(self):
        data = {}
        response = self.client.post('/shorten', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RedirectURLTestCase(TestCase):
    """Test URL redirection."""

    def setUp(self):
        cache.clear()

    def test_redirect_existing_url(self):
        url = Url.objects.create(
            code='test',
            original_url='https://example.com'
        )
        URLStats.objects.create(url=url)

        response = self.client.get('/test')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], 'https://example.com')

    def test_redirect_nonexistent_url(self):
        response = self.client.get('/nonexistent')
        self.assertEqual(response.status_code, 404)

    def test_redirect_expired_url(self):
        past = timezone.now() - timedelta(days=1)
        url = Url.objects.create(
            code='expired',
            original_url='https://example.com',
            expires_at=past
        )

        response = self.client.get('/expired')
        self.assertEqual(response.status_code, 410)

    def test_redirect_inactive_url(self):
        url = Url.objects.create(
            code='inactive',
            original_url='https://example.com',
            is_active=False
        )

        response = self.client.get('/inactive')
        self.assertEqual(response.status_code, 410)


class StatsAPITestCase(APITestCase):
    """Test the stats API endpoint."""

    def test_stats_endpoint(self):
        Url.objects.create(code='test1', original_url='https://example.com')
        Url.objects.create(code='test2', original_url='https://example.org')

        response = self.client.get('/stats')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_urls', response.data)
        self.assertIn('buffered_clicks', response.data)
        self.assertEqual(response.data['total_urls'], 2)


class HealthCheckTestCase(TestCase):
    """Test health check endpoint."""

    def test_health_check(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'OK')
