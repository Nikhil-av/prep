# Notification System — Complete Deep Dive

> Interview-ready documentation — Covers Push Notifications, Email, SMS, In-App Notifications

---

# 1. WHAT IS A NOTIFICATION SYSTEM?

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATION SYSTEM OVERVIEW                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

A Notification System sends messages to users across multiple channels:

CHANNELS:
  • Push Notifications (iOS, Android, Web)
  • Email
  • SMS
  • In-App Notifications
  • WhatsApp / Telegram

EXAMPLES:
  • Swiggy: "Your order has been delivered!"
  • Amazon: "Your package is out for delivery"
  • Instagram: "john_doe liked your photo"
  • Bank: "OTP for transaction is 123456"

SCALE (Large Platform):
  • Notifications/day: 1 billion
  • Push sent/sec: 50,000+
  • Email sent/day: 100 million
  • SMS sent/day: 10 million
```

---

# 2. FUNCTIONAL REQUIREMENTS

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Multi-Channel** | Push, Email, SMS, In-App |
| 2 | **Templating** | Reusable message templates |
| 3 | **Personalization** | Insert user-specific data |
| 4 | **User Preferences** | Opt-in/out per channel, DND hours |
| 5 | **Rate Limiting** | Max N notifications per hour to user |
| 6 | **Scheduling** | Send at specific time |
| 7 | **Priority** | Urgent (OTP) vs marketing |
| 8 | **Analytics** | Delivery, open, click tracking |
| 9 | **Retry & Failover** | Retry failed, fallback channels |
| 10 | **Batch Send** | Send to millions efficiently |

---

# 3. NON-FUNCTIONAL REQUIREMENTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SCALE & REQUIREMENTS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCALE:
  DAU:                    100 million
  Notifications/day:      1 billion
  Peak notifications/sec: 100,000
  
LATENCY:
  Critical (OTP):         < 5 seconds end-to-end
  Transactional:          < 30 seconds
  Marketing:              < 5 minutes
  
AVAILABILITY:
  99.9% for critical path
  
RELIABILITY:
  At-least-once delivery
  No duplicate OTPs (dedupe for critical)
```

---

# 4. NOTIFICATION CHANNELS DEEP DIVE

## 4.1 Push Notifications

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PUSH NOTIFICATION FLOW                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

HOW PUSH WORKS:

1. App registers with OS push service
   iOS → APNs (Apple Push Notification Service)
   Android → FCM (Firebase Cloud Messaging)
   Web → Web Push (VAPID)

2. OS returns device token
   iOS: a3f2d8b1...
   Android: cJz9Pk2qR...

3. App sends token to your backend
   You store: user_id → device_token

4. To send notification:
   You → APNs/FCM → Device


DEVICE TOKEN STORAGE:

user_id: U123
├── iOS: {token: "a3f2d8...", app_version: "2.1", last_active: "2024-02-07"}
├── Android: {token: "cJz9Pk...", app_version: "2.0", last_active: "2024-02-08"}
└── Web: {token: "BPyJf2...", browser: "Chrome", last_active: "2024-02-06"}

One user = multiple devices = multiple tokens!


APNs REQUEST:

POST /3/device/{device_token}
Headers:
  authorization: bearer {jwt}
  apns-topic: com.yourapp.ios
  apns-priority: 10
  apns-push-type: alert

Body:
{
  "aps": {
    "alert": {
      "title": "Order Delivered!",
      "body": "Your order #123 has been delivered"
    },
    "sound": "default",
    "badge": 5
  },
  "order_id": "123"
}


FCM REQUEST:

POST https://fcm.googleapis.com/v1/projects/{project}/messages:send
Headers:
  Authorization: Bearer {oauth_token}

Body:
{
  "message": {
    "token": "cJz9Pk2qR...",
    "notification": {
      "title": "Order Delivered!",
      "body": "Your order #123 has been delivered"
    },
    "data": {
      "order_id": "123",
      "click_action": "OPEN_ORDER_DETAILS"
    },
    "android": {
      "priority": "high"
    }
  }
}


HANDLING TOKEN EXPIRY:

APNs/FCM may return:
  - Unregistered (app uninstalled)
  - Invalid token (expired/changed)

