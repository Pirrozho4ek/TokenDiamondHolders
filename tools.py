import os
import requests
from agents import function_tool
from datetime import datetime, timedelta
from typing import Any, Dict
from web3 import Web3

def _validate_ethereum_address(address: str) -> str:
    """
    Validates if the provided address is a valid Ethereum address.
    Returns a string with validation result.
    """
    try:
        # Проверяем, что адрес не пустой
        if not address or not isinstance(address, str):
            return "Error: Address is required and must be a string"

        # Убираем пробелы и приводим к нижнему регистру
        address = address.strip().lower()

        # Проверяем базовый формат (0x + 40 hex символов)
        if not address.startswith('0x') or len(address) != 42:
            return "Error: Invalid address format. Must start with '0x' and be 42 characters long"

        # Проверяем, что все символы после 0x являются hex
        if not all(c in '0123456789abcdef' for c in address[2:]):
            return "Error: Address contains invalid characters. Only hex characters allowed after '0x'"

        # Проверяем, что это не нулевой адрес
        if address == '0x0000000000000000000000000000000000000000':
            return "Error: Zero address is not allowed"

        # Конвертируем в checksum адрес
        try:
            checksum_address = Web3.to_checksum_address(address)
            return f"Valid Ethereum address: {checksum_address}"
        except Exception as e:
            return f"Error: Invalid address format - {str(e)}"

    except Exception as e:
        return f"Error: {str(e)}"

def _fetch_diamond_holders_data(
    token_address: str,
    days_since_last_balance_update: int = 30,
    limit: int = 10
) -> Dict[str, Any]:
    BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")
    if not BITQUERY_API_KEY:
        return {"error": "BITQUERY_API_KEY not set in environment variables.", "data": None}

    BITQUERY_GRAPHQL_URL = os.getenv("BITQUERY_GRAPHQL_URL", "https://graphql.bitquery.io/")

    today_date = datetime.utcnow().date()
    cutoff_date = today_date - timedelta(days=days_since_last_balance_update)

    query = """
        query(
            $tokenAddress: String!,
            $lastUpdateBeforeDate: String!,
            $snapshotDate: String!,
            $limit: Int!
        ) {
          EVM(dataset: archive) {
            TokenHolders(
              date: $snapshotDate
              tokenSmartContract: $tokenAddress
              where: {
                BalanceUpdate: {
                  LastDate: { before: $lastUpdateBeforeDate }
                }
              }
              limit: { count: $limit }
              orderBy: { descending: Balance_Amount }
            ) {
              Holder {
                Address
              }
              Balance {
                Amount
              }
              BalanceUpdate {
                LastDate
              }
              Currency {
                Name
                Symbol
              }
            }
          }
        }
    """

    variables = {
        "tokenAddress": token_address,
        "lastUpdateBeforeDate": cutoff_date.isoformat(),
        "snapshotDate": today_date.isoformat(),
        "limit": limit
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BITQUERY_API_KEY}"
    }

    try:
        response = requests.post(BITQUERY_GRAPHQL_URL, headers=headers, json={'query': query, 'variables': variables})
        print(f"Response: {response.text}")
        response.raise_for_status()
        data = response.json()

        if 'errors' in data:
            return {"error": f"BitQuery GraphQL error: {data['errors']}", "data": data['errors']}

        token_holders_data = data.get('data', {}).get('EVM', {}).get('TokenHolders', [])

        diamond_holders_list = []
        token_info = {}

        for holder_info in token_holders_data:
            address = holder_info.get('Holder', {}).get('Address')
            balance_amount = holder_info.get('Balance', {}).get('Amount')
            last_update_date = holder_info.get('BalanceUpdate', {}).get('LastDate')

            if not token_info:
                token_info["Name"] = holder_info.get('Currency', {}).get('Name')
                token_info["Symbol"] = holder_info.get('Currency', {}).get('Symbol')

            if address and balance_amount:
                try:
                    # Округляем баланс до 2 знаков после запятой
                    rounded_balance = round(float(balance_amount), 2)
                except (ValueError, TypeError):
                    # Если не удалось преобразовать в число, оставляем как есть
                    rounded_balance = balance_amount

                diamond_holders_list.append({
                    "address": address,
                    "balance": rounded_balance,
                    "last_balance_update": last_update_date
                })

        return {"error": None, "token_info": token_info, "data": diamond_holders_list}

    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching diamond holder data from BitQuery: {e}", "data": None}


@function_tool
def get_diamond_holders(
    token_address: str,
    days_since_last_balance_update: int = 5,
    limit: int = 10
) -> str:
    # Сначала валидируем адрес
    validation_result = _validate_ethereum_address(token_address)
    if not validation_result.startswith("Valid Ethereum address"):
        return validation_result

    # Извлекаем checksum адрес из результата валидации
    checksum_address = validation_result.split(": ")[1]

    result = _fetch_diamond_holders_data(
        token_address=checksum_address,
        days_since_last_balance_update=days_since_last_balance_update,
        limit=limit
    )

    if result["error"]:
        return f"Error: {result['error']}"

    return str({
        "token_info": result["token_info"],
        "diamond_holders": result["data"],
        "query_params": {
            "token_address": checksum_address,
            "days_since_last_balance_update": days_since_last_balance_update,
            "limit": limit
        }
    })
