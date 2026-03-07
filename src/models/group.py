"""Data models for the BPSR mobile client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class User:
    connection_id: str
    username: str
    role: str = "member"  # "leader" | "member"
    device_type: str = "desktop"  # "desktop" | "mobile"

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            connection_id=data.get("connection_id", ""),
            username=data.get("username", ""),
            role=data.get("role", "member"),
            device_type=data.get("device_type", "desktop"),
        )


@dataclass
class Group:
    id: str
    name: str
    leader_id: str
    has_password: bool = False
    key_locks: Dict[str, bool] = field(default_factory=dict)
    member_count: int = 0
    members: List[User] = field(default_factory=list)
    created_at: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "Group":
        members = [User.from_dict(m) for m in data.get("members", [])]
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            leader_id=data.get("leader_id", ""),
            has_password=data.get("has_password", False),
            key_locks=data.get("key_locks", {}),
            member_count=data.get("member_count", len(members)),
            members=members,
            created_at=data.get("created_at", 0.0),
        )
