# Alexa → Clawdia Integration (Voice to Assistant)

Goal: You say **"Alexa, Clawdia..."** and your spoken message is sent directly to Clawdia/OpenClaw.

This guide gives a practical end-to-end setup with AWS + Alexa Skill + webhook relay.

---

## Recommended architecture

1. **Alexa Custom Skill** (invocation: `clawdia`)
2. **AWS Lambda** backend for the skill
3. Lambda sends text to **OpenClaw inbound webhook** (or automation endpoint)
4. OpenClaw processes the message and replies via your normal channels (WhatsApp/Slack/etc.)

This is the cleanest and most controllable way.

---

## Resulting UX

You say:
- "Alexa, open Clawdia"
- "send message: turn hallway pump off"

Or one-shot:
- "Alexa, ask Clawdia turn hallway pump off"

---

## Prerequisites

- Amazon Developer account
- AWS account (Lambda + CloudWatch)
- OpenClaw reachable endpoint (HTTPS) for inbound text events
- Secret token for webhook auth

---

## 1) Create Alexa Custom Skill

1. Go to: `developer.amazon.com/alexa/console/ask`
2. Create skill:
   - Name: `Clawdia`
   - Type: **Custom**
   - Model: **Custom model**
   - Backend: **Provision your own**
3. Invocation name: `clawdia`

### Interaction model

Create intent `SendToClawdiaIntent` with slot:
- `message` (type `AMAZON.SearchQuery`)

Sample utterances:
- `send {message}`
- `message {message}`
- `tell Clawdia {message}`
- `{message}`

Build model.

---

## 2) Create AWS Lambda

Runtime: Node.js 20+ (or Python). Below is Node.js example.

### Environment variables (Lambda)

- `OPENCLAW_WEBHOOK_URL` = your HTTPS endpoint
- `OPENCLAW_WEBHOOK_TOKEN` = shared secret

### Lambda code (Node.js)

```js
export const handler = async (event) => {
  const request = event?.request || {};

  // LaunchRequest
  if (request.type === 'LaunchRequest') {
    return speak('Ready. Say your message.');
  }

  if (request.type === 'IntentRequest' && request.intent?.name === 'SendToClawdiaIntent') {
    const msg = request.intent?.slots?.message?.value?.trim();
    if (!msg) return speak('I did not catch the message. Please try again.');

    const payload = {
      source: 'alexa',
      user: 'owner',
      text: msg,
      ts: new Date().toISOString()
    };

    const r = await fetch(process.env.OPENCLAW_WEBHOOK_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENCLAW_WEBHOOK_TOKEN}`
      },
      body: JSON.stringify(payload)
    });

    if (!r.ok) {
      return speak('I could not reach Clawdia right now.');
    }

    return speak('Sent to Clawdia.');
  }

  return speak('Sorry, I could not handle that request.');
};

function speak(text) {
  return {
    version: '1.0',
    response: {
      outputSpeech: { type: 'PlainText', text },
      shouldEndSession: true
    }
  };
}
```

Deploy Lambda.

---

## 3) Connect Alexa Skill to Lambda

In Alexa Skill -> Endpoint:
- Choose **AWS Lambda ARN**
- Paste Lambda ARN for your region
- Save

Enable skill testing in dev console.

---

## 4) OpenClaw webhook relay requirements

Your OpenClaw side should accept payload:

```json
{
  "source": "alexa",
  "user": "owner",
  "text": "turn hallway pump off",
  "ts": "2026-03-03T17:00:00Z"
}
```

And then route `text` into your main assistant session.

### Minimum security

- Require Bearer token
- Reject unknown source or missing fields
- Rate-limit endpoint
- Log request id + timestamp (not secrets)

---

## 5) Voice shortcuts to make it natural

Because Alexa requires invocation phrase, the practical closest forms are:
- "Alexa, ask Clawdia <message>"
- "Alexa, open Clawdia" + "<message>"

If you want true one-liner feel, set utterances so `{message}` is accepted once Clawdia skill is invoked.

---

## 6) Optional return channel

You requested message-in first. Replies can later go via:
- WhatsApp (current)
- Slack DM
- Alexa spoken response (next phase: Lambda waits for OpenClaw short response)

---

## 7) Testing checklist

1. Skill invocation works
2. Intent recognizes full spoken sentence
3. Lambda logs show parsed `message`
4. OpenClaw webhook receives payload
5. Clawdia processes command and sends confirmation (e.g. WhatsApp)

---

## 8) Common issues

- Alexa captures only first words -> use `AMAZON.SearchQuery` slot
- 403 from webhook -> token mismatch
- Skill timeout -> keep Lambda call fast, async if needed
- Wrong locale -> ensure skill language matches device language

---

## 9) Recommended next step

After base setup works, add:
- `intent: confirm/abort` for sensitive actions
- user voice profile / speaker pin
- short memory tag `source=alexa` in `ha_ai_memory`

---

## Notes for this project

This repo now has a complete setup plan for Alexa-to-Clawdia voice forwarding. Implementation can be done as a small AWS Lambda + OpenClaw webhook bridge without changing core HA logic.
