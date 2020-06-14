# sample_websocket_app v0.01

# Remark on v0.01

This simple test version uses Websocket to input the buy and sell price, as a proof of concept. The actual Bitmex API only accept Buy and Sell order through REST API, not websocket.

Also, the local Redis version I tested is Redis 3.0.504 in Windows, and so I don't have access to more recent Redis commands (in particular, ZPOPMIN, ZPOPMAX)

# How to use:

1. Run a local version of Redis on your computer.

2. Run host_script.websocket_host.py

3. Run client_script.client.py

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
Info are stored in Redis in the following sorted-set:
```
sell_prices
buy_prices
order_size
```
where the scores are sell_price/buy_price/order_size respectively, with value/key being the order_id.

(Future work: Change order_size to hashset, because there is no need to sort based on order_size) 