from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class CacheEntry:
    """
    Represents a single cache entry in a data cache.
    """
    def __init__(self, tag, index, address, dirty=False):
        self.tag = tag
        self.index = index
        self.address = address
        self.dirty = dirty

    def mark_dirty(self):
        """
        Marks the cache entry as dirty.
        :return: None
        """
        self.dirty = True

class DataCache(CacheCore):
    """
    Wrapper around CacheCore for data caches (DC, L2, other future caches)
    """
    def __init__(self, name, num_sets, associativity, tag_bits, index_bits, *, offset_bits, phys_bits, ppn_bits,
                 page_offset_bits, policy=None, line_size):
        self.alloc_on_write_miss = 0
        self.writebacks_during_run = 0
        self.l2_lower_R_calls = 0  # number of times L2 calls its lower level with "R"
        self.l2_read_miss_calls = 0
        super().__init__(name, num_sets, associativity, tag_bits, index_bits, offset_bits=offset_bits,
                         phys_bits=phys_bits, ppn_bits=ppn_bits, page_offset_bits=page_offset_bits, policy=policy,
                         line_size=line_size)

    def possibly_evict(self, address):
        """
        Evicts the least recently used cache entry if the set is full.
        :param address: binary string address
        :return: the evicted CacheEntry if eviction occurred, else None
        """
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if len(set_dict) >= self.associativity:
            # evict the least recently used item (first item in ordered dict)
            lru_info, evicted = set_dict.popitem(last=False)
            self.evictions += 1
            if evicted.dirty:
                self.write_backs += 1
            return evicted
        return None

    def back_fill(self, operation, address, dirty=False):
        """
        Fills the cache with a new entry for the given address, possibly evicting from the relevant set.
        :param operation: string "R" or "W"
        :param address: binary string address
        :param dirty: bool indicating if the new entry should be marked dirty
        :return: AccessResult indicating the result of the back fill operation
        """
        tag, index, offset = self.parse_address(address)
        evicted = self.possibly_evict(address)
        cache_entry = CacheEntry(tag, index, self._block_base(address))
        if dirty:
            cache_entry.mark_dirty()
        self.sets[index][tag] = cache_entry
        return AccessResult(self.name, operation, address, False, tag, index, offset, allocated=True,
                            evicted_entry=evicted,wrote_back=(evicted.dirty if evicted else False))

    def iter_dirty_entries(self):
        """
        Generator to iterate over all dirty cache entries in the cache.
        :return: yields dirty CacheEntry objects
        """
        for set_dict in self.sets:
            for entry in set_dict.values():
                if entry.dirty:
                    yield entry

class DCCache(DataCache):
    """
    lightweight wrapper around DataCache for L1 data cache
    """
    def __init__(self, config):
        num_sets = config.dc.num_sets
        policy = config.dc.policy
        line_size = config.dc.line_size
        associativity = config.dc.associativity
        tag_bits = config.bits.dc_tag_bits
        index_bits = config.bits.dc_index_bits
        offset_bits = config.bits.dc_offset_bits
        ppn_bits = config.bits.ppn_bits
        page_offset_bits = config.bits.page_offset_bits
        phys_bits = ppn_bits + page_offset_bits
        super().__init__("DC", num_sets, associativity, tag_bits, index_bits, offset_bits=offset_bits,
                         phys_bits=phys_bits, ppn_bits=ppn_bits, page_offset_bits=page_offset_bits, policy=policy,
                         line_size=line_size)

class L2Cache(DataCache):
    """
    lightweight wrapper around DataCache for L2 cache
    """
    def __init__(self, config):
        num_sets = config.l2.num_sets
        policy = config.l2.policy
        line_size = config.l2.line_size
        associativity = config.l2.associativity
        tag_bits = config.bits.l2_tag_bits
        index_bits = config.bits.l2_index_bits
        offset_bits = config.bits.l2_offset_bits
        ppn_bits = config.bits.ppn_bits
        page_offset_bits = config.bits.page_offset_bits
        phys_bits = ppn_bits + page_offset_bits
        super().__init__("L2", num_sets, associativity, tag_bits, index_bits, offset_bits=offset_bits,
                         phys_bits=phys_bits, ppn_bits=ppn_bits, page_offset_bits=page_offset_bits, policy=policy,
                         line_size=line_size)