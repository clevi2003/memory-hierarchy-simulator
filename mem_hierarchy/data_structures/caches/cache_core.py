from collections import OrderedDict
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class CacheCore:
    """
    A class representing a generic cache, can be inherited by specific cache types
    """
    def __init__(self, name, num_sets, associativity, tag_bits, index_bits, *, offset_bits=0, phys_bits=None,
                 ppn_bits=None, page_offset_bits=None, policy=None, line_size=None,):
        self.name = name
        self.num_sets = num_sets
        self.associativity = associativity
        self.tag_bits = tag_bits
        self.index_bits = index_bits
        self.offset_bits = offset_bits or 0

        # precompute masks
        self._phys_mask = (1 << phys_bits) - 1 if phys_bits else (1 << (tag_bits + index_bits + offset_bits)) - 1
        self._index_mask = (1 << self.index_bits) - 1
        self._offset_mask = (1 << self.offset_bits) - 1 if self.offset_bits > 0 else 0

        # widths used for page invalidation
        self.phys_bits = None if phys_bits is None else phys_bits
        self.ppn_bits = None if ppn_bits is None else ppn_bits
        self.page_offset_bits = None if page_offset_bits is None else page_offset_bits

        # storage and policy
        self.sets = [OrderedDict() for _ in range(self.num_sets)]
        self.policy = policy
        self.line_size = line_size

        # stats
        self.reads = self.writes = 0
        self.read_hits = self.write_hits = 0
        self.read_misses = self.write_misses = 0
        self.evictions = self.write_backs = 0

    @staticmethod
    def _coerce_addr(address):
        if isinstance(address, int):
            return address
        s = address.strip()
        return int(s, 2)

    def parse_address(self, address):
        """
        Parse a binary string address into its tag, index, and offset components
        :param address: binary string address
        :return: integer tag, index, and offset
        """
        addr = self._coerce_addr(address) & self._phys_mask
        offset = addr & self._offset_mask
        index = (addr >> self.offset_bits) & self._index_mask
        tag = addr >> (self.index_bits + self.offset_bits)
        return tag, index, offset

    @staticmethod
    def get_update_mru(set_dict, tag):
        """
        Get the cache entry and update it to be the most recently used
        :param set_dict: set within the cache to update
        :param tag: integer tag of the cache entry to update
        :return: the cache entry
        """
        cache_entry = set_dict.pop(tag)
        set_dict[tag] = cache_entry
        return cache_entry

    def probe(self, operation, address):
        """
        Check if the address is in the cache without modifying the cache state (other than lru info)
        :param operation: string "R" or "W"
        :param address: binary string address
        :return: AccessResult object indicating hit or miss and other info
        """
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if tag in set_dict:
            self.get_update_mru(set_dict, tag)
            return AccessResult(self.name, operation, address, True, tag, index, offset)
        return AccessResult(self.name, operation, address, False, tag, index, offset,
                            needs_lower_read=operation=="R")

    def invalidate(self, address):
        """
        Invalidate cache entry that maps to this address
        :param address: binary string address
        :return: boolean indicating if an entry was invalidated
        """
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if tag in set_dict:
            set_dict.pop(tag)
            return True
        return False

    def invalidate_page(self, evicted_entry):
        """
        Invalidate all cache entries that map to the ppn of the evicted page
        :param evicted_entry: EvictedPageTableEntry
        :return: None
        """
        shift = self.phys_bits - self.ppn_bits
        for set_dict in self.sets:
            tags_to_invalidate = []
            for tag, entry in set_dict.items():
                physical_address = self._coerce_addr(entry.address) & self._phys_mask
                entry_ppn = physical_address >> shift
                if entry_ppn == evicted_entry.ppn:
                    tags_to_invalidate.append(tag)
            for tag in tags_to_invalidate:
                set_dict.pop(tag)

    def get_stats(self):
        """
        Get cache stats
        :return: dict of stats
        """
        hits = self.read_hits + self.write_hits
        misses = self.read_misses + self.write_misses
        stats = {"hits": hits,
                 "misses": misses,
                 "hit rate": hits / (hits + misses) if (hits + misses) > 0 else 0}
        return stats
