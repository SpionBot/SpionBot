import redis
from dotenv import load_dotenv
from typing import Callable, Literal
import os
import random
import json
load_dotenv()
HOST = os.getenv("REDIS_HOST")
PORT = os.getenv("REDIS_PORT")
r = redis.Redis(
    host=HOST,
    port=PORT,
    db=0,
    decode_responses=True
)
ROOM_PROB_TTL_SECONDS = 14400

def _set_json(key: int | str, value: object, *, ex: int | None = None) -> None:
    r.set(key, json.dumps(value), ex=ex)

def _load_room_probs(room_id: int) -> dict[int, float]:
    raw = r.get(room_id)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    result: dict[int, float] = {}
    for key, value in data.items():
        try:
            result[int(key)] = float(value)
        except (ValueError, TypeError):
            continue
    return result

def _save_room_probs(room_id: int, users_prob: dict[int, float]) -> None:
    _set_json(room_id, users_prob, ex=ROOM_PROB_TTL_SECONDS)

def _apply_room_prob_update(
    room_id: int,
    updater: Callable[[dict[int, float]], bool],
) -> None:
    users_prob = _load_room_probs(room_id)
    if not users_prob:
        return
    if not updater(users_prob):
        return
    _save_room_probs(room_id, update_probability(users_prob))

def set_clue_hero(hero : str,content : dict)->None:
    _set_json(hero, content)
def get_clue_hero(hero : str,complexity: Literal["easy", "medium", "hard"]) -> str:
    value = json.loads(r.get(hero))
    number = random.randint(0,9)
    clue = value[complexity][number]
    return clue

def set_room_prob(user_ids: int | list[int], room_id: int) -> None:
    "Создание комнаты для n игроков."
    if isinstance(user_ids, int):
        users = [user_ids]
    else:
        users = list(user_ids)
    if not users:
        return
    _set_json(
        room_id,
        {user_id: 1 for user_id in users},
        ex=ROOM_PROB_TTL_SECONDS
    )
def update_prob_user(user_id : int,room_id : int,count_players:int)->None:
    "Обновление вероятностей"
    def _updater(users_prob: dict[int, float]) -> bool:
        if user_id not in users_prob:
            return False
        users_prob[user_id] = users_prob[user_id] * (1 - (0.5 / count_players))
        return True
    _apply_room_prob_update(room_id, _updater)

def add_user_room(user_id: int,room_id: int,count_player : int)->None:
    "Добавление нового user в dict вероятностей"
    def _updater(users_prob: dict[int, float]) -> bool:
        users_prob[user_id] = 1 / count_player
        return True
    _apply_room_prob_update(room_id, _updater)

def delete_user_room(user_id: int,room_id: int)->None:
    "Удаление user_id из dict по ключу"
    def _updater(users_prob: dict[int, float]) -> bool:
        if user_id not in users_prob:
            return False
        del users_prob[user_id]
        return True
    _apply_room_prob_update(room_id, _updater)

def update_probability(users_prob: dict)->dict:
    users_sm_prob = sum([users_prob[id] for id in users_prob])
    for id in users_prob:
        users_prob[id] /= users_sm_prob
    return users_prob

def get_player(users_prob: dict[int, float]) -> int:
    total = sum(users_prob.values())
    r = random.random() * total
    cum = 0.0
    last_id = None
    for player_id, prob in users_prob.items():
        cum += prob
        last_id = player_id
        if r < cum:
            return player_id
    return last_id
