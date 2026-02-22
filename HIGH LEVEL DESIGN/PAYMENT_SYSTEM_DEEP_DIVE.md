# Payment System — Complete Deep Dive

> Interview-ready documentation — Covers Stripe, Razorpay, PayPal, Square

---

# 0. UNDERSTANDING PAYMENTS (Start Here!)

## What Happens When You Pay Online?

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                     REAL-WORLD PAYMENT FLOW (What You Experience)                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

YOU BUY A ₹1000 ITEM ON FLIPKART:

Step 1: You click "Pay Now"
        ↓
Step 2: You enter card details (or UPI/NetBanking)
        ↓
Step 3: You get OTP on phone (3D Secure)
        ↓
Step 4: You enter OTP
        ↓
Step 5: "Payment Successful!" message
        ↓
Step 6: Order confirmed, seller ships


BEHIND THE SCENES (10+ parties involved!):

You  →  Flipkart  →  Razorpay (Payment Gateway)  →  HDFC Bank (Acquirer)
                                                            ↓
                                                   Visa/Mastercard Network
                                                            ↓
                                                   ICICI Bank (Your Bank - Issuer)
                                                            ↓
                                                   Your Account Debited!
```

## The Payment Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY PLAYERS IN PAYMENTS                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. CARDHOLDER (You)
   - The person paying
   - Has a card/UPI from their bank

2. MERCHANT (Flipkart, Amazon, Swiggy)
   - Business accepting payment
   - Pays fees to accept cards

3. ISSUING BANK (Your Bank - ICICI, SBI)
   - Issued your card
   - Approves/declines transactions
   - Sends you monthly statement

4. ACQUIRING BANK (Merchant's Bank - HDFC)
   - Merchant has account here
   - Receives money from card network
   - Deposits to merchant

5. CARD NETWORK (Visa, Mastercard, RuPay)
   - Connects all banks
   - Routes transactions
   - Sets rules and fees

6. PAYMENT GATEWAY (Razorpay, Stripe, PayU)
   - Tech company we're designing!
   - Provides APIs to merchants
   - Handles complexity
   - Connects to multiple banks/networks


THE MONEY FLOW:

Customer pays ₹1000
    ↓
Issuing Bank (ICICI) debits ₹1000 from customer
    ↓
Card Network (Visa) routes ₹1000
    ↓
Acquiring Bank (HDFC) receives ₹997 (after interchange)
    ↓
Payment Gateway (Razorpay) takes ₹20 fee
    ↓
Merchant (Flipkart) receives ₹977

FEES BREAKDOWN (typical):
  Interchange Fee (to issuing bank): 1.5-2%
  Network Fee (to Visa/MC): 0.1-0.3%
  Gateway Fee (to Razorpay): 2% of ₹1000 = ₹20
```

---

# 1. FUNCTIONAL REQUIREMENTS (With Examples)

| # | Feature | Real-World Example |
|---|---------|-------------------|
| 1 | **Accept Payments** | Customer pays on Swiggy checkout |
| 2 | **Multiple Methods** | Card, UPI, NetBanking, Wallets, BNPL |
| 3 | **Idempotency** | Customer clicks Pay twice → charge once only! |
| 4 | **Refunds** | Customer cancels order → money back |
| 5 | **Partial Capture** | Book ₹5000 hotel, capture ₹4500 (no minibar) |
| 6 | **Recurring** | Netflix monthly subscription |
| 7 | **Webhooks** | Notify merchant when payment succeeds |
| 8 | **Fraud Detection** | Block stolen cards |
| 9 | **Disputes** | Customer says "I didn't buy this!" |
| 10 | **Settlement** | Transfer collected money to merchant's bank |
| 11 | **Multi-currency** | Tourist pays in USD, merchant gets INR |
| 12 | **Saved Cards** | "Pay with saved Visa ending 4242" |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SCALE & REQUIREMENTS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCALE (Razorpay-like):
  Daily transactions:     10 million
  Peak TPS:               10,000 transactions/second
  Total processed/year:   $100 billion
  Merchants:              10 million+

LATENCY:
  Payment initiation:     < 100ms (return payment_id)
  Card authorization:     < 3 seconds (depends on bank)
  API response:           < 200ms (p99)

CRITICAL REQUIREMENTS:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  EXACTLY-ONCE PROCESSING                                             │
  │                                                                       │
  │  If you charge twice, GAME OVER!                                     │
  │  - Customer loses trust                                               │
  │  - Merchant faces chargebacks                                         │
  │  - Your company loses reputation                                      │
  │                                                                       │
  │  THIS IS THE #1 PRIORITY IN PAYMENT SYSTEMS!                         │
  └──────────────────────────────────────────────────────────────────────┘

AVAILABILITY:
  Target: 99.99% (52 minutes downtime/year max)
  Why: Every minute down = lost transactions = angry merchants

DATA DURABILITY:
  Target: 99.999999999% (11 nines)
  Why: Financial records are legally required for 7+ years

COMPLIANCE:
  PCI-DSS Level 1: Required to handle card data
  RBI Guidelines: For Indian payment aggregators
