from pydantic import BaseModel

class request(BaseModel):
    story_audio:str
    images:list[str]