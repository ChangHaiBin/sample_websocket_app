import pymongo

myclient = pymongo.MongoClient("mongodb://localhost:27017/")

mydb = myclient["user_accounts"]["accounts"]

query = {"username": "user1", "password": "passasdfword1"}
newValues = {"$set": {"cash_amount": 77777, "micro_bitcoin": 44444}}
mydb.update_one(query, newValues)

result = mydb.find(query)
print(result)