```

---

# 3. PAYMENT METHODS DEEP DIVE

## 3.1 Card Payments

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CARD PAYMENT FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CARD NUMBER ANATOMY:
  4532 1234 5678 9012
  │    │              │
  │    │              └── Check digit (Luhn algorithm)
  │    └── Account number (unique to you)
  └── BIN (Bank Identification Number)
      4 = Visa
      5 = Mastercard
      6 = RuPay

AUTHORIZATION vs CAPTURE:

  ┌────────────────────────────────────────────────────────────────────────┐
  │  SCENARIO: You book Uber at airport for ₹500                          │
  │                                                                        │
  │  AUTHORIZE (immediately):                                              │
  │    Uber asks bank: "Can this card pay ₹500?"                          │
  │    Bank: "Yes, I've RESERVED ₹500" (not yet charged!)                 │
  │    Your available balance: ₹10,000 → ₹9,500                           │
  │                                                                        │
  │  CAPTURE (after ride):                                                 │
  │    Ride cost ₹450 (shorter route)                                     │
  │    Uber captures ₹450 (not ₹500!)                                     │
  │    Remaining ₹50 released back to you                                 │
  │                                                                        │
  │  WHY SEPARATE?                                                         │
  │    - Final amount unknown at booking                                   │
  │    - Can void if customer cancels                                      │
  │    - Hotel holds for incidentals                                       │
  └────────────────────────────────────────────────────────────────────────┘


DETAILED CARD FLOW:

1. CUSTOMER ENTERS CARD
   
   Browser collects:
   {
     card_number: "4532123456789012",
     expiry: "12/26",
     cvv: "123",
     name: "JOHN DOE"
   }
   
   SECURITY: This NEVER touches your server!
   Client sends directly to payment gateway (Razorpay)
   Gateway returns token: "tok_1234abc"

2. MERCHANT CREATES PAYMENT
   
   POST /v1/payments
   {
     amount: 100000,        // ₹1000 in paise
     currency: "INR",
     token: "tok_1234abc",  // Tokenized card
     capture: true          // Authorize + Capture together
   }

3. GATEWAY SENDS TO ACQUIRER
   
   HTTP to HDFC Bank:
   {
     merchant_id: "FLIP12345",
     amount: 100000,
     card_token: encrypted,
     mcc: "5411"  // Merchant Category Code
   }

4. ACQUIRER ROUTES TO NETWORK
   
   ISO 8583 message to Visa:
   {
     message_type: "0100",  // Authorization
     pan: encrypted,
     amount: 100000,
     merchant_details: {...}
   }

5. NETWORK ROUTES TO ISSUER
   
   Visa finds ICICI Bank (from BIN)
   Forwards authorization request

6. ISSUER VALIDATES
   
   ICICI checks:
   ✓ Card not expired?
   ✓ Card not blocked?
   ✓ Sufficient balance?
   ✓ Fraud rules pass?
   ✓ CVV matches?
   
   If 3D Secure required:
     Returns: "Please authenticate via OTP"

7. 3D SECURE (OTP)
   
   Customer redirected to bank page
   Enters OTP sent to phone
   Bank validates OTP

8. AUTHORIZATION RESPONSE
   
   ICICI → Visa → HDFC → Razorpay → Flipkart
   
   Response:
   {
     status: "approved",
     auth_code: "A12345",
     rrn: "123456789012"  // Retrieval Reference Number
   }

9. SETTLEMENT (End of Day)
   
   Visa settles with banks
   ICICI debits customer, credits Visa
   Visa credits HDFC
   HDFC credits Flipkart (minus fees)
   
   T+1 or T+2 days for actual money transfer
```

---

## 3.2 UPI Payments (India)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              UPI PAYMENT FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

UPI = Unified Payments Interface (NPCI)
Direct bank-to-bank, no cards!

UPI ID: yourname@okaxis, phone@ybl

FLOW OPTIONS:

1. COLLECT REQUEST (Merchant initiates)
   
   Merchant → "Please pay ₹500 to merchant@razorpay"
   Customer gets notification in GPay/PhonePe
   Customer approves with PIN
   Money moves instantly!

2. INTENT (QR Code / Deep Link)
   
   Customer scans QR
   Opens UPI app
   Confirms and enters PIN
   
   QR contains: upi://pay?pa=merchant@razorpay&pn=Swiggy&am=500

3. UPI MANDATE (Recurring)
   
   Customer pre-approves: "Auto-debit ₹499/month for Netflix"
   Monthly debit happens automatically
   New RBI rules: Customer notified 24 hrs before


TECHNICAL FLOW:

1. CREATE PAYMENT ORDER
   
   POST /v1/orders
   {
     amount: 50000,
     currency: "INR",
     method: "upi"
   }
   
   Response:
   {
     order_id: "order_abc123",
     payment_link: "upi://pay?...",
     qr_code: "base64..."
   }

2. CUSTOMER PAYS
   
   Opens GPay → Scans QR → Enters PIN

3. UPI CALLBACK (NPCI → Gateway)
   
   {
     txn_id: "AXI123456789",
     status: "SUCCESS",
     rrn: "123456789012",
     payer_vpa: "customer@oksbi"
   }

4. WEBHOOK TO MERCHANT
   
   POST merchant.com/webhooks
   {
     event: "payment.captured",
     order_id: "order_abc123",
     amount: 50000
   }


UPI ADVANTAGES:
  - Instant settlement (T+0)
  - Lower fees than cards (0.3% vs 2%)
  - No CVV/OTP friction
  - Works offline (USSD)
