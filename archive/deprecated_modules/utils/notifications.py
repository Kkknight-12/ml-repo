"""
Notification Manager - Handles alerts and notifications
Supports Mac native notifications and sound alerts
"""
import os
import sys
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationManager:
    """
    Manages system notifications for trading signals
    """

    def __init__(self):
        """Initialize notification manager"""
        self.enabled = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
        self.sound_enabled = os.getenv('ENABLE_SOUND_ALERTS', 'true').lower() == 'true'

        # Check platform
        self.is_mac = sys.platform == 'darwin'
        self.is_windows = sys.platform == 'win32'
        self.is_linux = sys.platform.startswith('linux')

        logger.info(f"Notification manager initialized. Platform: {sys.platform}")

    def send_notification(self, title: str, message: str, sound: bool = True):
        """
        Send system notification

        Args:
            title: Notification title
            message: Notification message
            sound: Whether to play sound
        """
        if not self.enabled:
            return

        try:
            if self.is_mac:
                self._send_mac_notification(title, message, sound)
            elif self.is_windows:
                self._send_windows_notification(title, message)
            elif self.is_linux:
                self._send_linux_notification(title, message)
            else:
                # Fallback to console
                print(f"\n[NOTIFICATION] {title}: {message}")

        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

    def _send_mac_notification(self, title: str, message: str, sound: bool = True):
        """Send Mac notification using osascript"""
        try:
            # Build AppleScript command
            script = f'display notification "{message}" with title "{title}"'

            if sound and self.sound_enabled:
                script += ' sound name "Glass"'

            # Execute
            subprocess.run(['osascript', '-e', script], check=True)

            # Alternative: Use terminal-notifier if installed
            # subprocess.run(['terminal-notifier', '-title', title, '-message', message])

        except subprocess.CalledProcessError:
            # Fallback to simpler notification
            os.system(f"""
                osascript -e 'display notification "{message}" with title "{title}"'
            """)

    def _send_windows_notification(self, title: str, message: str):
        """Send Windows notification"""
        try:
            # Try using Windows 10 toast notifications
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=10)
        except ImportError:
            # Fallback to balloon tip
            self._windows_balloon_tip(title, message)

    def _send_linux_notification(self, title: str, message: str):
        """Send Linux notification using notify-send"""
        try:
            subprocess.run(['notify-send', title, message], check=True)
        except:
            print(f"\n[NOTIFICATION] {title}: {message}")

    def _windows_balloon_tip(self, title: str, message: str):
        """Windows balloon tip fallback"""
        try:
            import ctypes
            from ctypes import wintypes

            # This is a simplified version
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        except:
            print(f"\n[NOTIFICATION] {title}: {message}")

    def play_sound(self, sound_type: str = "alert"):
        """
        Play alert sound

        Args:
            sound_type: Type of sound (alert, success, error)
        """
        if not self.sound_enabled:
            return

        try:
            if self.is_mac:
                # Mac system sounds
                sounds = {
                    "alert": "Glass",
                    "success": "Hero",
                    "error": "Basso"
                }
                sound_name = sounds.get(sound_type, "Glass")
                subprocess.run(['afplay', f'/System/Library/Sounds/{sound_name}.aiff'])

            elif self.is_windows:
                # Windows beep
                import winsound
                if sound_type == "error":
                    winsound.MessageBeep(winsound.MB_ICONHAND)
                else:
                    winsound.MessageBeep(winsound.MB_OK)

            else:
                # Linux/Unix beep
                print('\a')  # Terminal bell

        except Exception as e:
            logger.error(f"Failed to play sound: {str(e)}")

    def test_notifications(self):
        """Test notification system"""
        print("Testing notifications...")

        # Test basic notification
        self.send_notification(
            "Test Notification",
            "This is a test notification from Lorentzian Scanner",
            sound=True
        )

        # Test different sounds
        if self.is_mac:
            print("Testing sounds...")
            for sound_type in ["alert", "success", "error"]:
                print(f"Playing {sound_type} sound...")
                self.play_sound(sound_type)
                import time
                time.sleep(1)

        print("Notification test complete!")


# Utility functions for quick notifications
def notify_signal(symbol: str, signal_type: str, price: float):
    """Quick function to notify about a trading signal"""
    notifier = NotificationManager()

    emoji = "🟢" if signal_type == "BUY" else "🔴"
    title = f"{emoji} {signal_type} Signal: {symbol}"
    message = f"Price: ₹{price:.2f}"

    notifier.send_notification(title, message, sound=True)


def notify_error(error_message: str):
    """Quick function to notify about an error"""
    notifier = NotificationManager()
    notifier.send_notification(
        "⚠️ Scanner Error",
        error_message,
        sound=True
    )
    notifier.play_sound("error")


if __name__ == "__main__":
    # Test notifications
    manager = NotificationManager()
    manager.test_notifications()