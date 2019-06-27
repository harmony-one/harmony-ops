**Backing up your keys to your local machine**

For every foundational node operator there are two keys of importanace.
* BLS Key - This is used for signing your transactions which earns rewards
* Wallet Key - this is used to access (sign transactions) for the rewards earned 

**It is important these two keys are backed up**

Here is how to copy the keys to your local machine from your AWS Instance

* Locate your bls keys - this will depend on the name you gave them
By default the keys should be in the same directory you run `./node.sh` and be stored with a UTC prefix
```
cd ~
ls UTC*
```
Gives the key name e.g. `UTC--2019-06-12T19-22-43.157337000Z--bls_19101de3d0578c3146a1904f25a3344a998dcb0a18433dc5cc977d05f378676b0652b4a64fa8dff6c819cfd52dc94c14`
* 
* Locate your wallet key - this should be stored in `.hmy/keystore/`
```
ls ./hmy/keystore/*
```
Gives the wallet keys e.g.
```
.hmy/keystore/UTC--2019-06-12T19-19-44.548607000Z--56151cda1f9574543d0f5f0b2c33384dbfdf0fb7
```
where your wallet key is 
UTC--2019-06-12T19-19-44.548607000Z--56151cda1f9574543d0f5f0b2c33384dbfdf0fb7


**Using SCP**
* Here we will use `scp -i` which has the format `scp -i <pem> <from> <to>` where 
  * <pem> is the pem file used to connect to AWS
  * <from> is the file your copying from
  * <to> is the file your copying to

  e.g. `scp -i oregon-key-benchmark.pem ec2-user@54.190.19.255:/home/ec2-user/UT* ./keybackup/`

  or `scp -i  oregon-key-benchmark.pem ec2-user@ec2-34-222-17-175.us-west-2.compute.amazonaws.com;/home/ec2-user/UT* ./keybackup/`

** Download the keys to your local machine**
* Create a directory where you would like to keep your downloaded keys
* Move your `.pem` file to that machine so you can access your AWS instance
* Get your AWS connection information this can be retrieved by going to you AWS Console, selecting the EC2 instance and pressing connect
* Use SCP to download your BLS Key
* Use SCP to download your wallet key
* Check that your files have been downloaded

For example
```
mkdir keybackup
cp ./sample.pem .
scp -i oregon-key-benchmark.pem ec2-user@54.190.19.255:/home/ec2-user/UT* ./keybackup/
scp -i oregon-key-benchmark.pem ec2-user@54.190.19.255:/home/ec2-user/.hmy/keystore/* ./keybackup/
```