```

---

# 4. DETAILED HLD ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT GATEWAY ARCHITECTURE                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                             MERCHANT APPLICATIONS
           ┌───────────────────────────────────────────────────────────────────────────┐
           │    Web Checkout     Mobile SDK      Server-to-Server      POS             │
           └───────────────────────────────────────────────────────────────────────────┘
                                              │
                            ┌─────────────────┴─────────────────┐
                            │ HTTPS + Idempotency-Key Header    │
                            ▼                                   ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                            API GATEWAY                                      │
           │   ┌─────────────────────────────────────────────────────────────────────┐ │
           │   │  Rate Limiting │ Auth │ Request Validation │ Idempotency Check     │ │
           │   └─────────────────────────────────────────────────────────────────────┘ │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
        ┌─────────────────────────────────────┼─────────────────────────────────────────┐
        ▼                                     ▼                                         ▼
┌───────────────────┐               ┌───────────────────┐               ┌───────────────────┐
│  PAYMENT SERVICE  │               │   ORDER SERVICE   │               │   TOKEN VAULT     │
├───────────────────┤               ├───────────────────┤               ├───────────────────┤
│ • Create payment  │               │ • Create order    │               │ • Store cards     │
│ • Process auth    │               │ • Track status    │               │ • Tokenize        │
│ • Handle capture  │               │ • Link payments   │               │ • Detokenize      │
│ • Process refund  │               │                   │               │ • PCI compliant   │
└───────────────────┘               └───────────────────┘               └───────────────────┘
        │                                     │                                         │
        └─────────────────────────────────────┼─────────────────────────────────────────┘
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         PAYMENT ROUTER                                       │
           │                                                                             │
           │   Routes to best processor based on:                                        │
           │   • Payment method (Card → Visa, UPI → NPCI)                               │
           │   • Success rate per bank                                                   │
           │   • Cost (interchange fees)                                                 │
           │   • Latency                                                                 │
           │   • Merchant preferences                                                    │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
        ┌──────────────┬──────────────┬───────┴───────┬──────────────┬──────────────┐
        ▼              ▼              ▼               ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │  HDFC   │   │  ICICI  │   │  NPCI   │   │  Paytm  │   │ PayPal  │   │ Stripe  │
   │ Acquirer│   │ Acquirer│   │  (UPI)  │   │ Wallet  │   │         │   │ Connect │
   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘


           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                          ASYNC PROCESSING                                   │
           │                                                                             │
           │   ┌───────────────┐     ┌───────────────┐     ┌───────────────┐           │
           │   │ FRAUD ENGINE  │     │ WEBHOOK SVC   │     │ LEDGER SVC    │           │
           │   ├───────────────┤     ├───────────────┤     ├───────────────┤           │
           │   │ ML scoring    │     │ Retry logic   │     │ Double-entry  │           │
           │   │ Rules engine  │     │ Delivery track│     │ Reconciliation│           │
           │   │ Block/Allow   │     │ Signatures    │     │ Settlement    │           │
           │   └───────────────┘     └───────────────┘     └───────────────┘           │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                          DATA LAYER                                         │
           │                                                                             │
           │   PostgreSQL          Redis              Cassandra          Vault           │
           │   (Transactions)      (Cache/Locks)      (Events)          (Secrets)        │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. THE IDEMPOTENCY PATTERN (MOST CRITICAL!)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              WHY IDEMPOTENCY MATTERS                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

DISASTER SCENARIO:

Customer on Swiggy, orders food for ₹500
Clicks "Pay"... page hangs... clicks again
Network was slow, both requests reach server!

WITHOUT IDEMPOTENCY:
  Request 1: Charge ₹500 ✓
  Request 2: Charge ₹500 ✓
  Customer charged ₹1000!!! 💀

WITH IDEMPOTENCY:
  Request 1: Charge ₹500 ✓
  Request 2: "Already processed, returning same result" ✓
  Customer charged ₹500 only! ✓


HOW IT WORKS:

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  MERCHANT GENERATES UNIQUE KEY PER PAYMENT ATTEMPT                                                 │
│                                                                                                     │
│  POST /v1/payments                                                                                 │
│  Idempotency-Key: "order_123_attempt_1"    ← Unique per attempt                                   │
│  {                                                                                                 │
│    amount: 50000,                                                                                  │
│    currency: "INR"                                                                                 │
│  }                                                                                                 │
│                                                                                                     │
│  Key format suggestions:                                                                           │
│    - order_{order_id}_pay_{timestamp}                                                              │
│    - {uuid_v4}                                                                                     │
│    - {merchant_id}_{order_id}_{attempt}                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘


SERVER-SIDE FLOW:

def process_payment(request, idempotency_key):
    
    # Step 1: Check if key exists
    existing = redis.get(f"idempotency:{idempotency_key}")
    
    if existing:
        if existing.status == "completed":
            # Already processed! Return cached response
            return existing.response
        
        if existing.status == "processing":
            # Another request in progress!
            return Error("Payment in progress, please wait")
    
    # Step 2: Lock the key
    acquired = redis.set(
        f"idempotency:{idempotency_key}",
        {"status": "processing"},
        nx=True,  # Only if not exists
        ex=86400  # 24 hour expiry
    )
    
    if not acquired:
        # Race condition - another request got it
        return retry_after_delay()
    
    try:
        # Step 3: Process payment
        result = charge_card(request)
        
        # Step 4: Cache result
        redis.set(
            f"idempotency:{idempotency_key}",
            {"status": "completed", "response": result},
            ex=86400
        )
        
        return result
        
    except Exception as e:
        # Allow retry on failure
        redis.delete(f"idempotency:{idempotency_key}")
        raise e


DATABASE SCHEMA:

CREATE TABLE idempotency_keys (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    merchant_id     UUID NOT NULL,
    status          VARCHAR(20),  -- 'processing', 'completed'
    request_hash    VARCHAR(64),  -- SHA256 of request body
    response_body   JSONB,
    created_at      TIMESTAMP DEFAULT NOW(),
    expires_at      TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
);

-- Important: Same key, different request body = ERROR!
-- Prevent merchant from reusing key for different payment
```

