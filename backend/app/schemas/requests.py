from pydantic import BaseModel,ConfigDict,Field,field_validator
from uuid import UUID
import math

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid')

class ReviewInput(Strict):
    text:str=Field(min_length=10,max_length=20000)
    language_code:str=Field(pattern=r'^(en|hi|hi-Latn|mul)$')
    user_rating:float|None=None
    training_permitted:bool=False
    moderation_permitted:bool=False
    evidence_permitted:bool
    consent_version:str=Field(min_length=1,max_length=80)
    @field_validator('text')
    @classmethod
    def nonempty(cls,value):
        if not value.strip(): raise ValueError('Nonempty original review required.')
        value.encode('utf-8',errors='strict')
        return value
    @field_validator('user_rating')
    @classmethod
    def stars(cls,value):
        if value is not None and (not math.isfinite(value) or not .5<=value<=5 or value*2!=int(value*2)):
            raise ValueError('Use0.5..5 in half-star increments.')
        return value

class ReviewEdit(ReviewInput):
    expected_revision:int=Field(ge=1)

class Preferences(Strict):
    genres:dict[str,float]=Field(default_factory=dict)
    themes:dict[str,float]=Field(default_factory=dict)
    personalization_permitted:bool=False
    @field_validator('genres','themes')
    @classmethod
    def weights(cls,value):
        if len(value)>50 or any(not key or len(key)>80 or not math.isfinite(weight) or not 0<=weight<=1 for key,weight in value.items()):
            raise ValueError('Bounded explicit preferences required.')
        return value

class RatingInput(Strict):
    value:float
    @field_validator('value')
    @classmethod
    def valid_star(cls,value):
        if not math.isfinite(value) or not .5<=value<=5 or value*2!=int(value*2):raise ValueError('Use half-star ratings within0.5..5.')
        return value

class ChatInput(Strict):
    text:str=Field(min_length=1,max_length=2000)
    conversation_id:UUID|None=None

class ArtifactInput(Strict):
    component:str=Field(pattern=r'^(sentiment_transformer|multilingual_sentiment|aspect_extraction|aspect_sentiment|embeddings|themes)$')
    version:str=Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9:_-]{0,127}$')
    config_path:str=Field(max_length=500)
    run_path:str=Field(max_length=500)
    approval_reference:str=Field(max_length=500)
    language_scope:list[str]=Field(min_length=1,max_length=4)

