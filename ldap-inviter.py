from typing import Type, Optional, TypedDict

from maubot.handlers import command
from mautrix.client.api.events import EventMethods
from mautrix.client.api.rooms import RoomMethods
from mautrix.errors import MNotFound
from mautrix.types import UserID, RoomID, StateEvent, Membership, RoomNameStateEventContent, \
    PowerLevelStateEventContent, RoomDirectoryVisibility
from mautrix.types.event.type import EventType
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from maubot import Plugin, MessageEvent


class UserConfig(TypedDict):
    mxid: str
    power_level: Optional[int]


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("sync_rooms")


class LDAPInviterBot(Plugin):
    room_methods = None
    event_methods = None

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()
        self.room_methods = RoomMethods(api=self.client.api)
        self.event_methods = EventMethods(api=self.client.api)

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @staticmethod
    def state_events_to_member_list(state_events: [StateEvent]):
        member_mxids = []
        invite_mxids = []
        member_event_type = EventType.find("m.room.member", EventType.Class.STATE)
        for event in state_events:
            if event.type == member_event_type and event.content.membership == Membership.JOIN:
                member_mxids.append(event.state_key)
            if event.type == member_event_type and event.content.membership == Membership.INVITE:
                invite_mxids.append(event.state_key)
        return member_mxids, invite_mxids

    async def ensure_room_visibility(self, evt: MessageEvent, room_id: RoomID, visibility: str):
        await evt.respond(f'Ensuring visibility for {room_id}...')
        current_visibility = await self.room_methods.get_room_directory_visibility(room_id)
        if current_visibility != visibility:
            await self.room_methods.set_room_directory_visibility(room_id, RoomDirectoryVisibility(visibility))

    async def ensure_room_name(self, evt: MessageEvent, room_id: RoomID, name: str) -> None:
        current_name = await self.room_methods.get_state_event(room_id, EventType.ROOM_NAME)
        if not current_name['name'] == name:
            await evt.respond(f'Setting name \'{name}\' for room {room_id}')
            await self.event_methods.send_state_event(room_id, EventType.ROOM_NAME, RoomNameStateEventContent(name))

    async def create_room_with_alias(self, evt: MessageEvent, alias: str) -> RoomID:
        await evt.respond(f'Creating room {alias}...')
        alias_local_part = alias[1:-1].split(':')[0]
        new_room_id = await self.room_methods.create_room(alias_local_part)
        await evt.respond(f'Created room: {new_room_id}')
        return new_room_id

    async def ensure_room_with_alias(self, evt, alias) -> RoomID:
        await evt.respond(f'Ensuring {alias} exists...')
        try:
            room = await self.room_methods.get_room_alias(alias)
        except MNotFound:
            await evt.respond(f'Alias {alias} not found.')
            return await self.create_room_with_alias(evt, alias)
        if room is None:
            await evt.respond('Wäääh, kaputt')
        else:
            await evt.respond(f'Found room: {room.room_id}')
            return room.room_id

    async def ensure_room_invitees(self, evt: MessageEvent, room_id: RoomID, users: [UserConfig]):
        room_member_events = await self.event_methods.get_members(room_id)
        room_members, room_invitees = self.state_events_to_member_list(room_member_events)
        await evt.respond(f'Room {room_id} has members:{str(room_members)}')
        await evt.respond(f'Room {room_id} has invitees:{str(room_invitees)}')
        for user_id in users:
            if user_id['mxid'] not in room_members and user_id['mxid'] not in room_invitees:
                await evt.respond(f'User {user_id["mxid"]} not invited or in the room, inviting...')
                await self.room_methods.invite_user(room_id, user_id['mxid'])
        await evt.respond(f'Successfully ensured invitees for {room_id}')

    async def ensure_room_power_levels(self, evt: MessageEvent, room_id: RoomID, users: [UserConfig]):
        current_state = await self.room_methods.get_state_event(room_id, EventType.ROOM_POWER_LEVELS)
        current_power_levels: dict[UserID, int] = current_state['users']
        await evt.respond(f'Current power levels: {str(current_power_levels)}')
        user: UserConfig
        for user in users:
            current_power_levels[UserID(user['mxid'])] = user['power_level']
        await self.room_methods.send_state_event(room_id, EventType.ROOM_POWER_LEVELS,
                                                 PowerLevelStateEventContent(users=current_power_levels))
        await evt.respond(f'Successfully ensured power levels')

    async def sync_room(self, evt: MessageEvent, room):
        alias = room['alias']
        await evt.respond(f'Syncing room: {alias}')
        # Ensure room exists
        room_id = await self.ensure_room_with_alias(evt, alias)
        # Ensure room has the correct name
        await self.ensure_room_name(evt, room_id, room['name'])
        # Ensure hardcoded users are invited
        await self.ensure_room_invitees(evt, room_id, room['members'])
        # Ensure users have correct power levels
        await self.ensure_room_power_levels(evt, room_id, room['members'])
        # Ensure room is (in) visible in Room Directory
        await self.ensure_room_visibility(evt, room_id, room['visibility'])
        await evt.respond(f'Successfully synced room.')

    async def sync_rooms(self, evt, rooms):
        for room in rooms:
            await self.sync_room(evt, room)

    @command.new(name='ldap-sync')
    async def ldap_sync(self, evt: MessageEvent) -> None:
        await evt.respond('Starting sync...')
        await self.sync_rooms(evt, self.config["sync_rooms"])
