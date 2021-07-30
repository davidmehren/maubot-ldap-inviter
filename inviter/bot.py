import asyncio
from pprint import pformat
from typing import Type

from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.client.api.events import EventMethods
from mautrix.client.api.rooms import RoomMethods
from mautrix.util.config import BaseProxyConfig

from .config import MemberConfig, SyncRoomConfig, LDAPInviterConfig
from .ldap import get_all_matrix_users_of_sync_room
from .matrix_utils import MatrixUtils, UserInfoMap, UserConfig


class LDAPInviterBot(Plugin):
    room_methods = None
    event_methods = None
    matrix_utils = None
    config: LDAPInviterConfig

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()
        self.room_methods = RoomMethods(api=self.client.api)
        self.event_methods = EventMethods(api=self.client.api)
        self.matrix_utils = MatrixUtils(self.client.api)

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return LDAPInviterConfig

    @staticmethod
    def template_room_alias(alias: str, arg1: str) -> str:
        if "<1>" in alias and arg1 == "":
            raise Exception(f'Room alias "{alias}" includes a placeholder, but no argument was provided')
        return alias.replace('<1>', arg1)

    @staticmethod
    def to_user_info_map(member_config: [MemberConfig]) -> UserInfoMap:
        user_info_map = {}
        user: dict
        for user in member_config:
            user_info_map[user['mxid']] = UserConfig(power_level=user.get('power_level', 0))
        return user_info_map

    async def sync_room(self, evt: MessageEvent, room, arg1: str):
        alias = room['alias']
        alias = self.template_room_alias(alias, arg1)
        await evt.respond(f'Syncing room: {alias}')
        # Ensure room exists
        room_id = await self.matrix_utils.ensure_room_with_alias(evt, alias)
        # Ensure room has the correct name
        await self.matrix_utils.ensure_room_name(evt, room_id, room['name'])
        # Ensure hardcoded users are invited
        await self.matrix_utils.ensure_room_invitees(evt, room_id, self.to_user_info_map(room['members']))
        # Ensure users have correct power levels
        await self.matrix_utils.ensure_room_power_levels(evt, room_id, self.to_user_info_map(room['members']))
        # Ensure room is (in) visible in Room Directory
        await self.matrix_utils.ensure_room_visibility(evt, room_id, room['visibility'])
        await evt.respond(f'Successfully synced room.')

    async def sync_rooms(self, evt, rooms, arg1: str):
        for room in rooms:
            await self.sync_room(evt, room, arg1)

    @command.new(name='ldap-sync')
    @command.argument("arg1", "Argument 1", pass_raw=True, required=False)
    async def ldap_sync(self, evt: MessageEvent, arg1: str) -> None:
        if evt.sender not in self.config['admin_users']:
            await evt.respond('You are not allowed to run a sync.')
            return None
        await evt.respond(f'Starting sync. Arg1: "{arg1}"')
        try:
            await self.sync_rooms(evt, self.config["sync_rooms"], arg1)
        except Exception as e:
            # Wait a bit to hopefully clear too many requests
            await asyncio.sleep(5)
            await evt.respond(f'Encountered fatal error: {e}')

    @command.new(name='debug-map')
    async def ldap_check(self, evt: MessageEvent):
        await evt.respond(f'User map: {self.to_user_info_map(self.config["sync_rooms"][0]["members"])}')

    @command.new(name='ldap-check')
    async def ldap_check(self, evt: MessageEvent):
        await evt.respond("Checking LDAP connection...")
        try:
            import ldap
            # Create LDAP connection
            con = ldap.initialize(self.config['ldap']['uri'])
            con.simple_bind_s(self.config['ldap']['connect_dn'], self.config['ldap']['connect_password'])
            await evt.respond(f'Successfully connected. I am `{con.whoami_s()}`')
            room: SyncRoomConfig
            for room in self.config['sync_rooms']:
                uids = await get_all_matrix_users_of_sync_room(self.config, evt, con, room)
                await evt.respond(f'Members of room `{room["alias"]}`:\n```\n{pformat(uids)}\n```')
            con.unbind_s()
        except Exception as e:
            await evt.respond(f'Encountered fatal error: {e}')
            raise e
