let json = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "blskey": "",
        "version": "Harmony (C) 2019. harmony, version v4983-v1.2.1-22-g1cea6c62 (ec2-user@ 2020-01-28T00:17:21+0000)",
        "network": "testnet",
        "chainid": "2",
        "is-leader": true,
        "shard-id": 0,
        "role": "Unknown"
    }
}

exports.hmy_getNodeMetadata = (id) => {
    //will send identical responses to simulate consensus loss
    json.id = id;
    return JSON.stringify(json);
}