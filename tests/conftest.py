import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Optional

import pytest


@dataclass
class FakeUser:
    id: int
    full_name: str = "Test User"
    username: Optional[str] = None


@dataclass
class FakeChat:
    type: str = "private"
    id: int = 0
    sent_messages: list = None

    async def send_message(self, text, **kwargs):
        if self.sent_messages is None:
            self.sent_messages = []
        self.sent_messages.append({"text": text, "kwargs": kwargs})
        return None


class FakeMessage:
    def __init__(self, text: str = "", chat_id: int = 0):
        self.text = text
        self.chat_id = chat_id
        self.replies = []
        self.edits = []
        self.deleted = False
        self.reply_markup = None
        self.caption = None

    async def reply_text(self, text, **kwargs):
        self.replies.append({"text": text, "kwargs": kwargs})
        return None

    async def delete(self):
        self.deleted = True
        return None

    async def edit_text(self, text, **kwargs):
        self.text = text
        self.reply_markup = kwargs.get("reply_markup")
        self.edits.append({"text": text, "kwargs": kwargs})
        return None

    async def edit_caption(self, caption=None, **kwargs):
        self.caption = caption
        self.reply_markup = kwargs.get("reply_markup")
        self.edits.append({"caption": caption, "kwargs": kwargs})
        return None

    async def edit_message_media(self, media=None, **kwargs):
        self.edits.append({"media": media, "kwargs": kwargs})
        return None


class FakeCallbackQuery:
    def __init__(self, data, user_id=1, message=None):
        self.data = data
        self.from_user = FakeUser(user_id)
        self.message = message or FakeMessage(chat_id=user_id)
        self.answered = []

    async def answer(self, *args, **kwargs):
        self.answered.append({"args": args, "kwargs": kwargs})
        return None

    async def edit_message_media(self, media=None, **kwargs):
        self.message.edits.append({"media": media, "kwargs": kwargs})
        return None


class FakePhoto:
    def __init__(self, file_id: str):
        self.file_id = file_id


class FakeSentMessage:
    def __init__(self, photos=None):
        self.photo = photos or []


class FakeBot:
    def __init__(self):
        self.sent_messages = []
        self.sent_photos = []
        self.sent_invoices = []
        self._file_counter = 0

    async def send_message(self, chat_id, text, **kwargs):
        self.sent_messages.append(
            {"chat_id": chat_id, "text": text, "kwargs": kwargs}
        )
        return None

    async def send_photo(self, chat_id, photo, caption=None, **kwargs):
        self._file_counter += 1
        file_id = f"file_{self._file_counter}"
        self.sent_photos.append(
            {
                "chat_id": chat_id,
                "photo": photo,
                "caption": caption,
                "kwargs": kwargs,
                "file_id": file_id,
            }
        )
        return FakeSentMessage(photos=[FakePhoto(file_id)])

    async def get_chat_member(self, chat_id, user_id):
        return type("Member", (), {"status": "member"})

    async def send_invoice(self, chat_id, title, description, payload, currency, prices, start_parameter, provider_token):
        self.sent_invoices.append(
            {
                "chat_id": chat_id,
                "title": title,
                "description": description,
                "payload": payload,
                "currency": currency,
                "prices": prices,
                "start_parameter": start_parameter,
                "provider_token": provider_token,
            }
        )
        return None


class FakeContext:
    def __init__(self, bot):
        self.bot = bot
        self.args = []
        self.user_data = {}


class FakeUpdate:
    def __init__(self, user_id=1, text="", chat_type="private", message=None):
        self.effective_user = FakeUser(user_id)
        self.effective_chat = FakeChat(chat_type, id=user_id)
        self.message = message or FakeMessage(text, chat_id=user_id)
        self.callback_query = None
        self.pre_checkout_query = None


class FakePreCheckoutQuery:
    def __init__(self):
        self.answered = []

    async def answer(self, **kwargs):
        self.answered.append(kwargs)
        return None


