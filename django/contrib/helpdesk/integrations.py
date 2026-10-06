import json


def parse_trello_boards(content):
    """
    Parse the boards list returned by the Trello API. Raise ValueError if the
    payload doesn't have the expected shape.
    """
    boards = json.loads(content)
    if not isinstance(boards, list):
        raise ValueError("Expected a list of boards")
    for board in boards:
        if not isinstance(board, dict) or not isinstance(board.get("lists"), list):
            raise ValueError("Unexpected board entry")
        for key in ("id", "name"):
            if not isinstance(board.get(key), str):
                raise ValueError("Unexpected board entry")
    return boards
