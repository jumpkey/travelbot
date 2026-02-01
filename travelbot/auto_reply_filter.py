"""
Auto-reply and bounce detection for TravelBot.

This module provides heuristic-based detection of auto-generated emails
(out-of-office replies, bounces, mailing lists) to prevent email loops.

RFC 3834 defines standard headers for automatic responses.
"""

from email.message import Message
from email.utils import parseaddr
from typing import Tuple, Optional, Dict, Any


def should_skip_auto_reply(
    msg: Message,
    email_content: Dict[str, Any],
    smtp_user: str
) -> Tuple[bool, Optional[str]]:
    """
    Determine if an email is auto-generated and should not receive a reply.
    
    This is the first line of defense against email loops. It checks
    standard headers and sender patterns BEFORE calling the LLM.
    
    Args:
        msg: The raw email.message.Message object with headers
        email_content: The parsed email content dict from EmailClient
        smtp_user: The configured SMTP user (to detect self-loops)
    
    Returns:
        Tuple of (should_skip: bool, reason: str or None)
        If should_skip is True, reason explains why.
    """
    
    # 1. Check RFC 3834 Auto-Submitted header
    # Values: "no" (human), "auto-generated", "auto-replied", "auto-notified"
    auto_submitted = (msg.get('Auto-Submitted') or '').lower().strip()
    if auto_submitted and auto_submitted != 'no':
        return True, f"Auto-Submitted header: {auto_submitted}"
    
    # 2. Check Precedence header (bulk, junk, list indicate automated/mass mail)
    precedence = (msg.get('Precedence') or '').lower().strip()
    if precedence in ('bulk', 'junk', 'list', 'auto_reply'):
        return True, f"Precedence header: {precedence}"
    
    # 3. Check for empty Return-Path (indicates bounce/DSN)
    return_path = msg.get('Return-Path') or ''
    if return_path == '<>' or (return_path and not return_path.strip('<>')):
        return True, "Empty Return-Path (bounce indicator)"
    
    # 4. Check X-Auto-Response-Suppress header (Microsoft/Exchange)
    if msg.get('X-Auto-Response-Suppress'):
        return True, "X-Auto-Response-Suppress header present"
    
    # 5. Check for mailing list headers
    if msg.get('List-Id') or msg.get('List-Unsubscribe'):
        return True, "Mailing list headers present"
    
    # 6. Check for bounce/daemon senders
    from_addr = email_content.get('from', '').lower()
    bounce_senders = [
        'mailer-daemon', 'mail-daemon', 'postmaster',
        'bounce', 'returned', 'undeliverable',
        'mail delivery', 'delivery status'
    ]
    for pattern in bounce_senders:
        if pattern in from_addr:
            return True, f"Bounce sender pattern: {pattern}"
    
    # 7. Check for self-loop (replying to our own address)
    # Parse the actual email address from the From header (which may include display name)
    if smtp_user:
        _, parsed_from = parseaddr(email_content.get('from', ''))
        _, parsed_smtp = parseaddr(smtp_user)
        if parsed_from.lower() == parsed_smtp.lower():
            return True, "Self-loop detected (from own address)"
    
    # 8. Check for common auto-reply subject patterns
    subject = email_content.get('subject', '').lower()
    auto_reply_subjects = [
        'automatic reply',
        'auto-reply',
        'autoreply',
        'out of office',
        'out of the office',
        'away from',
        'on vacation',
        'delivery status notification',
        'delivery failure',
        'undeliverable',
        'returned mail',
        'mail delivery failed',
        'failure notice',
        'delayed mail',
        'could not be delivered',
        'read receipt',
        'read: ',
    ]
    for pattern in auto_reply_subjects:
        if pattern in subject:
            return True, f"Auto-reply subject pattern: {pattern}"
    
    # No auto-reply indicators found
    return False, None


