import unittest
from unittest import mock

from utils.qr_login import QRLoginManager
from cookie_manager import CookieManager
import reply_server


class QRLoginCookieTests(unittest.TestCase):
    def test_browser_cookies_use_playwright_url_shape(self):
        manager = QRLoginManager()

        cookies = manager._build_browser_cookies(
            "https://passport.goofish.com/iv/remote/pc/mini_login_check.htm",
            {"foo": "bar"},
        )

        self.assertEqual(cookies[0]["url"], "https://passport.goofish.com")
        self.assertNotIn("path", cookies[0])

    def test_incomplete_qr_cookie_is_saved_without_starting_account_task(self):
        current_user = {"user_id": 1, "username": "tester"}
        raw_cookie = "unb=682496487; sgcookie=sg; cookie2=c2; t=t1"

        manager = mock.Mock()
        manager.add_cookie = mock.Mock()
        with mock.patch.object(reply_server.db_manager, "save_cookie") as save_cookie, \
             mock.patch.object(reply_server.cookie_manager, "manager", manager), \
             mock.patch("XianyuAutoAsync.XianyuLive.clear_password_login_failure_backoff") as clear_backoff:
            result = __import__('asyncio').run(reply_server._fallback_save_qr_cookie(
                "682496487",
                raw_cookie,
                1,
                True,
                current_user,
                "test refresh timeout",
            ))

        save_cookie.assert_called_once_with("682496487", raw_cookie, 1)
        manager.add_cookie.assert_not_called()
        clear_backoff.assert_called_once_with("682496487")
        self.assertFalse(result["task_restarted"])
        self.assertIn("_m_h5_tk", result["missing_required_fields"])
        self.assertIn("账号任务未启动", result["warning_message"])

    def test_task_cookie_validation_requires_signing_token(self):
        self.assertIn(
            "_m_h5_tk",
            CookieManager.get_task_cookie_validation_error("unb=682496487; cookie2=c2"),
        )
        self.assertIsNone(CookieManager.get_task_cookie_validation_error(
            "unb=682496487; cookie2=c2; _m_h5_tk=token_123"
        ))


if __name__ == "__main__":
    unittest.main()
