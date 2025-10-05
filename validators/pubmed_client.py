# WARNING: This is a copy of the outer pubmed_client.py to support a non-invasive prototype.
# TODO: reorganize so that we can remove this copy.

import httpx

async def get_publication_info(pubids: list[str], request_id: str, timeout: float=4.0) -> dict:
    """
    Fetch publication information from the docmetadata.transltr.io API.

    Args:
        pubids: List of PUBMED and PMCIDs (e.g., ['PMID:36008391', 'PMID:8959199', 'PMC8959199']). Other ids will not work
        request_id: Unique identifier for the request (can be a placeholder for the foreseeable)
        timeout: Request timeout in seconds (default: 4.0)

    Returns:
        { _meta: { n_results: N, processing time, etc. }
          results { "PMID:999": { "abstract": ..., "article_title": ..., etc.}
                    ... }
          not_found: ["blah", ...]
        }

    Raises:
        httpx.TimeoutException: If the request times out
        httpx.RequestError: If there's an error with the request
        httpx.HTTPStatusError: If the response has an HTTP error status
    """

    # If an ID starts with "PMC:" (including the colon), drop the colon so the
    # API sees e.g. "PMC12345" instead of "PMC:12345".
    sanitized_pubids = [
        pid.replace("PMC:", "PMC", 1) if pid.upper().startswith("PMC:") else pid
        for pid in pubids
    ]
    pubids_param = ','.join(sanitized_pubids)
    url = "https://docmetadata.transltr.io/publications"
    params = {
        'pubids': pubids_param,
        'request_id': request_id
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            return response.json()
    except httpx.TimeoutException:
        raise httpx.TimeoutException(f"Request timed out after {timeout}s")
    except httpx.RequestError as e:
        raise httpx.RequestError(f"Request error: {e}")
    except httpx.HTTPStatusError as e:
        raise httpx.HTTPStatusError(f"HTTP error {e.response.status_code}: {e.response.text}", request=e.request, response=e.response)


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(get_publication_info(('PMID:36008391','PMID:36008392','PMC8959199','not_an_id'), 'bob')))
