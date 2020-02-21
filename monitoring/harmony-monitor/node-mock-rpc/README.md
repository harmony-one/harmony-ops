# Mock RPC server
This is a small polka server running in node, for the purpose of unit testing our watchdog. 

## Running the server
```bash
$ npm install
$ npm start
```

## Exposed RPC procedures
- hmy_latestHeader
```json
{"jsonrpc":"2.0", "method":"hmy_latestHeader", "params":[], "id":1}
```
- hmy_getNodeMetadata
```json
{"jsonrpc":"2.0", "method":"hmy_getNodeMetadata", "params":[], "id":1}
```
- hmy_getPendingCxReceipts
```json
{"jsonrpc":"2.0", "method":"hmy_getPendingCxReceipts", "params":[], "id":1}
```