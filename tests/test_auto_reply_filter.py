"""
Tests for auto-reply and bounce detection.

These tests verify that TravelBot correctly identifies auto-generated emails
(OOO replies, bounces, mailing lists) to prevent email loops.
"""

from email.message import EmailMessage
from travelbot.auto_reply_filter import (
    should_skip_auto_reply,
    ReplyRateLimiter,
)


def make_msg(headers: dict) -> EmailMessage:
    """Helper to create an EmailMessage with specified headers."""
    msg = EmailMessage()
    for key, value in headers.items():
        msg[key] = value
    return msg


def make_email_content(from_addr: str, subject: str, body: str = "") -> dict:
    """Helper to create email_content dict."""
    return {
        "uid": "123",
        "from": from_addr,
        "subject": subject,
        "body_text": body,
        "pdf_text": None,
    }


class TestShouldSkipAutoReply:
    """Tests for the should_skip_auto_reply function."""

    def test_normal_email_not_skipped(self):
        """Normal human email should not be skipped."""
        msg = make_msg({
            "From": "human@example.com",
            "Subject": "Flight booking confirmation",
        })
        email_content = make_email_content("human@example.com", "Flight booking confirmation")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is False
        assert reason is None

    def test_auto_submitted_auto_replied(self):
        """RFC 3834 Auto-Submitted: auto-replied should be skipped."""
        msg = make_msg({
            "From": "user@example.com",
            "Subject": "Re: Your travel itinerary",
            "Auto-Submitted": "auto-replied",
        })
        email_content = make_email_content("user@example.com", "Re: Your travel itinerary")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "Auto-Submitted" in reason

    def test_auto_submitted_auto_generated(self):
        """RFC 3834 Auto-Submitted: auto-generated should be skipped."""
        msg = make_msg({
            "From": "notifications@example.com",
            "Subject": "System notification",
            "Auto-Submitted": "auto-generated",
        })
        email_content = make_email_content("notifications@example.com", "System notification")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "Auto-Submitted" in reason

    def test_auto_submitted_no_not_skipped(self):
        """Auto-Submitted: no means human-generated, should not skip."""
        msg = make_msg({
            "From": "user@example.com",
            "Subject": "My travel plans",
            "Auto-Submitted": "no",
        })
        email_content = make_email_content("user@example.com", "My travel plans")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is False

    def test_precedence_bulk(self):
        """Precedence: bulk should be skipped."""
        msg = make_msg({
            "From": "newsletter@example.com",
            "Subject": "Weekly newsletter",
            "Precedence": "bulk",
        })
        email_content = make_email_content("newsletter@example.com", "Weekly newsletter")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "Precedence" in reason

    def test_precedence_list(self):
        """Precedence: list should be skipped."""
        msg = make_msg({
            "From": "list@example.com",
            "Subject": "Mailing list post",
            "Precedence": "list",
        })
        email_content = make_email_content("list@example.com", "Mailing list post")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "Precedence" in reason

    def test_empty_return_path_bounce(self):
        """Empty Return-Path indicates bounce, should be skipped."""
        msg = make_msg({
            "From": "MAILER-DAEMON@mx.example.com",
            "Subject": "Mail delivery failed",
            "Return-Path": "<>",
        })
        email_content = make_email_content("MAILER-DAEMON@mx.example.com", "Mail delivery failed")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "Return-Path" in reason or "mailer-daemon" in reason.lower()

    def test_x_auto_response_suppress(self):
        """X-Auto-Response-Suppress header should trigger skip."""
        msg = make_msg({
            "From": "user@example.com",
            "Subject": "Meeting invite",
            "X-Auto-Response-Suppress": "All",
        })
        email_content = make_email_content("user@example.com", "Meeting invite")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "X-Auto-Response-Suppress" in reason

    def test_list_id_header(self):
        """List-Id header indicates mailing list, should be skipped."""
        msg = make_msg({
            "From": "user@example.com",
            "Subject": "Discussion topic",
            "List-Id": "<dev.example.com>",
        })
        email_content = make_email_content("user@example.com", "Discussion topic")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "list" in reason.lower()

    def test_list_unsubscribe_header(self):
        """List-Unsubscribe header indicates mailing list, should be skipped."""
        msg = make_msg({
            "From": "newsletter@example.com",
            "Subject": "Monthly update",
            "List-Unsubscribe": "<mailto:unsubscribe@example.com>",
        })
        email_content = make_email_content("newsletter@example.com", "Monthly update")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "list" in reason.lower()

    def test_mailer_daemon_sender(self):
        """MAILER-DAEMON sender should be skipped."""
        msg = make_msg({
            "From": "MAILER-DAEMON@mx.example.com",
            "Subject": "Undelivered Mail Returned to Sender",
        })
        email_content = make_email_content("MAILER-DAEMON@mx.example.com", "Undelivered Mail Returned to Sender")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "mailer-daemon" in reason.lower() or "Bounce" in reason

    def test_postmaster_sender(self):
        """postmaster sender should be skipped."""
        msg = make_msg({
            "From": "postmaster@example.com",
            "Subject": "Delivery Status Notification",
        })
        email_content = make_email_content("postmaster@example.com", "Delivery Status Notification")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True

    def test_self_loop_prevention(self):
        """Email from our own address should be skipped (self-loop)."""
        msg = make_msg({
            "From": "travelbot@example.com",
            "Subject": "Re: Your itinerary",
        })
        email_content = make_email_content("travelbot@example.com", "Re: Your itinerary")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "self-loop" in reason.lower() or "own address" in reason.lower()

    def test_out_of_office_subject(self):
        """Out of Office in subject should be skipped."""
        msg = make_msg({
            "From": "colleague@example.com",
            "Subject": "Out of Office: Re: Travel plans",
        })
        email_content = make_email_content("colleague@example.com", "Out of Office: Re: Travel plans")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "out of office" in reason.lower()

    def test_automatic_reply_subject(self):
        """Automatic reply in subject should be skipped."""
        msg = make_msg({
            "From": "user@example.com",
            "Subject": "Automatic reply: Your message",
        })
        email_content = make_email_content("user@example.com", "Automatic reply: Your message")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True
        assert "automatic reply" in reason.lower()

    def test_delivery_failure_subject(self):
        """Delivery failure in subject should be skipped."""
        msg = make_msg({
            "From": "mail-system@example.com",
            "Subject": "Delivery failure notification",
        })
        email_content = make_email_content("mail-system@example.com", "Delivery failure notification")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True

    def test_case_insensitive_matching(self):
        """Header and subject matching should be case-insensitive."""
        msg = make_msg({
            "From": "USER@EXAMPLE.COM",
            "Subject": "OUT OF OFFICE: Away",
            "Auto-Submitted": "AUTO-REPLIED",
        })
        email_content = make_email_content("USER@EXAMPLE.COM", "OUT OF OFFICE: Away")
        
        skip, reason = should_skip_auto_reply(msg, email_content, "travelbot@example.com")
        
        assert skip is True


