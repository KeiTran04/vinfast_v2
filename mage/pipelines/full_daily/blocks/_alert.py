from __future__ import annotations

import json
import os
import urllib.request


def send(status: str, batch_date: str, failed_block: str = "", run_url: str = "") -> None:
    url = os.environ.get("ALERT_WEBHOOK_URL", "")
    if not url:
        return
    data = json.dumps({"text": f"[vinfast] {status} date={batch_date} block={failed_block} {run_url}"}).encode()
    urllib.request.urlopen(urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}), timeout=10)