Action: Mark token as inactive, don't retry
```

---

## 4.2 Email

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              EMAIL NOTIFICATION FLOW                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

EMAIL PROVIDERS:
  • AWS SES (Simple Email Service)
  • SendGrid
  • Mailgun
  • Postmark

EMAIL TYPES:
  • Transactional: Order confirmation, OTP, password reset
  • Marketing: Promotions, newsletters
  • Triggered: Cart abandonment, inactive user

SENDING VIA AWS SES:

import boto3

ses = boto3.client('ses')

response = ses.send_email(
    Source='noreply@yourapp.com',
    Destination={
        'ToAddresses': ['user@example.com']
    },
    Message={
        'Subject': {'Data': 'Your order has shipped!'},
        'Body': {
            'Html': {'Data': '<h1>Order Shipped</h1><p>Track: ABC123</p>'},
            'Text': {'Data': 'Order Shipped. Track: ABC123'}
        }
    }
)


EMAIL DELIVERABILITY:

SPF (Sender Policy Framework):
  DNS TXT record listing authorized senders
  v=spf1 include:amazonses.com ~all

DKIM (DomainKeys Identified Mail):
  Cryptographic signature in email header
  Proves email wasn't modified

DMARC:
  Policy for handling SPF/DKIM failures


TRACKING:

Open Tracking:
  Embed invisible 1x1 pixel image
  <img src="https://track.yourapp.com/open/{email_id}">
  When loaded = email opened

Click Tracking:
  Replace links with tracking URL
  https://track.yourapp.com/click/{email_id}?url=actual_url
  Redirect to actual URL after recording


RATE LIMITS:

AWS SES: 14 emails/second (can increase)
SendGrid: Based on plan

WARM-UP:
  New IP/domain starts with low reputation
  Gradually increase volume over weeks
  High bounce = reputation damage
```

---

## 4.3 SMS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SMS NOTIFICATION FLOW                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SMS PROVIDERS:
  • Twilio
  • AWS SNS
  • Gupshup (India)
  • Plivo

USE CASES:
  • OTP (highest priority!)
  • Critical alerts
  • Delivery updates
  • Appointment reminders

SENDING VIA TWILIO:

from twilio.rest import Client

client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Your OTP is 123456. Valid for 5 minutes.",
    from_="+1234567890",
    to="+919876543210"
)


SMS ROUTING (India):

TRANSACTIONAL SMS:
  - 6-character sender ID (e.g., SWIGYY)
  - Template pre-registered with DLT
  - Can send 24x7
  - Example: "Your OTP is {#var#}. Valid for {#var#} minutes."

PROMOTIONAL SMS:
  - Numeric sender (e.g., 56789)
  - Only 9 AM - 9 PM
  - Can't send to DND numbers

DLT REGISTRATION (India):
  All SMS templates must be registered
  Template: "Dear {#var#}, your order {#var#} is confirmed."
  Entity ID: 123456789


SMS COSTS:
  India: ₹0.10 - ₹0.25 per SMS
  USA: $0.0075 per SMS
  International: $0.05 - $0.10
```

---

## 4.4 In-App Notifications

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              IN-APP NOTIFICATION FLOW                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

IN-APP = Notification inside your app (bell icon 🔔)

TYPES:
  • Activity feed (likes, comments, follows)
  • System messages
  • Promotions
  • Updates

STORAGE:

notifications table:
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ id       │ user_id │ type           │ content                        │ read   │ created_at       │
├──────────┼─────────┼────────────────┼────────────────────────────────┼────────┼──────────────────┤
│ N001     │ U123    │ like           │ {"actor": "john", "post": 456} │ false  │ 2024-02-08 10:00 │
│ N002     │ U123    │ comment        │ {"actor": "jane", "text": ...} │ false  │ 2024-02-08 10:05 │
│ N003     │ U123    │ order_update   │ {"order": 789, "status": ...}  │ true   │ 2024-02-08 09:00 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘


API:

GET /api/notifications?limit=20&before_id=N003

Response:
{
  "notifications": [
    {
      "id": "N002",
      "type": "comment",
      "message": "jane commented on your post",
      "read": false,
      "timestamp": "2024-02-08T10:05:00Z",
      "action_url": "/posts/456"
    },
    ...
  ],
  "unread_count": 5
}


REAL-TIME UPDATES:

Use WebSocket for live updates:

1. User opens app → connect WebSocket
2. New notification created
3. Push via WebSocket immediately
4. Client shows notification badge

Channel: ws://api.yourapp.com/notifications
Message: {"type": "new_notification", "data": {...}}


AGGREGATION:

Don't show 100 separate "X liked your post"!

Aggregate: "john, jane, and 98 others liked your post"

Implementation:
  • Group by (target, action_type) within time window
  • Store individual + aggregated view
  • Show aggregated in feed
```