class TestReplyRateLimiter:
    """Tests for the rate limiter."""

    def test_allows_first_reply(self):
        """First reply should always be allowed."""
        limiter = ReplyRateLimiter(max_replies=3, window_seconds=3600)
        
        can_send, reason = limiter.can_send("user@example.com")
        
        assert can_send is True
        assert reason is None

    def test_allows_up_to_max_replies(self):
        """Should allow up to max_replies within window."""
        limiter = ReplyRateLimiter(max_replies=3, window_seconds=3600)
        
        for i in range(3):
            can_send, _ = limiter.can_send("user@example.com")
            assert can_send is True
            limiter.record_reply("user@example.com")

    def test_blocks_after_max_replies(self):
        """Should block after max_replies within window."""
        limiter = ReplyRateLimiter(max_replies=3, window_seconds=3600)
        
        for _ in range(3):
            limiter.record_reply("user@example.com")
        
        can_send, reason = limiter.can_send("user@example.com")
        
        assert can_send is False
        assert "Rate limit" in reason

    def test_different_addresses_independent(self):
        """Rate limits should be independent per address."""
        limiter = ReplyRateLimiter(max_replies=2, window_seconds=3600)
        
        limiter.record_reply("user1@example.com")
        limiter.record_reply("user1@example.com")
        
        can_send_user1, _ = limiter.can_send("user1@example.com")
        can_send_user2, _ = limiter.can_send("user2@example.com")
        
        assert can_send_user1 is False
        assert can_send_user2 is True

    def test_window_expiry(self):
        """Old replies should expire after window."""
        current_time = [0]
        def fake_now():
            return current_time[0]
        
        limiter = ReplyRateLimiter(max_replies=2, window_seconds=3600, now_func=fake_now)
        
        limiter.record_reply("user@example.com")
        limiter.record_reply("user@example.com")
        
        can_send_before, _ = limiter.can_send("user@example.com")
        assert can_send_before is False
        
        current_time[0] = 3601
        
        can_send_after, _ = limiter.can_send("user@example.com")
        assert can_send_after is True

    def test_case_insensitive_addresses(self):
        """Email addresses should be case-insensitive."""
        limiter = ReplyRateLimiter(max_replies=2, window_seconds=3600)
        
        limiter.record_reply("User@Example.com")
        limiter.record_reply("USER@EXAMPLE.COM")
        
        can_send, _ = limiter.can_send("user@example.com")
        
        assert can_send is False

    def test_clear_history(self):
        """Clear should reset all history."""
        limiter = ReplyRateLimiter(max_replies=1, window_seconds=3600)
        
        limiter.record_reply("user@example.com")
        can_send_before, _ = limiter.can_send("user@example.com")
        assert can_send_before is False
        
        limiter.clear()
        
        can_send_after, _ = limiter.can_send("user@example.com")
        assert can_send_after is True
