import math
from pprint import pprint

def is_power_of_two(n):
    """Check if a number is a power of two. uses bit operations."""
    return n > 0 and (n & (n - 1)) == 0

def safe_log_2(n):
    """Compute the base-2 logarithm of a number, ensuring the number is a power of two."""
    if not is_power_of_two(n):
        raise ValueError("Input must be a power of two.")
    return int(math.log2(n))

def safe_enabled(enabled):
    """Ensure that the enabled flag is y or n and then make it a boolean."""
    enabled = enabled.strip().lower()
    if enabled not in {'y', 'n'}:
        raise ValueError("Enabled flag must be 'y' or 'n'.")
    return enabled == 'y'


class BitCounts:
    def __init__(self):
        # initialize them all to zero to start
        # data table lookup buffer
        self.dtlb_tag_bits = 0
        self.dtlb_index_bits = 0
        self.dtlb_offset_bits = 0
        # DC
        self.dc_tag_bits = 0
        self.dc_index_bits = 0
        self.dc_offset_bits = 0
        # L2 cache
        self.l2_tag_bits = 0
        self.l2_index_bits = 0
        self.l2_offset_bits = 0
        # VM
        self.vpn_bits = 0
        self.page_offset_bits = 0
        self.ppn_bits = 0

class CacheConfig:
    def __init__(self, num_sets, associativity, line_size, policy, enabled=True):
        self.num_sets = num_sets
        self.associativity = associativity
        self.line_size = line_size
        self.policy = policy
        self.enabled = enabled

class PageTableConfig:
    def __init__(self, n_virtual_pages, n_physical_pages, page_size):
        self.n_virtual_pages = n_virtual_pages
        self.n_physical_pages = n_physical_pages
        self.page_size = page_size

class DTLBConfig:
    def __init__(self, num_sets, associativity, enabled=True):
        self.num_sets = num_sets
        self.associativity = associativity
        self.enabled = enabled

