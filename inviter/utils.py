from inviter.config import MemberConfig
from inviter.matrix_utils import UserInfoMap, UserConfig


def template_room_alias(alias: str, arg1: str) -> str:
    """Replaces placeholder in room alias with argument"""
    if "<1>" in alias and arg1 == "":
        raise Exception(
            f'Room alias "{alias}" includes a placeholder, but no argument was provided'
        )
    return alias.replace("<1>", arg1)


def to_user_info_map(member_config: [MemberConfig]) -> UserInfoMap:
    user_info_map = {}
    user: dict
    for user in member_config:
        user_info_map[user["mxid"]] = UserConfig(power_level=user.get("power_level", 0))
    return user_info_map
