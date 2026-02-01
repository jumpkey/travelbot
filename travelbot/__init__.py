"""
TravelBot v1.0 - Intelligent Travel Email Processing System

A professional travel itinerary processing system that monitors email for travel
information, extracts comprehensive travel details using AI, and automatically
generates timezone-aware calendar responses.

Key Features:
- Comprehensive travel service detection (flights, hotels, car rentals, etc.)
- Timezone-aware calendar generation with proper VTIMEZONE handling
- Professional email responses with tailored content
- Smart reply-to logic for forwarded and do-not-reply emails
- Fault-tolerant continuous monitoring daemon

Usage:
    from travelbot import TravelBotDaemon
    daemon = TravelBotDaemon()
    daemon.run_polling_loop()

Or via command line:
    python3 -m travelbot.daemon --poll-interval 30
"""

__version__ = "1.0.0"
__author__ = "TravelBot Development Team"
__email__ = "travelbot@example.com"

from .email_client import EmailClient
from .pdf_processor import extract_text_from_pdf

__all__ = ['EmailClient', 'extract_text_from_pdf']
