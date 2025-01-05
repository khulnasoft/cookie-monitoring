#!/usr/bin/env python3

from datetime import datetime
from datetime import timezone
from datetime import timedelta
import dataclasses
import typing as t
import os
from khulnasoft import KhulnasoftApiClient
import time
import json


class Cookie(t.TypedDict):
    domain: str
    name: str
    path: str
    value: str


class CursorData(t.TypedDict):
    cursor: str


@dataclasses.dataclass
class MonitorContext:
    api_client: KhulnasoftApiClient

    ####################
    ## Cursor Methods ##
    ####################
    get_cursor: t.Callable[[], str | None]
    save_cursor: t.Callable[[str], None]

    #######################
    ## Cookie Management ##
    #######################
    verify_cookie: t.Callable[[Cookie], bool]
    invalidate_cookie: t.Callable[[Cookie], None]


def get_cursor() -> str | None:
    # TODO: Implement a method here that loads your cursor,
    # perhaps from a database.
    data: str = ""
    if not os.path.exists("cursor.txt"):
        return None
    with open("cursor.txt", "r", encoding="utf-8") as f:
        data = f.read().strip()
    if not data:
        return None
    cursor_data: CursorData = json.loads(data)
    return cursor_data["cursor"]


def save_cursor(cursor: str) -> None:
    # TODO: Implement a method here that saves the cursor.
    print(f"Would save {cursor=}")
    cursor_data: CursorData = CursorData(cursor=cursor)
    with open("cursor.txt", "w") as f:
        f.write(json.dumps(cursor_data))
        f.write("\n")


def verify_cookie(cookie: Cookie) -> bool:
    print(f"Would verify {cookie=}...")
    return True


def invalidate_cookie(cookie: Cookie) -> None:
    # TODO: Implement a method that would invalidate the cookie.
    print(f"Would invalidate {cookie=}...")
    pass


def run_monitor_cookies(
    *,
    context: MonitorContext,
    domain: str,
    cookie_name: str,
    include_expired: bool,
    time_since_imported: timedelta | None = None,
) -> None:
    cursor: str | None = context.get_cursor()

    query: dict = {
        "from": cursor,
        "domain": domain,
        "names": [cookie_name],
        "size": 50,
    }
    if not include_expired:
        query["expires_after"] = datetime.now(tz=timezone.utc).isoformat()
    if time_since_imported is not None:
        query["imported_after"] = (
            datetime.now(tz=timezone.utc) - time_since_imported
        ).isoformat()

    for resp in context.api_client.scroll(
        method="POST",
        url="/leaksdb/v2/cookies/_search",
        json=query,
    ):
        # Ratelimit
        time.sleep(1)

        resp_data: dict = resp.json()

        # Save the cursor
        next_cursor: str | None = resp_data["next"]
        if next_cursor:
            context.save_cursor(next_cursor)

        cookies: list[Cookie] = resp_data["items"]
        print(f"Fetched {len(cookies)} cookies...")

        for cookie in cookies:
            # If this cookie is no longer valid, continue.
            if not context.verify_cookie(cookie):
                continue

            # This cookie is valid, let's invalidate it.
            context.invalidate_cookie(cookie)


def main() -> None:
    api_key: str = os.environ["KHULNASOFT_API_KEY"]
    tenant_id: str | None = os.environ.get("KHULNASOFT_TENANT_ID")

    context: MonitorContext = MonitorContext(
        api_client=KhulnasoftApiClient(
            api_key=api_key,
            tenant_id=int(tenant_id) if tenant_id is not None else None,
        ),
        # Cursors
        get_cursor=get_cursor,
        save_cursor=save_cursor,
        # Cookies
        verify_cookie=verify_cookie,
        invalidate_cookie=invalidate_cookie,
    )
    run_monitor_cookies(
        context=context,
        domain=os.environ.get(
            "KHULNASOFT_COOKIE_DOMAIN",
            "scatterholt.com",
        ),
        cookie_name=os.environ.get(
            "KHULNASOFT_COOKIE_NAME",
            "session",
        ),
        include_expired=True,
        time_since_imported=timedelta(days=90),
    )


if __name__ == "__main__":
    main()
