
const { Harmony } = require('@harmony-js/core');

// import or require settings
const { ChainID, ChainType } = require('@harmony-js/utils');
const { StakingFactory } = require('@harmony-js/staking');

const URL_TESTNET = `https://api.s0.b.hmny.io`;
const URL_MAINNET = `https://api.s0.t.hmny.io`;

// 1. initialize the Harmony instance

const harmony = new Harmony(
  // rpc url
  URL_TESTNET,
  {
    // chainType set to Harmony
    chainType: ChainType.Harmony,
    // chainType set to HmyLocal
    chainId: ChainID.HmyTestnet,
  },
);

const staking = new StakingFactory(harmony.blockchain)
const validator = staking.createValidator({
    validatorAddress: 'one10g06yrl4eawv49uvj083am3mtj0zuaq72a8adr',
    description: {
        name: 'A mighty validator...',
    },
    commissionRate: {
        rate: '0.1',
        maxRate: '0.1',
        maxChangeRate: '0.1',
    },
    minSelfDelegation: '0.1',
    maxTotalDelegation: '0.1',
    slotPubKeys: [
        '1480fca328daaddd3487195c5500969ecccbb806b6bf464734e0e3ad18c64badfae8578d76e2e9281b6a3645d056960a'
    ],
    amount: 1,
})
console.log(validator)

// harmony.blockchain
//   .getBalance({
//     address: `one1vjywuur8ckddmc4dsyx6qdgf590eu07ag9fg4a`,
//   })
//   .then((res) => {
//     console.log(new harmony.utils.Unit(res.result).asWei().toEther());
//   })
//   .catch((err) => {
//     console.log(err);
//   });

