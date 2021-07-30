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


class LDAPConfig(TypedDict):
    uri: str
    base_dn: str
    connect_dn: str
    connect_password: str
    user_filter: str
    mxid_homeserver: str


class LDAPInviterConfig(BaseProxyConfig):
    sync_rooms: List[SyncRoomConfig]
    admin_users: List[str]
    ldap: LDAPConfig

    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("sync_rooms")
        helper.copy("admin_users")
        helper.copy("ldap")
