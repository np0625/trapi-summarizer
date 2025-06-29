import httpx

def get_pub_info(pubids: list[str], request_id: str, timeout: float=4.0) -> dict:
    """
    Fetch publication information from the docmetadata.transltr.io API.

    Args:
        pubids: List of PUBMED IDs (e.g., ['PMID:36008391', 'PMID:8959199']). Other ids will not work
        request_id: Unique identifier for the request (can be a placeholder for the foreseeable)
        timeout: Request timeout in seconds (default: 4.0)

    Returns:
        { _meta: { n_results: N, processing time, etc. }
          results { "PMID:999": { "abstract": ..., "article_title": ..., etc.}
                    ... }
          not_found: ["PMC:999", ...]
        }

    Raises:
        httpx.TimeoutException: If the request times out
        httpx.RequestError: If there's an error with the request
        httpx.HTTPStatusError: If the response has an HTTP error status
    """

    # Join pubids with comma for URL parameter
    pubids_param = ','.join(pubids)

    # Construct the URL with parameters
    url = "https://docmetadata.transltr.io/publications"
    params = {
        'pubids': pubids_param,
        'request_id': request_id
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP error status codes
            return response.json()
    except httpx.TimeoutException:
        raise httpx.TimeoutException(f"Request timed out after {timeout}s")
    except httpx.RequestError as e:
        raise httpx.RequestError(f"Request error: {e}")
    except httpx.HTTPStatusError as e:
        raise httpx.HTTPStatusError(f"HTTP error {e.response.status_code}: {e.response.text}", request=e.request, response=e.response)


if __name__ == "__main__":
    print(get_pub_info(('PMID:36008391','PMID:36008392','PMC:8959199'), 'bob'))