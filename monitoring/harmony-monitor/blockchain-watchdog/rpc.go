package main

// RPC definitions
const (
	NodeMetadataRPC   = "hmy_getNodeMetadata"
	BlockHeaderRPC    = "hmy_latestHeader"
	PendingCXRPC      = "hmy_getPendingCXReceipts"
	SuperCommitteeRPC = "hmy_getSuperCommittees"
	LastCrossLinkRPC  = "hmy_getLastCrossLinks"
	JSONVersion       = "2.0"
)

type NodeMetadataReply struct {
	BLSPublicKey   string `json:"blskey"`
	Version        string `json:"version"`
	NetworkType    string `json:"network"`
	IsLeader       bool   `json:"is-leader"`
	ShardID        uint32 `json:"shard-id"`
	NodeRole       string `json:"role"`
	BlocksPerEpoch int    `json:"blocks-per-epoch"`
	DNSZone        string `json:"dns-zone,omit-empty"`
	ArchivalNode   bool   `json:"is-archival,omit-empty"`
	ChainConfig    struct {
		ChainID         int `json:"chain-id"`
		CrossLinkEpoch  int `json:"cross-link-epoch"`
		CrossTxEpoch    int `json:"cross-tx-epoch"`
		Eip155Epoch     int `json:"eip155-epoch"`
		PreStakingEpoch int `json:"prestaking-epoch"`
		S3Epoch         int `json:"s3-epoch"`
		StakingEpoch    int `json:"staking-epoch"`
	} `json:"chain-config"`
}

type NodeMetadata struct {
	Payload NodeMetadataReply
	IP      string
}

type BlockHeaderReply struct {
	BlockHash        string `json:"blockHash"`
	BlockNumber      uint64 `json:"blockNumber"`
	ShardID          uint32 `json:"shardID"`
	Leader           string `json:"leader"`
	ViewID           uint64 `json:"viewID"`
	Epoch            uint64 `json:"epoch"`
	Timestamp        string `json:"timestamp"`
	UnixTime         int64  `json:"unixtime"`
	LastCommitSig    string `json:"lastCommitSig"`
	LastCommitBitmap string `json:"lastCommitBitmap"`
}

type BlockHeader struct {
	Payload BlockHeaderReply
	IP      string
}

// TODO: Come back to this
type PendingCXReply struct {
	PendingCX []CXReceiptProof `json:"-"`
}

// Don't care about contents of each Receipt
type CXReceiptProof struct {
	Receipts     interface{} `json:"receipts"`
	MerkleProof  interface{} `json:"merkleProof"`
	Header       interface{} `json:"header"`
	CommitSig    string      `json:"commitSig"`
	CommitBitmap string      `json:"commitBitmap"`
}

type SuperCommitteeReply struct {
	PreviousCommittee struct {
		Deciders      map[string]CommitteeInfo `json:"quorum-deciders"`
		ExternalCount int                      `json:"external-slot-count"`
	} `json:"previous"`
	CurrentCommittee struct {
		Deciders      map[string]CommitteeInfo `json:"quorum-deciders"`
		ExternalCount int                      `json:"external-slot-count"`
	} `json:"current"`
}

type CommitteeInfo struct {
	PolicyType    string            `json:"policy"`
	MemberCount   int               `json:"count"`
	Committee     []CommitteeMember `json:"committee-members"`
	HarmonyPower  string            `json:"hmy-voting-power"`
	StakedPower   string            `json:"staked-voting-power"`
	TotalRawStake string            `json:"total-raw-staked"`
}

type CommitteeMember struct {
	Address        string `json:"earning-account"`
	IsHarmonyNode  bool   `json:"is-harmony-slot"`
	BLSKey         string `json:"bls-public-key"`
	RawPercent     string `json:"voting-power-unnormalized,omitempty"`
	VotingPower    string `json:"voting-power-%"`
	EffectiveStake string `json:"effective-stake,omitempty"`
}

type LastCrossLinkReply struct {
	CrossLinks []CrossLink
}

type CrossLink struct {
	Hash            string `json:"hash"`
	BlockNumber     int    `json:"block-number"`
	Signature       string `json:"signature"`
	SignatureBitmap string `json:"signature-bitmap"`
	ShardID         int    `json:"shard-id"`
	EpochNumber     int    `json:"epoch-number"`
}

func getRPCRequest(rpc string) map[string]interface{} {
	return map[string]interface{}{
		"jsonrpc": JSONVersion,
		"method":  rpc,
		"params":  []interface{}{},
	}
}
