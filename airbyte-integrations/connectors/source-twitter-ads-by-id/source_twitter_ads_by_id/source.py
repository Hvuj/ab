#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Iterator, Callable
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator
from twitter_ads.client import Client
from twitter_ads.campaign import Campaign
from twitter_ads.enum import ENTITY_STATUS
from datetime import datetime, timedelta, timezone
import logging
import traceback
import requests
import pendulum


# Basic full refresh stream
class TwitterAdsByIdStream(HttpStream, ABC):

    def __init__(self, client: Client, config: Mapping[str, Any]) -> None:
        super().__init__()
        self.client = client
        self.config = config

    url_base = "/11/stats/accounts/"

    def next_page_token(self) -> Optional[Mapping[str, Any]]:
        return None

    def request_params(
            self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        """
        TODO: Override this method to define any query parameters to be set. Remove this method if you don't need to define request params.
        Usually contains common params e.g. pagination size etc.
        """
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        TODO: Override this method to define how a response is parsed.
        :return an iterable containing each record in the response
        """
        yield {}


class TwitterClient:
    def __init__(
            self,
            consumer_key: str,
            consumer_secret: str,
            access_token: str = None,
            token_secret: str = None,
            account_id: str = None,
            reports_start_date: str = None,
            **kwargs: Mapping[str, Any],
    ) -> None:
        self.consumer_key = consumer_key
        self.client_secret = consumer_secret
        self.access_token = access_token
        self.token_secret = token_secret
        self.account_id = account_id

        self.client = self.get_auth_client(consumer_key=consumer_key,
                                           consumer_secret=consumer_secret,
                                           access_token=access_token,
                                           token_secret=token_secret)
        # self.campaigns = self._get_access_token()
        # self.reports_start_date = pendulum.parse(reports_start_date).astimezone(tz=timezone.utc)

    @staticmethod
    def get_auth_client(consumer_key: str, consumer_secret: str, access_token: str, token_secret: str) -> Client:
        try:
            return Client(
                consumer_key,
                consumer_secret,
                access_token,
                token_secret,
                options={
                    'handle_rate_limit': True,
                    'retry_max': 3,
                    'retry_delay': 5000,
                    'retry_on_status': list(range(300, 600)),
                    'retry_on_timeouts': True,
                    'timeout': (1.0, 3.0)
                })
        except Exception as e:
            raise print('There was an error: {e}') from e


class Campaigns(TwitterAdsByIdStream):
    primary_key = "account_id"

    def send_request(self, query: str, customer_id: str) -> Iterator[Campaign]:
        client = self.client
        account_id = self.account_id
        yield from client.accounts(account_id)

    def path(
            self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        """
        TODO: Override this method to define the path this stream corresponds to. E.g. if the url is https://example-api.com/v1/customers then this
        should return "customers". Required.
        """
        return "customers"


# Basic incremental stream
class IncrementalTwitterAdsByIdStream(TwitterAdsByIdStream, ABC):
    """
    TODO fill in details of this class to implement functionality related to incremental syncs for your connector.
         if you do not need to implement incremental sync for any streams, remove this class.
    """

    # TODO: Fill in to checkpoint stream reads after N records. This prevents re-reading of data if the stream fails for any reason.
    state_checkpoint_interval = None

    @property
    def cursor_field(self) -> str:
        """
        TODO
        Override to return the cursor field used by this stream e.g: an API entity might always use created_at as the cursor field. This is
        usually id or date based. This field's presence tells the framework this in an incremental stream. Required for incremental.

        :return str: The name of the cursor field.
        """
        return []

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        """
        Override to determine the latest state after reading the latest record. This typically compared the cursor_field from the latest record and
        the current state and picks the 'most' recent cursor. This is how a stream's state is determined. Required for incremental.
        """
        return {}


class SourceTwitterAdsById(AbstractSource):

    @staticmethod
    def get_account_id(config: Mapping[str, Any]) -> MutableMapping[str, Any]:
        if "account_id" in config and config["account_id"].strip():
            return config["account_id"]

    def check_connection(self, logger: logging.Logger, config: Mapping[str, Any]) -> Tuple[bool, any]:
        logger.info("Checking the config")
        try:
            if account_id := self.get_account_id(config=config):
                account = TwitterClient(**config).client.accounts(account_id)
                return True, None
            else:
                raise Exception("You have an error with the credentials provided. Please check them.")
        except (KeyError, ValueError, TypeError) as base_errors:
            print(f'There is an error: {base_errors}')
            return False, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        client = TwitterClient(**config)
        return [Campaigns(client, config)]
