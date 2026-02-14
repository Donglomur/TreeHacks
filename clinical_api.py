import requests

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

def fetch_trials(disease, max_results=10):
    params = {
        "filter.overallStatus": "TERMINATED,WITHDRAWN,SUSPENDED",
        "query.cond": disease,
        "pageSize": max_results,
        "sort": "@relevance",
        "fields": (
            "protocolSection.identificationModule"
            "|protocolSection.statusModule"
            "|protocolSection.armsInterventionsModule"
        )
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    data = response.json()
    return data.get("studies", [])
