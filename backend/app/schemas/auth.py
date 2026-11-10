from pydantic import BaseModel,ConfigDict,Field,SecretStr,field_validator
from uuid import UUID

class LoginInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email:str=Field(min_length=3,max_length=254)
    password:SecretStr
    @field_validator('email')
    @classmethod
    def normalize(cls,value):
        value=value.strip().casefold()
        if value.count('@')!=1 or any(character.isspace() for character in value) or '.' not in value.split('@')[1]:
            raise ValueError('A valid email address is required.')
        return value
    @field_validator('password')
    @classmethod
    def bounded(cls,value):
        if not 12<=len(value.get_secret_value())<=128: raise ValueError('Use12..128 password characters.')
        return value

class RegisterInput(LoginInput):
    display_name:str=Field(min_length=1,max_length=80)

class PublicUser(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:UUID
    display_name:str
    email:str
    is_admin:bool
