const { Harmony } = require('@harmony-js/core');    // import the Account class
const {Account} = require('@harmony-js/account');
const { ChainID, ChainType } = require('@harmony-js/utils');
const { StakingFactory } = require('@harmony-js/staking');
const { spawn } = require( 'child_process' );

/********************************

Testing the harmony js sdk

@todo for portions that are not finished I have added a "useHMY" to the test to use the CLI (unfinished)
@todo verify the api calls are successful by checking delegations and balances
********************************/


// env vars
const URL_RPC_SRC = process.env.RPC_SRC;
const URL_RPC_DST = process.env.RPC_DST;

// const test data
const bls_keys_for_new_val = [
  "1480fca328daaddd3487195c5500969ecccbb806b6bf464734e0e3ad18c64badfae8578d76e2e9281b6a3645d056960a",
  "9d657b1854d6477dba8bca9606f6ac884df308558f2b3b545fc76a9ef02abc87d3518cf1134d21acf03036cea2820f02",
  "e2c13c84c8f2396cf7180d5026e048e59ec770a2851003f1f2ab764a79c07463681ed7ddfe62bc4d440526a270891c86",
]
// Sourced from harmony/test/config/local-resharding.txt (Keys must be in provided keystore).
const foundational_node_data = [
  {
    address: "one1ghkz3frhske7emk79p7v2afmj4a5t0kmjyt4s5", bls_key:
      "eca09c1808b729ca56f1b5a6a287c6e1c3ae09e29ccf7efa35453471fcab07d9f73cee249e2b91f5ee44eb9618be3904"
  },
  {
    address: "one1d7jfnr6yraxnrycgaemyktkmhmajhp8kl0yahv", bls_key:
      "f47238daef97d60deedbde5302d05dea5de67608f11f406576e363661f7dcbc4a1385948549b31a6c70f6fde8a391486"
  },
  {
    address: "one1r4zyyjqrulf935a479sgqlpa78kz7zlcg2jfen", bls_key:
      "fc4b9c535ee91f015efff3f32fbb9d32cdd9bfc8a837bb3eee89b8fff653c7af2050a4e147ebe5c7233dc2d5df06ee0a"
  },
  {
    address: "one1p7ht2d4kl8ve7a8jxw746yfnx4wnfxtp8jqxwe", bls_key:
      "ca86e551ee42adaaa6477322d7db869d3e203c00d7b86c82ebee629ad79cb6d57b8f3db28336778ec2180e56a8e07296"
  },
  {
    address: "one1z05g55zamqzfw9qs432n33gycdmyvs38xjemyl", bls_key:
      "95117937cd8c09acd2dfae847d74041a67834ea88662a7cbed1e170350bc329e53db151e5a0ef3e712e35287ae954818"
  },
  {
    address: "one1ljznytjyn269azvszjlcqvpcj6hjm822yrcp2e", bls_key:
      "68ae289d73332872ec8d04ac256ca0f5453c88ad392730c5741b6055bc3ec3d086ab03637713a29f459177aaa8340615"
  },
  {
    address: "one1uyshu2jgv8w465yc8kkny36thlt2wvel89tcmg", bls_key:
      "a547a9bf6fdde4f4934cde21473748861a3cc0fe8bbb5e57225a29f483b05b72531f002f8187675743d819c955a86100"
  },
  {
    address: "one103q7qe5t2505lypvltkqtddaef5tzfxwsse4z7", bls_key:
      "678ec9670899bf6af85b877058bea4fc1301a5a3a376987e826e3ca150b80e3eaadffedad0fedfa111576fa76ded980c"
  },
  {
    address: "one1658znfwf40epvy7e46cqrmzyy54h4n0qa73nep", bls_key:
      "576d3c48294e00d6be4a22b07b66a870ddee03052fe48a5abbd180222e5d5a1f8946a78d55b025de21635fd743bbad90"
  },
  {
    address: "one1d2rngmem4x2c6zxsjjz29dlah0jzkr0k2n88wc", bls_key:
      "16513c487a6bb76f37219f3c2927a4f281f9dd3fd6ed2e3a64e500de6545cf391dd973cc228d24f9bd01efe94912e714"
  }
]

