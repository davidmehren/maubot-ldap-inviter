from typing import TypedDict, Optional, List

from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper


class LDAPMemberConfig(TypedDict):
    ldap_group: str
    power_level: Optional[int]


class MemberConfig(TypedDict):
    mxid: str
    power_level: Optional[int]


class SyncRoomConfig(TypedDict):
    alias: str
    visibility: str
    name: str
    ldap_members: List[LDAPMemberConfig]
    members: List[MemberConfig]


class LDAPInviterConfig(BaseProxyConfig):
    sync_rooms: List[SyncRoomConfig]
    admin_users: List[str]

    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("sync_rooms")
        helper.copy("admin_users")
        helper.copy("ldap")
