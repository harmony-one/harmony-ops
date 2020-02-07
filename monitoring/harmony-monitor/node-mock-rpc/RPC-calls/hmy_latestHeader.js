let json = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "blockHash": "0xfbb722f572d2b2e8a0e292aa6f91acc73023dde5f281f32b6c5447b5b3102d59",
        "blockNumber": 165597,
        "shardID": 1,
        "leader": "one1wh4p0kuc7unxez2z8f82zfnhsg4ty6dupqyjt2",
        "viewID": 165594,
        "epoch": 367,
        "timestamp": "2020-02-07 18:37:54 +0000 UTC",
        "unixtime": 1581100674,
        "lastCommitSig": "d10f5af3e55ccbfea9e336733ffa9dcf4d12594f9b9a825c92e1611ef654cd0cc70966d243f2338a1970243ae9e49c0f8fa15fa138e7bea92a12d10b43af254624751f603f7dd8f0415099854da3678a90d8185076ca904fbbbb9cab63aa0c96",
        "lastCommitBitmap": "ff03"
    }
}

exports.hmy_latestHeader = (id) => {
    json.id = id;
    return JSON.stringify(json);
}