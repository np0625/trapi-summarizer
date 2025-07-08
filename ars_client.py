import httpx
import json
import os

def fetch_response(pk: str, data_dir: str = './data/'):
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, f"{pk}.json")

    if os.path.exists(output_path):
        return output_path

    url = 'https://ars-prod.transltr.io/ars/api'
    with httpx.Client() as client:
        res = client.get(url + f"/messages/{pk}?trace=y")
        merged_version = res.json().get('merged_version', None)
        if not merged_version:
            raise Exception(f"No merged version for ${pk}")
        res = client.get(url + f"/messages/{merged_version}")

        # Save the response JSON to a file
        with open(output_path, "w") as f:
            json.dump(res.json(), f)

    return output_path

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Fetch ARS response by PK')
    parser.add_argument('pk', help='Primary key of the ARS response to fetch')
    parser.add_argument('-d', '--data-dir', default='./data/',
                       help='Directory to store response data (default: ./data/)')

    args = parser.parse_args()

    try:
        output_path = fetch_response(args.pk, args.data_dir)
        print(f"Response saved to: {output_path}")
    except Exception as e:
        print(f"Error fetching response: {e}")
        exit(1)