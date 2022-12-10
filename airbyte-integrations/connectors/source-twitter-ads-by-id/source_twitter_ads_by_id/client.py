import sys
from typing import Mapping, Any, Final, Optional
from twitter_ads.client import Client
from twitter_ads.http import Request
from twitter_ads.enum import ENTITY_STATUS
from twitter_ads.enum import ENTITY, GRANULARITY, METRIC_GROUP, PLACEMENT


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

        self.twitter_client = self.get_auth_client(consumer_key=consumer_key,
                                                   consumer_secret=consumer_secret,
                                                   access_token=access_token,
                                                   token_secret=token_secret,
                                                   account_id=account_id)
        # self.campaigns = self._get_access_token()
        # self.reports_start_date = pendulum.parse(reports_start_date).astimezone(tz=timezone.utc)

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
            return twitter_client.accounts(account_id)
        except Exception as e:
            raise print('There was an error: {e}') from e

    def get_campaigns(self) -> Optional[list]:
        campaigns: Final[Optional[Any]] = self.twitter_client
        ids: Final[list[dict[Optional[str, str]]]] = [{"campaign_id": campaign.id,
                                                       "campaign_name": campaign.name} for campaign in campaigns.campaigns() if
                                                      self.account_id]

        return ids

    def request(self, campaign_ids: Optional[list]):
        resource = f"/11/stats/accounts/{self.account_id}/"

        campaign_id = ','.join(campaign_ids)

        metric_groups = f'{METRIC_GROUP.ENGAGEMENT},{METRIC_GROUP.BILLING}'
        print(campaign_id)
        params = {
            "entity": ENTITY.CAMPAIGN,
            "entity_ids": f'{campaign_id}',
            "start_time": last_7_days,
            "end_time": yesterday,
            "granularity": GRANULARITY.DAY,
            "metric_groups": metric_groups,
            "placement": PLACEMENT.PUBLISHER_NETWORK
        }

        req = Request(client=self.twitter_client,
                      method="GET",
                      resource=resource,
                      params=params)

        yield from req.perform()
