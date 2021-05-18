#!/usr/bin/env python

import logging
import os
import time

import requests
import uds


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

OFFSET_FILE = "/tmp/uds_telegrambot_offset"
BOT_TOKEN = os.environ["BOT_TOKEN"]

base = f"https://api.telegram.org/bot{BOT_TOKEN}/"


def get_aqi_hanoi():
    resp = requests.get(
        "https://api.waqi.info/mapq/bounds/?bounds=20.96111901161895,105.75405120849611,21.09571147652958,105.91609954833986"
    )
    locs = resp.json()
    for i in locs:
        if "US Embassy" in i["city"]:
            us_embassy = i
            break
    return us_embassy["city"], us_embassy["aqi"], us_embassy["utime"]


def get_aqi_hcm():
    resp = requests.get(
        "https://api.waqi.info/mapq/bounds/?bounds=9.96885060854611,105.71594238281251,12.232654837013484,108.30871582031251"
    )
    locs = resp.json()
    us_embassy = locs[0]
    return us_embassy["city"], us_embassy["aqi"], us_embassy["utime"]


def send_message(session, chat_id, text="hi"):
    msg = {
        "chat_id": chat_id,
        "text": text,
    }
    session.post(base + "sendMessage", json=msg, timeout=10)


def fit_meanings_to_message(url, meanings):
    result = []
    for idx, meaning in enumerate(meanings):
        if idx == 3:
            result.append("...")
            break

        if len(meaning) > 140:
            meaning = f"{meaning[:140]}..."
        msg = f"{idx+1}. {meaning}"
        result.append(msg)
    result.append(url)
    return "\n".join(result)


def main():
    with requests.Session() as S:
        try:
            with open(OFFSET_FILE) as f:
                offset = int(f.read().strip())
                params = {"offset": offset + 1}
        except IOError:
            params = None

        resp = S.get(base + "getUpdates", json=params, timeout=20)
        d = resp.json()
        rs = d["result"]
        update_id = None
        for r in rs:
            update_id = r["update_id"]
            message = r["message"]
            if "text" in message:
                chat_id = r["message"]["chat"]["id"]
                text = r["message"]["text"].strip()

                if text.startswith("/uds "):
                    _uds, keyword = text.split(" ", 1)

                    try:
                        result = uds.urbandictionary(keyword)
                        url, meanings = result["url"], result["means"]

                    except Exception:
                        logger.exception(keyword)
                    else:
                        msg = fit_meanings_to_message(url, meanings)
                        send_message(
                            session=S,
                            chat_id=chat_id,
                            text=f"UrbanDictionary result for `{keyword}`\n"
                            + msg,
                        )
                        logger.info("UDS: served keyword %s", keyword)

                elif text.startswith("/cam "):
                    _cam, keyword = text.split(" ", 1)

                    try:
                        result = uds.cambridge(keyword)
                        url, ipa, meanings = (
                            result["url"],
                            result["ipa"],
                            result["means"],
                        )
                    except Exception:
                        logger.exception(keyword)
                    else:
                        msg = fit_meanings_to_message(url, meanings)
                        send_message(
                            session=S,
                            chat_id=chat_id,
                            text=f"Cambridge result for `{keyword}`\nIPA: {ipa}\n"
                            + msg,
                        )
                        logger.info("UDS: served cam keyword %s", keyword)

                elif text.startswith("/fr "):
                    _cam, keyword = text.split(" ", 1)

                    try:
                        result = uds.cambridge_fr(keyword)
                        url, ipa, meanings = (
                            result["url"],
                            result["ipa"],
                            result["means"],
                        )
                    except Exception:
                        logger.exception(keyword)
                    else:
                        msg = fit_meanings_to_message(url, meanings)
                        send_message(
                            session=S,
                            chat_id=chat_id,
                            text=f"Cambridge result for `{keyword}`\nIPA: {ipa}\n"
                            + msg,
                        )
                        logger.info("UDS: served camfr keyword %s", keyword)

                elif text.startswith("/aqi"):
                    # _aqi, city = text.split(" ", 1)
                    city = "hn&hcm"
                    location, value, utime = get_aqi_hanoi()
                    send_message(
                        session=S,
                        chat_id=chat_id,
                        text=f"PM2.5 {value} at {location} at {utime}",
                    )

                    location, value, utime = get_aqi_hcm()
                    send_message(
                        session=S,
                        chat_id=chat_id,
                        text=f"PM2.5 {value} at {location} at {utime}",
                    )
                    logger.info("AQI: served city %s", city)

                else:
                    logger.info("Unknown command: %s", text)

                with open(OFFSET_FILE, "w") as f:
                    f.write(str(update_id))

    time.sleep(30)


if __name__ == "__main__":
    while True:
        main()