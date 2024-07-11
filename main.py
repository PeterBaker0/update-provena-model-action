import os
from config import GithubInputs
import logging
from logging_setup import setup_logger
from provenaclient import ProvenaClient, Config
from provenaclient.auth.manager import LogType, Log
from provenaclient.auth.implementations import DeviceFlow, OfflineFlow
from ProvenaInterfaces.RegistryModels import RecordInfo
from ProvenaInterfaces.RegistryAPI import VersionRequest
from asyncio import run

def get_logger(level: int) -> logging.Logger:
    return setup_logger("update-action-logger", level=level)


def int_to_log_level(level: int) -> LogType:
    try:
        return Log(level)
    except Exception as e:
        print(
            f"Failed to resolve log type for provided log level {level}... Reverting to info default. See https://docs.python.org/3/library/logging.html#levels. Exception {e}."
        )
        return Log.INFO


def parse_inputs() -> GithubInputs:
    try:
        # Parse the inputs
        settings = GithubInputs()
    except Exception as e:
        print(f"Inputs could not be parsed! Validation error. Error: {e}")
        raise Exception("Failed input pydantic validation") from e

    return settings


def set_github_action_output(output_name: str, output_value: str) -> None:
    """
    Sets a github action output

    Args:
        output_name (str): The output name
        output_value (str): The output value
    """
    f = open(os.path.abspath(os.environ["GITHUB_OUTPUT"]), "a")
    f.write(f"{output_name}={output_value}")
    f.close()


def setup_provena_client(settings: GithubInputs) -> ProvenaClient:
    """
    Sets up a provena client from the provided github input information.

    NOTE assumes automated-access is the client id to use.

    Args:
        settings (GithubInputs): The set of parsed inputs from the action.

    Returns:
        ProvenaClient: The instantiated provena client object ready to use.
    """
    log_level = int_to_log_level(settings.input_log_level)
    config = Config(domain=settings.input_domain, realm_name=settings.input_realm_name)
    auth = OfflineFlow(
        config=config,
        client_id="automated-access",
        offline_token=settings.input_offline_token,
        log_level=log_level,
    )
    client = ProvenaClient(auth=auth, config=config)
    return client

async def produce_new_version_of_item(client: ProvenaClient, log: logging.Logger, settings: GithubInputs) -> str:
    """
    
    Takes the client, logger and inputs and produces the new version.

    Args:
        client (ProvenaClient): The client to use
        log (logging.Logger): The logger
        inputs (GithubInputs): The inputs

    Returns:
        str: The ID of the new version of existing item
    """
    # item id
    id = settings.input_item_id

    # fetch the item at generic level
    log.debug(f"Fetching existing item with id {id}.")

    # TODO error handle this
    item = await client.registry.general_fetch_item(
        id=id
    )

    # check subtype
    # TODO error handle this
    assert item.item

    # parse as base record info 
    record_info = RecordInfo.parse_obj(item.item)
    subtype = record_info.item_subtype


    # now use L2 client method to version
    # TODO error handle this
    response = await client._registry_client.version(
        version_request=VersionRequest(
            id=id,
            reason=settings.input_reason
        ),
        item_subtype=subtype
    ) 

    return response.new_version_id


async def update_details_of_item(new_id: str, client: ProvenaClient, log: logging.Logger, settings: GithubInputs) -> None:
    """
    
    Takes the new id, client, logger and inputs and updates the details.

    Merges existing metadata with the provided json values and validates.

    Args:
        client (ProvenaClient): The client to use
        log (logging.Logger): The logger
        inputs (GithubInputs): The inputs

    Returns:
        str: The ID of the new version of existing item
    """

    # get current item
    # TODO handle error
    current_item = (await client.registry.general_fetch_item(id=new_id)).item

    assert current_item




async def main() -> None:
    # parse inputs
    settings = parse_inputs()

    # setup logger
    log = get_logger(level=settings.input_log_level)

    # setup client
    client = setup_provena_client(settings=settings)


if __name__ == "__main__":
    run(main())
