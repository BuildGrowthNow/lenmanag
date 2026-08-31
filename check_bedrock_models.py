"""List Bedrock foundation models available to the configured AWS identity.

Authentication is supplied by the standard AWS credential provider chain, for
example environment variables, an AWS profile, or an attached instance role.
Never place access keys or secrets in source control.
"""

import boto3


def main() -> None:
    client = boto3.client("bedrock", region_name="us-east-1")
    response = client.list_foundation_models()
    for model in response["modelSummaries"]:
        print(f"{model['modelId']}: {model['modelName']}")


if __name__ == "__main__":
    main()
