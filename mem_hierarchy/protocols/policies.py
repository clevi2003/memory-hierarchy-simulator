from abc import abstractmethod, ABC
from mem_hierarchy.data_structures.caches.data_cache import CacheEntry
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult


class WritePolicy(ABC):
    @abstractmethod
    def on_write(self, cache, address):
        pass

class WriteThroughNoWriteAllocate(WritePolicy):
    def on_write(self, cache, address):
        tag, index, offset = cache.parse_address(address)
        cache.writes += 1
        set_dict = cache.sets[index]

        # write hit, update most recently used
        if tag in set_dict:
            cache.write_hits += 1
            cache.get_update_mru(set_dict, tag)
            return AccessResult(cache.name, "W", address, True, tag, index, offset, needs_lower_write=True)
        # write miss, write only to lower level, don't change current cache
        else:
            cache.write_misses += 1
            return AccessResult(cache.name, "W", address, False, tag, index, offset, needs_lower_write=True)

class WriteBackWriteAllocate(WritePolicy):
    def on_write(self, cache, address):
        tag, index, offset = cache.parse_address(address)
        cache.writes += 1
        set_dict = cache.sets[index]

        # write hit, mark as dirty
        if tag in set_dict:
            cache.write_hits += 1
            cache.get_update_mru(set_dict, tag).mark_dirty()
            return AccessResult(cache.name, "W", address, True, tag, index, offset)
        # write miss, allocate in cache and mark as dirty
        else:
            cache.write_misses += 1
            evicted = cache.possibly_evict(address)
            new_entry = CacheEntry(tag, index, address)
            new_entry.mark_dirty()
            set_dict[tag] = new_entry
            return AccessResult(cache.name, "W", address, False, tag, index, offset, allocated=True,
                                evicted_entry=evicted, wrote_back=(evicted and evicted.dirty))


class InclusionPolicy(ABC):
    @abstractmethod
    def on_lower_eviction(self, upper_cache, evicted_entry):
        pass

class InclusivePolicy(InclusionPolicy):
    def on_lower_eviction(self, upper_cache, address):
        upper_cache.invalidate(address)

