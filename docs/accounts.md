# Accounts

An account is a service name, the URL of a Tergite API (MSS) and an app token. You get a token
from the Tergite dashboard, for example [QAL 9000](https://www.qal9000.se/), or from your own
[tergite-frontend](https://github.com/tergite/tergite-frontend).

There are three ways to give the SDK an account.

## Save it

```python
from tergite import Tergite

provider = Tergite.use_provider_account(
    service_name="MY_SERVICE_NAME",
    url="https://api.qal9000.se",
    token="MY_API_TOKEN",
    save=True,
)
```

This writes the account to `~/.qiskit/tergiterc`, a file only you can read (mode 600). The token
is stored in plain text. Afterwards, get it back by name from anywhere:

```python
provider = Tergite.get_provider(service_name="MY_SERVICE_NAME")
```

`get_provider` raises for a name it does not know, rather than picking another account.

## Use it without saving

Leave out `save`. Nothing is written to disk, which suits automated tests.

```python
provider = Tergite.use_provider_account(
    service_name="MY_SERVICE_NAME",
    url="https://api.qal9000.se",
    token="MY_API_TOKEN",
)
```

## Take it from the environment

Set `TERGITE_API_URL` and `TERGITE_API_TOKEN`, as Qiskit's IBM provider reads `QISKIT_IBM_URL`
and `QISKIT_IBM_TOKEN`:

```shell
export TERGITE_API_URL="https://api.qal9000.se"
export TERGITE_API_TOKEN="MY_API_TOKEN"
```

```python
provider = Tergite.get_provider()
```

This account is named `env`. It is never saved, and `Tergite.get_provider()` returns it ahead
of any saved account.

## On a shared computer

On a login that others use too, such as a lab's guest account, anyone can read a saved token
and run jobs with it; `Tergite.get_provider()` would even pick it for them. There:

- don't save your account: use one without saving, or the environment variables;
- use an app token with a short lifespan, made for the session, and delete it in the dashboard
  when you are done.
