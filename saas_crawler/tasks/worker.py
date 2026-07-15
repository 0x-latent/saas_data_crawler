"""RQ worker entrypoint."""

from __future__ import annotations

import os

from redis import Redis
from rq import SimpleWorker, Worker

from saas_crawler.storage import settings
from saas_crawler.tasks.queue import QUEUE_NAME


def main() -> None:
    redis = Redis.from_url(settings.REDIS_URL)
    worker_class = SimpleWorker if os.name == "nt" else Worker
    worker_class([QUEUE_NAME], connection=redis).work()


if __name__ == "__main__":
    main()
