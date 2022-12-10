#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#
import sys
from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Iterator, Callable, Final
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from source_twitter_ads_by_id.client import TwitterClient
from datetime import datetime, timedelta, timezone
import logging
import traceback
import requests
import pendulum


# Basic full refresh stream
class TwitterAdsByIdStream(Stream, ABC):
    # url_base = "/11/stats/accounts/"

    primary_key: Any = None

    def __init__(self, twitter_client: TwitterClient, config: Mapping[str, Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self.twitter_client = twitter_client
        self.account_id = config["account_id"]
        self.config = config

    def next_page_token(self, response, current_page_token: Optional[int]) -> Optional[Mapping[str, Any]]:
        return None

    @staticmethod
    def split_list(list_, n):
        """Splits a list by a given number (n) and returns a generator object."""
        list_size = len(list_)
        for sp in range(0, list_size, n):
            yield list_[sp:min(sp + n, list_size)]

    # def parse_response(self, response: sudsobject.Object, **kwargs) -> Iterable[Mapping]:
    #     if response is not None and hasattr(response, self.data_field):
    #         yield from self.client.asdict(response)[self.data_field]
    #
    #     yield from []

    # def send_request(self, params: Mapping[str, Any], method: str, resource: str,
    #                  entity:) -> Mapping[str, Any]:
    #     request_kwargs = {
    #         "service_name": self.service_name,
    #         "customer_id": customer_id,
    #         "account_id": self.account_id,
    #         "operation_name": self.operation_name,
    #         "params": params,
    #     }
    #     request = self.client.request(**request_kwargs)

    def parse_response(self, response, **kwargs) -> Iterable[Mapping]:
        print('this is the response from parse_response')
        if response is not None and hasattr(response, self.data_field):
            yield from self.client.asdict(response)[self.data_field]

        yield from []

    # ids: list = []
    # for campaign_id in stream_slice:
    #     ids.append(campaign_id[0])
    #     print(campaign_id[0])
    #
    # if not ids:
    #     print('Error: A minimum of 1 items must be provided for entity_ids')
    #     sys.exit()
    #
    # yield list(self.split_list(ids, 20))

    def send_request(self, params: Mapping[str, Any], account_id: str) -> Mapping[str, Any]:
        request_kwargs = {
            "account_id": self.config['account_id'],
            "params": params,
        }
        # request = self.twitter_client.request(**request_kwargs)
        request = params
        print('hey')
        print(params)
        # for i in params:
        #     print(i)
        # print(f"this is the params:\n{params}")
        return {"strssss": list(request)}

    def read_records(
            self,
            sync_mode: SyncMode,
            stream_slice: Mapping[dict[str], Any] = None,
            stream_state: Mapping[str, Any] = None,
            **kwargs: Mapping[str, Any],
    ) -> Iterable[Mapping[str, Any]]:
        stream_state = stream_state or {}
        next_page_token = None
        account_id = str(self.account_id) if stream_slice else None

        # yield from stream_slice
        # ids: Final[Optional[list[str]]] = [mini_slice["campaign_id"] for mini_slice in stream_slice]
        #
        # if not ids:
        #     print('Error: A minimum of 1 items must be provided for entity_ids')
        #     sys.exit()
        # campaign_ids_list = list(self.split_list(ids, 20))

        while True:
            params = self.request_params(
                stream_state=stream_state,
                stream_slice=stream_slice,
                next_page_token=next_page_token,
                account_id=account_id,
            )
            # the params are the campaign_id and campaign_name dict
            # for i in params:
            #     print(i)

            # send request function return the actual data we want
            response = self.send_request(params, account_id=account_id)
            print(f'this is the response\n{params}')
            print(f'this is the response\n{response}')
            for record in self.parse_response(response):
                yield record
            #
            # next_page_token = self.next_page_token(response, current_page_token=next_page_token)
            if not next_page_token:
                break

        yield from []


class Campaigns(TwitterAdsByIdStream):
    primary_key: Final[str] = "id"
    use_cache: Final[bool] = True
    data_field: Final[str] = "id"

    def next_page_token(self, response, current_page_token: Optional[int]) -> Optional[Mapping[str, Any]]:
        current_page_token = current_page_token or 0
        if response is not None and hasattr(response, self.data_field):
            return None if self.page_size_limit > len(response[self.data_field]) else current_page_token + 1
        else:
            return None

    def request_params(
            self,
            stream_slice: Mapping[str, Any] = None,
            **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:

        print('campaigns work')
        yield from self.twitter_client.get_campaigns()


class CampaignInsights(TwitterAdsByIdStream):
    primary_key: Final[str] = "id"
    use_cache: Final[bool] = True
    data_field: Final[str] = "account_id"

    def request_params(
            self,
            stream_slice: Mapping[str, Any] = None,
            **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        print('this one 2')
        return {"account_id": self.account_id, "stream_slice": stream_slice}

    def stream_slices(
            self,
            **kwargs: Mapping[str, Any],
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        # a = self.Campaigns().read_records(SyncMode.full_refresh)
        for campaign in Campaigns(self.twitter_client, self.config).read_records(SyncMode.full_refresh):
            print(campaign)

        yield {"account_id": 2}
        # yield from []


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
                twitter_client = TwitterClient(**config)
                return True, twitter_client
            else:
                raise Exception("You have an error with the credentials provided. Please check them.")
        except (KeyError, ValueError, TypeError) as base_errors:
            print(f'There is an error: {base_errors}')
            return False, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        twitter_client = TwitterClient(**config)
        return [Campaigns(twitter_client, config), CampaignInsights(twitter_client, config)]
