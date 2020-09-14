from datetime import datetime
from typing import Callable

from connectors.api_fnac_stocks import get_stocks_from_fnac_api, is_siret_registered


def get_fnac_stock_information(siret: str, last_processed_isbn: str = '', modified_since: str = '',
                               get_fnac_stocks: Callable = get_stocks_from_fnac_api) -> iter:
    api_response = get_fnac_stocks(siret, last_processed_isbn, modified_since)
    return iter(api_response['Stocks'])


def can_be_synchronized_with_fnac(siret: str) -> bool:
    return is_siret_registered(siret)


def read_last_modified_date(date: datetime) -> str:
    return datetime.strftime(date, '%Y-%m-%dT%H:%M:%SZ') if date else ''