/********************************
Consts
********************************/
const validatorArgs = {
  description: {
    name: 'Alice',
    identity: 'alice',
    website: 'alice.harmony.one',
    securityContact: 'Bob',
    details: "Don't mess with me!!!",
  },
  commissionRate: {
    rate: '0.1',
    maxRate: '0.9',
    maxChangeRate: '0.05',
  },
  minSelfDelegation: '0x2',
  maxTotalDelegation: '0x2',
  amount: 0.1,
}
const txParams = { nonce: '0x2', gasPrice: '0x', gasLimit: '0x0927c0', chainId: ChainID.HmyLocal }
const new_bls_key = "249976f984f30306f800ef42fb45272b391cfdd17f966e093a9f711e30f66f77ecda6c367bf79afc9fa31a1789e9ee8e"
const offset = 3
const sleep = (ms) => new Promise((res) => setTimeout(res, ms));
const getHarmony = () => new Harmony(
  URL_RPC_SRC,
  {
    chainId: ChainID.HmyLocal,
    chainType: ChainType.Harmony,
  },
)

const validators = []
const accounts = []

const createRandomAccounts = () => {
  [1, 2, 3].forEach(() => {
    accounts.push(new Account())
  })
} 

/********************************
Test 1 - Create Validators

JS SDK not finished

flag useHMY (called at bottom) uses the command line (not finished)
********************************/
const createValidator = async (useHMY = false) => {
  if (useHMY) {
    try {
      const hmy = spawn( 'hmy staking create-validator', [ '--amount 3' ] );
    } catch (e) {
      console.log(e)
    }
    hmy.stdout.on( 'data', data => {
        console.log( `stdout: ${data}` );
    });
    hmy.stderr.on( 'data', data => {
        console.log( `stderr: ${data}` );
    });
    hmy.on( 'close', code => {
        console.log( `child process exited with code ${code}` );
    });
  } else {
    console.log('\x1b[33m%s\x1b[0m', 'Test 1 - Create Validators - Random Accounts')
    bls_keys_for_new_val.slice(0, 1).forEach(async (key) => {
      const harmony = getHarmony()
  
      /********************************
      Must setup wallet
      ********************************/
  
      node.setMessenger(harmony.blockchain)
      const validator = harmony.stakings.createValidator({
        ...validatorArgs,
        validatorAddress: node.bech32Address,
        slotPubKeys: [
          key
        ],
      })
      const tx = validator.setTxParams({ txParams }).build()
      const signedTxn = await harmony.wallet.signStaking(tx);
      const [sentTxn, txnHash] = await signedTxn.sendTransaction();
      console.log(sentTxn);
      
      if (tx) console.log('createValidator: %s - \x1b[32m%s\x1b[0m', node.address, 'PASSED')
      validators.push(validator)
    })
  
    console.log('\x1b[33m%s\x1b[0m', 'Test 1 - Create Validators - Foundational Accounts')
    foundational_node_data.forEach((node) => {
      const staking = new StakingFactory(harmony.blockchain)
      const validator = staking.createValidator({
        ...validatorArgs,
        validatorAddress: node.address,
        slotPubKeys: [
          node.bls_key
        ],
      })
      if (validator) console.log('createValidator: %s - \x1b[32m%s\x1b[0m', node.address, 'PASSED')
      validators.push(validator)
    })
  }
  
}

/********************************
Test 2 - Edit Validators
********************************/
const editValidator = async () => {
  console.log('\x1b[33m%s\x1b[0m', 'Test 2 - Edit Validators - Random Accounts (3)')
  validators.slice(0, 3).forEach((node) => {
    // console.log(node.stakeMsg)
    const staking = new StakingFactory(harmony.blockchain)
    const validator = staking.editValidator({
      ...validatorArgs,
      commissionRate: '0.1', //should be commission rate object / another name
      slotKeyToRemove: node.stakeMsg.slotPubKeys[0],
      slotKeyToAdd: new_bls_key,
    })
    if (validator) console.log('editValidator: %s - \x1b[32m%s\x1b[0m', node.stakeMsg.validatorAddress, 'PASSED')
  })

}

