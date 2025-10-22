from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult
import collections
import copy

class CacheEntry:
    """
    Represents a single cache entry in a data cache.
    """
    def __init__(self, tag, index, address, inserted_at, dirty=False):
        self.tag = tag
        self.index = index
        self.address = address
        self.dirty = dirty
        self.inserted_at = inserted_at
        self.last_used = inserted_at

    def mark_dirty(self):
        """
        Marks the cache entry as dirty.
        :return: None
        """
        self.dirty = True

    def __eq__(self, other):
        if not isinstance(other, CacheEntry):
            return NotImplemented
        return (self.tag == other.tag and self.index == other.index and
                self.address == other.address and self.dirty == other.dirty)

    def __str__(self):
        return f"CacheEntry(tag={self.tag}, index={self.index}, address={self.address}, dirty={self.dirty})"

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
        self.clean_evictions = 0
        self.dirty_evictions = 0
        self.dirty_evictions_per_set = collections.Counter()
        super().__init__(name, num_sets, associativity, tag_bits, index_bits, offset_bits=offset_bits,
                         phys_bits=phys_bits, ppn_bits=ppn_bits, page_offset_bits=page_offset_bits, policy=policy,
                         line_size=line_size)

    # def get_update_mru_new(self, index, tag):
    #     """
    #     Get the cache entry and update it to be the most recently used
    #     :param set_dict: set within the cache to update
    #     :param tag: integer tag of the cache entry to update
    #     :return: the cache entry
    #     """
    #     set_dict = self.sets[index]
    #     old_set_dict = copy.deepcopy(set_dict)
    #     cache_entry = set_dict.pop(tag)
    #     print(cache_entry)
    #     #cache_entry.last_used  = set_dict[max(set_dict, key=lambda e: set_dict[e].last_used)].last_used + 1 if set_dict else cache_entry.last_used + 1
    #     set_dict[tag] = cache_entry
    #     if len(old_set_dict) > 1 and old_set_dict[tag] != cache_entry:
    #         assert old_set_dict != set_dict
    #     return cache_entry

    # def choose_victim(self, index):
    #     set_dict = self.sets[index]
    #     # LRU with stable tie-break on insertion time
    #     victim_tag, victim_entry = min(
    #         set_dict.items(),
    #         key=lambda kv: (kv[1].last_used, kv[1].inserted_at)
    #     )
    #     return victim_tag, victim_entry
    #
    # def possibly_evict(self, address):
    #     """
    #     Evicts the least recently used cache entry if the set is full.
    #     :param address: binary string address
    #     :return: the evicted CacheEntry if eviction occurred, else None
    #     """
    #     tag, index, _ = self.parse_address(self._block_base(address))
    #     set_dict = self.sets[index]
    #     if len(set_dict) < self.associativity:
    #         return None
    #     victim_tag, victim_entry = self.choose_victim(index)
    #     set_dict.pop(victim_tag)
    #     return victim_entry
        # address = self._block_base(address)
        # tag, index, offset = self.parse_address(address)
        # set_dict = self.sets[index]
        # if len(set_dict) >= self.associativity:
        #     # evict the least recently used item (first item in ordered dict)
        #     victim_key = min(set_dict, key=lambda e: (set_dict[e].last_used, set_dict[e].inserted_at))
        #     victim = set_dict[victim_key]
        #     # remove the victim
        #     evicted = CacheEntry(victim.tag, victim.index, victim.address, victim.inserted_at, dirty=victim.dirty)
        #     del set_dict[victim_key]
        #     #lru_info, evicted = set_dict.popitem(last=False)
        #     self.evictions += 1
        #     if evicted.dirty:
        #         self.write_backs += 1
        #         self.dirty_evictions += 1
        #         self.dirty_evictions_per_set[index] += 1
        #     else:
        #         self.clean_evictions += 1
        #     return evicted
        # return None

    def back_fill(self, operation, address, dirty=False):
        """
        Fills the cache with a new entry for the given address, possibly evicting from the relevant set.
        :param operation: string "R" or "W"
        :param address: binary string address
        :param dirty: bool indicating if the new entry should be marked dirty
        :return: AccessResult indicating the result of the back fill operation
        """
        base = self._block_base(address)  # <— add
        tag, index, offset = self.parse_address(base)  # (now parse the base)
        evicted = self.possibly_evict(base)
        self.mru_counter += 1
        cache_entry = CacheEntry(tag, index, base, self.mru_counter, dirty=False)
        if dirty and operation == "W":
            cache_entry.mark_dirty()
        if operation == "R":
            assert not cache_entry.dirty
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