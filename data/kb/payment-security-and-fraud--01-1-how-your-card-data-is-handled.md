Everstorm Outfitters — Payment Security, 3-D Secure & Declines · Revision 2.1 · Status: current · Document PAY-SEC-002
Section: 1. How your card data is handled

# Payment Security, 3-D Secure & Declines

## 1. How your card data is handled

All checkout traffic runs over **TLS 1.3**. We are **Level 1 PCI-DSS
compliant**, audited annually by a Qualified Security Assessor.

We never store full card numbers. Card details go directly from your browser to
our payment processor, which returns a token. What Everstorm holds is that
token, the last four digits, the expiry month and the card brand — enough to
show you "Visa ending 4242" and to process a refund, and not enough to make a
charge anywhere else.

Our support agents cannot see your full card number. If anyone claiming to be
from Everstorm asks you to read out a card number, CVV or one-time code, it is
not us. Hang up and email billing@everstorm.example.
