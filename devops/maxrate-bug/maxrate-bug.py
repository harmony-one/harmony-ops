from pyhmy import rpc
from pyhmy import staking, blockchain
import json
import os
from staking_tx_history import gather_staking_transactions

# Harmony RPC endpoint
harmony_rpc_url = "https://a.api.s0.t.hmny.io"
# numbre of pages required to get through all validators in validator_all_information
allvalidatorpages = 14
# max_rate threshold
max_rate_threshold = 0.93

# from epoch 7% activation, check for all >93$ max rate validator and for all epoch
# the pending undelegation ojects and confirm if over time to now, they were cleared

def write_json_to_file(json_object, filename):
    with open(filename, 'w') as file:
        json.dump(json_object, file, indent=4)

    print(f"{filename} has been created")

def get_all_high_fee_validators_at_block(blocknum):
    validators = []
    # file where the previous validator_all_information was processed
    filepath = f"validator-infos/Validator_all_infos_{blocknum}.json"

    # load previous file if any is existing
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            validators = json.load(file)
            print(f"Loaded and returned data from {filepath}")
            return validators

    seen_addresses = set()

    # Iterate through pages to get the list of all validators
    for i in range(allvalidatorpages):
        # Fetch the validators for the current page
        current_validators = staking.get_all_validator_information_by_block_number(block_num=blocknum, page=i, endpoint=harmony_rpc_url)

        for validator in current_validators:
            # Extract the validator address
            validator_address = validator['validator']['address']

            # Check if the validator address is already seen
            if validator_address not in seen_addresses:
                # Add the validator address to the seen set
                seen_addresses.add(validator_address)

                # Check if the validator has a high max rate fee
                #if (float(validator['validator']['max-rate']) > max_rate_threshold) and (validator['active-status'] == "active" or validator['epos-status'] == "eligible to be elected next epoch"):
                if (float(validator['validator']['max-rate']) > max_rate_threshold):
                    # Add the validator to the high fee validators list
                    validators.append(validator)

    print(f"get all high fee validators detail at block {blocknum} done")

    write_json_to_file(validators, f"validator-infos/Validator_all_infos_{blocknum}.json")

    return validators

def atto_to_one(atto_amount):
    ONE = 10**18
    return atto_amount / ONE

# array of all pending undelegation since HIP30
# a undelegation is uniquely identified by a validator, a delegator and an epoch
# undelegated amount is not used as it can be updated as delegator delegate back the validator
# undelegation object is a dict defined as below :
# - validator_add : validator address the delegator delegated to
# - delegator_add : the delegator address
# - epoch : epoch of the undelegation transaction
# - epoch_cleared : epoch at which the undelegation disappeared
#       default will be 0 and an epoch number when clearing is detected
#       if it disappeared after the 8th epoch, and there delegation tx it means they received bad ONEs
# - original_amount : the total amount undelegated at epoch
# - final_amount : the total final undelegated amount when script is done, in theory it should be the same as original amount
# final amount may decrease if the pending undelegation was cleared as we read through all the epoch 1 by 1
# - malicious : whether the delegator account has been flagged malicious or not
all_pending_undelegation=[]

# take an undelegation object and will update all_pending_undelegation
def add_undelegation(validator, delegator, undelegation):
    # Check if the undelegation already exists
    for existing_undelegation in all_pending_undelegation:
        if (existing_undelegation['validator_add'] == validator and
            existing_undelegation['delegator_add'] == delegator and
            existing_undelegation['epoch'] == undelegation['epoch']):

            # Update the existing undelegation amounts
            if existing_undelegation['final_amount'] != atto_to_one(undelegation['amount']):
                print(f"Updating Validator {validator} delegator {delegator} epoch {undelegation['epoch']} to {atto_to_one(undelegation['amount'])}")
                existing_undelegation['final_amount'] = atto_to_one(undelegation['amount'])
            return

    # If not found, add a new undelegation to the list
    undelegation = {
            'validator_add': validator,
            'delegator_add': delegator,
            'epoch': undelegation['epoch'],
            'epoch_cleared': 0,
            'original_amount': atto_to_one(undelegation['amount']),
            'final_amount': atto_to_one(undelegation['amount']),
            'malicious' : False # assumed false
        }
    all_pending_undelegation.append(undelegation)

