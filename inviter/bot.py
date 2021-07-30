import asyncio
from pprint import pformat
from traceback import format_exc
from typing import Type

from maubot import Plugin, MessageEvent
from maubot.handlers import command
from mautrix.client.api.events import EventMethods
from mautrix.client.api.rooms import RoomMethods
from mautrix.util.config import BaseProxyConfig

from .config import SyncRoomConfig, LDAPInviterConfig
from .ldap import LDAPManager
from .matrix_utils import MatrixUtils
from .utils import template_room_alias, to_user_info_map


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
        self.matrix_utils = MatrixUtils(self.client.api, self.log)

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return LDAPInviterConfig

    async def sync_room(
        self, evt: MessageEvent, room: SyncRoomConfig, template_arg1: str
    ):
        """Sync a single Matrix room"""
        # Setup LDAP connection
        ldap_manager = LDAPManager(
            self.config["ldap"]["uri"],
            self.config["ldap"]["connect_dn"],
            self.config["ldap"]["connect_password"],
            self.config["ldap"]["base_dn"],
            self.config["ldap"]["user_filter"],
            self.config["ldap"]["mxid_homeserver"],
            self.log,
        )

        # Generate the final room alias
        alias = template_room_alias(room["alias"], template_arg1)
        await evt.respond(f"Syncing room: {alias}")
        self.log.debug(f"Syncing room: {alias}")

        # Ensure room exists
        room_id = await self.matrix_utils.ensure_room_with_alias(alias)

        # Ensure room has the correct name
        await self.matrix_utils.ensure_room_name(room_id, room["name"])

        # Generate map of users
        all_users = {}
        all_users.update(
            await ldap_manager.get_all_matrix_users_of_sync_room(room["ldap_members"])
        )
        # Hardcoded users are added last to allow overriding LDAP
        all_users.update(to_user_info_map(room.get("members", [])))

        # Ensure users are invited
        await self.matrix_utils.ensure_room_invitees(room_id, all_users)

        # Ensure users have correct power levels
        await self.matrix_utils.ensure_room_power_levels(room_id, all_users)

        # Ensure room is (in) visible in Room Directory
        await self.matrix_utils.ensure_room_visibility(room_id, room["visibility"])

        await evt.respond(f"Successfully synced room.")
        self.log.debug(f"Successfully synced room.")

    async def sync_rooms(
        self, evt: MessageEvent, rooms: [SyncRoomConfig], template_arg1: str
    ):
        """Loops through a list of rooms to sync them"""
        for room in rooms:
            await self.sync_room(evt, room, template_arg1)

    @command.new(name="ldap-sync")
    @command.argument("arg1", "Argument 1", pass_raw=True, required=False)
    async def ldap_sync(self, evt: MessageEvent, arg1: str) -> None:
        # Check if the user is allowed to sync
        if evt.sender not in self.config["admin_users"]:
            await evt.respond("You are not allowed to run a sync.")
            return None

        await evt.respond(f'Starting sync.')
        try:
            await self.sync_rooms(evt, self.config["sync_rooms"], arg1)
        except Exception as e:
            # Wait a bit to hopefully clear too many requests
            await asyncio.sleep(5)
            await evt.respond(f"Encountered fatal error: {e}\n```\n{format_exc()}\n```")
            raise e

    @command.new(name="debug-map")
    async def ldap_check(self, evt: MessageEvent):
        await evt.respond(
            f'User map: {to_user_info_map(self.config["sync_rooms"][0]["members"])}'
        )

    @command.new(name="ldap-check")
    async def ldap_check(self, evt: MessageEvent):
        await evt.respond("Checking LDAP connection...")
        try:
            ldap_manager = LDAPManager(
                self.config["ldap"]["uri"],
                self.config["ldap"]["connect_dn"],
                self.config["ldap"]["connect_password"],
                self.config["ldap"]["base_dn"],
                self.config["ldap"]["user_filter"],
                self.config["ldap"]["mxid_homeserver"],
                self.log,
            )
            await evt.respond(
                f"Successfully connected. I am `{ldap_manager.connection.whoami_s()}`"
            )
            room: SyncRoomConfig
            for room in self.config["sync_rooms"]:
                uids = await ldap_manager.get_all_matrix_users_of_sync_room(
                    room["ldap_members"]
                )
                await evt.respond(
                    f'Members of room `{room["alias"]}`:\n```\n{pformat(uids)}\n```'
                )
        except Exception as e:
            await evt.respond(f"Encountered fatal error: {e}\n```\n{format_exc()}\n```")
            raise e