def get_message_type_from_headers(
    msg: Message,
    email_content: Dict[str, Any]
) -> Tuple[str, Optional[str]]:
    """
    Classify message type based on headers (before LLM call).
    
    Returns:
        Tuple of (message_type: str, reason: str or None)
        message_type is one of: "AUTO_REPLY", "BOUNCE", "MAILING_LIST", "NORMAL"
    """
    
    # Check for auto-reply indicators
    auto_submitted = (msg.get('Auto-Submitted') or '').lower().strip()
    if auto_submitted == 'auto-replied':
        return "AUTO_REPLY", f"Auto-Submitted: {auto_submitted}"
    
    # Check for bounce indicators
    return_path = msg.get('Return-Path') or ''
    from_addr = email_content.get('from', '').lower()
    
    if return_path == '<>' or 'mailer-daemon' in from_addr or 'postmaster' in from_addr:
        return "BOUNCE", "Bounce/DSN indicators present"
    
    # Check for auto-generated (could be notification, not reply)
    if auto_submitted == 'auto-generated' or auto_submitted == 'auto-notified':
        return "AUTO_REPLY", f"Auto-Submitted: {auto_submitted}"
    
    # Check for mailing list
    if msg.get('List-Id') or msg.get('List-Unsubscribe'):
        return "MAILING_LIST", "Mailing list headers present"
    
    # Check precedence
    precedence = (msg.get('Precedence') or '').lower().strip()
    if precedence in ('bulk', 'junk', 'list'):
        return "MAILING_LIST", f"Precedence: {precedence}"
    
    # Check subject patterns for auto-reply
    subject = email_content.get('subject', '').lower()
    ooo_patterns = ['out of office', 'automatic reply', 'auto-reply', 'autoreply']
    for pattern in ooo_patterns:
        if pattern in subject:
            return "AUTO_REPLY", f"Subject contains: {pattern}"
    
    bounce_patterns = ['delivery status', 'delivery failure', 'undeliverable', 'returned mail']
    for pattern in bounce_patterns:
        if pattern in subject:
            return "BOUNCE", f"Subject contains: {pattern}"
    
    return "NORMAL", None


class ReplyRateLimiter:
    """
    Rate limiter to prevent sending too many replies to the same address.
    
    This is a safety net in case auto-reply detection fails.
    """
    
    def __init__(
        self,
        max_replies: int = 3,
        window_seconds: int = 3600,
        now_func=None
    ):
        """
        Args:
            max_replies: Maximum replies to same address within window
            window_seconds: Time window in seconds (default 1 hour)
            now_func: Optional function returning current time (for testing)
        """
        import time
        self.max_replies = max_replies
        self.window_seconds = window_seconds
        self.now_func = now_func or time.time
        self._reply_history: Dict[str, list] = {}
    
    def can_send(self, email_address: str) -> Tuple[bool, Optional[str]]:
        """
        Check if we can send a reply to this address.
        
        Args:
            email_address: The recipient email address
            
        Returns:
            Tuple of (can_send: bool, reason: str or None)
        """
        email_lower = email_address.lower()
        now = self.now_func()
        
        # Clean up old entries
        if email_lower in self._reply_history:
            self._reply_history[email_lower] = [
                t for t in self._reply_history[email_lower]
                if now - t < self.window_seconds
            ]
        
        # Check count
        history = self._reply_history.get(email_lower, [])
        if len(history) >= self.max_replies:
            return False, f"Rate limit exceeded: {len(history)} replies in {self.window_seconds}s"
        
        return True, None
    
    def record_reply(self, email_address: str) -> None:
        """Record that we sent a reply to this address."""
        email_lower = email_address.lower()
        now = self.now_func()
        
        if email_lower not in self._reply_history:
            self._reply_history[email_lower] = []
        
        self._reply_history[email_lower].append(now)
    
    def clear(self) -> None:
        """Clear all history (for testing)."""
        self._reply_history.clear()
