from typing import List

from pcapi.models import Offerer


class PaginatedOfferers:
    def __init__(self, offerers: List[Offerer], total: int):
        self.offerers = offerers
        self.total = total
