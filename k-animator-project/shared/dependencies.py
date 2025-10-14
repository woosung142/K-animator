from fastapi import HTTPException, status, Header

# API 게이트웨이가 알려주는 사용자 ID를 가져오는 함수
async def get_user_id_from_gateway(
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> str:
    if x_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="정상적인 접근 경로가 아닙니다."
        )
    return x_user_id