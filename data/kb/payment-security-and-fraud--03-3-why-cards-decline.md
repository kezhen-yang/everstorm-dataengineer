Everstorm Outfitters — Payment Security, 3-D Secure & Declines · Revision 2.1 · Status: current · Document PAY-SEC-002
Section: 3. Why cards decline

## 3. Why cards decline

We see the same handful of causes over and over:

| Reason | What to do |
|---|---|
| Billing ZIP or postcode mismatch | Enter the address your **bank** has, not the delivery address |
| CVV typo | Re-enter carefully; three attempts usually locks the card for an hour |
| Foreign transaction blocked | Call your bank and authorise a US merchant |
| Card expired | Check the expiry month |
| Insufficient funds | Including where a previous authorisation is still holding the balance |
| Bank fraud rule triggered | Only your bank can override it |
| 3DS challenge failed | See §2 |

**We cannot override a decline.** The decision is made by your issuing bank and
arrives at us as a single code with no detail attached. When an agent says they
cannot see why your card declined, that is literally true — we receive a
two-digit code, not an explanation.
