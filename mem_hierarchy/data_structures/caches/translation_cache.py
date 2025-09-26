from .cache_core import CacheCore
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult
#from collections import OrderedDict

class TranslationEntry:
    def __init__(self, ppn):
        self.ppn = ppn

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
            self.get_update_mru(set_dict, tag)
            translation_entry = set_dict[tag]
            physical_address = (translation_entry.ppn << self.page_offset_bits) | offset
            return AccessResult(self.name, operation, physical_address, True, tag, index, page_offset)
        # miss
        return AccessResult(self.name, operation, address, False, tag, index, page_offset,
                            needs_lower_read=operation=="R")

    def possibly_evict(self, address):
        tag, index, offset = self.parse_address(address)
        set_dict = self.sets[index]
        if len(set_dict) >= self.associativity:
            # evict the least recently used item (first item in ordered dict)
            lru_info, evicted = set_dict.popitem(last=False)
            self.evictions += 1
            return evicted
        return None

    def backfill(self, virtual_address, physical_address):
        ppn = physical_address >> self.page_offset_bits
        tag, index, offset = self.parse_address(virtual_address)
        evicted = self.possibly_evict(virtual_address)
        self.sets[index][tag] = TranslationEntry(ppn)
        page_offset = self.addr_to_offset(virtual_address)
        return AccessResult(self.name, "R", virtual_address, False, tag, index, page_offset,
                            allocated=True, evicted_entry=evicted)

    def invalidate(self, evicted_entry):
        for set_dict in self.sets:
            kill = [tag for tag, entry in set_dict.items() if entry.ppn == evicted_entry.ppn]
            for tag in kill:
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
#
# # class TranslationEntry:
# #     """
# #     A class representing a translation entry in a translation cache
# #     """
# #     def __init__(self, tag, index, ppn):
# #         self.tag = tag
# #         self.index = index
# #         self.ppn = ppn
#
# # class TranslationEntry:
# #     """
# #     A class representing a translation entry in a translation cache
# #     """
# #     def __init__(self, v_address, p_address):
# #         self.virtual_address = v_address
# #         self.physical_address = p_address
#
# class TranslationEntry:
#     def __init__(self, vpn, ppn):
#         self.vpn = vpn
#         self.ppn = ppn  # store the physical page number
#
#     def build_physical_address(self, offset, offset_bits):
#         # print("type of ppn:", type(self.ppn), self.ppn)
#         # print("type of offset:", type(offset), offset)
#         offset_str = bin(offset)[2:].zfill(offset_bits)
#         return self.ppn + offset_str
#
# class TranslationCache(CacheCore):
#     """
#     Wrapper around CacheCore for translation caches (i.e., TLBs)
#     """
#     def __init__(self, name, ppn, num_sets, associativity, tag_bits, index_bits):
#         self.ppn = ppn
#         super().__init__(name, num_sets, associativity, tag_bits, index_bits)

    # def parse_address(self, ):
    #     print(self.tag_bits, self.index_bits, self.offset_bits)
    #     print("--------------------")
    #     """
    #     Parse a binary string address into its tag, index, and offset components
    #     :param address: binary string address
    #     :return: integer tag, index, and offset
    #     """
    #     if len(address) < self.expected_bits:
    #         address = address.zfill(self.expected_bits)
    #     # get first bits for the tag
    #     tag = address[:self.tag_bits]
    #     # get middle bits for index
    #     index = address[self.tag_bits:self.tag_bits + self.index_bits]
    #     # get final bits for offset
    #     #offset = address[-self.offset_bits:]
    #     offset = address[self.tag_bits + self.index_bits:]
    #     return int(tag, 2), int(index, 2), int(offset, 2)
#
#     def probe(self, operation, address):
#         """
#         Probe the cache for a given operation and address. Overwrites the CacheCore probe method because must handle
#         addresses differently
#         :param operation: string operation, either "R" or "W"
#         :param address: binary string address
#         :return: AccessResult object indicating the result of the probe
#         """
#         #print("parsing address:", address, len(address))
#         tag, index, offset = self.parse_address(address)
#
#         set_dict = self.sets[index]
#         # hit
#         if tag in set_dict:
#             self.get_update_mru(set_dict, tag)
#             translation_entry = set_dict[tag]
#             physical_address = translation_entry.build_physical_address(offset, self.offset_bits)
#             # physical_address = translation_entry.physical_address
#             return AccessResult(self.name, operation, physical_address, True, tag, index, offset)
#         # miss
#         return AccessResult(self.name, operation, address, False, tag, index, offset,
#                             needs_lower_read=operation=="R")
#
#     def possibly_evict(self, address):
#         """
#         Evicts the least recently used cache entry if the set is full.
#         :param address: binary string address
#         :return: the evicted TranslationEntry if eviction occurred, else None
#         """
#         tag, index, offset = self.parse_address(address)
#         set_dict = self.sets[index]
#         if len(set_dict) >= self.associativity:
#             # evict the least recently used item (first item in ordered dict)
#             lru_info, evicted = set_dict.popitem(last=False)
#             self.evictions += 1
#             return evicted
#         return None
#
#     def back_fill(self, v_address, ppn):
#         """
#         Fills the cache with a new entry for the given virtual address and ppn, possibly evicting from the relevant set
#         :param v_address: binary string virtual address
#         :param ppn: binary string physical page number
#         :return: AccessResult indicating the result of the back fill operation
#         """
#         tag, index, offset = self.parse_address(v_address)
#         vpn = v_address[:-self.ppn]  # get the vpn portion of the v_address
#         # print("back fill tag:", tag, index, offset)
#         evicted = self.possibly_evict(v_address)
#         self.sets[index][tag] = TranslationEntry(vpn, ppn)
#         return AccessResult(self.name, "R", int(v_address, 2), False, tag, index, offset, allocated=True, evicted_entry=evicted)
#
# class DTLB(TranslationCache):
#     """
#     Lightweight wrapper around TranslationCache for the DTLB
#     """
#     def __init__(self, config):
#         super().__init__("DTLB",
#                          config.bits.ppn_bits,
#                          config.dtlb.num_sets,
#                          config.dtlb.associativity,
#                          config.bits.dtlb_tag_bits,
#                          config.bits.dtlb_index_bits
#                          )
#         # need to add offset bits for physical address reconstruction
#
