# Ada Handoffs API Demo

This is a demo project providing a minimal implementation of a custom handoff

## Prerequisites
- Python 3.12+ (`python3 --version` to check)
- A reverse proxy solution (this README setup uses [ngrok](https://ngrok.com), but any reverse proxy is fine)
- Access to Platform > APIs and Platform > Webhooks in your Ada AI Agent
```

## 1. Setting up this repo

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

The last thing you will need to do is setup a reverse proxy to the service. Any reverse proxy is fine, but for
the sake of this guide we will use ngrok. After installing and setting up [ngrok](https://ngrok.com), you will need
to grab a reserved ngrok domain from your account. Login to ngrok and go to `Universal Gateway > Domains`.

Here, you should either see a free dev domain if you're on a free ngrok account, or you should be able to reserve custom domains
if you have a paid ngrok account. Note your dev/reserved domain. Then run `ngrok config edit`, and add the following
under the `tunnels` section of the yaml config and save it:

```yaml
handoffs-api-demo:
    addr: localhost:8090
    proto: http
    hostname: <your ngrok domain>
```

Then you can start this tunnel by running `ngrok start handoffs-api-demo`

> [!IMPORTANT]
> You will need to start this tunnel every time you want to run this demo repo

## 2. Configuring the handoff

Next we will need to configure the handoff in the AI Agent dashboard. First you will need to configure a handoff flow to use
the HTTP request block as the triggering point for the handoff. Follow these steps to configure the block:

1. Add a **Request** block to your handoff flow.
2. Set the **Method** to `POST`.
3. Enter your ngrok endpoint URL in the **URL** field: `https://<your-ngrok-domain>/webhooks/start-handoff`.
4. Under **Body Content**, add the following field:

   | Key | Value | Type |
   |-----|-------|------|
   | `ada_conversation_id` | `@conversation_id` | string |

5. Enable the **Track as Handoff** option. This tells the AI Agent to enter a handoff state when the request succeeds.
6. Enable the **Pause conversation here until handoff ends** option. This prevents the AI Agent from responding while the handoff is active.
7. Set the **Handoff integration label** to `custom-handoff`. This value identifies your integration in webhook events and allows you to filter webhook deliveries so this integration only receives its own events.

The configured block should look like this:

![Request Block Configuration](docs/assets/request-block-configuration.png)

<details><summary>Alternatively you can copy and paste this blob into your handoffs flow</summary>

```json
[{"isLoading":false,"locked":false,"reviewableMessage":false,"variableId":null,"type":"http_request_recipe","headers":{"":""},"headersList":[{"key":"","value":""}],"errorResponse":true,"isHandoff":true,"shouldPause":true,"handoffIntegrationLabel":"custom-handoff","requestUrl":"https://<replace-with-ngrok-domain>/webhooks/start-handoff","requestPayload":[{"key":"ada_conversation_id","value":"replace with @conversation_id variable","type":"string"}],"requestPayloadType":"json","requestType":"POST","variablesData":[],"successBusinessEvent":{"value":"","eventKey":"","isVariable":false}}]
```

</details>

> [!IMPORTANT]
> Make sure to update the URL and `ada_conversation_id` body field as instructed.

## 3. Configuring API Keys and Webhooks

Next we will setup the remaining configuration to enable bidirectional communication between your AI Agent and the demo repo.
To start with, create a new Platform API Key by navigating to `Platform > APIs` and create a new API key. Copy this value
into your `.env` file you created from [step 1](#1-setting-up-this-repo); it should be set as the value for `ADA_API_KEY`.

Then you will need to configure a webhook in your AI Agent that will send events to this demo repo.

In your AI Agent dashboard, go to `Platform > Webhooks` and create a new endpoint. The URL should be `https://<ngrok-domain>/webhooks/events`
(e.g. `https://custom-handoff.ngrok.io/webhooks/events`), and you should subscribe to at minimum the `v1.conversation.message` and
`v1.conversation.handoff.ended` events. Once the webhook is created, click on the Endpoint to view it, and on the right hand side,
reveal the Signing Secret value. Copy this value into `WEBHOOK_SECRET` in your `.env` file from [step 1](#1-setting-up-this-repo).

Lastly, set `ADA_BASE_URL` in your `.env` file to point to your AI Agent's base URL with "/api" appended to it. This would take
the form `https://<ai-agent-handle>[.<region>].ada.support/api`.


## 4. Running the Custom Handoff

With everything configured, you can now run the demo repo. Ensure you have your reverse proxy running, and then run

```python
. .venv/bin/activate
python run.py
```

With the repo running, go to your AI Agent's chat, and trigger the handoff flow with your request block. If the handoff is
successful:
- the AI Agent will stop responding
- a conversation transcript will appear in the demo agent chat
- messages sent as the demo agent should forward to the end user's chat
- messages sent by the end user should appear in the demo agent chat
- closing the conversation from the end user's side should show a notification on the demo agent chat
- ending the handoff from the demo agent chat should ned the handoff from the end user's chat

> [!NOTE]
> This code is for example use only, and modifications may be needed to run this code. Additionally, pull requests and/or issues for this repository will not be monitored.