---

# 6. REQUEST FLOWS FOR EACH FEATURE

## Flow 1: Complete Payment Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPLETE PAYMENT FLOW                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

STEP 1: CREATE ORDER (Merchant Backend)
─────────────────────────────────────────
Merchant: "Customer wants to pay ₹1000"

POST /v1/orders
Headers:
  Authorization: Bearer sk_live_xxxxx
  Content-Type: application/json
Body:
{
  "amount": 100000,      // In smallest unit (paise)
  "currency": "INR",
  "receipt": "order_123",
  "notes": {
    "customer_id": "cust_456",
    "product": "iPhone 15"
  }
}

Response:
{
  "id": "order_abc123",
  "amount": 100000,
  "currency": "INR",
  "status": "created",
  "created_at": 1707325800
}


STEP 2: COLLECT PAYMENT DETAILS (Frontend)
──────────────────────────────────────────
Customer on checkout page:
  - Sees payment options (Card, UPI, NetBanking)
  - Enters card: 4532 1234 5678 9012
  - Our SDK tokenizes immediately (never hits merchant server!)

Razorpay.js:
  Token: "tok_1234abcd"


STEP 3: CREATE PAYMENT (Merchant Backend)
─────────────────────────────────────────
Merchant submits payment:

POST /v1/payments
Headers:
  Authorization: Bearer sk_live_xxxxx
  Idempotency-Key: "order_123_pay_1707325800"
Body:
{
  "order_id": "order_abc123",
  "amount": 100000,
  "currency": "INR",
  "payment_method": "tok_1234abcd",
  "capture": true
}


STEP 4: FRAUD CHECK (Internal)
──────────────────────────────
Before charging, check fraud:

Input to ML Model:
{
  "amount": 100000,
  "card_country": "IN",
  "customer_ip": "103.21.x.x",
  "device_id": "dev_123",
  "velocity": 3,  // 3rd transaction today
  "card_bin": "453212"
}

Output:
{
  "risk_score": 15,  // 0-100, lower is safer
  "decision": "allow",
  "reasons": []
}


STEP 5: ROUTE TO PROCESSOR
──────────────────────────
Payment Router decides:
  - Card BIN 453212 = HDFC issued card
  - Best acquirer for HDFC cards: ICICI Acquirer (98% success rate)
  - Route to ICICI


STEP 6: AUTHORIZE WITH BANK
───────────────────────────
Gateway → Acquirer → Card Network → Issuing Bank

ISO 8583 Authorization Request:
{
  "mti": "0100",        // Message Type: Authorization
  "pan": "4532...9012", // Card number (encrypted)
  "amount": "100000",
  "currency": "356",    // INR
  "merchant_id": "RAZORPAY001",
  "terminal_id": "TERM001",
  "mcc": "5411"         // Grocery stores
}

Bank Response:
{
  "mti": "0110",        // Authorization Response
  "response_code": "00", // Approved
  "auth_code": "A12345",
  "rrn": "407123456789"
}


STEP 7: 3D SECURE (If Required)
───────────────────────────────
Bank requires OTP for security:

Response to Gateway:
{
  "status": "3ds_required",
  "redirect_url": "https://acs.icicibank.com/3ds/...",
  "pareq": "base64encodeddata..."
}

Customer redirected to bank page:
  - Sees "Enter OTP sent to 98XXX12345"
  - Enters OTP: 123456
  - Bank validates
  
Bank callback:
{
  "status": "authenticated",
  "cavv": "base64authenticationvalue",
  "eci": "05"  // Fully authenticated
}


STEP 8: COMPLETE AUTHORIZATION
──────────────────────────────
With 3DS complete, finalize auth:

Bank Response:
{
  "response_code": "00",
  "auth_code": "A12345",
  "message": "Approved"
}


STEP 9: CAPTURE (If auto-capture enabled)
─────────────────────────────────────────
Immediately after auth, capture funds:

ISO 8583 Capture Request:
{
  "mti": "0200",         // Financial transaction
  "original_auth": "A12345",
  "amount": "100000"
}


STEP 10: UPDATE DATABASE
────────────────────────
Within transaction:

BEGIN;

-- Create payment record
INSERT INTO payments (
  payment_id, order_id, merchant_id, amount, status,
  processor, auth_code, captured_at
) VALUES (
  'pay_xyz', 'order_abc123', 'merch_001', 100000, 'captured',
  'ICICI', 'A12345', NOW()
);

