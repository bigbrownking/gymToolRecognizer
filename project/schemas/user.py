from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, validator


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str
    username: str
    gender: Optional[str] = None
    dateOfBirth: Optional[date] = None

    @validator('dateOfBirth')
    def validate_date_of_birth(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%d/%m/%Y').date()
            except ValueError:
                raise ValueError('dateOfBirth must be in DD/MM/YYYY format')
        return v


class UserLogin(UserBase):
    password: str


class UserCreateOAuth(UserBase):
    password: str
    username: Optional[str] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[date] = None


class UserProfile(UserBase):
    id: int
    username: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[str] = None
    profile_image_url: Optional[str] = None

    is_oauth_user: bool = False
    oauth_provider: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @validator('dateOfBirth', pre=True)
    def format_date_of_birth(cls, v):
        if v is None:
            return v
        if isinstance(v, date):
            return v.strftime('%d/%m/%Y')
        return v

    @validator('age', pre=True, always=True)
    def calculate_age(cls, v, values):
        if 'dateOfBirth' in values and values['dateOfBirth']:
            try:
                if isinstance(values['dateOfBirth'], str):
                    birth_date = datetime.strptime(values['dateOfBirth'], '%d/%m/%Y').date()
                elif isinstance(values['dateOfBirth'], date):
                    birth_date = values['dateOfBirth']
                else:
                    return v

                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                return age
            except (ValueError, TypeError):
                pass
        return v


class UserProfileUpdate(BaseModel):
    username: Optional[str] = None
    gender: Optional[str] = None
    dateOfBirth: Optional[date] = None
    profile_image_url: Optional[str] = None

    @validator('dateOfBirth')
    def validate_date_of_birth(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%d/%m/%Y').date()
            except ValueError:
                raise ValueError('dateOfBirth must be in DD/MM/YYYY format')
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


class OAuthUserResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile


class UserRegistrationResponse(BaseModel):
    message: str
    user_id: int
    user: UserProfile


class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile
