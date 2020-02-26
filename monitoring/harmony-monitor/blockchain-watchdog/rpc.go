package main

// RPC definitions
const (
  NodeMetadataRPC    = "hmy_getNodeMetadata"
  BlockHeaderRPC     = "hmy_latestHeader"
  PendingCxRPC       = "hmy_getPendingCxReceipts"
  SuperCommitteeRPC  = "hmy_getSuperCommittees"
  JSONVersion        = "2.0"
)

// NodeMetadataReply
type NodeMetadataReply struct {
  BLSPublicKey   string `json:"blskey"`
	Version        string `json:"version"`
	NetworkType    string `json:"network"`
	IsLeader       bool   `json:"is-leader"`
	ShardID        uint32 `json:"shard-id"`
	NodeRole       string `json:"role"`
	BlocksPerEpoch int    `json:"blocks-per-epoch"`
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

type SuperCommitteeReply struct {
  PreviousCommittee struct {
    Deciders map[string]CommitteeInfo `json:"deciders"`
  } `json:"previous"`
  CurrentCommittee  struct {
    Deciders map[string]CommitteeInfo `json:"deciders"`
  } `json:"current"`
}

type CommitteeInfo struct {
  PolicyType    string            `json:"policy"`
  ShardID       int               `json:"shard-id"`
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
  VotingPower    string `json:"voting-power-%"`
  EffectiveStake string `json:"effective-stake,omitempty"`
}
