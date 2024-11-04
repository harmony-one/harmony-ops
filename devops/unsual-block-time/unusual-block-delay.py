import time
import json
import argparse
from pyhmy import blockchain
from concurrent.futures import ThreadPoolExecutor, as_completed

# Script will return the last miners before the next unsual block time (ie more than 2s)
# output will be in json format
# Usage: python3 unsual-block-delay.py <start_block> <end_block> --num_threads <num_threads>
# Example: python3 unsual-block-delay.py 1000 2000 --num_threads 100

endpoint = "https://api.s0.t.hmny.io"

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

        for future in as_completed(future_to_block_range):
            block_range = future_to_block_range[future]
            try:
                block_list = future.result()
                blocks.extend(block_list)
            except Exception as e:
                print(f"Blocks {block_range[0]} to {block_range[1]} retrieval failed: {e}")
    return blocks

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
    blocks.sort(key=lambda x: x['number'], reverse=True)  # Ensure blocks are sorted by block number in descending order

    last_block_time = blocks[0]['timestamp']
    miners = []

    miner_blocks = {}

    for block in blocks:
        block_time = block['timestamp']
        time_diff = last_block_time - block_time

        if time_diff > threshold:
            miner = block['miner']
            if miner not in miner_blocks:
                miner_blocks[miner] = []
            miner_blocks[miner].append({block['number']: time_diff})

        last_block_time = block_time

    return miner_blocks

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get last miners before unusual block time.")
    parser.add_argument("start_block", type=int, help="The starting block number.")
    parser.add_argument("end_block", type=int, help="The ending block number.")
    parser.add_argument("--num_threads", type=int, default=100, help="The number of threads to use for parallel block retrieval.")
    args = parser.parse_args()

    miners = get_last_miners_between_blocks(endpoint, args.start_block, args.end_block, num_threads=args.num_threads)
    print("Last miners with block before next unusual block time:")
    print(json.dumps(miners, indent=2))