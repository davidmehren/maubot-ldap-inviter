from inviter.config import MemberConfig
from inviter.matrix_utils import UserInfoMap, UserInfo


def process_template(template: str, arg1: str) -> str:
    """Replaces placeholder in a template with argument"""
    if "<1>" in template and arg1 == "":
        raise Exception(
            f'Template string "{template}" includes a placeholder, but no argument was provided'
        )
    return template.replace("<1>", arg1)


def to_user_info_map(member_config: [MemberConfig]) -> UserInfoMap:
    user_info_map = {}
    user: dict
    for user in member_config:
        user_info_map[user["mxid"]] = UserInfo(power_level=user.get("power_level", 0))
    return user_info_map
