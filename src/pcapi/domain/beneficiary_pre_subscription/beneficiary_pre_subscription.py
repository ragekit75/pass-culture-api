from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pcapi.domain.postal_code.postal_code import PostalCode


@dataclass
class BeneficiaryPreSubscription:
    activity: str
    address: str
    application_id: int
    city: str
    civility: str
    date_of_birth: datetime
    email: str
    first_name: str
    last_name: str
    phone_number: str
    postal_code: str
    source: str
    source_id: Optional[int]
    raw_department_code: Optional[str] = None

    @property
    def department_code(self) -> str:
        if self.raw_department_code:
            return self.raw_department_code
        return PostalCode(self.postal_code).get_departement_code()

    @property
    def deposit_source(self) -> str:
        return f"dossier {self.source} [{self.application_id}]"

    @property
    def public_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
