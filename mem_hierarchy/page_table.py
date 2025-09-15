from .access_results import EvictedPageTableEntry, TranslationResult

class PageTable:
    def __init__(self, config):
        # page table config
        self.n_virtual_pages = config.pt.n_virtual_pages
        self.n_physical_pages = config.pt.n_physical_pages
        self.page_size = config.pt.page_size
        self.vpn_bits = config.bits.vpn_bits
        self.ppn_bits = config.bits.ppn_bits
        self.page_offset_bits = config.bits.page_offset_bits

        # page table state
        self.vpn_to_ppn = {}
        self.ppn_to_vpn = {}
        self.free_ppns = [format(elem, f'0{self.ppn_bits}b') for elem in range(self.n_physical_pages)]
        self.lru_ppns = []

        # stats for tracking
        self.hits = 0
        self.misses = 0
        self.accesses = 0
        self.disk_references = 0

    def _touch_ppn_mru(self, ppn):
        """Mark the given PPN as most recently used."""
        if ppn in self.lru_ppns:
            # self.lru_ppns.move_to_end(ppn)
            self.lru_ppns.remove(ppn)
            self.lru_ppns.append(ppn)
        else:
            #self.lru_ppns[ppn] = None
            self.lru_ppns.append(ppn)

    def _allocate_ppn(self):
        """Allocate a PPN, evicting if necessary."""
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
        # final bits are the page offset
        page_offset = address[-self.page_offset_bits:]
        # first bits are the vpn
        vpn = address[:-self.page_offset_bits]
        return page_offset, vpn

    def translate(self, virtual_address):
        """Translate a virtual address to a physical address."""
        self.accesses += 1
        page_offset, vpn = self.parse_address(virtual_address)
        # pt hit
        if vpn in self.vpn_to_ppn:
            self.hits += 1
            ppn = self.vpn_to_ppn[vpn]
            self._touch_ppn_mru(ppn)
            physical_address = ppn + page_offset
            return TranslationResult(True, vpn, ppn, physical_address, page_offset)
        # pt miss
        self.misses += 1
        self.disk_references += 1
        ppn, evicted_entry = self._allocate_ppn()
        self.vpn_to_ppn[vpn] = ppn
        self.ppn_to_vpn[ppn] = vpn
        self._touch_ppn_mru(ppn)
        physical_address = ppn + page_offset
        #print("length physical address:", len(physical_address))
        return TranslationResult(False, vpn, ppn, physical_address, page_offset, evicted_entry=evicted_entry)

    def get_stats(self):
        stats = {
            "accesses": self.accesses,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / self.accesses if self.accesses > 0 else 0,
            "disk_references": self.disk_references
        }
        return stats