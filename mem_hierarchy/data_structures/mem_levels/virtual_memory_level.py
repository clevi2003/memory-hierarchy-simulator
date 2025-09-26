from .level_core import MemoryLevel

class VirtualMemoryLevel(MemoryLevel):
    def __init__(self, page_table, invalidation_bus, lower_level=None, dtlb_level=None):
        super().__init__("Page Table", lower_level)
        self.page_table = page_table
        self.invalidation_bus = invalidation_bus
        self.lower_level = lower_level
        self.dtlb_level = dtlb_level

    @staticmethod
    def update_line(translation_result, line):
        # line.vpn = int(translation_result.vpn, 2)
        # line.page_offset = int(translation_result.offset, 2)
        # line.ppn = int(translation_result.ppn, 2)
        line.vpn = translation_result.vpn
        line.page_offset = translation_result.offset
        line.ppn = translation_result.ppn
        line.page_table_result = translation_result.hit


    def update_dtlb_hit_line(self, virtual_address, physical_address, line):
        page_offset, vpn = self.page_table.parse_address(virtual_address)
        _, ppn = self.page_table.parse_address(physical_address)
        # print("_:", _)
        # print("_ == physical adress:", _ == physical_address)
        # print("len physical address:", len(physical_address))
        line.vpn = int(vpn, 2)
        line.page_offset = int(page_offset, 2)
        line.ppn = int(ppn, 2)

    def _manage_translation(self, address, line):
        translation_info = self.page_table.translate(address)
        self.update_line(translation_info, line)
        if translation_info.evicted_entry:
            self.invalidation_bus.publish_page_evicted(translation_info.evicted_entry)
        return translation_info

    def access(self, operation, address, line):
        if self.dtlb_level:
            cached_translation = self.dtlb_level.access("R", address, line)
            if cached_translation.hit:
                physical_address = cached_translation.addr
                self.update_dtlb_hit_line(address, physical_address, line)
                translation_info = self._manage_translation(address, line)
                physical_address_translated = translation_info.physical_address
                print("cached address:", physical_address, len(physical_address))
                print("translated address:", physical_address_translated, len(physical_address_translated))
                print("addresses match:", physical_address == physical_address_translated)


            else:
                translation_info = self._manage_translation(address, line)
                physical_address = translation_info.physical_address
                self.dtlb_level.access("W", address, translation_info)
                self.update_line(translation_info, line)
                if translation_info.evicted_entry:
                    self.invalidation_bus.publish_page_evicted(translation_info.evicted_entry)
        else:
            translation_info = self._manage_translation(address, line)
            physical_address = translation_info.physical_address
            self.update_line(translation_info, line)
            if translation_info.evicted_entry:
                self.invalidation_bus.publish_page_evicted(translation_info.evicted_entry)
        return self.lower_level.access(operation, physical_address, line)

    def get_stats(self):
        return self.page_table.get_stats()