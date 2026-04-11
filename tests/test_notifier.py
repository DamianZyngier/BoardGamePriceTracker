import pytest
from unittest.mock import patch, MagicMock
from src.notifier import EmailNotifier
from src.config import settings

def test_email_notifier_uses_correct_receiver():
    """Test that EmailNotifier uses the receiver property from settings."""
    # Temporarily set EMAIL_RECEIVER to None to ensure fallback is used
    with patch('src.config.settings.EMAIL_RECEIVER', None):
        # And ensure EMAIL_SENDER is set
        with patch('src.config.settings.EMAIL_SENDER', 'sender@example.com'):
            notifier = EmailNotifier()
            assert notifier.receiver == 'sender@example.com'

def test_email_notifier_sends_email_with_mock():
    """Test that EmailNotifier.send calls smtplib.SMTP_SSL correctly."""
    with patch('smtplib.SMTP_SSL') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_instance
        
        # Setup settings for test
        with patch('src.config.settings.EMAIL_SENDER', 'sender@example.com'):
            with patch('src.config.settings.EMAIL_APP_PASSWORD', MagicMock(get_secret_value=MagicMock(return_value='password'))):
                with patch('src.config.settings.EMAIL_RECEIVER', 'receiver@example.com'):
                    notifier = EmailNotifier()
                    success = notifier.send("Test Subject", "Test Body")
                    
                    assert success is True
                    # Verify login and send_message were called
                    mock_instance.login.assert_called_with('sender@example.com', 'password')
                    mock_instance.send_message.assert_called_once()
                    
                    # Check if 'To' header was set correctly in the message passed to send_message
                    args, _ = mock_instance.send_message.call_args
                    msg = args[0]
                    assert msg['To'] == 'receiver@example.com'
                    assert msg['Subject'] == 'Test Subject'
