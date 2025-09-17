from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class TranslationEntry:
    """
    A class representing a translation entry in a translation cache
    """
    def __init__(self, tag, index, ppn):
        self.tag = tag
        self.index = index
        self.ppn = ppn

class TranslationCache(CacheCore):
    """
    Wrapper around CacheCore for translation caches (i.e., TLBs)
    """
    def __init__(self, name, ppn, num_sets, associativity, tag_bits, index_bits):
        self.ppn = ppn
        super().__init__(name, num_sets, associativity, tag_bits, index_bits)

    def probe(self, operation, address):
        """
        Probe the cache for a given operation and address. Overwrites the CacheCore probe method because must handle
        addresses differently
        :param operation: string operation, either "R" or "W"
        :param address: binary string address
        :return: AccessResult object indicating the result of the probe
        """
        tag, index, offset = self.parse_address(address)

        set_dict = self.sets[index]
        # hit
        if tag in set_dict:
            self.get_update_mru(set_dict, tag)
            translation_entry = set_dict[tag]
            # for a hit, must reconstruct the physical address
            physical_address = translation_entry.ppn + bin(offset)[3:].zfill(self.offset_bits)
            return AccessResult(self.name, operation, physical_address, True, tag, index, offset)
        # miss
        return AccessResult(self.name, operation, address, False, tag, index, offset,
                            needs_lower_read=operation=="R")

    def possibly_evict(self, address):
        """
        Evicts the least recently used cache entry if the set is full.
        :param address: binary string address
        :return: the evicted TranslationEntry if eviction occurred, else None
        """
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if len(set_dict) >= self.associativity:
            # evict the least recently used item (first item in ordered dict)
            lru_info, evicted = set_dict.popitem(last=False)
            self.evictions += 1
            return evicted
        return None

    def back_fill(self, v_address, ppn):
        """
        Fills the cache with a new entry for the given virtual address and ppn, possibly evicting from the relevant set
        :param v_address: binary string virtual address
        :param ppn: binary string physical page number
        :return: AccessResult indicating the result of the back fill operation
        """
        tag, index, offset = self.parse_address(v_address)
        evicted = self.possibly_evict(v_address)
        self.sets[index][tag] = TranslationEntry(tag, index, ppn)
        return AccessResult(self.name, "R", int(v_address, 2), False, tag, index, offset, allocated=True, evicted_entry=evicted)

class DTLB(TranslationCache):
    """
    Lightweight wrapper around TranslationCache for the DTLB
    """
    def __init__(self, config):
        super().__init__("DTLB",
                         config.bits.ppn_bits,
                         config.dtlb.num_sets,
                         config.dtlb.associativity,
                         config.bits.dtlb_tag_bits,
                         config.bits.dtlb_index_bits)