---

# 5. DETAILED HLD ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATION SYSTEM ARCHITECTURE                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                              TRIGGER SOURCES
           ┌───────────────────────────────────────────────────────────────────────────┐
           │    Order Service    │  User Service  │  Marketing  │  Scheduled Jobs     │
           └───────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ Notification Request
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         NOTIFICATION SERVICE                                 │
           │                                                                             │
           │   ┌─────────────────────────────────────────────────────────────────────┐ │
           │   │  • Validate request                                                  │ │
           │   │  • Fetch user preferences                                            │ │
           │   │  • Check rate limits                                                 │ │
           │   │  • Apply DND rules                                                   │ │
           │   │  • Render template                                                   │ │
           │   │  • Route to channels                                                 │ │
           │   └─────────────────────────────────────────────────────────────────────┘ │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         MESSAGE QUEUE (Kafka)                                │
           │                                                                             │
           │   Topics:                                                                   │
           │   ├── notifications.push.high_priority    (OTP, critical)                  │
           │   ├── notifications.push.normal                                            │
           │   ├── notifications.email.transactional                                    │
           │   ├── notifications.email.marketing                                        │
           │   ├── notifications.sms                                                    │
           │   └── notifications.inapp                                                  │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                    │               │               │               │
                    ▼               ▼               ▼               ▼
           ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
           │ PUSH WORKER   │ │ EMAIL WORKER  │ │ SMS WORKER    │ │ INAPP WORKER  │
           ├───────────────┤ ├───────────────┤ ├───────────────┤ ├───────────────┤
           │ • Fetch tokens│ │ • Render HTML │ │ • DLT lookup  │ │ • Store in DB │
           │ • Send APNs   │ │ • Send SES    │ │ • Send Twilio │ │ • Push WS     │
           │ • Send FCM    │ │ • Track opens │ │ • Track status│ │ • Aggregate   │
           └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘
                    │               │               │               │
                    ▼               ▼               ▼               ▼
           ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
           │     APNs      │ │   AWS SES     │ │   Twilio      │ │   WebSocket   │
           │     FCM       │ │   SendGrid    │ │   Gupshup     │ │   Gateway     │
           └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘


           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                              DATA STORES                                     │
           │                                                                             │
           │   PostgreSQL           Redis                 Cassandra                      │
           │   ├─ Users             ├─ Rate limits        ├─ Notification logs          │
           │   ├─ Preferences       ├─ Device tokens      ├─ Delivery status            │
           │   ├─ Templates         ├─ Dedup cache        │                             │
           │   └─ Device mappings   └─ Unread counts      │                             │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. REQUEST FLOWS

## Flow 1: Sending a Push Notification

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PUSH NOTIFICATION FLOW                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

TRIGGER: Order delivered, send push to user

STEP 1: ORDER SERVICE CALLS NOTIFICATION SERVICE
─────────────────────────────────────────────────
POST /api/notifications/send
{
  "user_id": "U123",
  "type": "order_delivered",
  "template_id": "order_delivered_v1",
  "data": {
    "order_id": "ORD456",
    "restaurant": "Pizza Hut"
  },
  "channels": ["push", "inapp"],
  "priority": "normal"
}


STEP 2: VALIDATE & ENRICH
─────────────────────────
a) Fetch user preferences
   user_preferences:U123 = {
     push_enabled: true,
     dnd_start: "23:00",
     dnd_end: "07:00"
   }

b) Check DND (current time: 10:30)
   Not in DND window ✓

c) Check rate limit
   Redis: INCR notif_rate:U123:push → 5
   Limit: 10/hour → OK ✓


STEP 3: RENDER TEMPLATE
───────────────────────
Template: "order_delivered_v1"
  Title: "Order Delivered! 🎉"
  Body: "Your order from {{restaurant}} has been delivered."

Rendered:
  Title: "Order Delivered! 🎉"
  Body: "Your order from Pizza Hut has been delivered."


STEP 4: FETCH DEVICE TOKENS
───────────────────────────
Redis: device_tokens:U123 = [
  {type: "ios", token: "a3f2d8...", active: true},
  {type: "android", token: "cJz9Pk...", active: true}
]


STEP 5: PUBLISH TO QUEUE
────────────────────────
Kafka topic: notifications.push.normal

