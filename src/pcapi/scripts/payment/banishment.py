from typing import List

from pcapi.domain.payments import UnmatchedPayments
from pcapi.domain.payments import apply_banishment
from pcapi.repository import repository
from pcapi.repository.payment_queries import find_payments_by_message
from pcapi.utils.logger import logger


def parse_raw_payments_ids(raw_ids: str) -> List[int]:
    return [int(id_) for id_ in raw_ids.split(",")]


def do_ban_payments(message_id: str, payment_ids_to_ban: List[int]):
    matching_payments = find_payments_by_message(message_id)

    try:
        banned_payments, retry_payments = apply_banishment(matching_payments, payment_ids_to_ban)
    except UnmatchedPayments as e:
        logger.exception(
            "Le message %s ne contient pas les paiements : %s. Aucun paiement n'a été mis à jour.",
            message_id,
            e.payment_ids,
        )
    else:
        if banned_payments:
            repository.save(*(banned_payments + retry_payments))

        logger.info("Paiements bannis : %s ", [p.id for p in banned_payments])
        logger.info("Paiements à réessayer : %s ", [p.id for p in retry_payments])
