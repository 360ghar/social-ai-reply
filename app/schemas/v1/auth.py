from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)
    workspace_name: str = Field(min_length=2, max_length=255)


class OAuthCompleteRequest(BaseModel):
    workspace_name: str = Field(min_length=2, max_length=255)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supabase_user_id: str
    email: EmailStr
    full_name: str
    is_active: bool


class WorkspaceSummary(BaseModel):
    id: int
    name: str
    slug: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse
    workspace: WorkspaceSummary