{
  "notification_id": "N789",
  "user_id": "U123",
  "devices": [
    {"type": "ios", "token": "a3f2d8..."},
    {"type": "android", "token": "cJz9Pk..."}
  ],
  "payload": {
    "title": "Order Delivered! 🎉",
    "body": "Your order from Pizza Hut has been delivered.",
    "data": {"order_id": "ORD456", "action": "open_order"}
  }
}


STEP 6: PUSH WORKER CONSUMES
────────────────────────────
Worker picks up message, sends to APNs and FCM concurrently

iOS (APNs):
  POST /3/device/a3f2d8...
  Response: 200 OK

Android (FCM):
  POST .../messages:send
  Response: {"name": "projects/.../messages/123"}


STEP 7: RECORD DELIVERY STATUS
──────────────────────────────
Cassandra: notification_delivery
{
  notification_id: "N789",
  user_id: "U123",
  channel: "push",
  status: "delivered",
  device: "ios",
  delivered_at: "2024-02-08T10:30:05Z"
}


STEP 8: TRACK ENGAGEMENT (Optional)
───────────────────────────────────
When user taps notification:
  App sends: POST /api/notifications/N789/clicked
  Record click event for analytics
```

---

## Flow 2: Sending OTP (Critical Path)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OTP NOTIFICATION FLOW                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

OTP is CRITICAL — must be fast, reliable, deduplicated

STEP 1: AUTH SERVICE REQUESTS OTP
─────────────────────────────────
POST /api/notifications/send
{
  "user_id": "U123",
  "type": "otp",
  "template_id": "otp_sms",
  "data": {
    "otp": "123456",
    "expiry_minutes": 5
  },
  "channels": ["sms"],
  "priority": "critical",
  "idempotency_key": "otp_U123_1707384000"  // Prevent duplicate OTP
}


STEP 2: DEDUPLICATION CHECK
───────────────────────────
Redis: SETNX idempotency:otp_U123_1707384000 → 1 (success)
If already exists → return cached response, don't send again


STEP 3: BYPASS RATE LIMITS
──────────────────────────
Priority = "critical" → skip rate limiting
(OTP should always be sent)


STEP 4: HIGH PRIORITY QUEUE
───────────────────────────
Kafka topic: notifications.sms.critical

Separate queue with:
  - Dedicated workers
  - Higher resources
  - No batching delays


STEP 5: SMS WORKER (Fast Path)
──────────────────────────────
Worker picks up immediately

Twilio request:
{
  "To": "+919876543210",
  "From": "SWIGYY",
  "Body": "Your OTP is 123456. Valid for 5 minutes. Do not share."
}


STEP 6: FALLBACK ON FAILURE
───────────────────────────
If Twilio fails:
  Retry with Gupshup (backup provider)
  
If SMS fails completely:
  Try voice call OTP
  
If all fail:
  Alert on-call, return error to user


SLA:
  95th percentile: < 5 seconds from request to delivery
```

---

## Flow 3: Marketing Campaign (Batch)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              BATCH MARKETING NOTIFICATION                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO: Send "50% off sale" email to 10 million users

STEP 1: CAMPAIGN CREATION
─────────────────────────
Marketing team creates campaign:
{
  "campaign_id": "SALE_Q1_2024",
  "template_id": "sale_announcement",
  "segment_query": "last_order_date > 30 days AND email_opted_in = true",
  "schedule": "2024-02-08T09:00:00Z",
  "channels": ["email", "push"]
}


STEP 2: SEGMENT EXTRACTION (Scheduled Job)
──────────────────────────────────────────
SELECT user_id, email, preferences 
FROM users 
WHERE last_order_date > NOW() - INTERVAL '30 days'
AND email_opted_in = true;

Result: 10 million users


STEP 3: BATCH PRODUCER
──────────────────────
Produce messages in batches:

for batch in user_batches(size=1000):
    for user in batch:
        kafka.produce(
            topic="notifications.email.marketing",
            key=user.id,
            value={
                "user_id": user.id,
                "email": user.email,
                "template_id": "sale_announcement",
                "data": {"user_name": user.name}
            }
        )

Rate: 50,000 messages/second → 200 seconds to queue all


STEP 4: WORKER POOL
───────────────────
100 email workers consuming in parallel

Each worker:
  - Consumes batch of 100 messages
  - Renders templates
  - Batches to SES (100/request)
  - Records status

