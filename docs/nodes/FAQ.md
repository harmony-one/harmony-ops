# Frequently Asked Questions
  
**_I want to run more than one node on a single machine. Can I do that?_**
  
Yes, you can. However due to reliability issues, it is nadvised not to do that. If the machine fails, all your nodes will fail as well. It is imperative to keep as many nodes up as possible at all times.
  

**_I'm getting this error message. "Can't find the matching account key of account_index:123"_**
  
This is normal if you just got your index number! This means that there is a placeholder account on that account indexx. Please give the team 1-2 days to enter your account key and launch the index.
  
**_I can't find the balance on explorer.harmony.one_**
  
This is a known issue that the explorer has some compatibility issues with the view change algorithm. Even though it shows only 3 shards sometimes, it doesn't mean the shard is down. Please use your wallet ID to check your block rewards while we continue to fix this issue.
  
  
**_DEBUG[06-10|20:14:13.729] [SYNC] no peers to connect to_**
  
A known issue. Please run ``` sudo ./node.sh $account ``` to retry.
  

**_Is my ONE Address linked to my BLS keys?_**
  
Generation of the BLS keys are independent of your harmony ONE address, you can create any amont of BLS keys independent.
  

**_How do I know which shard my node is at?_**
  
You can run ```grep "shard" latest/validator-ip-address.log ``` and you'll see messages similar to
```
{"got notified":"harmony/0.0.1/node/shard/2/ActionPause","ip":"54.149.210.19","lvl":"info","msg":"[DISCOVERY]","port":"9000","t":"2019-06-14T23:48:41.523967984Z"}
```
Here the node is on shard 2.
