from fastapi import APIRouter, Depends
from typing import Annotated
from schema.home_schema import BuildingCreate
from schema.user_schema import User
from deps import get_current_user
from services.buildings import building_crud

buildingrouter = APIRouter()


@buildingrouter.post("/post_building/")
def post_a_building(building_data:BuildingCreate, current_user: Annotated[User, Depends(get_current_user)]):
    return building_crud.building_create(building_data, current_user)
    

@buildingrouter.get("/buildings/")
def show_buildings():
    return building_crud.show_buildings()


@buildingrouter.post("/buildings/save")
def save_a_building(id:str, current_user: Annotated[User, Depends(get_current_user)]):
    return building_crud.save_a_building(id, current_user)


@buildingrouter.get("/saved")
def show_saved(current_user: Annotated[User, Depends(get_current_user)]):
    return building_crud.list_saved_buildings(current_user)