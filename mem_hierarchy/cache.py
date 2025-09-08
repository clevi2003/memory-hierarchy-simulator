from collections import OrderedDict
from operator import index

from access_results import EvictedCacheEntry, AccessResult

class CacheEntry:
    def __init__(self, tag, index):
        self.tag = tag
        self.index = index
        self.dirty = False

    def mark_dirty(self):
        self.dirty = True


class Cache:
    def __init__(self, name, num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size):
        self.name = name
        self.num_sets = num_sets
        self.associativity = associativity
        self.tag_bits = tag_bits
        self.index_bits = index_bits
        self.offset_bits = offset_bits
        self.total_bits = self.tag_bits + self.index_bits + self.offset_bits
        self.sets = [OrderedDict() for _ in range(self.num_sets)]
        self.policy = policy
        self.line_size = line_size

        self.reads = 0
        self.writes = 0
        self.read_hits = 0
        self.write_hits = 0
        self.read_misses = 0
        self.write_misses = 0
        self.evictions = 0
        self.write_backs = 0

    def parse_address(self, address):
        # get first bits for the tag
        tag = address[:self.tag_bits]
        # get middle bits for index
        index = address[self.tag_bits:self.tag_bits + self.index_bits]
        # get final bits for offset
        offset = address[-self.offset_bits:]
        return int(tag, 2), int(index, 2), int(offset, 2)

    def possibly_evict(self, index):
        set_dict = self.sets[index]
        if len(set_dict) >= self.associativity:
            # evict the least recently used item (first item in ordered dict)
            lru_info, evicted = set_dict.popitem(last=False)
            self.evictions += 1
            if evicted.dirty:
                self.write_backs += 1
            return EvictedCacheEntry(evicted.tag, evicted.index, evicted.dirty)
        return None


    @staticmethod
    def get_update_mru(set_dict, tag):
        cache_entry = set_dict.pop(tag)
        set_dict[tag] = cache_entry
        return cache_entry

    def probe(self, operation, address):
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if tag in set_dict:
            self.get_update_mru(set_dict, tag)
            return AccessResult(self.name, operation, address, True, tag, index, offset)
        return AccessResult(self.name, operation, address, False, tag, index, offset,
                            needs_lower_read=operation=="R")

    def back_fill(self, operation, address, dirty=False):
        tag, index, offset = self.parse_address(address)
        evicted = self.possibly_evict(index)
        cache_entry = CacheEntry(tag, index)
        if dirty:
            cache_entry.mark_dirty()
        self.sets[index][tag] = cache_entry
        return AccessResult(self.name, operation, address, False, tag, index, offset, allocated=True,
                            evicted_entry=evicted,wrote_back=(evicted.dirty if evicted else False))

    def invalidate(self, address):
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if tag in set_dict:
            set_dict.pop(tag)
            return True
        return False


    # can't use read and write methods directly bc must coordinate with lower levels first
    def read_hit(self, address, tag, index, offset):
        self.read_hits += 1
        self.get_update_mru(self.sets[index], tag)
        return AccessResult(self.name, "R", address, True, tag, index, offset)

    def read_miss(self, address, tag, index, offset):
        self.read_misses += 1
        # possibly evict if cache is already full and put data into the cache
        evicted = self.possibly_evict(index)
        self.sets[index][tag] = CacheEntry(tag, index)
        return AccessResult(self.name, "R", address, False, tag, index, offset, allocated=True,
                            evicted_entry=evicted, wrote_back=bool(evicted and evicted.dirty), needs_lower_read=True)

    def read(self, address):
        self.reads += 1
        tag, index, offset = self.parse_address(address)
        if tag in self.sets[index]:
            return self.read_hit(address, tag, index, offset)
        return self.read_miss(address, tag, index, offset)

    def write_hit(self, address, tag, index, offset):
        self.write_hits += 1
        write_to_set = self.sets[index]
        # no write allocate and write through
        if self.policy:
            self.get_update_mru(write_to_set, tag)
            return AccessResult(self.name, "W", address, True, tag, index, offset, needs_lower_write=True)
        # write allocate and write back
        cache_entry = self.get_update_mru(write_to_set, tag)
        cache_entry.mark_dirty()
        return AccessResult(self.name, "W", address, True, tag, index, offset, needs_lower_write=False)

    def write_miss(self, address, tag, index, offset):
        self.write_misses += 1
        write_to_set = self.sets[index]
        # no write allocate and write through
        if self.policy:
            return AccessResult(self.name, "W", address, False, tag, index, offset, needs_lower_write=True)
        # write allocate and write back
        evicted = self.possibly_evict(index)
        cache_entry = CacheEntry(tag, index)
        cache_entry.mark_dirty()
        write_to_set[tag] = cache_entry
        return AccessResult(self.name, "W", address, False, tag, index, offset, allocated=True,
                            evicted_entry=evicted, wrote_back=(evicted and evicted.dirty))

    def write(self, address):
        self.writes += 1
        tag, index, offset = self.parse_address(address)
        write_to_set = self.sets[index]
        if tag in write_to_set:
            return self.write_hit(address, tag, index, offset)
        return self.write_miss(address, tag, index, offset)

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


class DataCache(Cache):
    def __init__(self, config):
        num_sets = config.dc.num_sets
        policy = config.dc.policy
        line_size = config.dc.line_size
        associativity = config.dc.associativity
        tag_bits = config.bits.dc_tag_bits
        index_bits = config.bits.dc_index_bits
        offset_bits = config.bits.dc_offset_bits
        self.name = "DC"
        super().__init__("DC", num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size)

class L2Cache(Cache):
    def __init__(self, config):
        num_sets = config.l2.num_sets
        policy = config.l2.policy
        line_size = config.l2.line_size
        associativity = config.l2.associativity
        tag_bits = config.bits.l2_tag_bits
        index_bits = config.bits.l2_index_bits
        offset_bits = config.bits.l2_offset_bits
        super().__init__("L2", num_sets, associativity, tag_bits, index_bits, offset_bits, policy, line_size)






