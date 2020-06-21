import pymongo
from host_script.order_class import Order



def reset_database(pm: pymongo.mongo_client.MongoClient):
    pm["user_accounts"]["accounts"].delete_many({})
    starting_db = [
        {"username": "username1", "password": "password1",
         "cash_amount": 10000, "microbitcoin_amount": 20000, "cash_on_hold": 0, "microbitcoin_on_hold": 0},

        {"username": "username2", "password": "password2",
         "cash_amount": 10000, "microbitcoin_amount": 20000, "cash_on_hold": 0, "microbitcoin_on_hold": 0}
    ]
    pm["user_accounts"]["accounts"].insert_many(starting_db)



def add_pymongo_order(pm: pymongo.mongo_client.MongoClient, order: Order):
    if order.side == "Buy":
        pm["user_accounts"]["accounts"].update_one(
            {
                "username": order.username,
            },
            {
                "$inc": {
                    "cash_amount": - order.price * order.size,
                    "cash_on_hold": order.price * order.size,
                }
            }
        )
    else:
        pm["user_accounts"]["accounts"].update_one(
            {
                "username": order.username,
            },
            {
                "$inc": {
                    "microbitcoin_amount": - order.size,
                    "microbitcoin_on_hold": order.size,
                }
            }
        )

def pymongo_process_order(pm: pymongo.mongo_client.MongoClient, order: Order, size_to_fulfill):
    if order.side == "Buy":
        pm["user_accounts"]["accounts"].update_one(
            {
                "username": order.username,
            },
            {
                "$inc": {
                    "microbitcoin_amount": size_to_fulfill,
                    "cash_on_hold": - order.price * size_to_fulfill,
                }
            }
        )
    else: #order.size == "Sell"
        pm["user_accounts"]["accounts"].update_one(
            {
                "username": order.username,
            },
            {
                "$inc": {
                    "microbitcoin_on_hold": - size_to_fulfill,
                    "cash_amount": order.price * size_to_fulfill,
                }
            }
        )