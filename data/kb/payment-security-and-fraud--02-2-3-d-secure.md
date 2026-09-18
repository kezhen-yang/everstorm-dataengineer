Everstorm Outfitters — Payment Security, 3-D Secure & Declines · Revision 2.1 · Status: current · Document PAY-SEC-002
Section: 2. 3-D Secure

## 2. 3-D Secure

3-D Secure — branded "Verified by Visa", "Mastercard Identity Check" or
"American Express SafeKey" — adds a one-time code or an app approval step.

It is **mandatory in the EU and UK** under PSD2 Strong Customer Authentication.
Elsewhere it triggers selectively, usually on a high-value order, a new device,
or a shipping address that does not match the billing address.

**Your bank controls that pop-up, not us.** We cannot skip it, resend the code,
or tell you what it will ask. If the challenge fails or times out, the payment
declines and you will need to retry.

Common 3DS failure causes:

- The code went to an old phone number your bank still has on file
- A pop-up blocker or aggressive privacy extension blocked the challenge window
- You took longer than the bank's timeout, often 5 minutes
- Your banking app was not installed on the device you were checking out from