/********************************
Test 3 - Delegate
********************************/
const delegate = async () => {
  console.log('\x1b[33m%s\x1b[0m', 'Test 3 - Delegate - Random Accounts (3) -> First (3) Foundational Accounts')
  accounts.slice(0, 1).forEach(async (node, i) => {

    const harmony = getHarmony()

    const keystore = '{"address":"806171f95c5a74371a19e8a312c9e5cb4e1d24f6","Crypto":{"cipher":"aes-128-ctr","ciphertext":"7ab03cb710ac9b623756f90ffedd1953ec588040fef688e2273d0dfd895ead63","cipherparams":{"iv":"f898400903878543a2643cf50b1c0c59"},"kdf":"scrypt","kdfparams":{"dklen":32,"n":262144,"p":1,"r":8,"salt":"09b87b6de8b3c5628ae20629b571f76afcee209b1658cad1eb51a0439d8e83a4"},"mac":"77fbd8d3244caa6bed5026b88fbdd6c49a88dbe0de572b3e54512e4a73fd28ab"},"id":"8730054b-72d5-4bfe-9235-ee9b671eeca3","version":3}'

    const delegator = await harmony.wallet.addByKeyStore(keystore, '')
    
    harmony.blockchain.getBalance({
      address: `one1spshr72utf6rwxseaz339j09ed8p6f8ke370zj`,
    })
    .then((res) => {
      console.log(new harmony.utils.Unit(res.result).asWei().toEther());
    })
    .catch((err) => {
      console.log(err);
    });


    const stakingTxn = harmony.stakings
    .delegate({
      delegatorAddress: 'one1spshr72utf6rwxseaz339j09ed8p6f8ke370zj',
      validatorAddress: 'one1d2rngmem4x2c6zxsjjz29dlah0jzkr0k2n88wc',
      amount: '0xde0b6b3a7640000',
    })
    .setTxParams({ nonce: '0x2', gasPrice: '0x', gasLimit: '0x0927c0', chainId: ChainID.HmyLocal })
    .build();

    const signedTxn = await harmony.wallet.signStaking(stakingTxn);
    // console.log(signedTxn)
    const [sentTxn, txnHash] = await signedTxn.sendTransaction();
    console.log(txnHash)
    const confiremdTxn = await sentTxn.confirm(txnHash);
    console.log(confiremdTxn)

    // const validator = harmony.stakings.createValidator({
    //   ...validatorArgs,
    //   validatorAddress: node.bech32Address,
    //   slotPubKeys: [
    //     key
    //   ],
    // })
    // const tx = validator.setTxParams({ txParams }).build()
    // const signedTxn = await harmony.wallet.signStaking(tx);
    // const [sentTxn, txnHash] = await signedTxn.sendTransaction();
    // console.log(sentTxn);

    // // console.log(node.stakeMsg)
    // const delegatorAddress = node.stakeMsg.validatorAddress
    // const validatorAddress = validators[offset + i].stakeMsg.validatorAddress
    // const staking = new StakingFactory(harmony.blockchain)
    // const validator = staking.delegate({
    //   delegatorAddress,
    //   validatorAddress,
    //   amount: 1
    // })
    // console.log('delegate: %s -> %s \x1b[32m%s\x1b[0m', delegatorAddress, validatorAddress, 'PASSED')
  })

}

/********************************
Test 4 - Undelegate
********************************/
const undelegate = async () => {
  console.log('\x1b[33m%s\x1b[0m', 'Test 4 - Undelegate - Random Accounts (3) <- First (3) Foundational Accounts')
  validators.slice(0, offset).forEach((node, i) => {
    // console.log(node.stakeMsg)
    const delegatorAddress = node.stakeMsg.validatorAddress
    const validatorAddress = validators[offset + i].stakeMsg.validatorAddress
    const staking = new StakingFactory(harmony.blockchain)
    const validator = staking.delegate({
      delegatorAddress,
      validatorAddress,
      amount: 1
    })
    if (validator) console.log('undelegate: %s <- %s \x1b[32m%s\x1b[0m', delegatorAddress, validatorAddress, 'PASSED')
  })

}

/********************************
Test 5 - Collect Rewards
********************************/
const collectRewards = async () => {
  console.log('\x1b[33m%s\x1b[0m', 'Test 5 - Collect Rewards - All Accounts')
  validators.forEach((node) => {
    const delegatorAddress = node.stakeMsg.validatorAddress
    const staking = new StakingFactory(harmony.blockchain)
    const validator = staking.delegate({delegatorAddress})
    if (validator) console.log('collectRewards: %s - \x1b[32m%s\x1b[0m', delegatorAddress, 'PASSED')
  })
    
}


const tests = (async() => {
  createRandomAccounts()
  //await createValidator(true)
  await sleep(1000)
  await delegate()
  await sleep(1000)
})()

