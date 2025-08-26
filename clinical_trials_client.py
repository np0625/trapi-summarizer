import httpx

async def get_clinical_trials_info(nct_ids: str | list[str], timeout: float = 4.0) -> dict:
    """
    Fetch clinical trial information from the ClinicalTrials.gov API.

    Args:
        nct_ids: Single NCT ID as string or list of NCT IDs (e.g., 'NCT00437242' or ['NCT00437242', 'NCT05279937'])
        timeout: Request timeout in seconds (default: 4.0)

    Returns:
        JSON response from the ClinicalTrials.gov API containing study information

    Raises:
        httpx.TimeoutException: If the request times out
        httpx.RequestError: If there's an error with the request
        httpx.HTTPStatusError: If the response has an HTTP error status
    """

    if isinstance(nct_ids, str):
        nct_ids = [nct_ids]
    nct_ids_param = ','.join(nct_ids)
    url = "https://clinicaltrials.gov/api/v2/studies"
    params = {
        'query.id': nct_ids_param,
        'fields': 'protocolSection,resultsSection,documentSection,hasResults',
        'countTotal': 'true'
        }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            retval = response.json()

            # Check if 'studies' key exists and is a non-empty array
            if 'studies' in retval and isinstance(retval['studies'], list) and len(retval['studies']) > 0:
                # For each study, remove the contactsLocationsModule if it exists
                for study in retval['studies']:
                    if ('protocolSection' in study and
                        isinstance(study['protocolSection'], dict) and
                        'contactsLocationsModule' in study['protocolSection']):
                        del study['protocolSection']['contactsLocationsModule']

            return retval

    except httpx.TimeoutException:
        raise httpx.TimeoutException(f"Request timed out after {timeout}s")
    except httpx.RequestError as e:
        raise httpx.RequestError(f"Request error: {e}")
    except httpx.HTTPStatusError as e:
        raise httpx.HTTPStatusError(f"HTTP error {e.response.status_code}: {e.response.text}", request=e.request, response=e.response)


if __name__ == "__main__":
    import asyncio
    import json

    print(json.dumps(asyncio.run(get_clinical_trials_info('NCT00437242'))))
    print(json.dumps(asyncio.run(get_clinical_trials_info(['NCT00104273','NCT02359552']))))