# 1673 is the HIP30 with start of mimimum 7%
# 1733 is the maxrate epoch where we wanted wanted to fix the max_rate for validator below 7%
# which introduce the issue of validator with 107%
for epoch in range(1733, 1974):
    # get all validator information for epoch
    last_block_of_epoch = blockchain.epoch_last_block(epoch=epoch, endpoint=harmony_rpc_url)
    # we use last_block_of_epoch -1 because last_block_of_epoch have the next epoch info instead
    all_validators_at_epoch = get_all_high_fee_validators_at_block(last_block_of_epoch - 1)
    # for all >93% max rate validator
    for validator in all_validators_at_epoch:
        # get the pending undelegation object for the validators in all_validators_at_epoch
        #print(json.dumps(validator))
        validator_delegations_list=validator['validator']["delegations"]
        validator_add = validator['validator']['address']

        # for each new epoch and each validator
        # check whether the existing pending undelegation was cleared
        # if yes register the epoch
        for existing_pending in all_pending_undelegation:
            if (existing_pending['validator_add'] == validator_add and
                    existing_pending['epoch_cleared'] == 0):
                # find the delegation object matching the epoch
                delegation_at_epoch = [delegation for delegation in validator_delegations_list
                    if existing_pending['delegator_add'] == delegation['delegator-address']]
                if len(delegation_at_epoch) != 0:
                    undelegation_at_epoch = [undelegation for undelegation in delegation_at_epoch[0]['undelegations']
                        if undelegation['epoch'] == existing_pending['epoch']]
                    if len(undelegation_at_epoch) == 0: # existing_pending_undelegation not found
                        print(f"Delegator {existing_pending['delegator_add']} with Validator {existing_pending['validator_add']} "
                            f"of final_amount {existing_pending['final_amount']} was cleared at {epoch} (before {existing_pending['epoch']})")
                        existing_pending['epoch_cleared'] = epoch

        # validator who became inactive doesn't trigger the bug after the undelegation

        # add new pending undelegation
        for delegation in validator_delegations_list:
            delegator_add = delegation["delegator-address"]
            pending_undelegations_list_at_epoch = delegation["undelegations"]
            for undelegation in pending_undelegations_list_at_epoch:
                add_undelegation(validator_add, delegator_add, undelegation)

# check if any pending undelegation was cleared in the recent epoch and detect malicious address
recent_epoch=1975
last_block_of_epoch = blockchain.epoch_last_block(epoch=recent_epoch, endpoint=harmony_rpc_url)
recent_all_validators_at_epoch = get_all_high_fee_validators_at_block(last_block_of_epoch - 1)

# a legit delegator would haven't tried to delegate and zero-out a pending undelegation
# a malicious actor would to delegate and remove the pending undelegation the final amount is below
# the original or the pending undelegation completely disappeared
# at a recent epoch where the bug is not yet fixed, the pending undelegation should be untouched

