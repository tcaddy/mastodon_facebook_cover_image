import daemon
import hashlib
import json
import lockfile
import logging
import os
import requests
import shutil
import signal
import sys
import time
import apprise

from pathlib import Path
from facebook_scraper import get_profile

class MastodonFacebookCoverPhoto():
  SLEEP_DURATION = 300

  def main(self):
    with daemon.DaemonContext(
        chroot_directory=None,
        pidfile=lockfile.FileLock(
          f"{Path(__file__).parent.resolve()}"
          "/main.py.pid"),
        signal_map={
          signal.SIGTERM: self._receive_shutdown,
          signal.SIGINT: self._receive_shutdown,
          signal.SIGQUIT: self._receive_shutdown,
          signal.SIGHUP: self._receive_shutdown,
        },
        stdout=sys.stdout,
        stderr=sys.stderr,
        detach_process=False,
        working_directory=Path(__file__).parent.resolve()):
      try:
        while not self.shutdown_received:
          self.process()
          time.sleep(self.SLEEP_DURATION)
        sys.exit(0)
      finally:
        try:
          os.remove(self.jpg_filename())
        except FileNotFoundError:
          logging.info("File is not present to remove: {self.jpg_filename()}")

  def __init__(self):
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.info(f"{time.strftime('%Y/%m/%d %H:%M:%S', time.localtime())} - "
      "MastodonFacebookCoverPhoto instance initialized")
    self.shutdown_received = False
    self.initialize_last_cover_photo()
    self.apobj = apprise.Apprise()
    self.apobj.add(f"toots://{os.environ.get('MASTODON_ACCESS_TOKEN')}@{os.environ.get('MASTODON_ACCOUNT')}")

  def _receive_shutdown(self, *args):
    logging.info(f"{time.strftime('%Y/%m/%d %H:%M:%S', time.localtime())} - "
      "shutdown signal received")
    self.shutdown_received = True

  def process(self):
    logging.info("self.process() called...")
    new_cover_photo = self.cover_photo()
    if self.last_cover_photo is None or self.last_cover_photo != new_cover_photo:
      logging.info("cover photo URL has changed.")
      self.update_last_cover_photo(new_cover_photo)
    else:
      logging.info("cover photo URL has not changed.")

  def cover_photo(self):
    return str(self.profile_info()["cover_photo"])

  def profile_info(self):
    try:
      return get_profile(os.environ.get("FB_PROFILE"))
    except Exception as err:
      logging.info("error calling self.get_profile()")
      logging.error(f"Exception type: {type(err)}")
      logging.error(f"Exception: {err}")
      sys.exit(1)

  def update_last_cover_photo(self, new_cover_photo):
    self.last_cover_photo = new_cover_photo
    self.download_cover_photo()
    old_sha = self.last_cover_photo_sha256
    new_sha = self.jpg_sha()
    if self.last_cover_photo_sha256 != self.jpg_sha():
      self.toot()
      self.save_last_cover_photo()

  def json_filename(self):
    return f"{Path(__file__).parent.resolve()}/tmp/last_cover_photo.json"

  def jpg_filename(self):
    return f"{Path(__file__).parent.resolve()}/tmp/last_cover_photo.jpg"

  def save_last_cover_photo(self):
    with open(self.json_filename(), "w") as f:
      self.last_cover_photo_sha256 = self.jpg_sha()
      f.write(
        json.dumps(
          {
            "last_cover_photo": self.last_cover_photo,
            "last_cover_photo_sha256": self.last_cover_photo_sha256
          }
        )
      )

  def jpg_sha(self):
    with open(self.jpg_filename(), "rb") as f:
      return hashlib.sha256(f.read()).hexdigest();

  def download_cover_photo(self):
    try:
      res = requests.get(url=self.last_cover_photo, stream=True)
      if res.status_code == 200:
        with open(self.jpg_filename(), "wb") as f:
          shutil.copyfileobj(res.raw, f)
      else:
        logging.info(f"response status code: {res.status_code}")
        logging.info(f"response headers: {json.dumps(res.headers, default=str)}")
        for line in res.iter_lines():
          logging.info(line)
        raise Exception(f"Error downloading cover photo from {self.last_cover_photo}")
    except Exception as err:
      logging.info(f"Error when downloading cover photo from {self.last_cover_photo}")
      logging.error(f"Exception type: {type(err)}")
      logging.error(f"Exception: {err}")
      raise err

  def toot(self):
    self.apobj.notify(attach=self.jpg_filename(),
      body=f"Cover photo for {os.environ.get('FB_PROFILE')} account has changed")

  def initialize_last_cover_photo(self):
    try:
      with open(self.json_filename(), "r") as f:
        obj = json.load(f)
      self.last_cover_photo = obj["last_cover_photo"]
      self.last_cover_photo_sha256 = obj["last_cover_photo_sha256"]
    except Exception as err:
      logging.info("Error calling self.initialize_last_cover_photo()")
      logging.error(f"Exception type: {type(err)}")
      logging.error(f"Exception: {err}")
      self.last_cover_photo = None
      self.last_cover_photo_sha256 = None

if __name__ == "__main__":
  mfcp = MastodonFacebookCoverPhoto()
  mfcp.main()
