import time
import json
import argparse
from pyhmy import blockchain
from concurrent.futures import ThreadPoolExecutor, as_completed

# Script will return the last miners before the next unsual block time (ie more than 2s)
# output will be in json format
# Usage: python3 unsual-block-delay.py <start_block> <end_block> --num_threads <num_threads>
# Example: python3 unsual-block-delay.py 1000 2000 --num_threads 100

def write_dict_to_disk(data, filename):
    """
    Writes a dictionary to a file in JSON format.

    Args:
        data (dict): The dictionary to write to disk.
        filename (str): The name of the file to write the dictionary to.
    """
    with open(filename, 'w') as file:
        json.dump(data, file)

def get_blocks_with_retries(start_block, end_block, endpoint, retries):
    """
    Retrieves the blocks within the specified range, with retries in case of failure.
    Args:
        start_block (int): The starting block number.
        end_block (int): The ending block number.
        endpoint (str): The blockchain endpoint to query.
        retries (int): The number of retry attempts for failed requests.
    Returns:
        list: A list of block dictionaries.
    """
    for attempt in range(retries):
        try:
            return blockchain.get_blocks(start_block=start_block, end_block=end_block, full_tx=False, include_tx=False, include_staking_tx=False, include_signers=False, endpoint=endpoint)
        except Exception as e:
            if attempt < retries - 1:
                print(f"Blocks {start_block} to {end_block} retrieval failed: {e}. {attempt + 1} time(s) retried.")
                time.sleep(1)  # Wait for 1 second before retrying
            else:
                raise e

def fetch_all_blocks(endpoint, start_block, end_block, retries, num_threads):
    """
    Retrieves all blocks within the specified range
    Args:
        endpoint (str): The blockchain endpoint to query.
        start_block (int): The starting block number.
        end_block (int): The ending block number.
        retries (int): The number of retry attempts for failed requests.
        num_threads (int): The number of threads to use for parallel block retrieval.
    Returns:
        list: A list of block dictionaries.
    """
    blocks = []
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_block_range = {}
        for block_num in range(start_block, end_block + 1, 1000):
            range_end_block = min(block_num + 999, end_block)
            future = executor.submit(get_blocks_with_retries, block_num, range_end_block, endpoint, retries)
            future_to_block_range[future] = (block_num, range_end_block)
            #print(f"Blocks {block_num} to {range_end_block} retrieval scheduled.")

        for future in as_completed(future_to_block_range):
            block_range = future_to_block_range[future]
            try:
                block_list = future.result()
                blocks.extend(block_list)
                #print(f"Blocks {block_range[0]} to {block_range[1]} retrieved successfully. added {len(block_list)} blocks.")
            except Exception as e:
                print(f"Blocks {block_range[0]} to {block_range[1]} retrieval failed: {e}")
    return blocks

def calculate_block_time_diffs(blocks):
    """
    Calculates the time differences between consecutive blocks.

    Args:
        blocks (list): A list of block dictionaries.

    Returns:
        list: A list of dictionaries with block numbers and their time differences with the next block.
    """
    block_time_diffs = []
    for i in range(len(blocks) - 1):
        current_block = blocks[i]
        next_block = blocks[i + 1]
        time_diff = next_block['timestamp'] - current_block['timestamp']
        if time_diff > 10 or time_diff < -10:
            print(f"Block {current_block['number']} to {next_block['number']} has unusual time difference: {time_diff} seconds")
            print(f"  Current Block {current_block['number']} timestamp: {current_block['timestamp']}")
            print(f"  Next Block {next_block['number']} timestamp: {next_block['timestamp']}")
        block_time_diffs.append({current_block['number']: time_diff})
    return block_time_diffs

def get_last_miners_between_blocks(endpoint, start_block, end_block, threshold=2, retries=10, num_threads=10):
    """
    Retrieves the list of miners for blocks between the specified start and end blocks,
    stopping when the time difference between blocks exceeds the given threshold.

    Args:
        endpoint (str): The blockchain endpoint to query.
        start_block (int): The starting block number.
        end_block (int): The ending block number.
        threshold (int, optional): The maximum allowed time difference between
                                   blocks in seconds. Defaults to 2.
        retries (int, optional): The number of retry attempts for failed requests. Defaults to 10.
        num_threads (int, optional): The number of threads to use for parallel block retrieval. Defaults to 10.

    Returns:
        list: A list of miner addresses for the blocks within the specified range.
    """
    blocks = fetch_all_blocks(endpoint, start_block, end_block, retries, num_threads)
    blocks.sort(key=lambda x: x['number'], reverse=False)  # Ensure blocks are sorted by block number in descending order
    blocks_time = calculate_block_time_diffs(blocks)

    if len(blocks) < 2:
        raise ValueError("At least 2 blocks are required to calculate time differences.")

    last_block_time = blocks[0]['timestamp']
    miners = []

    miner_blocks = {}

    for block in blocks:
        block_time = block['timestamp']
        time_diff = block_time - last_block_time

        if time_diff > threshold:
            miner = block['miner']
            if miner not in miner_blocks:
                miner_blocks[miner] = []
            miner_blocks[miner].append({block['number']: time_diff})

        last_block_time = block_time

    return miner_blocks, blocks_time


def analyze_block_production(blocks, normal_block_time=2):
    """
    Analyzes the block production and prints statistics.

    Args:
        blocks (list): A list of dictionaries with block numbers and their time differences.
        normal_block_time (int, optional): The normal block time in seconds. Defaults to 2.
    """
    total_blocks = len(blocks)
    if total_blocks < 2:
        print("Not enough blocks to analyze.")
        return

    total_time = sum(list(block.values())[0] for block in blocks)
    total_time_diff = total_time - total_blocks * normal_block_time

    print(f"Total blocks processed: {total_blocks} between blocks {list(blocks[0].keys())[0]} and {list(blocks[-1].keys())[0]}")
    print(f"Total time: {total_time} seconds")
    print(f"block time: {total_time / total_blocks} (vs {normal_block_time}s)")
    print(f"Total blocks time should be : {total_blocks * normal_block_time}s")
    print(f"Total time difference: {total_time_diff} seconds")
    print(f"Missing blocks production number: {total_time_diff / normal_block_time}")
    blocks_above_threshold = [block for block in blocks if list(block.values())[0] > normal_block_time]
    print(f"Number of blocks with time difference above {normal_block_time}s: {len(blocks_above_threshold)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get last miners before unusual block time.")
    parser.add_argument("start_block", type=int, help="The starting block number.")
    parser.add_argument("end_block", type=int, help="The ending block number.")
    parser.add_argument("--num_threads", type=int, default=100, help="The number of threads to use for parallel block retrieval.")
    parser.add_argument("--shard", type=int, choices=[0, 1], default=0, help="The shard number to query (0 or 1).")
    args = parser.parse_args()

    if args.shard == 0:
        endpoint = "https://api.s0.t.hmny.io"
    else:
        endpoint = "https://api.s1.t.hmny.io"

    miners, blockstimes = get_last_miners_between_blocks(endpoint, args.start_block, args.end_block, num_threads=args.num_threads)
    print("write Last miners with block before next unusual block time to file")
    write_dict_to_disk(miners, "miners.json")
    print("write blocks time diff to file")
    write_dict_to_disk(blockstimes, "blocks_time.json")

    analyze_block_production(blockstimes)

