

class InvalidationBus:
    def __init__(self):
        self.listeners = []

    def register_listener(self, listener):
        self.listeners.append(listener)

    def publish_page_evicted(self, evicted_entry):
        for listener in self.listeners:
            on_page_evicted = getattr(listener, "on_page_evicted", None)
            if on_page_evicted:
                on_page_evicted(evicted_entry)