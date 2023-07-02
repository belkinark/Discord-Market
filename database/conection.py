import motor.motor_asyncio

db = motor.motor_asyncio.AsyncIOMotorClient("mongodb://localhost:27017")["DevRoom"]