SES rate: 500 emails/second
10M emails ÷ 500/sec = ~5.5 hours


STEP 5: THROTTLING
──────────────────
Problem: Don't overwhelm SES, ISPs

Solution:
  - Token bucket rate limiting
  - Spread over time window
  - Warm up IP if new
  - Monitor bounce/complaint rates


STEP 6: ANALYTICS
─────────────────
Track:
  - Sent: 10,000,000
  - Delivered: 9,800,000 (98%)
  - Opened: 1,500,000 (15%)
  - Clicked: 300,000 (3%)
  - Unsubscribed: 5,000 (0.05%)
```

---

# 7. KEY PATTERNS

## 7.1 Rate Limiting

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RATE LIMITING                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

WHY?
  - Protect users from spam
  - Prevent abuse
  - Respect channel limits

IMPLEMENTATION (Per-User Rate Limit):

User limit: 10 push notifications per hour

def check_rate_limit(user_id, channel):
    key = f"notif_rate:{user_id}:{channel}"
    window = 3600  # 1 hour
    
    current = redis.get(key) or 0
    
    if current >= LIMIT:
        return False  # Rate limited
    
    # Increment with TTL
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window)
    pipe.execute()
    
    return True


PRIORITY BYPASS:

Critical notifications (OTP) bypass rate limits:

if notification.priority == "critical":
    skip_rate_limit = True
```

---

## 7.2 User Preferences

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              USER PREFERENCES                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PREFERENCE SCHEMA:

{
  "user_id": "U123",
  "channels": {
    "push": {
      "enabled": true,
      "categories": {
        "orders": true,
        "promotions": false,
        "social": true
      }
    },
    "email": {
      "enabled": true,
      "frequency": "daily_digest"  // instant, daily, weekly
    },
    "sms": {
      "enabled": true,
      "only_critical": true  // Only OTP, no marketing
    }
  },
  "dnd": {
    "enabled": true,
    "start": "23:00",
    "end": "07:00",
    "timezone": "Asia/Kolkata"
  }
}


ENFORCEMENT:

def should_send(user_id, channel, category):
    prefs = get_preferences(user_id)
    
    # Check channel enabled
    if not prefs.channels[channel].enabled:
        return False
    
    # Check category
    if not prefs.channels[channel].categories.get(category, True):
        return False
    
    # Check DND
    if prefs.dnd.enabled:
        user_time = now_in_timezone(prefs.dnd.timezone)
        if is_in_dnd_window(user_time, prefs.dnd):
            # Queue for later (after DND ends)
            return "queue_for_later"
    
    return True
```

---

## 7.3 Retry & Failover

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RETRY & FAILOVER                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

RETRY STRATEGY:

1st attempt: Immediate
2nd attempt: After 30 seconds
3rd attempt: After 2 minutes
4th attempt: After 10 minutes
5th attempt: After 1 hour

Max retries: 5

def send_with_retry(notification):
    for attempt in range(MAX_RETRIES):
        try:
            result = send(notification)
            if result.success:
                return result
        except TransientError:
            delay = backoff(attempt)  # 30s, 2m, 10m, 1h
            schedule_retry(notification, delay)
            return "retrying"
        except PermanentError:
            # Token invalid, user unsubscribed
            mark_failed(notification)
            return "failed"
    
    # Max retries exceeded
    move_to_dlq(notification)


FAILOVER (Multiple Providers):

SMS:
  Primary: Twilio
  Secondary: Gupshup
  Tertiary: AWS SNS

def send_sms(notification):
    providers = [twilio, gupshup, aws_sns]
    
    for provider in providers:
        try:
            result = provider.send(notification)
            if result.success:
                return result
        except ProviderError:
            continue  # Try next provider
    
    return "all_providers_failed"
```

---

# 8. DATABASE SCHEMA