for undelegation in all_pending_undelegation:
    # check if the undelegation was cleared
    if (undelegation['epoch_cleared'] != 0 and
        undelegation['epoch_cleared'] - undelegation['epoch'] > 8):
        print(f"Malicious = True ==> Delegator {undelegation['delegator_add']} with Validator {undelegation['validator_add']}"
                        f"cleared the pending undelegation before the 8th epoch")
        undelegation['malicious'] = True
        continue # next undelegation

    undelegation_found = False
    # Get the validator info associated to the delegator
    validator_recent_info = [validator for validator in recent_all_validators_at_epoch
        if validator['validator']['address'] == undelegation["validator_add"]]

    if len(validator_recent_info) != 1:
        if len(validator_recent_info) == 0:
            continue # validator is no longer active, should we check anything here ?
        write_json_to_file(validator_recent_info, "validator_recent_info.json")
        print(f"More than 1 validator info error for {undelegation['validator_add']}")
        exit()

    validator_recent_info = validator_recent_info[0]['validator']
    #print(json.dumps(validator_recent_info))
    validator_addr = validator_recent_info['address']

    delegator_delegation = [delegation for delegation in validator_recent_info['delegations']
            if delegation['delegator-address'] == undelegation['delegator_add']]

    delegator_addr = undelegation['delegator_add']

    if len(delegator_delegation) == 0:
        print("next delegation but should never hit here")
        continue
    else:
        recent_undelegations = delegator_delegation[0]['undelegations']
        for recent_undelegation in recent_undelegations:
            if recent_undelegation['epoch'] == undelegation['epoch']:
                undelegation_found = True
                undelegation['final_amount'] = atto_to_one(recent_undelegation['amount'])

                # compare final and original which may have partial ONE minted
                # those undelegation are malcious if the epoch of undelegation was already above 7
                if (undelegation['original_amount'] != undelegation['final_amount'] and
                        undelegation['epoch'] - recent_epoch > 7):
                    print(f"Malicious = True ==> Delegator {delegator_addr} with Validator {validator_addr}"
                        f"at epoch {undelegation['epoch']} original amount is now different."
                        f"original: {undelegation['original_amount']} now {undelegation['final_amount']}")
                    undelegation['malicious'] = True

                break

write_json_to_file(all_pending_undelegation, "pending_undelegation-before-staking.json")

# reports of malicious users without the staking tx check
bad_undelegations = [
    undelegation for undelegation in all_pending_undelegation if undelegation['malicious'] == True
]

write_json_to_file(bad_undelegations, "bad_undelegation-before-staking.json")

# summarize the data without the staking tx check
summary = {}
for item in bad_undelegations:
    delegator = item['delegator_add']
    amount = item['original_amount']
    if delegator in summary:
        summary[delegator] += amount
    else:
        summary[delegator] = amount

summarized_data = [{'delegator_add': k, 'total_amount': v} for k, v in summary.items()]
# Sort the summarized data by highest total_original_amount
summarized_data.sort(key=lambda x: x['total_amount'], reverse=True)

write_json_to_file(summarized_data, "summarize_bad_undelegation-before-staking.json")

# We'll use the staking transaction to further refine the list if necessary
for undelegation in bad_undelegations:
    staking_txs = gather_staking_transactions(undelegation['delegator_add'])
    filtered_staking_txs = [staking for staking in staking_txs
        if staking['epoch'] >= undelegation['epoch']
        and staking['status'] == 1 and staking['type'] == "Delegate"]
    for staking_tx in filtered_staking_txs: #staking_txs are ordered old to new
        transaction_epoch = staking_tx['epoch']
        if undelegation['epoch_cleared'] > undelegation['epoch'] + 8:
            undelegation['malicious'] = True
            continue
        else:
            undelegation['malicious'] = False
            continue
    if len(filtered_staking_txs) == 0:
        undelegation['malicious'] = False
    write_json_to_file(bad_undelegations, "bad_undelegation-with-staking.json")

# print(json.dumps(bad_undelegation))
write_json_to_file(bad_undelegations, "bad_undelegation-with-staking.json")

# summarize the data
summary = {}
for item in bad_undelegations:
    if item['malicious'] == True:
        delegator = item['delegator_add']
        amount = item['original_amount']
        if delegator in summary:
            summary[delegator] += amount
        else:
            summary[delegator] = amount

summarized_data = [{'delegator_add': k, 'total_amount': v} for k, v in summary.items()]
# Sort the summarized data by highest total_original_amount
summarized_data.sort(key=lambda x: x['total_amount'], reverse=True)

write_json_to_file(summarized_data, "summarize_bad_undelegation-with-staking.json")