class Config:
    def __init__(self,
                 virtual_addresses,
                 dtlb_enabled,
                 l2_enabled,
                 dtlb_cfg,
                 pt_cfg,
                 dc_cfg,
                 l2_cfg=None):
        self.virtual_addresses = virtual_addresses
        self.dtlb_enabled = dtlb_enabled
        self.l2_enabled = l2_enabled
        self.dtlb = dtlb_cfg
        self.pt = pt_cfg
        self.dc = dc_cfg
        self.l2 = l2_cfg if self.l2_enabled else None
        self.address_bits = 0  # fixed at 32 bits
        self.bits = BitCounts()
        self.validate()
        self.derive_bits()

    @classmethod
    def from_config_file(cls, filepath):
        # parse out config info
        with open(filepath) as infile:
            raw_lines = [ln.rstrip("\n") for ln in infile]

        # Section names exactly as in the file
        section_headers = {
            "Data TLB configuration": "dtlb",
            "Page Table configuration": "pt",
            "Data Cache configuration": "dc",
            "L2 Cache configuration": "l2",
        }

        # Buckets for per-section key/values
        sections = {
            "dtlb": {},
            "pt": {},
            "dc": {},
            "l2": {},
            "toggles": {},  # for bottom y/n switches
        }

        current = None
        for ln in raw_lines:
            line = ln.strip()
            if not line:
                # blank line ends key-value streak but not strictly needed
                continue

            # Enter a new section?
            if line in section_headers:
                current = section_headers[line]
                continue

            # Bottom toggles (appear after sections)
            if line.lower().startswith("virtual addresses:") \
                    or line.lower().startswith("tlb:") \
                    or line.lower().startswith("l2 cache:"):
                key, val = line.split(":", 1)
                sections["toggles"][key.strip()] = val.strip()
                continue

            # Regular "Key: value" inside a section
            if ":" in line and current is not None:
                key, val = line.split(":", 1)
                sections[current][key.strip()] = val.strip()
                continue

        # DTLB config info
        dtlb_num_sets = int(sections["dtlb"].get("Number of sets", 0))
        dtlb_associativity = int(sections["dtlb"].get("Set size", 1))
        dtlb_enabled = safe_enabled(sections["toggles"]["TLB"])

        # Page table config info
        n_virtual_pages = int(sections["pt"].get("Number of virtual pages", 0))
        n_physical_pages = int(sections["pt"].get("Number of physical pages", 0))
        page_size = int(sections["pt"].get("Page size", 0))

        #L2 cache config info
        l2_num_sets = int(sections["l2"].get("Number of sets", 0))
        l2_associativity = int(sections["l2"].get("Set size", 1))
        l2_line_size = int(sections["l2"].get("Line size", 0))
        l2_policy = safe_enabled(sections["l2"]["Write through/no write allocate"])
        l2_enabled = safe_enabled(sections["toggles"]["L2 cache"])

        # DC config info
        DC_num_sets = int(sections["dc"].get("Number of sets", 0))
        DC_associativity = int(sections["dc"].get("Set size", 1))
        DC_line_size = int(sections["dc"].get("Line size", 0))
        DC_policy = safe_enabled(sections["dc"]["Write through/no write allocate"])

        # Virtual address config info
        virtual_addresses_enabled = safe_enabled(sections["toggles"]["Virtual addresses"])

        # make config class, validate it, and derive bit info
        config = cls(
            virtual_addresses=virtual_addresses_enabled,
            dtlb_enabled=dtlb_enabled,
            l2_enabled=l2_enabled,
            dtlb_cfg=DTLBConfig(dtlb_num_sets, dtlb_associativity, dtlb_enabled),
            pt_cfg=PageTableConfig(n_virtual_pages, n_physical_pages, page_size),
            dc_cfg=CacheConfig(DC_num_sets, DC_associativity, DC_line_size, DC_policy, enabled=True),
            l2_cfg=CacheConfig(l2_num_sets, l2_associativity, l2_line_size, l2_policy, enabled=l2_enabled)
        )
        return config

    def _validate_dtlb(self):
        # max DTLB sets is 256
        if self.dtlb.num_sets < 1 or self.dtlb.num_sets > 256:
            raise ValueError("DTLB number of sets must be between 1 and 256.")
        # max associativity is 8 for DTLB
        if self.dtlb.associativity < 1 or self.dtlb.associativity > 8:
            raise ValueError("DTLB associativity must be between 1 and 8.")
        # number of sets and line size for DTLB must be powers of two
        if not is_power_of_two(self.dtlb.num_sets):
            raise ValueError("DTLB number of sets must be a power of two.")

    def _validate_dc(self):
        # max DC sets is 8192
        if self.dc.num_sets < 1 or self.dc.num_sets > 8192:
            raise ValueError("DC number of sets must be between 1 and 8192.")
        # max associativity is 8 for L2, DC
        if self.dc.associativity < 1 or self.dc.associativity > 8:
            raise ValueError("DC associativity must be between 1 and 8.")
        # number of sets and line size for DC must be powers of two
        if not is_power_of_two(self.dc.num_sets):
            raise ValueError("DC number of sets must be a power of two.")
        if not is_power_of_two(self.dc.line_size):
            raise ValueError("DC line size must be a power of two.")
        # min data line size for DC is 8
        if self.dc.line_size < 8:
            raise ValueError("DC line size must be at least 8 bytes.")

    def _validate_pt(self):
        # max number of virtual pages is 8192
        if self.pt.n_virtual_pages < 1 or self.pt.n_virtual_pages > 8192:
            raise ValueError("Number of virtual pages must be between 1 and 8192.")
        # max number of physical pages is 1024
        if self.pt.n_physical_pages < 1 or self.pt.n_physical_pages > 1024:
            raise ValueError("Number of physical pages must be between 1 and 1024.")
        # num virtual pages and page size must be powers of two
        if not is_power_of_two(self.pt.n_virtual_pages):
            raise ValueError("Number of virtual pages must be a power of two.")
        if not is_power_of_two(self.pt.page_size):
            raise ValueError("Page size must be a power of two.")
        # max reference address length is 32 bits
        if self.virtual_addresses and (self.pt.n_virtual_pages * self.pt.page_size) > 2**32:
            raise ValueError("Maximum virtual address space exceeded (2^32).")

    def _validate_l2(self):
        # max associativity is 8 for L2
        if self.l2.associativity < 1 or self.l2.associativity > 8:
            raise ValueError("L2 associativity must be between 1 and 8.")
        # data line size for L2 must be at least as large as DC line size
        if self.l2.line_size < self.dc.line_size:
            raise ValueError("L2 line size must be at least as large as DC line size.")

    def validate(self):
        # address bits must be <= 32
        if self.address_bits > 32:
            raise ValueError("Address bits exceed 32 bits.")
        if self.dtlb_enabled:
            self._validate_dtlb()
        self._validate_dc()
        self._validate_pt()
        if self.l2_enabled:
            self._validate_l2()

    @staticmethod
    def _bit_slicer(addr_bits, sets=None, line_size=None):
        index_bits = safe_log_2(sets) if sets is not None else 0
        offset_bits = safe_log_2(line_size) if line_size is not None else 0
        tag_bits = addr_bits - index_bits - offset_bits
        if tag_bits < 0:
            raise ValueError(
                f"Invalid bit configuration: negative tag bits "
                f"(addr_bits={addr_bits}, index_bits={index_bits}, offset_bits={offset_bits})"
            )
        return {"tag": tag_bits, "index": index_bits, "offset": offset_bits}

    def derive_bits(self):
        # virtual memory bits
        if self.virtual_addresses:
            self.bits.page_offset_bits = safe_log_2(self.pt.page_size)
            self.bits.vpn_bits = safe_log_2(self.pt.n_virtual_pages)
            self.bits.ppn_bits = safe_log_2(self.pt.n_physical_pages)
            self.address_bits = safe_log_2(self.pt.n_virtual_pages) + safe_log_2(self.pt.page_size)

        else:
            self.bits.page_offset_bits = 0
            self.bits.vpn_bits = 0
            self.address_bits = safe_log_2(self.pt.n_physical_pages) + safe_log_2(self.pt.page_size)

        # DTLB bits slice the VPN, not the full 32-bit VA
        if self.dtlb_enabled and self.virtual_addresses:
            dtlb_bits = self._bit_slicer(
                addr_bits=self.bits.vpn_bits,
                sets=self.dtlb.num_sets,
                line_size=None
            )
            self.bits.dtlb_tag_bits = dtlb_bits["tag"]
            self.bits.dtlb_index_bits = dtlb_bits["index"]
            self.bits.dtlb_offset_bits = 0
        else:
            self.bits.dtlb_tag_bits = 0
            self.bits.dtlb_index_bits = 0
            self.bits.dtlb_offset_bits = 0

        # DC bits slice 32 bit address
        dc_bits = self._bit_slicer(
            addr_bits=self.address_bits,  # 32
            sets=self.dc.num_sets,
            line_size=self.dc.line_size
        )
        self.bits.dc_tag_bits = dc_bits["tag"]
        self.bits.dc_index_bits = dc_bits["index"]
        self.bits.dc_offset_bits = dc_bits["offset"]

        # l2 cache slice 32 bit address
        if self.l2_enabled:
            l2_bits = self._bit_slicer(
                addr_bits=self.address_bits,  # 32
                sets=self.l2.num_sets,
                line_size=self.l2.line_size
            )
            self.bits.l2_tag_bits = l2_bits["tag"]
            self.bits.l2_index_bits = l2_bits["index"]
            self.bits.l2_offset_bits = l2_bits["offset"]

    def __str__(self):
        print_str = ""
        print_str += f"Data TLB contains {self.dtlb.num_sets} sets.\n"
        print_str += f"Each set contains {self.dtlb.associativity} entries.\n"
        print_str += f"Number of bits used for the index is {self.bits.dtlb_index_bits}.\n\n"
        print_str += f"Number of virtual pages is {self.pt.n_virtual_pages}.\n"
        print_str += f"Number of physical pages is {self.pt.n_physical_pages}.\n"
        print_str += f"Each page contains {self.pt.page_size} bytes.\n"
        print_str += f"Number of bits used for the page table index is {self.bits.vpn_bits}.\n"
        print_str += f"Number of bits used for the page offset is {self.bits.page_offset_bits}.\n\n"
        print_str += f"D-cache contains {self.dc.num_sets} sets.\n"
        print_str += f"Each set contains {self.dc.associativity} entries.\n"
        print_str += f"Each line is {self.dc.line_size} bytes.\n"
        print_str += f"The cache uses a {'no ' if self.dc.policy else ''}write allocate and {'write-through' if self.dc.policy else 'write-back'} policy.\n"
        print_str += f"Number of bits used for the index is {self.bits.dc_index_bits}.\n"
        print_str += f"Number of bits used for the offset is {self.bits.dc_offset_bits}.\n\n"
        if self.l2_enabled:
            print_str += f"L2 cache contains {self.l2.num_sets} sets.\n"
            print_str += f"Each set contains {self.l2.associativity} entries.\n"
            print_str += f"Each line is {self.l2.line_size} bytes.\n"
            print_str += f"The cache uses a {'no ' if self.l2.policy else ''}write allocate and {'write-through' if self.l2.policy else 'write-back'} policy.\n"
            print_str += f"Number of bits used for the index is {self.bits.l2_index_bits}.\n"
            print_str += f"Number of bits used for the offset is {self.bits.l2_offset_bits}.\n\n"
        if self.virtual_addresses:
            print_str += "The addresses read in are virtual addresses."
        else:
            print_str += "The addresses read in are physical addresses."
        print_str += "\n"
        return print_str



