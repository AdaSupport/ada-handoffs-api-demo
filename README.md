# Ada Handoffs API Demo

This is a demo project that can be used to test a custom handoff implementation via Simple Apps and our public APIs

## Setup

### 1. Setting up this repo

First, you will need to setup your python environment. Ensure you have python 3.12 installed,
and then run the following commands:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .
```

Then copy the contents of .env.example into a .env file

```bash
cp .env.example .env
```

The .env file will need the correct credentials; we will fill these in later on.

The last thing you will need to do is setup a reverse proxy to the service. For this you can
use ngrok, and you can add this tunnel config to your ngrok config:

```yaml
handoffs-api-demo:
    addr: localhost:8090
    proto: http
    hostname: <ngrok host domain url to reserve>
```

You can start this tunnel by running `ngrok start handoffs-api-demo`.

### 2. Configuring the handoff

Next we will need to configure the handoff in the bot manager dashboard. In a typical production implementation,
by the Solutions team, they will do this by using the Simple Apps API (an api built off
[the integrations repo](https://github.com/adaSupport/integrations)) to create a new block.

To simplify testing, a block configured to trigger a handoff is available in the integrations repo, known as the "Sandbox Integration".
First you will need to enable this block:

- **Deployed Environment** — you can enable the block through https://bat.ops.ada.support. Search for your bot and go to manage
it, then go to `Edit Ada Apps > Apps with Actions > Sandbox Integration`. Toggle it on, and then save.
- **Local Dev Environment** — you will need to start the `integrations` service. The simplest way to do this is through docker.
In the API monolith repo, run the command `./plz run-docker-integrations` to run the service from a dev2 image. Then you can enable the
block by running:

  ```bash
  curl --location --request PATCH 'http://localhost:8084/v1/clients/<client_id>' \
  --header 'x-ada-clienthandle: <client_handle>' \
  --header 'Content-Type: application/json' \
  --header 'Authorization: Bearer local-master-token' \
  --data '{
      "enabled_integrations": [
          "sandbox"
      ]
  }'
  ```

Then in the dashboard navigate to `Platform > Apps > Sandbox Integration > Configure`. For all of the fields, you can put in any
random dummy data, except for the last field, "Initiate Handoff Webhook". For this configuration field, grab ngrok host domain
url you reserved in Step 1, and set this equal to `<ngrok-domain-url>/webhooks/start-handoff` (e.g.
`https://custom-handoff.ngrok.io/webhooks/start-handoff`). Then save.

Lastly, head over to `AI Agent profile > Handoffs` and create a new handoff flow. In the block editor, drag in the Sandbox
Integration block from the toolbar, and select the "Trigger Handoffs API Handoff" action. Set the Conversation ID to the
`@conversation_id` variable, and enable the "Pause conversation here until handoff ends" and "Track as Handoff" options.
Then save the handoff flow.

### 3. Configuring API Keys and Webhooks

Next we will setup the remaining configuration to enable bidirectional communication between your bot and the demo repo.
To start with, create a new Platform API Key by navigating to `Platform > APIs` and create a new API key. Copy this value
into your `.env` file you created from [step 1](#1-setting-up-this-repo); it should be set as the value for `ADA_API_KEY`.

> [!TIP]
> If you are on a local dev environment, and the API Key page doesn't work, see the
> [Authentication Local Testing Guide](https://github.com/AdaSupport/api/tree/master/platform_apis#api-key-local-testing).

Then you will need to configure a webhook in your bot that will send events to this demo repo.

> [!TIP]
> If you are on a local dev environment, ensure you have followed the instructions in the
> [Webhooks Local Testing Guide](https://github.com/AdaSupport/api/tree/master/platform_apis#webhooks-local-testing) first.

In your bot, go to `Platform > Webhooks` and create a new endpoint. The URL should be `<ngrok-domain-url>/webhooks/events`
(e.g. `https://custom-handoff.ngrok.io/webhooks/events`), and you should subscribe to all `conversation` events. Once
the webhook is created, click on the Endpoint to view it, and on the right hand side, reveal the Signing Secret value.
Copy this value into your `.env` file from [step 1](#1-setting-up-this-repo); it should be set as the value for `WEBHOOK_SECRET`.

Lastly, `ADA_BASE_URL` should point to the base URL for the `api` service under your bot handle's subdomain. This would be:

- **Deployed Environment** — `https://<bot-handle>[.<region>].ada.support/api`
- **Local Dev Environment** — `http://<bot-handle>.localhost:8000`


### 4. Running the Custom Handoff

With everything configured, you can now run the demo repo. Ensure you have ngrok running, and then run

```python
. .venv/bin/activate
python run.py
```

With the repo running, go to your bot's chat, and trigger the handoff flow with the custom Sandbox handoff. If the handoff is
successful, the bot should stop responding, and a conversation transcript should appear in the demo repo's window. Enter a message
in the demo repo to connect + send the first agent message. You should be able to then chat back and forth and end the handoff just
any other handoff integration.

# Footnotes
## Explanation of Required Action Manifest Values

You can view the Sandbox block manifest description [here](https://github.com/AdaSupport/integrations/blob/main/integrations/sandbox/manifest.yaml#L71-L89).
The key detail of the manifest is the `block_configuration` section:

```yaml
...
  block_configuration:
    allow_count_as_handoff: true
    show_pause_checkbox: true
    handoff_integration_label: sandbox-handoff
```

These configurations ensure that when the block executes it will:

1. Trigger a handoff state in which the AI Agent no longer responds (as long as the should_pause checkbox is enabled)
1. Connect that handoff state to a custom handoff identified by the `handoff_integration_label` field

Under the hood, these will affect the `ada_glass_env` and `current_state` properties of the conversation document.
