#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#
import json
import sys
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple, Iterator, Callable, Final
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from source_twitter_ads_by_id.client import TwitterClient
from datetime import datetime, timedelta, timezone, date
import logging
import traceback
import requests
import pendulum


# Basic full refresh stream
class TwitterAdsByIdStream(Stream, ABC):
    primary_key: Any = None

    def __init__(self, twitter_client: TwitterClient, config: Mapping[str, Any], **kwargs) -> None:
        super().__init__(**kwargs)
        self.twitter_client = twitter_client
        self.account_id = config['credentials']["account_id"]
        self.config = config

    @property
    @abstractmethod
    def data_field(self) -> str:
        """
        Specifies root object name in a stream response
        """
        pass

    def next_page_token(self, response, current_page_token: Optional[int]) -> Optional[Mapping[str, Any]]:
        return None

    @staticmethod
    def split_list(list_, n):
        """Splits a list by a given number (n) and returns a generator object."""
        list_size = len(list_)
        for sp in range(0, list_size, n):
            yield list_[sp:min(sp + n, list_size)]

    def parse_response(self, response, **kwargs) -> Iterable[Mapping]:
        print('this is 2nd')
        yield response

    def send_request(self,
                     campaign_ids_list: Optional[Iterable[list[str]]],
                     start_date: str,
                     end_date: str) -> Mapping[str, Any]:
        try:
            request_kwargs: Final[Mapping[str, Any]] = {
                "campaign_ids_list": campaign_ids_list,
                "account_id": self.account_id,
                "start_date": start_date,
                "end_date": end_date
            }

            request: Final[Optional[Any]] = self.twitter_client.request(**request_kwargs)
            if request is not None:
                for _ in request:
                    return _
        except (KeyError, ValueError, TypeError) as base_errors:
            print(f'There is an error: {base_errors}')
            raise base_errors

    def read_records(
            self,
            sync_mode: SyncMode,
            stream_slice: Mapping[str, Any] = None,
            stream_state: Mapping[str, Any] = None,
            **kwargs: Mapping[str, Any],
    ) -> Iterable[Mapping[str, Any]]:
        stream_state = stream_state or {}
        next_page_token = None
        account_id = str(self.account_id) if stream_slice else None
        start_date = str(self.config['reports_start_date'])
        end_date = str(self.config['reports_end_date'])
        print(stream_slice)

        while True:
            params = self.request_params(
                stream_state=stream_state,
                stream_slice=stream_slice,
                next_page_token=next_page_token
            )

            if 'campaign_ids' in params:
                campaign_ids_list = params['campaign_ids']
                response = self.send_request(campaign_ids_list=params['campaign_ids'],
                                             start_date=start_date,
                                             end_date=end_date)
                response["campaign_data"] = params['campaign_data']
                yield from self.parse_response(response)
                next_page_token = self.next_page_token(response, current_page_token=next_page_token)

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
            stream_state: Mapping[str, Any] = None,
            **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:

        params = self.twitter_client.get_campaigns()
        ids: Optional[list[str]] = [campaign_id["campaign_id"] for campaign_id in params]
        if len(ids) == 0:
            print('Error: A minimum of 1 items must be provided for entity_ids')
            sys.exit()

        campaign_ids_list: Optional[list[list[str]]] = list(self.split_list(ids, 20))
        print('this is 1st')
        return {"campaign_ids": campaign_ids_list, "campaign_data": params}


# class CampaignInsights(TwitterAdsByIdStream):
#     primary_key: Final[str] = "id"
#     use_cache: Final[bool] = True
#     data_field: Final[str] = "id"
#
#     def request_params(
#             self,
#             stream_slice: Mapping[str, Any] = None,
#             stream_state: Mapping[str, Any] = None,
#             **kwargs: Mapping[str, Any],
#     ) -> MutableMapping[str, Any]:
#         print('this is last')
#
#         return {"stream_slice": stream_slice}
#
#     def stream_slices(
#             self,
#             **kwargs: Mapping[str, Any],
#     ) -> Iterable[Optional[Mapping[str, Any]]]:
#         campaigns = Campaigns(self.twitter_client, self.config)
#
#         for campaign in campaigns.read_records(SyncMode.full_refresh,
#                                                stream_slice={"account_id": self.account_id,
#                                                              "start_date": self.config["reports_start_date"],
#                                                              "end_date": self.config["reports_end_date"]}):
#             print('this is 3rd')
#             # yield {"campaign_id": [i['id'] for i in campaign["data"]],
#             #        "account_id": self.account_id,
#             #        "start_date": self.config["reports_start_date"],
#             #        "end_date": self.config["reports_end_date"]}
#             yield campaign
#         yield from []


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
        if 'credentials' in config and "account_id" in config['credentials'] and config['credentials']["account_id"].strip():
            return config['credentials']["account_id"]

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
        # return [CampaignInsights(twitter_client, config)]
        return [Campaigns(twitter_client, config)]
