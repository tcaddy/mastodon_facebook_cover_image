FROM python:buster

ARG HOST_UID
ARG HOST_GID

ENV \
  DEBIAN_FRONTEND=noninteractive

# change to Bash
SHELL ["/bin/bash", "-c"]

RUN \
  apt-get update && \
  apt-get -y install locales && \
  apt-get -y upgrade && \
  apt-get -y dist-upgrade && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \

  # timezone config
  ln -sf /usr/share/zoneinfo/UTC /etc/localtime && \
  dpkg-reconfigure --frontend noninteractive tzdata && \

  # use en_US.UTF-8
  localedef en_US.UTF-8 -i en_US -fUTF-8 && \
  echo "LANG=en_US.UTF-8" >> /etc/default/locale && \

  # update pip
  pip3 install --upgrade pip && \

  mkdir -p /opt/mastodon_facebook_cover_image/tmp && \
  python3 -m venv /opt/mastodon_facebook_cover_image && \
  touch /opt/mastodon_facebook_cover_image/tmp/last_cover_photo.json && \
  touch /opt/mastodon_facebook_cover_image/tmp/cookies.txt && \

  # echo -e "MastodonFacebookCoverPhoto\nMastodonFacebookCoverPhoto" | passwd root && \

  useradd --shell /bin/bash --create-home --uid $HOST_UID ubuntu && \
  usermod -aG $HOST_GID ubuntu

COPY --chown=$HOST_UID:$HOST_GID requirements.txt /opt/mastodon_facebook_cover_image

RUN \
  cd /opt/mastodon_facebook_cover_image && \
  ./bin/pip install --no-cache-dir -r requirements.txt && \
  chown -R $HOST_UID:$HOST_GID /opt/mastodon_facebook_cover_image

COPY --chown=$HOST_UID:$HOST_GID main.py /opt/mastodon_facebook_cover_image
COPY --chown=$HOST_UID:$HOST_GID entrypoint.sh /opt/mastodon_facebook_cover_image

USER ubuntu

WORKDIR /opt/mastodon_facebook_cover_image

ENTRYPOINT "./entrypoint.sh"
