from typing import Literal

from pydantic import BaseModel

AttackType = Literal[
    "recipient_change",
    "over_limit",
    "edge_of_limit",
    "rapid_retries",
    "pressure_language",
    "bad_work",
]


class AttackAccepted(BaseModel):
    attack_id: str
    type: AttackType
    status: Literal["started"] = "started"
