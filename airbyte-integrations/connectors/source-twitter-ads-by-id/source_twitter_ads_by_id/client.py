from typing import Mapping, Any, Final, Optional, Iterable
from twitter_ads.client import Client
from twitter_ads.http import Request
from twitter_ads.enum import ENTITY_STATUS
from twitter_ads.enum import ENTITY, GRANULARITY, METRIC_GROUP, PLACEMENT
from requests.exceptions import HTTPError, ConnectionError, TooManyRedirects


class TwitterClient:
    def __init__(
            self,
            credentials: Mapping[str, Any],
            **kwargs: Mapping[str, Any],
    ) -> None:
        self.consumer_key: Final[str] = credentials['consumer_key']
        self.consumer_secret: Final[str] = credentials['consumer_secret']
        self.access_token: Final[str] = credentials['access_token']
        self.token_secret: Final[str] = credentials['token_secret']
        self.account_id: Final[str] = credentials['account_id']

        self.twitter_client = self.get_auth_client(consumer_key=self.consumer_key,
                                                   consumer_secret=self.consumer_secret,
                                                   access_token=self.access_token,
                                                   token_secret=self.token_secret,
                                                   account_id=self.account_id)

    @staticmethod
    def get_auth_client(consumer_key: str, consumer_secret: str, access_token: str, token_secret: str, account_id: str) -> Client:
        try:
            twitter_client: Final[Any] = Client(
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
            return twitter_client
        except Exception as e:
            raise print('There was an error: {e}') from e

    def get_campaigns(self) -> Optional[list]:
        campaigns: Final[Optional[Any]] = self.twitter_client.accounts(self.account_id)
        ids: Final[list[dict[Optional[str, str]]]] = [{"campaign_id": campaign.id,
                                                       "campaign_name": campaign.name} for campaign in campaigns.campaigns() if
                                                      self.account_id]
        return ids

    def request(self, campaign_ids_list: Iterable[list[str]],
                account_id: Optional[str],
                start_date: str,
                end_date: str):
        resource: Final[str] = f"/11/stats/accounts/{account_id}/"

        full_data: Final[list] = []
        for campaign_ids in campaign_ids_list:
            campaign_id: str = ','.join(campaign_ids)
            metric_groups: str = f'{METRIC_GROUP.ENGAGEMENT},{METRIC_GROUP.BILLING}'
            params: Mapping[str, Any] = {
                "entity": ENTITY.CAMPAIGN,
                "entity_ids": f'{campaign_id}',
                "start_time": start_date,
                "end_time": end_date,
                "granularity": GRANULARITY.DAY,
                "metric_groups": metric_groups,
                "placement": PLACEMENT.ALL_ON_TWITTER
            }

            req: Optional[Request] = Request(client=self.twitter_client,
                                             method="GET",
                                             resource=resource,
                                             params=params)
            try:
                res = req.perform()
                if hasattr(res, 'code') and 200 <= res.code < 300:
                    full_data.append(res.body)
            except (TooManyRedirects, HTTPError, ConnectionError) as errors:
                print(f'There is an error: {errors}')
                raise errors
            except (KeyError, ValueError, TypeError) as base_errors:
                print(f'There is an error: {base_errors}')
                raise base_errors
        return full_data
