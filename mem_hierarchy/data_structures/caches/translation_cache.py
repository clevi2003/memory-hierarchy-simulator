from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult
#from collections import OrderedDict

class TranslationEntry:
    def __init__(self, ppn, insertes_at):
        self.ppn = ppn
        self.inserted_at = insertes_at
        self.last_used = insertes_at

class TranslationCache(CacheCore):
    def __init__(self, name, ppn_bits, num_sets, associativity, dtlb_tag_bits, dtlb_index_bits, page_offset_bits):
        super().__init__(name, num_sets, associativity, dtlb_tag_bits, dtlb_index_bits, offset_bits=0,
                         phys_bits=ppn_bits + page_offset_bits, ppn_bits=ppn_bits, page_offset_bits=page_offset_bits,
                         policy=None, line_size=None)

        # precompute masks
        self._dtlb_index_mask = (1 << self.index_bits) - 1
        self._page_offset_mask = (1 << self.page_offset_bits) - 1

    def addr_to_vpn(self, v_address):
        return v_address >> self.page_offset_bits

    def addr_to_offset(self, v_address):
        return v_address & self._page_offset_mask

    def parse_address(self, address):
        vpn = self.addr_to_vpn(address)
        index = vpn & self._dtlb_index_mask
        tag = vpn >> self.index_bits
        offset = self.addr_to_offset(address)
        return tag, index, offset

    def probe(self, operation, address):
        tag, index, offset = self.parse_address(address)
        page_offset = self.addr_to_offset(address)

        set_dict = self.sets[index]
        # hit
        if tag in set_dict:
            #self.get_update_mru(set_dict, tag)
            self.get_update_mru_new(index, tag)
            translation_entry = set_dict[tag]
            physical_address = (translation_entry.ppn << self.page_offset_bits) | offset
            return AccessResult(self.name, operation, physical_address, True, tag, index, page_offset)
        # miss
        return AccessResult(self.name, operation, address, False, tag, index, page_offset,
                            needs_lower_read=operation=="R")

    # def possibly_evict(self, address):
    #     tag, index, offset = self.parse_address(address)
    #     set_dict = self.sets[index]
    #     if len(set_dict) >= self.associativity:
    #         # evict the least recently used item (first item in ordered dict)
    #         lru_info, evicted = set_dict.popitem(last=False)
    #         self.evictions += 1
    #         return evicted
    #     return None

    def backfill(self, virtual_address, physical_address):
        ppn = physical_address >> self.page_offset_bits
        tag, index, offset = self.parse_address(virtual_address)
        evicted = self.possibly_evict(virtual_address)
        self.mru_counter += 1
        self.sets[index][tag] = TranslationEntry(ppn, self.mru_counter)
        page_offset = self.addr_to_offset(virtual_address)
        return AccessResult(self.name, "R", virtual_address, False, tag, index, page_offset,
                            allocated=True, evicted_entry=evicted)

    def invalidate(self, evicted_entry):
        for set_dict in self.sets:
            kill = [tag for tag, entry in set_dict.items() if entry.ppn == evicted_entry.ppn]
            for tag in kill:
                set_dict.pop(tag)

    def invalidate_vpn(self, vpn):
        # Remove any entry for this VPN (per-set)
        index = vpn & self._dtlb_index_mask
        tag = vpn >> self.index_bits # or your parse function
        set_dict = self.sets[index]
        if tag in set_dict:
            set_dict.pop(tag)


class DTLB(TranslationCache):
    """ Lightweight wrapper around TranslationCache for the DTLB """
    def __init__(self, config):
        super().__init__(
            name="DTLB",
            ppn_bits=config.bits.ppn_bits,
            num_sets=config.dtlb.num_sets,
            associativity=config.dtlb.associativity,
            dtlb_tag_bits=config.bits.dtlb_tag_bits,
            dtlb_index_bits=config.bits.dtlb_index_bits,
            page_offset_bits=config.bits.page_offset_bits,
        )