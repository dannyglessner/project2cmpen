from collections import deque, OrderedDict
from utils import Level


class CacheLevel(Level):
    def __init__(self, size, block_size, associativity, eviction_policy, write_policy, level_name, higher_level=None, lower_level=None):
        super().__init__(level_name, higher_level, lower_level)
        self.size = size
        self.block_size = block_size
        self.associativity = associativity
        self.eviction_policy = eviction_policy  # FIFO | LRU | MRU
        self.write_policy = write_policy  # always WB for this assignment

        # define other structures / metadata here (hint, check the imports)
        # todo define number of sets
        # Compute number of sets
        self.num_sets = size // (block_size * associativity)
        # todo define metadata structures (tags, dirty bits, etc...)
        self.cache = {i: OrderedDict() for i in range(self.num_sets)}
        self.dirty_bits = {i: set() for i in range(self.num_sets)}  # Track dirty blocks
        

    def _calculate_index(self, address):
        return (address // self.block_size) % self.num_sets #returns index

    def _calculate_tag(self, address):
        return address // (self.block_size * self.num_sets) #returns tag

    def _calculate_block_address(self, address):
        return address - (address % self.block_size)

    def _calculate_block_address_from_tag_index(self, tag, cache_index):
        return (tag * self.num_sets + cache_index) * self.block_size

    def is_dirty(self, block_address):
        cache_index = self._calculate_index(block_address)
        tag = self._calculate_tag(block_address)
        return tag in self.dirty_bits[cache_index]

    def access(self, operation, address):
        """
        Perform a memory access to the given address. Operations are R for reads, W for writes, and B for block
        / writeback updates. B-type operations do not modify the eviction policy meta-details. To perform an access,
        check to see if the address is in this level. If it is a hit, then report the hit and update the eviction policy
        (if required). If the operation was a store make sure to set the block's dirty bits. If the access was a miss,
        report the miss and check if this set needs to evict a block. If it does, evict the target block. Now that the
        target is evicted allocate space for the next block, update the dirty bits (if required) and perform a read
        on the higher levels to propagate the block. Finally, if the block fetched from the higher block is dirty, set
        our block to also be dirty.
        """
        cache_index = self._calculate_index(address)
        tag = self._calculate_tag(address)
        block_address = self._calculate_block_address(address)
        
        if tag in self.cache[cache_index]:
            # Cache hit
            self.report_hit(address)
            if self.eviction_policy == "LRU":
                self.cache[cache_index].move_to_end(tag)
            
            if operation == 'W':
                self.dirty_bits[cache_index].add(tag)
        else:
            # Cache miss
            self.report_miss(address)
            
            if len(self.cache[cache_index]) >= self.associativity:
                self.evict(cache_index)
            
            self.cache[cache_index][tag] = block_address
            
            if operation == 'W':
                self.dirty_bits[cache_index].add(tag)

    def evict(self, cache_index):
        """
        Select a victim block in the given way provided this level's eviction policy. Calculate its block address and
        then invalidate said block.
        """
        # select a victim block in the set provided the eviction policy (FIFO | LRU | MRU)
        victim_block_tag = None 
        if self.eviction_policy == "FIFO":
            victim_block_tag, _ = next(iter(self.cache[cache_index].items()))
        elif self.eviction_policy == "LRU":
            victim_block_tag, _ = next(iter(self.cache[cache_index].items()))
        elif self.eviction_policy == "MRU":
            victim_block_tag, _ = next(reversed(self.cache[cache_index].items()))
        else:
            return
        
        evicted_block = self._calculate_block_address_from_tag_index(victim_tag, cache_index)
        
        if victim_block_tag in self.dirty_bits[cache_index]:
            self.report_writeback(evicted_block)
            self.dirty_bits[cache_index].remove(victim_block_tag)
        
        self.cache[cache_index].pop(victim_block_tag)
        self.report_eviction(evicted_block)
        # invalidate the block
        evicted_block = self._calculate_block_address_from_tag_index(victim_block_tag, cache_index)
        self.invalidate(evicted_block)

    def invalidate(self, block_address):
        """
        Invalidate the block given by block address. If the block is not in this level, then we know it is not in
        lower levels. If it is in this level, then we need to invalidate lower levels first since they may be dirty.
        Once all lower levels have been invalidated, we need to check if our level is dirty, and if it is, perform a
        writeback and report that. Finally, once all lower levels have been invalidated we can remove the block from
        our level and report the eviction.
        """
        cache_index = self._calculate_index(block_address)
        tag = self._calculate_tag(block_address)
        
        if tag in self.cache[cache_index]:
            if tag in self.dirty_bits[cache_index]:
                self.report_writeback(block_address)
                self.dirty_bits[cache_index].remove(tag)
            self.cache[cache_index].pop(tag)
            self.report_eviction(block_address)

