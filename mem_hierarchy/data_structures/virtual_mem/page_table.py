#from mem_hierarchy.data_structures.result_structures.access_results import EvictedPageTableEntry, TranslationResult

class EvictedPageTableEntry:
    """
    Represents an evicted page table entry
    """
    def __init__(self, ppn, vpn, page_offset_bits=0):
        self.ppn = ppn
        self.vpn = vpn
        self.page_offset_bits = page_offset_bits

class TranslationResult:
    """
    Represents the result of a page table translation
    """
    def __init__(self, hit, vpn, ppn, physical_address, offset, evicted_entry=None):
        self.hit = hit
        self.vpn = vpn
        self.ppn = ppn
        self.physical_address = physical_address
        self.evicted_entry = evicted_entry
        self.offset = offset

class PageTable:
    """
    Page table implementation with LRU eviction
    """
    def __init__(self, config):
        # page table config
        self.n_virtual_pages = config.pt.n_virtual_pages
        self.n_physical_pages = config.pt.n_physical_pages
        self.page_size = config.pt.page_size
        self.vpn_bits = config.bits.vpn_bits
        self.ppn_bits = config.bits.ppn_bits
        self.page_offset_bits = config.bits.page_offset_bits
        self.virt_bits = self.vpn_bits + self.page_offset_bits
        self.phys_bits = self.ppn_bits + self.page_offset_bits

        # masks
        self._offset_mask = (1 << self.page_offset_bits) - 1
        self._vpn_mask = (1 << self.vpn_bits) - 1
        self._ppn_mask = (1 << self.ppn_bits) - 1
        self._virt_mask = (1 << self.virt_bits) - 1
        self._phys_mask = (1 << self.phys_bits) - 1

        # page table state
        self.vpn_to_ppn = {}
        self.ppn_to_vpn = {}
        self.free_ppns = [elem for elem in range(self.n_physical_pages)]
        #self.free_ppns = [format(elem, f'0{self.ppn_bits}b') for elem in range(self.n_physical_pages)]
        self.lru_ppns = []

        # stats for tracking
        self.hits = 0
        self.misses = 0
        self.accesses = 0
        self.disk_references = 0

    def _touch_ppn_mru(self, ppn):
        """
        Mark a ppn as most recently used
        :param ppn: str, the ppn to mark as most recently used
        :return: None
        """
        if ppn in self.lru_ppns:
            self.lru_ppns.remove(ppn)
            self.lru_ppns.append(ppn)
        else:
            self.lru_ppns.append(ppn)

    def _allocate_ppn(self):
        """
        Allocate a PPN, evicting if necessary
        :return: None
        """
        # if there are free ppns, use one of those
        if self.free_ppns:
            ppn = self.free_ppns[0]
            self.free_ppns = self.free_ppns[1:]
            return ppn, None
        # if no free ppns, lru eviction. allocated ppn is the lru ppn
        victim_ppn = self.lru_ppns.pop(0)
        victim_vpn = self.ppn_to_vpn[victim_ppn]
        # remove the victim from the page table mappings
        del self.ppn_to_vpn[victim_ppn]
        del self.vpn_to_ppn[victim_vpn]
        return victim_ppn, EvictedPageTableEntry(victim_ppn, victim_vpn, page_offset_bits=self.page_offset_bits)

    def parse_address(self, address):
        """
        Parse a binary address into its page offset and vpn components
        :param address: binary string, the address to parse
        :return: binary string, binary string; the page offset and vpn
        """
        # # final bits are the page offset
        # page_offset = address[-self.page_offset_bits:]
        # # first bits are the vpn
        # vpn = address[:-self.page_offset_bits]
        # return page_offset, vpn
        address  = address & self._virt_mask
        offset = address & self._offset_mask
        vpn = (address >> self.page_offset_bits) & self._vpn_mask
        return offset, vpn

    def build_physical_address(self, ppn, offset):
        """
        Build a physical address from a ppn and offset
        :param ppn: binary string, the ppn
        :param offset: binary string, the page offset
        :return: binary string, the physical address
        """
        return ((ppn & self._ppn_mask) << self.page_offset_bits | (offset & self._offset_mask)) & self._phys_mask

    def translate(self, virtual_address):
        """
        Translate a virtual address to a physical address
        :param virtual_address: binary string, the virtual address to translate
        :return: TranslationResult
        """
        self.accesses += 1
        page_offset, vpn = self.parse_address(virtual_address)
        ppn = self.vpn_to_ppn.get(vpn, None)
        # pt hit
        if not ppn is None:
            self.hits += 1
            # use existing translation and update lru
            self._touch_ppn_mru(ppn)
            physical_address = self.build_physical_address(ppn, page_offset)
            return TranslationResult(True, vpn, ppn, physical_address, page_offset)
        # pt miss
        self.misses += 1
        self.disk_references += 1
        # allocate a new ppn, possibly evict lru ppn, evicted ppn is the new ppn to allocate
        ppn, evicted_entry = self._allocate_ppn()
        self.vpn_to_ppn[vpn] = ppn
        self.ppn_to_vpn[ppn] = vpn
        self._touch_ppn_mru(ppn)
        physical_address = self.build_physical_address(ppn, page_offset)
        return TranslationResult(False, vpn, ppn, physical_address, page_offset, evicted_entry=evicted_entry)

    def get_stats(self):
        """
        Get page table stats
        :return: dict of stats
        """
        stats = {
            "accesses": self.accesses,
            "hits": self.hits,
            "misses": self.misses,
            "hit rate": self.hits / self.accesses if self.accesses > 0 else 0,
            "disk refs": self.disk_references
        }
        return stats