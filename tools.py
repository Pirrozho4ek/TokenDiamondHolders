import os
import requests
from agents import function_tool
from datetime import datetime, timedelta
from typing import Any, Dict
from jinja2 import Template

def _fetch_diamond_holders_data(
    token_address: str,
    days_since_last_balance_update: int = 5,
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
                diamond_holders_list.append({
                    "address": address,
                    "balance": balance_amount,
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
    result = _fetch_diamond_holders_data(
        token_address=token_address,
        days_since_last_balance_update=days_since_last_balance_update,
        limit=limit
    )

    if result["error"]:
        return f"Error: {result['error']}"

    params = {
        "token_address": token_address,
        "days_since_last_balance_update": days_since_last_balance_update,
        "limit": limit
    }

    template = Template("""   
### Query Parameters
- **Token Address**: {{ params.token_address }}
- **Days Since Last Update**: {{ params.days_since_last_balance_update }}
- **Result Limit**: {{ params.limit }}                                   
### Token Info
- **Name**: {{ token_info.Name }}
- **Symbol**: {{ token_info.Symbol }}
{% if data %}
### Top Diamond Holders
{% for holder in data %}
- **Address**: `{{ holder.address }}`  
  **Balance**: {{ holder.balance }}  
  **Last Updated**: {{ holder.last_balance_update }}
{% endfor %}
{% endif %}             
    """.strip())

    result = template.render(token_info=result["token_info"], data=result["data"], params=params)
    print(f"Formated result: {result}")
    return result
