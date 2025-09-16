from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult, EvictedTranslationEntry

class TranslationEntry:
    def __init__(self, tag, index, ppn):
        self.tag = tag
        self.index = index
        self.ppn = ppn

class TranslationCache(CacheCore):
    def __init__(self, name, ppn, num_sets, associativity, tag_bits, index_bits):
        self.ppn = ppn
        super().__init__(name, num_sets, associativity, tag_bits, index_bits)

    def probe(self, operation, address):
        tag, index, offset = self.parse_address(address)

        set_dict = self.sets[index]
        if tag in set_dict:
            self.get_update_mru(set_dict, tag)
            translation_entry = set_dict[tag]
            physical_address = translation_entry.ppn + bin(offset)[3:].zfill(self.offset_bits)
            return AccessResult(self.name, operation, physical_address, True, tag, index, offset)
        return AccessResult(self.name, operation, address, False, tag, index, offset,
                            needs_lower_read=operation=="R")

    def possibly_evict(self, address):
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if len(set_dict) >= self.associativity:
            # evict the least recently used item (first item in ordered dict)
            lru_info, evicted = set_dict.popitem(last=False)
            self.evictions += 1
            return EvictedTranslationEntry(evicted.tag, evicted.index, evicted.ppn)
        return None

    def back_fill(self, v_address, ppn) -> AccessResult:
        tag, index, offset = self.parse_address(v_address)
        evicted = self.possibly_evict(v_address)
        self.sets[index][tag] = TranslationEntry(tag, index, ppn)
        return AccessResult(self.name, "R", int(v_address, 2), False, tag, index, offset, allocated=True, evicted_entry=evicted)

    def invalidate_page(self, evicted_entry):
        set_dict = self.sets[evicted_entry.index]
        if set_dict:
            if evicted_entry.tag in set_dict:
                set_dict.pop(evicted_entry.tag)

class DTLB(TranslationCache):
    def __init__(self, config):
        super().__init__("DTLB",
                         config.bits.ppn_bits,
                         config.dtlb.num_sets,
                         config.dtlb.associativity,
                         config.bits.dtlb_tag_bits,
                         config.bits.dtlb_index_bits)

