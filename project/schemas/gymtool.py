from pydantic import BaseModel


class AddMuscleRequest(BaseModel):
    gymtool_name: str
    primary_muscles: str
    secondary_muscles: str
    muscle_name: str


class AddLinkRequest(BaseModel):
    url: str
