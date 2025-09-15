from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class CacheEntry:
    def __init__(self, tag, index, address):
        self.tag = tag
        self.index = index
        self.address = address
        self.dirty = False

    def mark_dirty(self):
        self.dirty = True

class DataCache(CacheCore):
    def __init__(self, num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size, name="Data Cache"):
        super().__init__(name,
                         num_sets,
                         associativity,
                         tag_bits,
                         index_bits,
                         offset_bits,
                         policy,
                         line_size)

    def back_fill(self, operation, address, dirty=False):
        tag, index, offset = self.parse_address(address)
        evicted = self.possibly_evict(address)
        cache_entry = CacheEntry(tag, index, address)
        if dirty:
            cache_entry.mark_dirty()
        self.sets[index][tag] = cache_entry
        return AccessResult(self.name, operation, address, False, tag, index, offset, allocated=True,
                            evicted_entry=evicted,wrote_back=(evicted.dirty if evicted else False))

    def invalidate(self, address):
        # invalidate cache entry that maps to this address
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if tag in set_dict:
            set_dict.pop(tag)
            return True
        return False

    # def invalidate_by_tag_index(self, tag, index):
    #     set_dict = self.sets[index]
    #     if tag in set_dict:
    #         set_dict.pop(tag)
    #         return True
    #     return False

    def invalidate_page(self, evicted_entry):
        # invalidate all cache entries that map to this ppn
        # a cache entry maps to this ppn if the top bits of its address match the ppn
        ppn_bits = len(evicted_entry.ppn)
        for set_dict in self.sets:
            tags_to_invalidate = []
            for tag, entry in set_dict.items():
                entry_ppn = entry.address[:ppn_bits]
                if entry_ppn == evicted_entry.ppn:
                    tags_to_invalidate.append(tag)
            for tag in tags_to_invalidate:
                set_dict.pop(tag)

    def get_stats(self):
        stats = {"reads": self.reads,
                 "writes": self.writes,
                 "read_hits": self.read_hits,
                 "write_hits": self.write_hits,
                 "read_misses": self.read_misses,
                 "write_misses": self.write_misses,
                 "read_hit_rate": self.read_hits / self.reads if self.reads > 0 else 0,
                 "write_hit_rate": self.write_hits / self.writes if self.writes > 0 else 0,
                 "evictions": self.evictions,
                 "write backs": self.write_backs,}
        return stats


class DCCache(DataCache):
    def __init__(self, config):
        num_sets = config.dc.num_sets
        policy = config.dc.policy
        line_size = config.dc.line_size
        associativity = config.dc.associativity
        tag_bits = config.bits.dc_tag_bits
        index_bits = config.bits.dc_index_bits
        offset_bits = config.bits.dc_offset_bits
        super().__init__("DC", num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size)

class L2Cache(DataCache):
    def __init__(self, config):
        num_sets = config.l2.num_sets
        policy = config.l2.policy
        line_size = config.l2.line_size
        associativity = config.l2.associativity
        tag_bits = config.bits.l2_tag_bits
        index_bits = config.bits.l2_index_bits
        offset_bits = config.bits.l2_offset_bits
        super().__init__("L2", num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size)