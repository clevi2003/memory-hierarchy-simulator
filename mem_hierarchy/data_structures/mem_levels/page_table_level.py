from .level_core import MemoryLevel

class PageTableLevel(MemoryLevel):
    def __init__(self, page_table, invalidation_bus, lower_level=None):
        super().__init__("Page Table", lower_level)
        self.page_table = page_table
        self.invalidation_bus = invalidation_bus
        self.lower_level = lower_level

    @staticmethod
    def update_line(translation_result, line):
        line.vpn = int(translation_result.vpn, 2)
        line.page_offset = int(translation_result.offset, 2)
        line.ppn = int(translation_result.ppn, 2)
        line.page_table_result = translation_result.hit

    def access(self, operation, address, line):
        translation_info = self.page_table.translate(address)
        self.update_line(translation_info, line)
        if translation_info.evicted_entry:
            self.invalidation_bus.publish_page_evicted(translation_info.evicted_entry)
        physical_address = translation_info.physical_address
        if self.lower_level:
            return self.lower_level.access(operation, physical_address, line)
        result = AccessResult(self.name, operation, address, translation_info.hit, translation_info.vpn, 0,
                              translation_info.offset, evicted_entry=translation_info.evicted_entry)
        return result

    def get_stats(self):
        return self.page_table.get_stats()