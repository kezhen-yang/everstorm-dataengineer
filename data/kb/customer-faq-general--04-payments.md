Everstorm Outfitters — Customer FAQ — General · Revision 2.0 · Status: current · Document FAQ-GEN-002
Section: Payments

## Payments

**What do you accept?**
Visa, Mastercard, Amex, Discover (US), Apple Pay, Google Pay, PayPal, Shop Pay.
Shop Pay Installments in the US, Klarna Pay-in-4 in selected EU countries — not
the UK. USDC on Ethereum Mainnet over $500.
→ `payment-methods-and-processing.md`

**Why did I see a 3-D Secure pop-up?**
Your bank controls it; it is mandatory in the EU and UK under PSD2. We cannot
skip it or resend the code.

**Why was my card declined?**
Usually ZIP mismatch, CVV typo, a cross-border block, or a failed 3DS challenge.
We cannot override an issuer decline. Failed attempts leave authorisation holds,
not charges, and they drop off in 3–5 business days.
→ `payment-security-and-fraud.md`

**Can I split payment across two cards?**
Not directly. Buy a gift card with the first, then pay the balance with the
second.

**Is my card data safe?**
TLS 1.3, Level 1 PCI-DSS. We never store full card numbers and our agents cannot
see them. We will never ask you for a card number, password or one-time code.

**Do you charge sales tax?**
Yes, in 42 US states plus DC and applicable Canadian provinces. Apparel is
exempt or partially exempt in several states.
→ `sales-tax-and-vat.md`
