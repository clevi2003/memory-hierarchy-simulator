

class InvalidationBus:
    """
    A simple invalidation bus to notify listeners about page evictions
    """
    def __init__(self):
        self.listeners = []

    def register_listener(self, listener):
        """
        Register a listener to the invalidation bus
        :param listener: memory level
        :return: None
        """
        self.listeners.append(listener)

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