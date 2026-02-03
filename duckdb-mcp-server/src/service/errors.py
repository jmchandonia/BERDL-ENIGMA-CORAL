from fastapi import HTTPException


def bad_request(msg: str) -> HTTPException:
    return HTTPException(status_code=400, detail=msg)


def not_found(msg: str) -> HTTPException:
    return HTTPException(status_code=404, detail=msg)
