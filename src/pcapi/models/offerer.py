""" offerer """
from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import String
from sqlalchemy.orm import relationship

from pcapi.domain.ts_vector import create_ts_vector_and_table_args
from pcapi.models.bank_information import BankInformationStatus
from pcapi.models.db import Model
from pcapi.models.deactivable_mixin import DeactivableMixin
from pcapi.models.has_address_mixin import HasAddressMixin
from pcapi.models.has_thumb_mixin import HasThumbMixin
from pcapi.models.needs_validation_mixin import NeedsValidationMixin
from pcapi.models.pc_object import PcObject
from pcapi.models.providable_mixin import ProvidableMixin
from pcapi.models.user_offerer import UserOfferer
from pcapi.models.versioned_mixin import VersionedMixin


class Offerer(
    PcObject,
    Model,
    HasThumbMixin,
    HasAddressMixin,
    ProvidableMixin,
    NeedsValidationMixin,
    DeactivableMixin,
    VersionedMixin,
):
    id = Column(BigInteger, primary_key=True)

    dateCreated = Column(DateTime, nullable=False, default=datetime.utcnow)

    name = Column(String(140), nullable=False)

    users = relationship("User", secondary="user_offerer")

    siren = Column(
        String(9), nullable=True, unique=True
    )  # FIXME: should not be nullable, is until we have all SIRENs filled in the DB

    def grant_access(self, user):
        if not user:
            return None
        user_offerer = UserOfferer()
        user_offerer.offerer = self
        user_offerer.user = user
        return user_offerer

    @property
    def bic(self):
        return self.bankInformation.bic if self.bankInformation else None

    @property
    def iban(self):
        return self.bankInformation.iban if self.bankInformation else None

    @property
    def demarchesSimplifieesApplicationId(self):
        if not self.bankInformation:
            return None

        can_show_application_id = (
            self.bankInformation.status == BankInformationStatus.DRAFT
            or self.bankInformation.status == BankInformationStatus.ACCEPTED
        )
        if not can_show_application_id:
            return None

        return self.bankInformation.applicationId

    @property
    def nOffers(self):
        n_offers = 0
        for venue in self.managedVenues:
            n_offers += venue.nOffers
        return n_offers

    def append_user_has_access_attribute(self, user_id: int, is_admin: bool) -> None:
        if is_admin:
            self.userHasAccess = True
            return

        authorizations = [user_offer.isValidated for user_offer in self.UserOfferers if user_offer.userId == user_id]

        if authorizations:
            user_has_access_as_editor = authorizations[0]
        else:
            user_has_access_as_editor = False

        self.userHasAccess = user_has_access_as_editor


ts_indexes = [
    ("idx_offerer_fts_name", Offerer.name),
    ("idx_offerer_fts_address", Offerer.address),
    ("idx_offerer_fts_siret", Offerer.siren),
]

(Offerer.__ts_vectors__, Offerer.__table_args__) = create_ts_vector_and_table_args(ts_indexes)
