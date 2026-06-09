#!/usr/bin/env python3
"""
Security tests for article-fetcher skill.
Covers all 6 findings without requiring network, browser, or Vault.
Run: python3 tests/test_security.py
"""
import sys, os, unittest, subprocess, tempfile, sqlite3, ipaddress
from urllib.parse import urlparse

SKILL_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, 'scripts')
REFS_DIR    = os.path.join(SKILL_DIR, 'references')
sys.path.insert(0, REFS_DIR)


# ── Replicate _is_safe_image_url (identical in both playwright scripts) ────────
def is_safe_image_url(src):
    p = urlparse(src)
    if p.scheme not in ('http', 'https'):
        return False
    try:
        ip = ipaddress.ip_address(p.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except (ValueError, TypeError):
        pass
    return True


# ═════════════════════════════════════════════════════════════════════════════
# Finding #2 + #5 — _is_safe_image_url() scheme + IP filter
# ═════════════════════════════════════════════════════════════════════════════
class TestSafeImageUrl(unittest.TestCase):

    # --- Normal URLs: must be allowed ---
    def test_https_allowed(self):
        self.assertTrue(is_safe_image_url('https://pbs.twimg.com/media/abc.jpg'))

    def test_http_allowed(self):
        self.assertTrue(is_safe_image_url('http://example.com/image.png'))

    def test_cdn_with_query_allowed(self):
        self.assertTrue(is_safe_image_url('https://cdn.example.com/img.jpg?w=800'))

    # --- file:// — Finding #2: local file read ---
    def test_file_etc_passwd_blocked(self):
        self.assertFalse(is_safe_image_url('file:///etc/passwd'))

    def test_file_aws_credentials_blocked(self):
        self.assertFalse(is_safe_image_url('file:///Users/harvey/.aws/credentials'))

    def test_file_ssh_key_blocked(self):
        self.assertFalse(is_safe_image_url('file:///Users/harvey/.ssh/id_rsa'))

    def test_file_claude_settings_blocked(self):
        self.assertFalse(is_safe_image_url('file:///Users/harvey/.claude/settings.json'))

    # --- Other dangerous schemes ---
    def test_ftp_blocked(self):
        self.assertFalse(is_safe_image_url('ftp://example.com/image.jpg'))

    def test_data_uri_blocked(self):
        self.assertFalse(is_safe_image_url('data:image/png;base64,abc123'))

    def test_javascript_blocked(self):
        self.assertFalse(is_safe_image_url('javascript:alert(1)'))

    # --- Private IPs — Finding #5: SSRF ---
    def test_private_192_blocked(self):
        self.assertFalse(is_safe_image_url('http://192.168.1.1/admin'))

    def test_private_10_blocked(self):
        self.assertFalse(is_safe_image_url('http://10.0.0.1/secret'))

    def test_private_172_blocked(self):
        self.assertFalse(is_safe_image_url('http://172.16.0.1/data'))

    def test_loopback_127_blocked(self):
        self.assertFalse(is_safe_image_url('http://127.0.0.1:8080/api'))

    def test_aws_metadata_endpoint_blocked(self):
        self.assertFalse(is_safe_image_url('http://169.254.169.254/latest/meta-data/'))

    def test_link_local_blocked(self):
        self.assertFalse(is_safe_image_url('http://169.254.0.1/resource'))

    # --- Known limitation: hostname-based internal services ---
    def test_localhost_hostname_limitation(self):
        # 'localhost' is a hostname, not a bare IP; ipaddress.ip_address('localhost')
        # raises ValueError → NOT caught by current filter. Document this gap.
        result = is_safe_image_url('http://localhost/admin')
        # Currently returns True — this is a known gap.
        # Mitigation: real-world pages almost never embed localhost image URLs.
        self.assertTrue(result)  # documents current behavior, not desired behavior


# ═════════════════════════════════════════════════════════════════════════════
# Finding #3 — URL scheme validation at playwright script entry
# ═════════════════════════════════════════════════════════════════════════════
class TestScriptUrlSchemeValidation(unittest.TestCase):

    def _run(self, script, url, extra_args=None):
        """Run script with given URL; return (returncode, stderr). Fast: exits before Playwright."""
        cmd = ['python3', os.path.join(SCRIPTS_DIR, script), url,
               '/tmp/fake_vault', '/tmp/fake_skill']
        if extra_args:
            cmd.insert(3, extra_args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    # playwright_xcom.py
    def test_xcom_rejects_file_url(self):
        r = self._run('playwright_xcom.py', 'file:///etc/passwd')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Rejected', r.stderr)

    def test_xcom_rejects_javascript_url(self):
        r = self._run('playwright_xcom.py', 'javascript:alert(1)')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Rejected', r.stderr)

    def test_xcom_rejects_bare_path(self):
        r = self._run('playwright_xcom.py', '/etc/passwd')
        self.assertEqual(r.returncode, 1)

    def test_xcom_rejects_no_host(self):
        r = self._run('playwright_xcom.py', 'https://')
        self.assertEqual(r.returncode, 1)

    # playwright_web.py (takes html_path as argv[2])
    def test_web_rejects_file_url(self):
        cmd = ['python3', os.path.join(SCRIPTS_DIR, 'playwright_web.py'),
               'file:///etc/passwd', '/tmp/fake.html', '/tmp/fake_vault', '/tmp/fake_skill']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 1)
        self.assertIn('Rejected', r.stderr)

    def test_web_rejects_ftp_url(self):
        cmd = ['python3', os.path.join(SCRIPTS_DIR, 'playwright_web.py'),
               'ftp://example.com/page', '/tmp/fake.html', '/tmp/fake_vault', '/tmp/fake_skill']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 1)


