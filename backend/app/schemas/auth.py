"""Auth API schemas — login request, token response, decoded token payload."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login form. Either ``username`` or ``email`` shape — we accept the
    field as ``username`` and look up by either column server-side, so the
    frontend doesn't need to know which one the user typed.
    """

    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """What ``/auth/login`` returns on success.

    ``token_type`` is fixed to ``"bearer"`` so the frontend can construct the
    ``Authorization`` header without inspecting the response.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Token lifetime in seconds, derived from JWT_EXPIRE_MINUTES.",
    )


class TokenPayload(BaseModel):
    """Shape of the decoded JWT body. Documented for clarity only — we read
    these fields directly from the dict returned by ``decode_access_token``.
    """

    sub: str
    username: str
    iat: int
    exp: int
