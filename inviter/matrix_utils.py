from typing import Mapping, Optional, TypedDict

from mautrix.api import HTTPAPI
from mautrix.client.api.events import EventMethods
from mautrix.client.api.rooms import RoomMethods
from mautrix.errors import MNotFound
from mautrix.types import (
    RoomID,
    RoomDirectoryVisibility,
    EventType,
    RoomNameStateEventContent,
    UserID,
    PowerLevelStateEventContent,
    StateEvent,
    Membership,
)
from mautrix.util.logging import TraceLogger


class UserInfo(TypedDict):
    power_level: Optional[int]


UserInfoMap = Mapping[str, UserInfo]


class MatrixUtils:
    room_methods = None
    event_methods = None
    logger = None

    def __init__(self, mautrix_api: HTTPAPI, log: TraceLogger):
        self.room_methods = RoomMethods(api=mautrix_api)
        self.event_methods = EventMethods(api=mautrix_api)
        self.logger = log

    async def ensure_room_visibility(self, room_id: RoomID, visibility: str):
        self.logger.debug(f"Ensuring visibility for {room_id}...")
        current_visibility = await self.room_methods.get_room_directory_visibility(
            room_id
        )
        if current_visibility != visibility:
            await self.room_methods.set_room_directory_visibility(
                room_id, RoomDirectoryVisibility(visibility)
            )

    async def ensure_room_name(self, room_id: RoomID, name: str) -> None:
        try:
            current_name = (
                await self.room_methods.get_state_event(room_id, EventType.ROOM_NAME)
            )["name"]
        except MNotFound:
            current_name = ""
        if not current_name == name:
            self.logger.debug(f"Setting name '{name}' for room {room_id}")
            await self.event_methods.send_state_event(
                room_id, EventType.ROOM_NAME, RoomNameStateEventContent(name)
            )

    async def create_room_with_alias(self, alias: str) -> RoomID:
        self.logger.debug(f"Creating room {alias}...")
        alias_local_part = alias[1:-1].split(":")[0]
        new_room_id = await self.room_methods.create_room(alias_local_part)
        self.logger.debug(f"Created room: {new_room_id}")
        return new_room_id

    async def ensure_room_with_alias(self, alias) -> RoomID:
        self.logger.debug(f"Ensuring {alias} exists...")
        try:
            room = await self.room_methods.get_room_alias(alias)
        except MNotFound:
            self.logger.debug(f"Alias {alias} not found.")
            return await self.create_room_with_alias(alias)
        if room is None:
            raise Exception(f"Could not find nor create room for alias {alias}")
        else:
            self.logger.debug(f"Found room: {room.room_id}")
            return room.room_id

    @staticmethod
    def state_events_to_member_list(state_events: [StateEvent]):
        member_mxids = []
        invite_mxids = []
        member_event_type = EventType.find("m.room.member", EventType.Class.STATE)
        for event in state_events:
            if (
                event.type == member_event_type
                and event.content.membership == Membership.JOIN
            ):
                member_mxids.append(event.state_key)
            if (
                event.type == member_event_type
                and event.content.membership == Membership.INVITE
            ):
                invite_mxids.append(event.state_key)
        return member_mxids, invite_mxids

    async def ensure_room_invitees(self, room_id: RoomID, user_info_map: UserInfoMap):
        room_member_events = await self.event_methods.get_members(room_id)
        room_members, room_invitees = self.state_events_to_member_list(
            room_member_events
        )
        self.logger.debug(f"Room {room_id} has members:{str(room_members)}")
        self.logger.debug(f"Room {room_id} has invitees:{str(room_invitees)}")
        for mxid in user_info_map:
            if mxid not in room_members and mxid not in room_invitees:
                self.logger.debug(
                    f"User {mxid} not invited or in the room, inviting..."
                )
                await self.room_methods.invite_user(room_id, mxid)
        self.logger.debug(f"Successfully ensured invitees for {room_id}")

    async def ensure_room_power_levels(
        self, room_id: RoomID, user_info_map: UserInfoMap
    ):
        current_state = await self.room_methods.get_state_event(
            room_id, EventType.ROOM_POWER_LEVELS
        )
        current_power_levels: dict[UserID, int] = current_state["users"]
        self.logger.debug(f"Current power levels: {str(current_power_levels)}")
        for mxid in user_info_map:
            current_power_levels[UserID(mxid)] = user_info_map[mxid]["power_level"]
        await self.room_methods.send_state_event(
            room_id,
            EventType.ROOM_POWER_LEVELS,
            PowerLevelStateEventContent(users=current_power_levels),
        )
        self.logger.debug(f"Successfully ensured power levels")
