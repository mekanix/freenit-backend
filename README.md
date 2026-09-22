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

## Configuration

Configuration lives in Python files, just like `services/backend`. Defaults are
in `freenit/base_config.py`. Create `freenit/local_config.py` to override any
environment:

```python
from freenit.base_config import configs
from freenit.config import AuthConfig, Config, LDAPConfig


configs["development"] = Config(
    environment="development",
    dburl="sqlite:///.dev.sqlite",
    secret_key="dev-secret",
    debug=True,
    auth=AuthConfig(secure=False),
    ldap=LDAPConfig(
        host="ldap.example.com",
        user_dn_template="uid={username},ou=people,dc=example,dc=com",
    ),
)
```

Only `FREENIT_ENV` is read from the environment to pick which config to use
(`development`, `testing`, or `production`).

## LDAP authentication

When `Config.ldap` is set, login attempts are verified by binding to the LDAP
server. A matching local SQL user record is created or updated on first
successful login and used for sessions and role checks.

```python
from freenit.config import LDAPConfig

LDAPConfig(
    host="ldap.example.com",
    tls=True,
    user_dn_template="uid={username},ou=people,dc=example,dc=com",
    allow_local_fallback=True,
)
```

`LDAPConfig` fields:

| Field | Default | Description |
|---|---|---|
| `host` | `""` | LDAP server hostname (empty disables LDAP) |
| `tls` | `True` | Use LDAPS/TLS |
| `service_dn` | `""` | Service account DN for searching |
| `service_pw` | `""` | Service account password |
| `user_base` | `ou=people,dc=example,dc=com` | Search base when not using a DN template |
| `user_dn_template` | `uid={username},ou=people,dc=example,dc=com` | Direct DN format; disables search if set |
| `search_filter` | `(mail={email})` | Filter for service-account search mode |
| `attr_email` | `mail` | Attribute mapped to the user's email |
| `attr_fullname` | `cn` | Attribute mapped to the user's full name |
| `attr_user_class` | `userClass` | Attribute used for active/admin flags |
| `omemo_attr` | `omemoBundle` | Attribute that stores the OMEMO bundle. Use `description` to parse `__OMEMO__:<data>` entries |
| `active_classes` | `{"active"}` | Class values that mark an account active |
| `admin_classes` | `{"admin"}` | Class values that grant admin flag |
| `allow_local_fallback` | `True` | Allow local SQL login when LDAP auth fails |

If `allow_local_fallback=False`, LDAP failures reject the login instead of
falling back to local authentication.

## Production

Create `freenit/local_config.py` with production values:

```python
from freenit.base_config import configs
from freenit.config import AuthConfig, Config


configs["production"] = Config(
    environment="production",
    dburl="postgresql://user:pass@host/dbname",
    secret_key="a-long-random-secret",
    auth=AuthConfig(secure=True),
)
```

### FreeBSD rc.d

Install gunicorn and copy the config to the default rc.d location:

```sh
/home/meka/.virtualenvs/freenit/bin/pip install gunicorn
sudo mkdir -p /usr/local/etc/gunicorn
sudo cp gunicorn.conf.py /usr/local/etc/gunicorn/gunicorn.conf.py
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
FREENIT_ENV=production /home/meka/.virtualenvs/freenit/bin/gunicorn -c gunicorn.conf.py
```

Put Gunicorn behind a reverse proxy (nginx, Caddy, Traefik) for HTTPS
termination and static file serving.
