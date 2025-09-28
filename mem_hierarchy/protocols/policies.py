from abc import abstractmethod, ABC
from mem_hierarchy.data_structures.caches.data_cache import CacheEntry
from mem_hierarchy.data_structures.result_structures.access_results import AccessResult


class WritePolicy(ABC):
    """
    Abstract base class for write policies
    """
    @abstractmethod
    def on_write(self, cache, address):
        pass

class WriteThroughNoWriteAllocate(WritePolicy):
    """
    Write-through, no write-allocate policy
    """
    def on_write(self, cache, address):
        """
        Handle a write operation according to the write-through, no write-allocate policy
        :param cache: CacheCore or inherited class
        :param address: binary string address to write to
        :return: AccessResult object with the result of the write operation
        """
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
    """
    Write-back, write-allocate policy
    """
    def on_write(self, cache, address):
        """
        Handle a write operation according to the write-back, write-allocate policy
        :param cache: CacheCore or inherited class
        :param address: binary string address to write to
        :return: AccessResult object with the result of the write operation
        """
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
            base = cache._block_base(address)
            evicted = cache.possibly_evict(base)
            new_entry = CacheEntry(tag, index, base)
            new_entry.mark_dirty()
            set_dict[tag] = new_entry
            cache.alloc_on_write_miss += 1
            return AccessResult(cache.name, "W", address, False, tag, index, offset, allocated=True,
                                evicted_entry=evicted, wrote_back=(evicted and evicted.dirty))


class InclusionPolicy(ABC):
    """
    Abstract base class for inclusion policies
    """
    @abstractmethod
    def on_lower_eviction(self, upper_cache, evicted_entry):
        pass

class InclusivePolicy(InclusionPolicy):
    """
    Inclusive cache policy
    """
    def on_lower_eviction(self, upper_cache, address):
        """
        Invalidate the corresponding entry in the upper cache upon eviction from the lower cache
        :param upper_cache: CacheCore or inherited class
        :param address: binary string address that was evicted from the lower cache
        :return: None
        """

        base = upper_cache._block_base(address)
        hit = upper_cache.contains(base)
        was_dirty = False
        if hit:
            was_dirty = upper_cache.is_dirty(base)
            upper_cache.invalidate(base)
        return hit, was_dirty

