# This guide will act as a quick reference for those who need to reconnect to your node and/or check status

**First time running/setting up your node:**

```
cd downloads/									//change directory to downloads folder
chmod 400 Your_Pem_File							//makes your key not publicly viewable
ssh -i......from amazon connect					//ssh into aws instance
sudo yum update									//updates instance
mkdir -p ~/.hmy/keystore						//makes a new directory to store harmony keys
```
  
**Setting up a new wallet:**
  
```
curl -LO https://harmony.one/wallet.sh 			//downloads script
chmod 400 u+x wallet.sh
./wallet.sh -d
./wallet.sh new									//makes new Harmony wallet ID
./wallet.sh blsgen								//makes BLS keypair
./wallet.sh list
```
  
**Launching and running your node:**

```
sudo yum install -y tmux						//installs tmux
tmux new-session -s node						//creates new tmux session named "node"
curl -LO https://harmony.one/node.sh 			//downloads script
chmod a+x node.sh
sudo ./node.sh 									//sync your node to harmony blockchain
ctrl+b then d 									//detaches from tmux
```
  
**Monitoring your node:**
  
```
grep BINGO latest/validator*.log 				//checks BINGOs
./wallet.sh balances							//checks your node's current balance
curl -OL http://harmony.one/mystatus.sh 		//downloads script to check node status
chmod u+x ./mystatus.sh
./mystatus.sh all 								//checks all your node statuses
```

**Useful Commands:**
  
```
sudo ./node.sh -c 								//restarts sync/if genesis not found in blockchain
tmux attach 									//reattach back to tmux
./wallet.sh importBLS --key BLS_Private_Key 	//resets your passphrase
watch -n 10 ./wallet.sh balances
./wallet.sh exportPriKey --account 				//moves private key
```