-- Create ledger entries (double-entry!)
INSERT INTO ledger_entries (payment_id, account, type, amount) VALUES
  ('pay_xyz', 'customer_receivable', 'debit', 100000),
  ('pay_xyz', 'merchant_payable', 'credit', 98000),
  ('pay_xyz', 'platform_revenue', 'credit', 2000);

-- Update idempotency key
UPDATE idempotency_keys 
SET status = 'completed', response = '{"payment_id": "pay_xyz"}'
WHERE key = 'order_123_pay_1707325800';

COMMIT;


STEP 11: PUBLISH EVENTS
───────────────────────
Kafka event:
{
  "topic": "payment.captured",
  "key": "pay_xyz",
  "value": {
    "payment_id": "pay_xyz",
    "order_id": "order_abc123",
    "merchant_id": "merch_001",
    "amount": 100000,
    "captured_at": "2024-02-07T15:30:00Z"
  }
}


STEP 12: WEBHOOK TO MERCHANT
────────────────────────────
Webhook Service consumes event, sends to merchant:

POST https://merchant.com/webhooks/razorpay
Headers:
  X-Razorpay-Signature: sha256=abc123...
  Content-Type: application/json
Body:
{
  "event": "payment.captured",
  "payload": {
    "payment": {
      "id": "pay_xyz",
      "order_id": "order_abc123",
      "amount": 100000,
      "status": "captured"
    }
  }
}

Merchant responds: 200 OK


STEP 13: RETURN TO CUSTOMER
───────────────────────────
Customer sees: "Payment Successful! ₹1,000 paid to Flipkart"
Order confirmed, email sent!
```

---

## Flow 2: Refund Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REFUND FLOW                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Customer returns item, merchant initiates refund

STEP 1: MERCHANT REQUESTS REFUND
────────────────────────────────
Customer contacts support: "I want to return this"
Merchant initiates through dashboard or API:

POST /v1/payments/pay_xyz/refunds
Headers:
  Idempotency-Key: "refund_pay_xyz_1"
Body:
{
  "amount": 50000,  // Partial refund: ₹500 of ₹1000
  "reason": "customer_request",
  "notes": {
    "return_id": "return_456"
  }
}


STEP 2: VALIDATE REFUND
───────────────────────
Checks:
  ✓ Payment exists and is captured?
  ✓ Refund amount <= (captured - already_refunded)?
  ✓ Within refund window (usually 180 days)?
  ✓ Idempotency key not used?


STEP 3: PROCESS REFUND
──────────────────────
Card refund via bank:

ISO 8583 Reversal:
{
  "mti": "0400",         // Reversal
  "original_rrn": "407123456789",
  "amount": "50000"
}

Bank Response:
{
  "response_code": "00",
  "refund_rrn": "407987654321"
}


STEP 4: UPDATE LEDGER
─────────────────────
Reverse the money flow:

INSERT INTO ledger_entries (payment_id, account, type, amount) VALUES
  ('pay_xyz', 'customer_receivable', 'credit', 50000),  -- Return to customer
  ('pay_xyz', 'merchant_payable', 'debit', 50000);      -- Take from merchant

-- Platform fee usually NOT refunded!
-- Merchant effectively loses: ₹500 + ₹10 (original fee) = ₹510


STEP 5: UPDATE PAYMENT
──────────────────────
UPDATE payments 
SET amount_refunded = amount_refunded + 50000,
    status = CASE 
      WHEN amount_refunded + 50000 = amount_captured THEN 'refunded'
      ELSE 'partially_refunded'
    END
WHERE payment_id = 'pay_xyz';


STEP 6: NOTIFY
──────────────
Webhook: payment.refunded
Email to customer: "Refund of ₹500 initiated"

TIMELINE:
  - Cards: 5-7 business days
  - UPI: Instant
  - NetBanking: 3-5 business days
```

---

## Flow 3: Subscription/Recurring Payments

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SUBSCRIPTION FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Netflix ₹499/month subscription

STEP 1: CREATE SUBSCRIPTION
───────────────────────────
Customer signs up for Netflix:

POST /v1/subscriptions
{
  "plan_id": "plan_netflix_monthly",
  "customer_id": "cust_123",
  "payment_method": "tok_card_visa",
  "billing_cycle_anchor": "2024-02-07",  // Bill on 7th of each month
  "metadata": {
    "plan_name": "Premium 4K"
  }
}

Response:
{
  "id": "sub_abc123",
  "status": "active",
  "current_period_start": "2024-02-07",
  "current_period_end": "2024-03-07",
  "next_billing_date": "2024-03-07"
}


STEP 2: INITIAL CHARGE
──────────────────────
Immediately charge first month:

Create payment with subscription context:
{
  payment_id: "pay_sub_1",
  subscription_id: "sub_abc123",
  amount: 49900,
  type: "recurring"
}


STEP 3: SCHEDULER RUNS DAILY
────────────────────────────
Cron job at 6 AM:

SELECT * FROM subscriptions 
WHERE status = 'active' 
AND next_billing_date = CURRENT_DATE;

Found: sub_abc123 (Netflix for customer 123)


STEP 4: ATTEMPT CHARGE
──────────────────────
For each due subscription:

result = charge_saved_card(
  customer_id: "cust_123",
  amount: 49900,
  description: "Netflix Premium - Mar 2024"
)


STEP 5: HANDLE SUCCESS/FAILURE
──────────────────────────────
IF SUCCESS:
  Update subscription:
    next_billing_date = "2024-04-07"
    current_period_start = "2024-03-07"
    current_period_end = "2024-04-07"
  
  Send invoice email to customer

