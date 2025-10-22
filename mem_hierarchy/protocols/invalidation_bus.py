

class InvalidationBus:
    """
    A simple invalidation bus to notify listeners about page evictions
    """
    def __init__(self):
        self.listeners = []

    def __str__(self):
        print_str = "Invalidation Bus Listeners:\n"
        for listener in self.listeners:
            print_str += f" - {listener.name}\n"
        return print_str

    def _get_level_depth(self, level):
        """
        Number of lower_level hops until None.
        DC -> L2 -> Mem(None)  => DC:2, L2:1, Mem:0
        """
        d = 0
        cur = level
        seen = set()
        while getattr(cur, "lower_level", None) is not None:
            # guard against accidental cycles
            if id(cur) in seen:
                break
            seen.add(id(cur))
            d += 1
            cur = cur.lower_level
        return d

    def register_listener(self, listener):
        """
        Register a listener to the invalidation bus
        :param listener: memory level
        :return: None
        """
        self.listeners.append(listener)
        # sort listeners to make sure higher levels are notified first
        self.listeners.sort(
            key=lambda level: (self._get_level_depth(level), getattr(level, "name", "")),
            reverse=True
        )

    def publish_page_evicted(self, evicted_entry):
        """
        Handles each listener's on_page_evicted method if it exists
        :param evicted_entry: EvictedPageTableEntry
        :return: None
        """
        for listener in self.listeners:
            on_page_evicted = getattr(listener, "on_page_evicted", None)
            if on_page_evicted:
                on_page_evicted(evicted_entry)