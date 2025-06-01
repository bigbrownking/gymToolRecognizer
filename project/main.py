from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from project.api.auth import router as auth_router
from project.api.user import router as user_router
from project.api.gymtool import router as gymtool_router
from project.api.recognize import router as recognize_router
from project.api.muscle import router as muscle_router
from project.api.user_gym_log import router as user_gym_log
from project.api.payment import router as payment
from project.api.workout_generator import router as workout
from project.api.geo import router as geo

app = FastAPI(strict_slashes=False)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(gymtool_router)
app.include_router(user_router)
app.include_router(recognize_router)
app.include_router(muscle_router)
app.include_router(payment)
app.include_router(user_gym_log)
app.include_router(workout)
app.include_router(geo)