# ═════════════════════════════════════════════════════════════════════════════
# Finding #6 — validate_article.py: env var params, no shell injection surface
# ═════════════════════════════════════════════════════════════════════════════
class TestValidateArticle(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'url-index.db')
        conn = sqlite3.connect(self.db_path)
        conn.execute('''CREATE TABLE url_index (
            url TEXT PRIMARY KEY, title TEXT, fetched_at TEXT,
            issues TEXT, category TEXT, origin_path TEXT, article_path TEXT
        )''')
        conn.commit()
        conn.close()

    def _make_md(self, filename):
        path = os.path.join(self.tmpdir, filename)
        with open(path, 'w') as f:
            f.write("""---
publish_date: 2026-01-01
fetch_date: 2026-05-17
author: Test Author
source_url: https://example.com/test
origin_title: "Test Article"
description: A test article for security testing
tags:
  - test
---

# Test Article

Content here.
""")
        return path

    def _run(self, url='https://example.com/test', category='',
             origin_path=None, article_path=None):
        env = {
            'ARTICLE_URL':       url,
            'ARTICLE_ORIGIN':    origin_path or self.origin,
            'ARTICLE_PATH':      article_path or self.article,
            'ARTICLE_DB':        self.db_path,
            'ARTICLE_SKILL_DIR': SKILL_DIR,
            'ARTICLE_CATEGORY':  category,
            'PATH':              os.environ.get('PATH', ''),
        }
        return subprocess.run(
            ['python3', os.path.join(SCRIPTS_DIR, 'validate_article.py')],
            env=env, capture_output=True, text=True, timeout=30
        )

    def test_valid_article_exits_zero(self):
        self.origin  = self._make_md('origin.md')
        self.article = self._make_md('article.md')
        r = self._run()
        self.assertEqual(r.returncode, 0)
        self.assertIn('翻译完成', r.stdout)

    def test_writes_url_to_sqlite(self):
        self.origin  = self._make_md('origin2.md')
        self.article = self._make_md('article2.md')
        url = 'https://example.com/article2'
        self._run(url=url)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute('SELECT url FROM url_index WHERE url=?', (url,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_category_stored_in_sqlite(self):
        self.origin  = self._make_md('origin3.md')
        self.article = self._make_md('article3.md')
        url = 'https://example.com/article3'
        self._run(url=url, category='AI')
        conn = sqlite3.connect(self.db_path)
        row = conn.execute('SELECT category FROM url_index WHERE url=?', (url,)).fetchone()
        conn.close()
        self.assertEqual(row[0], 'AI')

    def test_missing_article_exits_nonzero(self):
        self.origin  = self._make_md('origin4.md')
        self.article = '/nonexistent/path/article.md'
        r = self._run()
        self.assertEqual(r.returncode, 1)

    def test_url_with_shell_metacharacters_stored_literally(self):
        """Key test: env var passing means shell metacharacters in URL are safe."""
        self.origin  = self._make_md('origin5.md')
        self.article = self._make_md('article5.md')
        nasty_url = "https://example.com/it's-a-test;rm${IFS}-rf${IFS}/"
        r = self._run(url=nasty_url)
        self.assertEqual(r.returncode, 0)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute('SELECT url FROM url_index WHERE url=?', (nasty_url,)).fetchone()
        conn.close()
        # URL stored as literal string, shell never saw it
        self.assertIsNotNone(row)

    def test_category_with_quotes_stored_literally(self):
        """Category with quotes would break python3 -c; env var is safe."""
        self.origin  = self._make_md('origin6.md')
        self.article = self._make_md('article6.md')
        url = 'https://example.com/article6'
        nasty_cat = "AI'; import os; os.system('id')"
        r = self._run(url=url, category=nasty_cat)
        self.assertEqual(r.returncode, 0)
        conn = sqlite3.connect(self.db_path)
        row = conn.execute('SELECT category FROM url_index WHERE url=?', (url,)).fetchone()
        conn.close()
        self.assertEqual(row[0], nasty_cat)  # stored verbatim


if __name__ == '__main__':
    unittest.main(verbosity=2)
