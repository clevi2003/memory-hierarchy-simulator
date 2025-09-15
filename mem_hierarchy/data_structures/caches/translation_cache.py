from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult

class TranslationEntry:
    def __init__(self, tag, index, ppn):
        self.tag = tag
        self.index = index
        self.ppn = ppn

class TranslationCache(CacheCore):
    def __init__(self, name, ppn, num_sets, associativity, tag_bits, index_bits):
        self.ppn = ppn
        super().__init__(name, num_sets, associativity, tag_bits, index_bits)

    def back_fill(self, v_address, ppn) -> AccessResult:
        tag, index, offset = self.parse_address(v_address)
        evicted = self.possibly_evict(index)
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
                         config.bits.ppn,
                         config.dtlb.num_sets,
                         config.dtlb.associativity,
                         config.bits.dtlb_tag_bits,
                         config.bits.dtlb_index_bits)

