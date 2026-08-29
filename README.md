# Freenit (Flask + HTMX + Chota + Oxide)

This service is a server-rendered web frontend for Freenit, built with:

* [Flask](https://flask.palletsprojects.com/)
* [HTMX](https://htmx.org/)
* [Chota](https://jenil.github.io/chota/)
* [Oxyde](https://github.com/oxyde/oxyde)

It replaces the previous FastAPI-based backend with a lightweight,
hypermedia-driven interface.

## Setup

```sh
/home/meka/.virtualenvs/freenit/bin/pip install -e '.[dev]'
```

## Run

```sh
FREENIT_ENV=development /home/meka/.virtualenvs/freenit/bin/flask --app freenit run --debug
```

## Migrate

```sh
FREENIT_ENV=development /home/meka/.virtualenvs/freenit/bin/oxyde migrate
```

## Test

```sh
/home/meka/.virtualenvs/freenit/bin/pytest
```

Production requires an explicit `FREENIT_SECRET_KEY` and database URL via
`FREENIT_DBURL`, `DATABASE_URL`, or `FREENIT_PRODUCTION_DBURL`.

## Production

### FreeBSD rc.d

Install gunicorn and copy the config to the default rc.d location:

```sh
/home/meka/.virtualenvs/freenit/bin/pip install gunicorn
sudo mkdir -p /usr/local/etc/gunicorn
sudo cp gunicorn.conf.py /usr/local/etc/gunicorn/gunicorn.conf.py
sudo cp gunicorn.env.sample /usr/local/etc/gunicorn/freenit.env
sudo chmod 640 /usr/local/etc/gunicorn/freenit.env
sudo editor /usr/local/etc/gunicorn/freenit.env   # set secrets
```

Add to `/etc/rc.conf`:

```sh
gunicorn_enable="YES"
gunicorn_config="/usr/local/etc/gunicorn/gunicorn.conf.py"
gunicorn_user="freenit"
gunicorn_group="freenit"
```

Create the user and run directory, then start:

```sh
sudo pw useradd freenit -d /nonexistent -s /usr/sbin/nologin
sudo mkdir -p /var/run/gunicorn
sudo chown freenit:freenit /var/run/gunicorn
sudo service gunicorn start
```

### Manual / generic

```sh
FREENIT_ENV=production \
FREENIT_SECRET_KEY="change-me" \
FREENIT_DBURL="postgresql+asyncpg://user:pass@host/dbname" \
/home/meka/.virtualenvs/freenit/bin/gunicorn -c gunicorn.conf.py
```

Put Gunicorn behind a reverse proxy (nginx, Caddy, Traefik) for HTTPS
termination and static file serving.
