import httpx

async def get_nmf_analysis(genes: list[str], timeout: float = 10.0) -> dict:
    """
    Fetch gene NMF (Non-negative Matrix Factorization) analysis from the genetics provider API.

    Args:
        genes: List of gene names for analysis
        timeout: Request timeout in seconds (default: 10.0)

    Returns:
        Dict containing NMF analysis results with gene groupings and factors

    Raises:
        httpx.TimeoutException: If the request times out
        httpx.RequestError: If there's an error with the request
        httpx.HTTPStatusError: If the response has an HTTP error status
    """
    url = "https://translator.broadinstitute.org/genetics_provider/bayes_gene/pigean"

    # build the input payload
    json_input = {
        "p_value": "0.5",
        "max_number_gene_sets": 150,
        "gene_sets": "default",
        "enrichment_analysis": "hypergeometric",
        "generate_factor_labels": False,
        "calculate_gene_scores": True,
        "exclude_controls": True,
        "genes": genes
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=json_input)
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
    import json
    # Sample test genes
    test_genes = ["BRCA1", "BRCA2", "TP53", "ATM"]
    print(json.dumps(asyncio.run(get_nmf_analysis(test_genes))))