class FakeSuccessfulPayment:
    def __init__(self, total_amount: int):
        self.total_amount = total_amount


class FakeDB:
    def __init__(self):
        self.rooms = {}
        self.room_players = {}
        self.player_data = {}
        self.image_cache = {}
        self.accounts = {}

    async def create_room(self, room_id, creator_id, mode="clash"):
        if room_id in self.rooms:
            return False
        self.rooms[room_id] = {
            "id": room_id,
            "creator_id": creator_id,
            "mode": mode,
            "word": None,
            "spy_id": None,
            "card_url": None,
            "game_started": False,
        }
        self.room_players[room_id] = []
        await self.add_player_to_room(creator_id, room_id)
        return True

    async def get_room(self, room_id):
        room = self.rooms.get(room_id)
        return dict(room) if room else None

    async def update_room_game_state(self, room_id, word, spy_id, card_url=None):
        room = self.rooms[room_id]
        room.update(
            {
                "word": word,
                "spy_id": spy_id,
                "card_url": card_url,
                "game_started": True,
            }
        )

    async def reset_room_game(self, room_id):
        room = self.rooms[room_id]
        room.update(
            {"word": None, "spy_id": None, "card_url": None, "game_started": False}
        )
        for key in list(self.player_data):
            if key[1] == room_id:
                self.player_data[key].update(
                    {"role": None, "word": None, "card_url": None}
                )

    async def delete_room(self, room_id):
        self.rooms.pop(room_id, None)
        self.room_players.pop(room_id, None)

    async def update_room_mode(self, room_id, mode):
        room = self.rooms[room_id]
        room["mode"] = mode

    async def add_player_to_room(self, user_id, room_id):
        players = self.room_players.get(room_id)
        if players is None:
            return False
        if len(players) >= 15:
            return False
        if user_id not in players:
            players.append(user_id)
        self.player_data[(user_id, room_id)] = {
            "user_id": user_id,
            "room_id": room_id,
            "role": None,
            "word": None,
            "card_url": None,
        }
        return True

    async def remove_player_from_room(self, user_id, room_id):
        players = self.room_players.get(room_id, [])
        if user_id in players:
            players.remove(user_id)
        self.player_data.pop((user_id, room_id), None)

    async def remove_player_from_all_rooms(self, user_id):
        for room_id, players in self.room_players.items():
            if user_id in players:
                players.remove(user_id)
            self.player_data.pop((user_id, room_id), None)

    async def get_room_players(self, room_id):
        return list(self.room_players.get(room_id, []))

    async def get_player_data(self, user_id, room_id):
        data = self.player_data.get((user_id, room_id))
        return dict(data) if data else None

    async def update_player_role(self, user_id, room_id, role, word=None, card_url=None):
        data = self.player_data.get((user_id, room_id), {})
        data.update({"role": role, "word": word, "card_url": card_url})
        self.player_data[(user_id, room_id)] = data

    async def get_user_room(self, user_id):
        for room_id, players in self.room_players.items():
            if user_id in players:
                return room_id
        return None

    async def get_room_creator(self, room_id):
        room = self.rooms.get(room_id)
        return room["creator_id"] if room else None

    async def transfer_room_ownership(self, room_id, new_creator_id):
        room = self.rooms[room_id]
        room["creator_id"] = new_creator_id

    async def cleanup_old_rooms(self):
        return None

    async def get_all_rooms_stats(self):
        return {
            "total_rooms": len(self.rooms),
            "active_rooms": sum(
                1 for room in self.rooms.values() if room.get("game_started")
            ),
            "total_players": sum(len(p) for p in self.room_players.values()),
        }

    async def get_cached_image(self, url):
        return self.image_cache.get(url)

    async def cache_image(self, url, file_id, mode):
        self.image_cache[url] = file_id

    async def cleanup_image_cache(self):
        return None

    async def ensure_user_account(self, user_id):
        self.accounts.setdefault(
            user_id,
            {
                "user_id": user_id,
                "balance": 0,
                "hard_hints": 0,
                "medium_hints": 0,
                "easy_hints": 0,
            },
        )

    async def get_user_account(self, user_id):
        return dict(self.accounts.get(user_id)) if user_id in self.accounts else None

    async def add_balance(self, user_id, amount):
        if amount <= 0:
            return None
        await self.ensure_user_account(user_id)
        self.accounts[user_id]["balance"] += amount
        return self.accounts[user_id]["balance"]

    async def purchase_hints(self, user_id, cost, hard=0, medium=0, easy=0):
        if cost < 0 or hard < 0 or medium < 0 or easy < 0:
            return None
        await self.ensure_user_account(user_id)
        if self.accounts[user_id]["balance"] < cost:
            return None
        self.accounts[user_id]["balance"] -= cost
        self.accounts[user_id]["hard_hints"] += hard
        self.accounts[user_id]["medium_hints"] += medium
        self.accounts[user_id]["easy_hints"] += easy
        return dict(self.accounts[user_id])


class FakeTransaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    def __init__(self, fetchrow_results=None, fetchval_results=None, fetch_results=None):
        self.fetchrow_results = deque(fetchrow_results or [])
        self.fetchval_results = deque(fetchval_results or [])
        self.fetch_results = deque(fetch_results or [])
        self.executed = []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return None

    async def fetchrow(self, sql, *args):
        if self.fetchrow_results:
            return self.fetchrow_results.popleft()
        return None

    async def fetchval(self, sql, *args):
        if self.fetchval_results:
            return self.fetchval_results.popleft()
        return None

    async def fetch(self, sql, *args):
        if self.fetch_results:
            return self.fetch_results.popleft()
        return []

    def transaction(self):
        return FakeTransaction()


class FakeAcquire:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return FakeAcquire(self._conn)


def run(coro):
    return asyncio.run(coro)


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end tests")


@pytest.fixture()
def fake_bot():
    return FakeBot()


@pytest.fixture()
def fake_context(fake_bot):
    return FakeContext(fake_bot)


@pytest.fixture()
def fake_db():
    return FakeDB()


@pytest.fixture()
def make_update():
    def _make_update(user_id=1, text="", chat_type="private"):
        return FakeUpdate(user_id=user_id, text=text, chat_type=chat_type)

    return _make_update


@pytest.fixture()
def make_callback_update():
    def _make_callback_update(user_id=1, data="action"):
        update = FakeUpdate(user_id=user_id, text="")
        update.callback_query = FakeCallbackQuery(data=data, user_id=user_id)
        return update

    return _make_callback_update


@pytest.fixture()
def make_precheckout_update():
    def _make_precheckout_update(user_id=1):
        update = FakeUpdate(user_id=user_id, text="")
        update.pre_checkout_query = FakePreCheckoutQuery()
        return update

    return _make_precheckout_update


@pytest.fixture()
def make_payment_update():
    def _make_payment_update(user_id=1, total_amount=100):
        update = FakeUpdate(user_id=user_id, text="")
        update.message.successful_payment = FakeSuccessfulPayment(total_amount)
        return update

    return _make_payment_update


@pytest.fixture()
def fake_conn():
    return FakeConn()


@pytest.fixture()
def fake_pool(fake_conn):
    return FakePool(fake_conn)


@pytest.fixture()
def patched_commands(monkeypatch, fake_db):
    import handlers.commands as commands
    import utils.decorators as decorators

    monkeypatch.setattr(commands, "db", fake_db)
    commands.decorators.db = fake_db

    async def always_subscribed(bot, user_id):
        return True

    monkeypatch.setattr(decorators, "is_subscribed", always_subscribed)
    return commands


__all__ = [
    "FakeBot",
    "FakeContext",
    "FakeUpdate",
    "FakeMessage",
    "FakeCallbackQuery",
    "FakeDB",
    "FakeConn",
    "FakePool",
    "FakePreCheckoutQuery",
    "FakeSuccessfulPayment",
    "run",
]
