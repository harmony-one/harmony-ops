package main

const (
	consensusMessage = `
Consensus stuck on shard %s!

Block height stuck at %d starting at %s

Block Hash: %s

Leader: %s

ViewID: %d

Epoch: %d

Block Timestamp: %s

LastCommitSig: %s

LastCommitBitmap: %s

Time since last new block: %d seconds (%f minutes)

See: http://watchdog.hmny.io/report-%s
`
	crossShardTransactionMessage = `
Cx Transaction Pool too large on shard %s!

Count: %d
`
	crossLinkMessage = `
Haven't processed a cross link for shard %d in a while!

Cross Link Hash: %s

Shard %d Block: %s

Shard %d Epoch: %s

Signature: %s

Signature Bitmap: %s

Time since last processed cross link: %d seconds (%f minutes)
`
)
