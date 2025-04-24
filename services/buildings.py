from fastapi import HTTPException
from schema.user_schema import User
from schema.home_schema import BuildingCreate, BuildingDisplay
from database import cursor,connection

class BuildingService:

    @staticmethod
    def building_create(building_data:BuildingCreate, current_user: User):
        if current_user.account_type.value not in ["Landlord", "Agent"]:
            raise HTTPException(status_code=401, detail="Message: Only LandLords Can Post Houses")
        try:
            cursor.execute("INSERT INTO Buildings(description,address,bedroom_no,bathroom_no,furnished,available_facilities,interior_features,exterior_features,purpose,price,payment_frequency,property_type) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",(building_data.description,building_data.address,building_data.bedroom_no,building_data.bathroom_no,building_data.furnished,building_data.available_facilities,building_data.interior_features,building_data.exterior_features,building_data.purpose,building_data.price,building_data.payment_frequency,building_data.property_type))
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Unable to add building to DB"+ str(e))

        return f"Building with Description: {building_data.description} had been created"

    @staticmethod
    def show_buildings():
        cursor.execute("SELECT * FROM Buildings")
        buildings = cursor.fetchall()

        if not buildings:
            raise HTTPException(status_code=404, detail="No building found in DB")

        building_list = []
        for b in buildings:
            building_list.append(BuildingDisplay(
                description = b[1],
                address = b[2],
                bedroom_no = b[3],
                bathroom_no = b[4],
                furnished = b[5],
                available_facilities = b[6],
                interior_features = b[7],
                exterior_features = b[8],
                purpose = b[9],
                price = b[10],
                payment_frequency = b[11],
                property_type = b[12]
            ))

        return building_list

    @staticmethod
    def save_a_building(id:str, current_user: User):
        if current_user.account_type.value != "User":
            raise HTTPException(status_code=401, detail="Message: Only Users can Save Buildings")

        cursor.execute("SELECT * FROM buildings WHERE id = %s",(id,))
        found_building = cursor.fetchone()

        if found_building is None:
            raise HTTPException(status_code=404, detail="Message: Building With that ID not found")

        cursor.execute("SELECT * FROM saved_buildings WHERE building_id = %s AND user_email = %s",(id,current_user.email))
        saved_building = cursor.fetchone()

        if saved_building:
            raise HTTPException(status_code=400, detail="Building Already Saved")

        try:
            cursor.execute("INSERT INTO saved_buildings(user_email,building_id) VALUES(%s, %s)",(current_user.email,id))
            connection.commit()
        except Exception as e:
            raise HTTPException(status_code=400,detail="Unable to add to DB: "+ str(e))

        return "Building Successfully saved"

    @staticmethod
    def list_saved_buildings(current_user: User):
        if current_user.account_type.value != "User":
            raise HTTPException(status_code=401, detail="Message: Only Users can View Saved Buildings")

        cursor.execute("SELECT b.* FROM Buildings b JOIN saved_buildings sb ON b.id = sb.building_id WHERE sb.user_email = %s", (current_user.email,))

        saved_buildings = cursor.fetchall()

        if not  saved_buildings:
            raise HTTPException(status_code=400,detail="No saved buildings")

        saved_list = []
        for building in saved_buildings:
            saved_list.append(BuildingDisplay(
                description = building[1],
                address = building[2],
                bedroom_no = building[3],
                bathroom_no = building[4],
                furnished = building[5],
                available_facilities = building[6],
                interior_features = building[7],
                exterior_features = building[8],
                purpose = building[9],
                price = building[10],
                payment_frequency = building[11],
                property_type = building[12]
            ))

        return saved_list
    
building_crud = BuildingService()