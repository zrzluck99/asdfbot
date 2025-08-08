from nonebot.adapters.qq import Bot, Event

async def fdu_group_checker(bot: Bot, event: Event):
    """
    检查是否为复旦大学相关群组
    """
    fdu_group_ids = [
        "0D7D5650FA37557C082B02ABCA099905",
        "F2B217E064F2F049A413E6509B267D30"
    ]

    session = event.get_session_id().split("_")
    if session[0] != "group":
        return False

    group_id = session[1]
    if group_id in fdu_group_ids:
        return True
    else:
        return False