IF FAILURE:
  Enter DUNNING MANAGEMENT:
  
  Attempt 1 (Day 0): Failed - Card declined
  Attempt 2 (Day 3): Retry with same card
  Attempt 3 (Day 7): Retry + Email "Update payment method"
  Attempt 4 (Day 10): Final attempt + SMS
  Day 14: Suspend subscription
  Day 30: Cancel subscription
  
  Customer can update card anytime to resume


STEP 6: CUSTOMER CANCELS
────────────────────────
POST /v1/subscriptions/sub_abc123/cancel
{
  "cancel_at_period_end": true  // Access until period ends
}

Subscription continues until March 7
Then status = "cancelled", no more charges
```

---

## Flow 4: Dispute/Chargeback

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DISPUTE/CHARGEBACK FLOW                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Customer tells bank "I didn't make this purchase!"

WHAT IS A CHARGEBACK?
  Customer disputes transaction directly with their bank
  Bank investigates and may forcibly reverse the payment
  Merchant loses money + pays chargeback fee (~₹500-1500)


STEP 1: CUSTOMER CONTACTS BANK
──────────────────────────────
Customer: "I see ₹5000 charge from 'Merchant XYZ' that I didn't make!"

Bank creates dispute:
  Reason code: 4837 (No Cardholder Authorization)
  Dispute amount: ₹5000


STEP 2: BANK NOTIFIES GATEWAY
─────────────────────────────
Card network sends dispute notification:

{
  "dispute_id": "disp_123",
  "payment_id": "pay_xyz",
  "amount": 500000,
  "reason_code": "4837",
  "reason": "No Cardholder Authorization",
  "evidence_due_by": "2024-02-21"
}


STEP 3: GATEWAY NOTIFIES MERCHANT
─────────────────────────────────
Webhook: payment.dispute.created

{
  "event": "payment.dispute.created",
  "data": {
    "dispute_id": "disp_123",
    "payment_id": "pay_xyz",
    "amount": 500000,
    "reason": "Customer claims unauthorized",
    "evidence_due_by": "2024-02-21"
  }
}

Funds immediately held from merchant balance!


STEP 4: MERCHANT SUBMITS EVIDENCE
─────────────────────────────────
Merchant must prove transaction was legitimate:

POST /v1/disputes/disp_123/evidence
{
  "evidence": {
    "customer_communication": "email_screenshot.pdf",
    "shipping_documentation": "tracking_info.pdf",
    "delivery_confirmation": "signed_receipt.pdf",
    "customer_signature": "signature.pdf",
    "service_documentation": "invoice.pdf"
  }
}

Evidence types by reason code:
  - Fraud: Show 3DS proof, IP matching delivery
  - Not received: Show delivery confirmation
  - Not as described: Show product description, correspondence
  - Duplicate: Show both transactions are different


STEP 5: BANK REVIEWS
────────────────────
Bank/Card network reviews evidence
Decision within 30-90 days


STEP 6: RESOLUTION
──────────────────
OUTCOME A: MERCHANT WINS
  - Funds released back to merchant
  - Webhook: payment.dispute.won
  - Customer doesn't get money back

OUTCOME B: CUSTOMER WINS (Merchant loses)
  - ₹5000 permanently reversed
  - ₹1000 chargeback fee charged to merchant
  - Webhook: payment.dispute.lost
  - Too many disputes = merchant account terminated!


CHARGEBACK RATES:
  Healthy: < 0.5% of transactions
  Warning: 0.5% - 1%
  Dangerous: > 1% (card networks may terminate merchant)
```

---

## Flow 5: Settlement

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SETTLEMENT FLOW                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

WHAT IS SETTLEMENT?
  Customer paid ₹1000
  Gateway collected it
  Now gateway must transfer to merchant's bank account
  (After deducting fees)


DAILY SETTLEMENT PROCESS:

STEP 1: END OF DAY AGGREGATION
──────────────────────────────
11:59 PM: Calculate merchant's earnings for the day

SELECT 
  merchant_id,
  SUM(amount_captured) as total_captured,
  SUM(amount_refunded) as total_refunded,
  COUNT(*) as transaction_count
FROM payments
WHERE merchant_id = 'merch_001'
AND captured_at BETWEEN '2024-02-07 00:00' AND '2024-02-07 23:59'
GROUP BY merchant_id;

Result:
  Captured: ₹1,00,000
  Refunded: ₹5,000
  Net: ₹95,000


STEP 2: CALCULATE FEES
──────────────────────
Gross: ₹95,000
Gateway Fee (2%): ₹1,900
GST on Fee (18%): ₹342

Net Payable: ₹95,000 - ₹1,900 - ₹342 = ₹92,758


STEP 3: CREATE SETTLEMENT RECORD
────────────────────────────────
INSERT INTO settlements (
  settlement_id, merchant_id, 
  gross_amount, fees, tax, net_amount,
  status, settlement_date
) VALUES (
  'stl_123', 'merch_001',
  9500000, 190000, 34200, 9275800,
  'pending', '2024-02-08'
);


STEP 4: INITIATE BANK TRANSFER
──────────────────────────────
For each merchant's settlement:

