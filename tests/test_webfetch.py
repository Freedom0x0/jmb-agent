from __future__ import annotations

import socket
import unittest
import urllib.error
import urllib.request
from unittest import mock

from jmb import webfetch


class WebfetchSafetyTest(unittest.TestCase):
    def test_private_and_special_urls_rejected(self) -> None:
        urls = [
            "http://127.0.0.1/",
            "http://127.0.0.1:7777/bubble",
            "http://localhost/",
            "http://10.0.0.1/",
            "http://192.168.1.1/",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/",
            "http://0.0.0.0/",
            "ftp://example.com/",
        ]
        for url in urls:
            self.assertFalse(webfetch.url_is_public(url), url)

    def test_public_url_with_public_dns(self) -> None:
        answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with mock.patch("socket.getaddrinfo", return_value=answer):
            self.assertTrue(webfetch.url_is_public("https://example.com/path"))

    def test_dns_failure_rejected(self) -> None:
        with mock.patch("socket.getaddrinfo", side_effect=OSError("no dns")):
            self.assertFalse(webfetch.url_is_public("https://example.com/"))

    def test_fetch_page_rejects_private(self) -> None:
        result = webfetch.fetch_page("http://127.0.0.1:7777/bubble")
        self.assertIn("公网", result)

    def test_redirect_to_private_rejected(self) -> None:
        request = urllib.request.Request("https://example.com/")
        handler = webfetch._SafeRedirectHandler()
        with self.assertRaises(urllib.error.URLError):
            handler.redirect_request(
                request, None, 302, "Found", {}, "http://127.0.0.1/secret")


if __name__ == "__main__":
    unittest.main()
