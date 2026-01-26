"""
Telegram object simulator for CLI testing.

Creates mock Update and Context objects that behave like real Telegram API objects.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class MockUser:
    """Mock Telegram User object."""
    id: int
    is_bot: bool = False
    first_name: str = "CLI"
    last_name: Optional[str] = "User"
    username: Optional[str] = "cli_debugger"
    language_code: str = "en"


@dataclass
class MockChat:
    """Mock Telegram Chat object."""
    id: int
    type: str = "private"
    username: Optional[str] = "cli_debugger"
    first_name: str = "CLI"
    last_name: Optional[str] = "User"


@dataclass
class MockVoice:
    """Mock Telegram Voice object."""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: str = "audio/ogg"
    file_size: Optional[int] = None


@dataclass
class MockAudio:
    """Mock Telegram Audio object."""
    file_id: str
    file_unique_id: str
    duration: int
    mime_type: str = "audio/mpeg"
    file_size: Optional[int] = None


@dataclass
class MockFile:
    """Mock Telegram File object."""
    file_id: str
    file_unique_id: str
    file_size: int
    file_path: str

    async def download_to_drive(self, custom_path: str) -> str:
        """Mock file download - copy source file to destination."""
        import shutil
        # Copy the source file (file_path) to the destination (custom_path)
        shutil.copy2(self.file_path, custom_path)
        return custom_path


@dataclass
class MockMessage:
    """Mock Telegram Message object."""
    message_id: int
    date: datetime
    chat: MockChat
    from_user: Optional[MockUser] = None
    text: Optional[str] = None
    voice: Optional[MockVoice] = None
    audio: Optional[MockAudio] = None
    caption: Optional[str] = None

    @property
    def chat_id(self) -> int:
        """Get chat_id from chat object (for compatibility with Telegram API)."""
        return self.chat.id

    async def reply_text(self, text: str, **kwargs) -> MockMessage:
        """Mock reply to message."""
        print(f"\n🤖 Bot Reply:\n{text}\n")
        return MockMessage(
            message_id=self.message_id + 1,
            date=datetime.now(),
            chat=self.chat,
            text=text,
        )


@dataclass
class MockCallbackQuery:
    """Mock Telegram CallbackQuery object."""
    id: str
    from_user: MockUser
    message: Optional[MockMessage]
    data: Optional[str]

    async def answer(self, text: Optional[str] = None, **kwargs):
        """Mock callback query answer."""
        if text:
            print(f"✅ Callback answered: {text}")


@dataclass
class MockUpdate:
    """Mock Telegram Update object."""
    update_id: int
    message: Optional[MockMessage] = None
    callback_query: Optional[MockCallbackQuery] = None
    edited_message: Optional[MockMessage] = None

    @property
    def effective_chat(self):
        """Get effective chat from update."""
        if self.message:
            return self.message.chat
        if self.callback_query and self.callback_query.message:
            return self.callback_query.message.chat
        return None

    @property
    def effective_user(self):
        """Get effective user from update."""
        if self.message:
            return self.message.from_user
        if self.callback_query:
            return self.callback_query.from_user
        return None


class MockBot:
    """Mock Telegram Bot object."""

    def __init__(self, simulator=None):
        """Initialize mock bot with optional simulator reference."""
        self.username = "editorbot_cli"
        self.simulator = simulator

    async def send_message(self, chat_id: int, text: str, **kwargs) -> MockMessage:
        """Mock send message."""
        print(f"\n🤖 Bot Message:\n{text}\n")
        return MockMessage(
            message_id=999,
            date=datetime.now(),
            chat=MockChat(id=chat_id),
            text=text,
        )

    async def get_file(self, file_id: str) -> MockFile:
        """Mock get file."""
        # Look up actual path from simulator if available
        if self.simulator and file_id in self.simulator.file_paths:
            actual_path = self.simulator.file_paths[file_id]
        else:
            actual_path = f"/tmp/{file_id}"

        return MockFile(
            file_id=file_id,
            file_unique_id=f"unique_{file_id}",
            file_size=1024,
            file_path=actual_path,
        )


@dataclass
class MockApplication:
    """Mock Application object."""
    bot: MockBot

    @property
    def bot_data(self):
        """Mock bot data storage."""
        return {}


@dataclass
class MockContext:
    """Mock Context object."""
    application: MockApplication
    bot: MockBot

    def __init__(self, simulator=None):
        self.bot = MockBot(simulator=simulator)
        self.application = MockApplication(bot=self.bot)


class TelegramSimulator:
    """
    Creates mock Telegram objects for CLI testing.
    """

    def __init__(self, chat_id: int = 12345):
        self.chat_id = chat_id
        self.user = MockUser(id=chat_id)
        self.chat = MockChat(id=chat_id)
        self.message_counter = 1000
        self.file_paths = {}  # Store file_id -> actual_path mapping

    def create_voice_update(self, file_path: str, duration: int = 3) -> MockUpdate:
        """
        Create mock Update for voice message.

        Args:
            file_path: Local path to audio file
            duration: Audio duration in seconds

        Returns:
            MockUpdate with voice message
        """
        file_id = f"voice_{self.message_counter}"

        # Store the actual file path for this file_id
        self.file_paths[file_id] = file_path

        voice = MockVoice(
            file_id=file_id,
            file_unique_id=f"unique_{self.message_counter}",
            duration=duration,
            file_size=1024 * 50,  # ~50KB
        )

        message = MockMessage(
            message_id=self.message_counter,
            date=datetime.now(),
            chat=self.chat,
            from_user=self.user,
            voice=voice,
        )

        self.message_counter += 1

        return MockUpdate(
            update_id=self.message_counter,
            message=message,
        )

    def create_text_update(self, text: str) -> MockUpdate:
        """
        Create mock Update for text message.

        Args:
            text: Message text

        Returns:
            MockUpdate with text message
        """
        message = MockMessage(
            message_id=self.message_counter,
            date=datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text=text,
        )

        self.message_counter += 1

        return MockUpdate(
            update_id=self.message_counter,
            message=message,
        )

    def create_callback_update(self, callback_data: str) -> MockUpdate:
        """
        Create mock Update for inline keyboard callback.

        Args:
            callback_data: Callback data (e.g., "template:explainer")

        Returns:
            MockUpdate with callback query
        """
        # Create a previous message for callback context
        message = MockMessage(
            message_id=self.message_counter - 1,
            date=datetime.now(),
            chat=self.chat,
            from_user=self.user,
            text="Previous message",
        )

        callback_query = MockCallbackQuery(
            id=f"callback_{self.message_counter}",
            from_user=self.user,
            message=message,
            data=callback_data,
        )

        self.message_counter += 1

        return MockUpdate(
            update_id=self.message_counter,
            callback_query=callback_query,
        )

    def create_context(self) -> MockContext:
        """
        Create mock Context object.

        Returns:
            MockContext with bot instance and simulator reference
        """
        return MockContext(simulator=self)