NEFT/IMPS/RTGS request:
{
  "beneficiary_account": "1234567890",
  "beneficiary_ifsc": "HDFC0001234",
  "beneficiary_name": "Merchant Pvt Ltd",
  "amount": 9275800,  // ₹92,758
  "reference": "STL_123_20240208"
}


STEP 5: BANK CONFIRMS
─────────────────────
Bank API callback:
{
  "status": "success",
  "utr": "HDFC2024020812345"  // Unique Transaction Reference
}


STEP 6: UPDATE STATUS
─────────────────────
UPDATE settlements 
SET status = 'completed', 
    utr = 'HDFC2024020812345',
    completed_at = NOW()
WHERE settlement_id = 'stl_123';


STEP 7: NOTIFY MERCHANT
───────────────────────
Email: "Settlement of ₹92,758 transferred to your account"

Dashboard shows:
  Settlement ID: stl_123
  Status: Completed ✓
  UTR: HDFC2024020812345
  Amount: ₹92,758


SETTLEMENT SCHEDULES:
  T+1: Next business day (premium)
  T+2: 2 business days (standard)
  T+7: Weekly (some merchants)
  On-demand: Instant settlement (higher fees)
```

---

# 7. DOUBLE-ENTRY LEDGER SYSTEM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DOUBLE-ENTRY ACCOUNTING                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

WHY DOUBLE-ENTRY?

Every money movement has TWO sides:
  - Money comes FROM somewhere
  - Money goes TO somewhere

RULE: Total Debits = Total Credits (ALWAYS!)

If they don't match → Something is WRONG!


ACCOUNTS IN PAYMENT SYSTEM:

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│  Account Type          │ Examples                              │ Debit =      │ Credit =           │
├────────────────────────┼───────────────────────────────────────┼──────────────┼─────────────────────┤
│  ASSETS                │ Cash, Bank, Receivables               │ Increase     │ Decrease            │
│  LIABILITIES           │ Merchant Payable, Refunds Due         │ Decrease     │ Increase            │
│  REVENUE               │ Platform Fees, Interest               │ Decrease     │ Increase            │
│  EXPENSES              │ Processing Costs, Fraud Loss          │ Increase     │ Decrease            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘


EXAMPLE: ₹1000 PAYMENT WITH 2% FEE

Customer pays ₹1000 to merchant:

Entry 1: Money received from customer
  DEBIT   Cash (Asset)                     +₹1000
  
Entry 2: Owe money to merchant  
  CREDIT  Merchant Payable (Liability)     +₹980
  
Entry 3: We earned fee
  CREDIT  Platform Revenue                 +₹20

CHECK: Debits (₹1000) = Credits (₹980 + ₹20 = ₹1000) ✓


LEDGER TABLE:

| Entry ID | Payment ID | Account              | Type   | Amount |
|----------|------------|----------------------|--------|--------|
| L001     | pay_xyz    | cash                 | debit  | 100000 |
| L002     | pay_xyz    | merchant_payable     | credit | 98000  |
| L003     | pay_xyz    | platform_revenue     | credit | 2000   |


REFUND ENTRIES:

₹500 refund:

| Entry ID | Payment ID | Account              | Type   | Amount |
|----------|------------|----------------------|--------|--------|
| L004     | pay_xyz    | cash                 | credit | 50000  |  ← Money going out
| L005     | pay_xyz    | merchant_payable     | debit  | 50000  |  ← Reduce what we owe

Note: We don't refund our fee! Merchant loses ₹500 + fee they paid.


RECONCILIATION:

Daily:
  1. Sum all our bank accounts
  2. Compare with ledger totals
  3. Investigate any mismatch!

This catches:
  - Missed webhooks
  - Double processing
  - System bugs
  - Fraud
```

---

# 8. DATABASE SCHEMA

```sql
-- Payments (Core)
CREATE TABLE payments (
    payment_id      VARCHAR(50) PRIMARY KEY,
    order_id        VARCHAR(50),
    merchant_id     VARCHAR(50) NOT NULL,
    
    -- Money
    amount          BIGINT NOT NULL,
    currency        VARCHAR(3) DEFAULT 'INR',
    
    -- Status
    status          VARCHAR(30) NOT NULL,
    
    -- Payment method
    method          VARCHAR(30),  -- card, upi, netbanking
    method_details  JSONB,        -- {card_last4: "4242", card_brand: "visa"}
    
    -- Processor info
    processor       VARCHAR(50),
    auth_code       VARCHAR(50),
    rrn             VARCHAR(50),
    
    -- Amounts
    amount_refunded BIGINT DEFAULT 0,
    
    -- Timestamps
    created_at      TIMESTAMP DEFAULT NOW(),
    authorized_at   TIMESTAMP,
    captured_at     TIMESTAMP,
    
    -- Idempotency
    idempotency_key VARCHAR(255) UNIQUE
);

-- Ledger entries (immutable!)
CREATE TABLE ledger_entries (
    entry_id        SERIAL PRIMARY KEY,
    payment_id      VARCHAR(50) NOT NULL,
    account_name    VARCHAR(100) NOT NULL,
    entry_type      VARCHAR(10) NOT NULL,  -- 'debit' or 'credit'
    amount          BIGINT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Never UPDATE or DELETE ledger entries!
-- Only INSERT (append-only for audit trail)

-- Settlements
CREATE TABLE settlements (
    settlement_id   VARCHAR(50) PRIMARY KEY,
    merchant_id     VARCHAR(50) NOT NULL,
    gross_amount    BIGINT NOT NULL,
    fees            BIGINT NOT NULL,
    net_amount      BIGINT NOT NULL,
    status          VARCHAR(30),  -- pending, processing, completed, failed
    settlement_date DATE,
    utr             VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Webhooks (for retry tracking)
CREATE TABLE webhook_deliveries (
    webhook_id      VARCHAR(50) PRIMARY KEY,
    merchant_id     VARCHAR(50),
    event_type      VARCHAR(50),
    payload         JSONB,
    status          VARCHAR(20),  -- pending, delivered, failed
    attempts        INT DEFAULT 0,
    next_attempt_at TIMESTAMP,
    delivered_at    TIMESTAMP
);
```

