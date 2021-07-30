import ldap
from ldap.ldapobject import SimpleLDAPObject

from maubot import MessageEvent

from .config import SyncRoomConfig
from .matrix_utils import UserInfoMap, UserConfig


class LDAPManager:
    connection = None

    def __init__(self, server_uri: str, user_dn: str, user_pass: str):
        # Create LDAP connection
        self.connection = ldap.initialize(server_uri)
        self.connection.simple_bind_s(
            user_dn,
            user_pass,
        )

    async def get_matrix_users_of_ldap_group(
        self,
        config,
        evt: MessageEvent,
        ldap_group: str,
        power_level: int,
    ) -> UserInfoMap:
        await evt.respond(f"Getting users for LDAP group `{ldap_group}`")
        ldap_filter = f"(&{config['ldap']['user_filter']}(memberOf={ldap_group}))"
        group_members = self.connection.search_s(
            config["ldap"]["base_dn"], ldap.SCOPE_SUBTREE, ldap_filter, ["uid"]
        )
        mxids = map(
            lambda member: f'@{member[1]["uid"][0].decode("utf-8")}:{config["ldap"]["mxid_homeserver"]}',
            group_members,
        )
        user_map = {}
        for mxid in mxids:
            user_map[mxid] = UserConfig(power_level=power_level)
        return user_map

    async def get_all_matrix_users_of_sync_room(
        self,
        config,
        evt: MessageEvent,
        sync_room: SyncRoomConfig,
    ) -> UserInfoMap:
        user_info_map = {}
        for ldap_config in sync_room["ldap_members"]:
            user_info_map.update(
                await self.get_matrix_users_of_ldap_group(
                    config,
                    evt,
                    ldap_config["ldap_group"],
                    ldap_config["power_level"],
                )
            )
        return user_info_map
