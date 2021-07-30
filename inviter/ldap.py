from typing import List

import ldap
from mautrix.util.logging import TraceLogger

from .config import LDAPMemberConfig
from .matrix_utils import UserInfoMap, UserInfo
from .utils import process_template


class LDAPManager:
    connection = None
    base_dn = None
    user_filter = None
    mxid_default_homeserver = None

    def __init__(
        self,
        server_uri: str,
        user_dn: str,
        user_pass: str,
        base_dn: str,
        user_filter: str,
        default_homeserver: str,
        logger: TraceLogger,
    ):
        self.logger = logger
        # Create LDAP connection
        self.connection = ldap.initialize(server_uri)
        self.connection.simple_bind_s(
            user_dn,
            user_pass,
        )
        self.base_dn = base_dn
        self.user_filter = user_filter
        self.mxid_default_homeserver = default_homeserver

    async def get_matrix_users_of_ldap_group(
        self,
        ldap_group: str,
        power_level: int,
    ) -> UserInfoMap:
        self.logger.debug(f"Getting users for LDAP group `{ldap_group}`")
        # Piece together LDAP filter from config and memberOf statement
        ldap_filter = f"(&{self.user_filter}(memberOf={ldap_group}))"
        # Search for group members in LDAP
        group_members = self.connection.search_s(
            self.base_dn, ldap.SCOPE_SUBTREE, ldap_filter, ["uid"]
        )
        # UTF-8-decode uids and create MXIDs
        mxids = map(
            lambda member: f'@{member[1]["uid"][0].decode("utf-8")}:{self.mxid_default_homeserver}',
            group_members,
        )
        # Build UserInfoMap from MXIDs and power level
        user_map = {}
        for mxid in mxids:
            user_map[mxid] = UserInfo(power_level=power_level)
        return user_map

    async def get_all_matrix_users_of_sync_room(
        self, ldap_members: List[LDAPMemberConfig], template_arg: str
    ) -> UserInfoMap:
        user_info_map = {}
        for member_config in ldap_members:
            user_info_map.update(
                await self.get_matrix_users_of_ldap_group(
                    process_template(member_config["ldap_group"], template_arg),
                    member_config["power_level"],
                )
            )
        return user_info_map