---

# 9. INTERVIEW QUESTIONS & ANSWERS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT SYSTEM INTERVIEW Q&A                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Q1: How do you prevent double charging?
────────────────────────────────────────
Answer:
  - Idempotency keys (client-generated, unique per attempt)
  - Store key with request hash in Redis with TTL
  - If key exists with completed status → return cached response
  - If key exists with processing status → reject (another request in progress)
  - Use SETNX/INSERT ON CONFLICT for atomic locking


Q2: What happens when payment succeeds but order update fails?
────────────────────────────────────────────────────────────────
Answer: Distributed transaction problem! Solutions:

  Option A: Saga Pattern
    - Payment Service charges card
    - Publishes "payment.success" event
    - Order Service listens and updates
    - If Order update fails → trigger compensating transaction (refund)
  
  Option B: Outbox Pattern
    - Write payment + event to same DB in single transaction
    - Separate process reads outbox and publishes to Kafka
    - Guarantees event published if payment persisted


Q3: Why separate Authorization and Capture?
───────────────────────────────────────────
Answer:
  - Auth = "Reserve money" (not charged yet)
  - Capture = "Actually take the money"
  
  Use cases:
    - Hotel: Auth at check-in, capture at checkout (final bill)
    - E-commerce: Auth at order, capture at shipping
    - Car rental: Auth extra for damages, capture/void later
  
  Benefits:
    - Verify inventory/fulfillment before charging
    - Handle cancellations gracefully (void vs refund)
    - Lower chargeback risk


Q4: How do webhooks work reliably?
──────────────────────────────────
Answer:
  - At-least-once delivery (NOT exactly-once)
  - Exponential backoff retry: 1min, 5min, 30min, 2hr, 8hr...
  - Merchants must deduplicate using event_id
  - HMAC signature for verification
  - Timestamp to prevent replay attacks
  - Dead letter queue after max retries


Q5: Explain the double-entry ledger system
──────────────────────────────────────────
Answer:
  Every transaction has balanced debit and credit entries.
  
  Payment received:
    DEBIT  Cash          +₹1000
    CREDIT Merchant Due  +₹980
    CREDIT Revenue       +₹20
  
  Benefits:
    - Audit trail (every rupee accounted for)
    - Reconciliation (match with bank statements)
    - Error detection (imbalance = bug!)


Q6: How do you handle 50,000 TPS during sales?
──────────────────────────────────────────────
Answer:
  1. Redis for hot path (idempotency, rate limits)
  2. Kafka for async processing (webhooks, notifications)
  3. Shard by merchant_id
  4. Read replicas for queries
  5. Auto-scaling based on queue depth
  6. Circuit breakers to failing processors
  7. Fallback routing if primary processor overwhelmed


Q7: PCI DSS Compliance - How to handle card data?
──────────────────────────────────────────────────
Answer:
  - NEVER store raw card numbers on your servers
  - Client-side tokenization (Razorpay.js sends to us directly)
  - Token stored in HSM (Hardware Security Module)
  - Encrypted at rest (AES-256)
  - Encrypted in transit (TLS 1.3)
  - Network segmentation
  - Regular security audits
  - Compliant with PCI-DSS Level 1
```

---

# 10. QUICK REFERENCE CHEAT SHEET

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT SYSTEM CHEAT SHEET                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CARD PAYMENT FLOW:
  Customer → Merchant → Gateway → Acquirer → Card Network → Issuing Bank
  (reverse for response)

KEY CONCEPTS:
  • Authorization: Reserve funds
  • Capture: Actually charge
  • Void: Cancel authorization
  • Refund: Return captured funds
  • Settlement: Transfer to merchant bank

IDEMPOTENCY:
  • Client sends unique key per attempt
  • Server caches response by key
  • Same key = return cached (no double charge!)

DOUBLE-ENTRY:
  • Every transaction: Debit = Credit
  • Immutable entries only
  • Enables reconciliation

WEBHOOKS:
  • At-least-once delivery
  • HMAC signature verification
  • Exponential backoff retry
  • Merchant must deduplicate

TIMELINE:
  • Authorization: 2-3 seconds
  • Capture: Immediate
  • Refund arrival: 5-7 days (cards), instant (UPI)
  • Settlement: T+1 or T+2 days

FEES:
  • Interchange: 1.5-2% (to issuing bank)
  • Network: 0.1-0.3% (to Visa/MC)
  • Gateway: 2% (to Razorpay/Stripe)
  
DISPUTE RATE:
  • Healthy: < 0.5%
  • Dangerous: > 1% (account termination risk)
```

---
