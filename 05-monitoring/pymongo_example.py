import pymongo

client = pymongo.MongoClient("mongodb://localhost:27018/")
db = client.get_database("prediction_service")
data_collection = db.get_collection("data")

data = list(data_collection.find())
print(data[0])
print(len(data))

