class Location(object):
    LOCAL = 0
    REMOTE = 1

    def __init__(self, address):
        self.address = address
        if address == "localhost":
            self.location = Location.LOCAL
        else:
            self.location = Location.REMOTE

    def is_local(self):
        return self.location == Location.LOCAL