```sql
-- User device tokens
CREATE TABLE device_tokens (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(50) NOT NULL,
    device_type     VARCHAR(20),  -- ios, android, web
    token           VARCHAR(500) NOT NULL,
    app_version     VARCHAR(20),
    is_active       BOOLEAN DEFAULT true,
    last_used       TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, device_type, token)
);

-- Notification templates
CREATE TABLE notification_templates (
    template_id     VARCHAR(50) PRIMARY KEY,
    channel         VARCHAR(20),  -- push, email, sms
    title_template  TEXT,
    body_template   TEXT,
    html_template   TEXT,  -- For email
    variables       JSONB,  -- Expected variables
    version         INT DEFAULT 1,
    is_active       BOOLEAN DEFAULT true
);

-- Notification log (in Cassandra for scale)
CREATE TABLE notification_log (
    notification_id UUID,
    user_id         VARCHAR(50),
    channel         VARCHAR(20),
    template_id     VARCHAR(50),
    status          VARCHAR(20),  -- queued, sent, delivered, failed
    sent_at         TIMESTAMP,
    delivered_at    TIMESTAMP,
    opened_at       TIMESTAMP,
    clicked_at      TIMESTAMP,
    error_message   TEXT,
    
    PRIMARY KEY ((user_id), notification_id)
) WITH CLUSTERING ORDER BY (notification_id DESC);

-- User preferences
CREATE TABLE user_notification_preferences (
    user_id         VARCHAR(50) PRIMARY KEY,
    preferences     JSONB,  -- Full preference object
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

---

# 9. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATION SYSTEM TECH STACK                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ API                    │ Go / Node.js                  │ High concurrency                 │
│ Message Queue          │ Kafka                         │ High throughput, ordering        │
│ Workers                │ Go / Python                   │ Scalable consumers               │
│                        │                               │                                  │
│ User Data              │ PostgreSQL                    │ Preferences, templates           │
│ Device Tokens          │ Redis                         │ Fast lookup                      │
│ Notification Log       │ Cassandra                     │ Write-heavy, time-series         │
│ Rate Limits            │ Redis                         │ Atomic counters                  │
│                        │                               │                                  │
│ Push                   │ APNs, FCM                     │ Platform providers               │
│ Email                  │ AWS SES, SendGrid             │ Deliverability, scale            │
│ SMS                    │ Twilio, Gupshup               │ Reliability, coverage            │
│ WebSocket              │ Socket.io / ws                │ Real-time in-app                 │
│                        │                               │                                  │
│ Monitoring             │ Prometheus + Grafana          │ Metrics, alerting                │
│ Tracing                │ Jaeger                        │ Request tracing                  │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

# 10. INTERVIEW Q&A

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATION SYSTEM INTERVIEW Q&A                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Q1: How do you handle 1 billion notifications/day?
──────────────────────────────────────────────────
A: • Kafka for async processing
   • Separate queues by priority (critical vs marketing)
   • Horizontal scaling of workers
   • Batch API calls to providers
   • Database sharding for logs

Q2: How to ensure OTP is delivered in < 5 seconds?
──────────────────────────────────────────────────
A: • Dedicated high-priority queue
   • Pre-warmed connections to providers
   • No batching for critical path
   • Multiple SMS providers with failover
   • Aggressive timeouts and retries

Q3: How do you handle device token expiry?
──────────────────────────────────────────
A: • APNs/FCM return error codes for invalid tokens
   • Mark token inactive on "Unregistered" error
   • Periodic cleanup of inactive tokens
   • Request new token on app launch

Q4: How to prevent notification fatigue?
────────────────────────────────────────
A: • Rate limiting per user per channel
   • User-configurable preferences
   • DND hours
   • Aggregation (group similar notifications)
   • Smart batching (digest emails)

Q5: How do you track if notification was read?
──────────────────────────────────────────────
A: • Push: App reports when opened
   • Email: Tracking pixel for opens, redirect for clicks
   • SMS: Delivery reports from provider
   • In-app: Mark read API call

Q6: How to handle multi-device push?
────────────────────────────────────
A: • One user = multiple device tokens
   • Send to ALL active devices
   • Let user configure per-device preferences
   • Dedupe on client if needed
```

---

# 11. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATION CHEAT SHEET                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHANNELS:
  Push → APNs (iOS), FCM (Android), Web Push
  Email → SES, SendGrid
  SMS → Twilio, Gupshup
  In-App → WebSocket + Database

PRIORITY:
  Critical (OTP): < 5s, bypass rate limits, dedicated queue
  Transactional: < 30s, normal limits
  Marketing: < 5min, heavy rate limiting

KEY PATTERNS:
  • Rate limiting per user per channel
  • DND enforcement
  • Template rendering with variables
  • Retry with exponential backoff
  • Failover across providers
  • Deduplication for critical

TRACKING:
  Email: Pixel for opens, redirect for clicks
  Push: App reports open
  SMS: Delivery reports

SCALE:
  Kafka for queuing
  Multiple workers per channel
  Cassandra for delivery logs
  Redis for rate limits & tokens
```

---
