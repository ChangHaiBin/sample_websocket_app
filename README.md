# sample_websocket_app v0.01

# Remark on v0.01

This simple test version uses Websocket to input the buy and sell price, as a proof of concept. The actual Bitmex API only accept Buy and Sell order through REST API, not websocket.

Also, the local Redis version I tested is Redis 3.0.504 in Windows, and so I don't have access to more recent Redis commands (in particular, ZPOPMIN, ZPOPMAX)

# How to use:

1. Run a local version of Redis and MongoDB on your computer.

2. Run host_script.websocket_host.py

(Remark: When websocket is started, we will reset all orders on Redis, and reset the account for each user to `cash_amount` of `10000`, and `microbitcoin_amount` of `20000`)

3. Run client_script.client.py (and client_script.client2.py to simulate two separate buyers/sellers)

## Buy and sell commands

You can type in your buy and sell commands as follows:

```
==============================
Input your command: 
Buy
Input price:
3.14
Input size:
1000
==============================
Input your command: 
Sell
Input price:
3.11
Input size:
2000
```

# Websocket messages
For orders that are inputted:
```
{"table": "orderBookL2", "action": "insert", "data": [{"symbol": "XBTUSD", "id": "11acab48ca6e42c4bed3b71dbc2cd3ef", "side": "Buy", "size": 1000.0, "price": 3.14}]}
{"table": "orderBookL2", "action": "insert", "data": [{"symbol": "XBTUSD", "id": "1b1fa7d74b86423f8ab647ef0d09aec7", "side": "Sell", "size": 2000.0, "price": 3.11}]}
```

For orders that are processed, some may be partially fulfilled
```
{"table": "orderBookL2", "action": "fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:11acab48ca6e42c4bed3b71dbc2cd3ef", "side": "Buy"}]}
{"table": "orderBookL2", "action": "partial_fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:1b1fa7d74b86423f8ab647ef0d09aec7", "side": "Sell", "remaining_size": 1000.0}]}
```

# Redis Sorted Set
Buy and sell prices are stored in Redis in the following sorted-set:
```
sell_prices
buy_prices
```
where the scores are sell_price/buy_price respectively, with value/key being the order_id.

On the other hand, order sizes (buy or sell), and user account names are stored here:
```
order_sizes
order_account_names
```
where key is order_id, and value is order_size and order_account_name respectively. 

# MongoDB
We store a very basic account info in MongoDB:
```
user_accounts.accounts
```
with information
```
{"_id":{"$oid":"5eeef4ab8da08adea06fa250"},
"username":"username1",
"password":"password1",
"cash_amount":10000,
"microbitcoin_amount":10000,
"cash_on_hold":0,
"microbitcoin_on_hold":0}


{"_id":{"$oid":"5eeef4ab8da08adea06fa251"},
"username":"username2",
"password":"password2",
"cash_amount":10000,
"microbitcoin_amount":10000,
"cash_on_hold":0,
"microbitcoin_on_hold":0}
```

# Example
Assuming user1 and user2 both start off with `cash_amount` of `10000`, and `microbitcoin_amount` of `20000`

### Buy order

User1 inputs:
```
==============================
Input your command: 
Buy
Input price:
3.14
Input size:
200
==============================
Input your command: 
Buy
Input price:
3.15
Input size:
300
```
with corresponding messages:
```
{"table": "orderBookL2", "action": "insert", "data": [{"symbol": "XBTUSD", "id": "order:47af2dbb8dd04ce982b827d3aa2791cd", "side": "Buy", "size": 200, "price": 3.14}]}
{"table": "orderBookL2", "action": "insert", "data": [{"symbol": "XBTUSD", "id": "order:bbd82af067db4409b6331208af3525a0", "side": "Buy", "size": 300, "price": 3.15}]}
```
And mongoDB:
```
{
    "username": "username1",
    "password": "password1",
    "cash_amount": 8427,
    "microbitcoin_amount": 20000,
    "cash_on_hold": 1573,
    "microbitcoin_on_hold": 0
}
```

### Sell order

User2 inputs:
```
Input your command: 
Sell
Input price:
3.11
Input size:
600
```
with corresponding message:
```
{"table": "orderBookL2", "action": "insert", "data": [{"symbol": "XBTUSD", "id": "order:450501a3ac9f45daafe2ac98a77cc582", "side": "Sell", "size": 600, "price": 3.11}]}
```
and MongoDB (prior to fulfillment)
```
{
    "username": "username2",
    "password": "password2",
    "cash_amount": 10000,
    "microbitcoin_amount": 19400,
    "cash_on_hold": 0,
    "microbitcoin_on_hold": 600
}
```

### Order fulfillment

The program will process the orders:
```
{"table": "orderBookL2", "action": "fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:9015556081524081befd84a0d6df6c40", "side": "Buy"}]}
{"table": "orderBookL2", "action": "partial_fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:f97d120a59904ea38eac31f9aec8a186", "side": "Sell", "remaining_size": 300}]}
{"table": "orderBookL2", "action": "fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:83c0c8f1c1cc4d058bee70ff1752a275", "side": "Buy"}]}
{"table": "orderBookL2", "action": "partial_fulfilled", "data": [{"symbol": "XBTUSD", "id": "order:f97d120a59904ea38eac31f9aec8a186", "side": "Sell", "remaining_size": 100}]}
```
And MongoDB:
```
{
    "username": "username1",
    "password": "password1",
    "cash_amount": 8427,
    "microbitcoin_amount": 20500,
    "cash_on_hold": 0,
    "microbitcoin_on_hold": 0
}

{
    "username": "username2",
    "password": "password2",
    "cash_amount": 11555,
    "microbitcoin_amount": 19400,
    "cash_on_hold": 0,
    "microbitcoin_on_hold": 100
}
```

### Remark:

We assume that any price differences are absorbed by us. e.g. if a buyer is willing to buy at $3.15, and a seller willing to sell at $3.11, then both of their orders are fulfilled at their requested price, and the $0.04 arbitrage is credited to the `admin` account.

### Future works:

#### Transactions

We will need to review and verify the transactions are performed in one go (e.g. is it possible for the Redis part to succeed, but the MongoDB part to fail, or vice versa?)

We may also consider using multi-document transactions when updating accounts for better guarantee, and see if that will add to latency.

#### Isolate Order-matching Function

We will also need to implement the order-matching part of the code as a separate component (i.e. the `execute_order_if_possible` function in `host_script.websocket_host.py`). 

Right now, the order matching function is only called when there is a new order, which could potentially be a problem if the matching function fails (e.g. due to network issue, or failure to ZPOPMIN or ZPOPMAX) while executing a match, and the match is reverted, resulting in unmatched orders. 

#### C++ Optimizations

To potentially speed up the program, we could potentially hold 1000 highest buy/lowest sell orders in memory, reducing calls to Redis. 
 
We could also group together account credit/debits to reduce calls to MongoDB.
 