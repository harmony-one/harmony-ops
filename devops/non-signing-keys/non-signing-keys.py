from pyhmy import blockchain
from pyhmy import staking
import sys
import os

ownfilename=os.path.basename(__file__)
if (len(sys.argv) != 2):
    print(f"follow example: python3 {ownfilename} 0")
    exit(1)

shard=str(sys.argv[1])
shards=["0","1","2","3"]
if (shard not in shards):
    print(f"follow example: python3 {ownfilename} 0")
    exit(2)

endpoint="https://api.s"+shard+".t.hmny.io"
s0_endpoint="https://api.s0.t.hmny.io"


latest_block_number=blockchain.get_latest_header(endpoint)['blockNumber']
latest_block_signer = blockchain.get_block_signers_keys(block_num=latest_block_number-1, endpoint=endpoint)
super_committees = staking.get_super_committees(s0_endpoint)
elected_bls=[x["bls-public-key"] for x in super_committees['current']["quorum-deciders"]["shard-"+shard]["committee-members"]]

non_signing_bls = list(filter(lambda x: not x in latest_block_signer, elected_bls))

print("Non Signing BLS:")
print(non_signing_bls);

non_voting_validators_external=[x["earning-account"] for x in super_committees['current']["quorum-deciders"]["shard-"+shard]["committee-members"] if x["bls-public-key"] in non_signing_bls and not x["is-harmony-slot"]]

print("External validators :")
#make the list unique
non_voting_validators_external=list(set(non_voting_validators_external))
print(non_voting_validators_external)

non_voting_validators_internal=[x["earning-account"] for x in super_committees['current']["quorum-deciders"]["shard-"+shard]["committee-members"] if x["bls-public-key"] in non_signing_bls and x["is-harmony-slot"]]

print("Internal validators (harmony):")
non_voting_validators_internal=list(set(non_voting_validators_internal))
print(non_voting_validators_internal)
