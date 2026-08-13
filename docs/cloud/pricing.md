# Arena Cloud Pricing Model

**Status:** Proposed

**Reviewed:** August 12, 2026
**Applies to:** Arena OSS and Arena Cloud

## Executive Summary

Arena uses an open-source-to-cloud business model:

- **Arena OSS is free forever.** Users bring their own compute, storage, and model credentials and process media locally.
- **Arena Cloud is paid.** Customers pay for managed compute, hosted workflows, collaboration, automation, analytics, and operational convenience.

The proposed Arena Cloud launch prices are:

- Creator: **$19 per month**
- Pro: **$49 per month**
- Studio: **$149 per month**
- Enterprise: **Starting at $499 per month**

Arena Cloud usage is measured in **source-video minutes**, not opaque AI credits. One minute of source media analyzed consumes one processing minute. Generating multiple clips or re-exporting an existing analysis does not charge the original source minute again.

## Pricing Principles

Arena pricing should follow these rules:

1. The complete local processing engine remains free and open source.
2. Cloud customers pay for convenience, capacity, coordination, and reliability—not artificially better editorial results.
3. Usage must be described using understandable units.
4. Charges must be predictable before processing begins.
5. Failed jobs caused by Arena must not consume a customer's allocation.
6. Customers must explicitly enable overage billing.
7. Cloud plans must maintain sustainable compute margins at full usage.
8. Pricing should encourage adoption without presenting Arena Cloud as a discount-only product.

## Product Boundary

### Arena OSS

Arena OSS is the complete local-first product.

Users provide:

- Their own CPU or GPU compute
- Local storage
- FFmpeg and other system dependencies
- Credentials for any external model provider they choose

Arena OSS includes:

- The four-layer editorial engine
- Local transcription and analysis
- Local clip generation
- Captioning and platform formatting
- Scene and audio-energy analysis
- Local caching and project artifacts
- Provider interfaces and bring-your-own-key support
- No Arena account requirement
- No Arena-imposed usage limits
- No watermark
- No mandatory telemetry

“Unlimited local processing” means Arena does not impose a usage quota. Users remain responsible for the costs and limits of their hardware and chosen model providers.

### Arena Cloud

Arena Cloud provides managed operations around the same Arena processing model:

- Hosted compute
- Managed transcription and AI usage
- Background job queues
- Hosted project storage
- Team workspaces
- Scheduling and automation
- Publishing integrations
- Analytics
- APIs and webhooks
- Reliability, support, and enterprise controls

Local and Cloud processing should produce compatible, versioned Arena artifacts.

## Billing Unit

### Source-video minute

The primary billing unit is one minute of source media submitted for analysis.

Examples:

| Operation | Usage charged |
|---|---:|
| Analyze a new 60-minute podcast | 60 minutes |
| Generate 10 clips from that saved analysis | 0 additional source minutes |
| Re-export a clip in a different aspect ratio | 0 source minutes |
| Re-run the complete analysis using a different model | 60 minutes |
| Analyze only a selected 15-minute range | 15 minutes |
| Retry a failed Arena-controlled job | 0 additional minutes |

The product may later introduce separate usage units for expensive optional operations such as generative B-roll, translation, dubbing, or third-party publishing. These operations must not silently consume ordinary processing minutes.

### Rounding

Recommended launch rule:

- Measure the actual submitted source duration in seconds.
- Convert the total to minutes at the job level.
- Round up to the nearest whole minute per job.
- Display the estimated charge before the job starts.

Arena should avoid rounding each clip or pipeline stage independently.

## Pricing Tiers

### Tier summary

| Plan | Monthly price | Included source minutes | Seats | Concurrent jobs | Intended customer |
|---|---:|---:|---:|---:|---|
| Arena OSS | $0 | Unlimited locally | Unlimited | User-managed | Local and technical users |
| Cloud Trial | $0 once | 60 | 1 | 1 | Prospective Cloud customers |
| Creator | $19/month | 250/month | 1 | 1 | Individual creators |
| Pro | $49/month | 750/month | 3 | 3 | Professionals and small teams |
| Studio | $149/month | 2,500/month | 10 | 10 | Agencies and production teams |
| Enterprise | From $499/month | Custom | Custom | Custom | Large organizations |

## Arena OSS — Free Forever

### Price

**$0**

### Entitlements

- Unlimited Arena-local processing
- Complete editorial pipeline
- Full-quality local exports
- Local storage and caches
- Bring-your-own compute
- Bring-your-own model credentials
- No watermark
- No account requirement
- No Cloud collaboration or hosted processing

### Strategic role

Arena OSS is not a restricted trial for Arena Cloud. It is a durable standalone product and the primary adoption channel for the Arena ecosystem.

## Cloud Trial

### Price

**$0, one time**

### Included usage

- 60 source-video minutes
- One user
- One concurrent job
- Full-quality export
- No watermark
- Seven-day raw-media retention
- No payment card required

### Restrictions

- One trial per verified user or organization
- No indefinite monthly reset
- Limited automation and API access
- Abuse-prevention limits may apply

### Rationale

Arena OSS already provides the permanent free option. The Cloud trial exists to demonstrate managed processing, not to become an indefinitely subsidized compute plan.

## Creator

### Price

**$19 per month**

### Annual price

**$190 per year**

The annual plan provides approximately two months free compared with monthly billing.

### Included usage

- 250 source-video minutes per month
- One seat
- One concurrent job
- 50 GB hosted storage
- 30-day raw-media retention
- Full-HD exports
- Captions and platform formatting
- Hosted project history
- Standard processing queue
- Email or community support

### Intended customer

Individual creators publishing approximately one long-form episode each week.

## Pro

### Price

**$49 per month**

### Annual price

**$490 per year**

### Included usage

- 750 source-video minutes per month
- Three seats
- Three concurrent jobs
- 250 GB hosted storage
- 90-day raw-media retention
- Full-HD and 4K exports where supported
- Batch processing
- Brand templates
- Social publishing scheduler
- Basic clip-performance analytics
- API and webhook access
- Priority processing queue
- Priority support

### Intended customer

Professional creators, marketers, podcasts, and small content teams processing several long-form videos each week.

## Studio

### Price

**$149 per month**

### Annual price

**$1,490 per year**

### Included usage

- 2,500 source-video minutes per month
- Ten seats
- Ten concurrent jobs
- 1 TB hosted storage
- Extended raw-media retention
- Client and project workspaces
- Roles and approval workflows
- Shared brand kits
- Bulk processing and publishing
- Advanced analytics
- Higher API and webhook limits
- Priority queue
- Priority support

### Intended customer

Agencies, media teams, and production studios managing multiple shows, brands, or clients.

## Enterprise

### Price

**Starting at $499 per month; custom quotation required**

### Potential entitlements

- Custom source-minute allocation
- Custom concurrency and queue capacity
- Custom storage and retention
- Unlimited or negotiated seats
- Dedicated or isolated processing capacity
- Single sign-on and identity provisioning
- Advanced permissions and audit logs
- Regional processing and data residency options
- Security reviews and contractual controls
- Service-level agreement
- Master service agreement
- Invoice billing
- Dedicated support channel
- Custom integrations

### Intended customer

Large media companies, enterprise content teams, regulated organizations, and customers with high-volume or specialized security requirements.

## Overage Pricing

Customers must explicitly enable overage billing and set a monthly spending cap.

| Plan | Overage rate |
|---|---:|
| Creator | $0.10 per source minute |
| Pro | $0.08 per source minute |
| Studio | $0.06 per source minute |
| Enterprise | Contracted rate |

When overages are disabled, Arena should pause new jobs after the included allocation is exhausted. Existing jobs may complete if their estimated usage was authorized when they started.

Arena must notify users at recommended thresholds:

- 50% consumed
- 80% consumed
- 100% consumed
- Every additional configured overage threshold

## Prepaid Minute Packs

Customers who do not want an ongoing overage commitment may purchase prepaid usage.

| Pack | Price | Effective rate |
|---|---:|---:|
| 100 minutes | $10 | $0.10/minute |
| 500 minutes | $40 | $0.08/minute |
| 2,000 minutes | $120 | $0.06/minute |

Recommended rules:

- Prepaid minutes expire after 12 months.
- Included subscription minutes are consumed before prepaid minutes.
- Prepaid balances remain available while the account is in good standing.
- Refund and regional consumer-law requirements must be documented before launch.

## Usage Reset and Rollover

Recommended launch behavior:

- Subscription allocations reset on the customer's billing date.
- Standard monthly minutes do not roll over.
- Annual plans receive monthly allocations rather than the full annual amount upfront.
- Prepaid minute packs remain available for 12 months.

Monthly allocations reduce financial exposure and discourage account sharing or burst abuse. Arena can test limited rollover later as a retention benefit.

## Job Charging Rules

### Successful jobs

Charge the final measured source duration, subject to the documented rounding policy.

### Arena-controlled failures

Automatically refund all reserved minutes when failure is caused by:

- Arena service errors
- Worker crashes
- Infrastructure timeouts
- Internal processing bugs
- Provider failures covered by Arena's managed service

### Invalid or unsupported input

Do not charge when validation fails before substantive processing begins.

### User cancellation

Recommended initial policy:

- No charge if cancellation occurs before processing starts.
- Charge measured consumption if expensive processing has already occurred.
- Display the estimated cancellation charge before confirmation where practical.

### Reprocessing

Charge again when a customer deliberately requests a new full analysis, such as changing the model, language, or editorial strategy. Do not charge again for generating or exporting from an existing compatible analysis.

## Storage and Retention

Storage quotas and retention periods are separate controls:

- **Storage quota** limits how much customer data may be hosted simultaneously.
- **Retention period** determines how long raw media is retained by default.

Derived artifacts such as transcripts, analyses, metadata, and clip definitions may be retained longer than raw media when permitted by the customer and privacy policy.

Customers must be able to:

- Delete raw media immediately
- Delete projects and derived artifacts
- Export their project data
- View retention deadlines
- Configure shorter retention where supported

Expired raw media should not make existing metadata or exported clips inaccessible unless clearly disclosed.

## Optional Premium Operations

The following operations may need separate pricing because their cost profile differs from normal Arena processing:

- AI-generated B-roll
- Video generation
- Voice cloning
- Dubbing
- Translation
- High-resolution upscaling
- Long-term archival storage
- Premium stock-media licenses
- Third-party publishing fees

These should use descriptive units such as generated seconds, translated minutes, or GB-months. They must not be hidden behind the normal source-minute balance.

## Discounts

### Annual billing

Offer approximately two months free, equivalent to a 16–17% discount.

### Launch promotions

Prefer bonus minutes or time-limited discounts instead of permanent lifetime pricing.

Recommended founding-customer offer:

- Standard monthly price
- 50% additional included minutes for the first six months
- Offer limited to the first 100–250 paying customers

This rewards early users without permanently weakening the public price anchor.

### Education, nonprofit, and regional pricing

These programs may be introduced after billing and fraud controls are mature. Eligibility, renewal, and verification requirements must be documented separately.

## Unit Economics

Arena must benchmark the actual variable cost of one source-video minute before launching paid plans.

Variable cost should include:

- Transcription
- Model inference
- CPU and GPU processing
- Video rendering
- Temporary storage
- Object operations and data transfer
- Queue and orchestration costs
- Payment processing
- Expected retry and failure costs
- Direct support burden where measurable

Use the following pricing floor:

```text
minimum revenue per minute =
    variable cost per minute / (1 - target gross margin)
```

At a 70% target gross margin:

| Variable cost per minute | Minimum revenue per minute |
|---:|---:|
| $0.015 | $0.050 |
| $0.020 | $0.067 |
| $0.025 | $0.083 |
| $0.030 | $0.100 |

The launch tiers imply these maximum included-minute rates:

| Plan | Price | Included minutes | Revenue per included minute |
|---|---:|---:|---:|
| Creator | $19 | 250 | $0.076 |
| Pro | $49 | 750 | $0.065 |
| Studio | $149 | 2,500 | $0.060 |

These figures exclude the value and cost of seats, storage, analytics, and support. Before launch, Arena must verify that each tier remains viable when a customer consumes the full allocation.

Recommended guardrails:

- Target at least 70% gross margin at expected usage.
- Preserve at least 60% gross margin at full included usage.
- Price overages at no less than three times the 95th-percentile variable cost per minute.
- Revisit included minutes before changing public plan prices.
- Isolate unusually expensive features behind separate limits or usage units.

## Conversion Model

Arena OSS is the primary acquisition channel for Arena Cloud.

```text
OSS discovery
    ↓
Successful local export
    ↓
Repeated or high-volume use
    ↓
Setup, compute, collaboration, or automation pain
    ↓
Arena Cloud trial
    ↓
Paid Cloud subscription
```

At a blended average revenue per paying account of approximately $33 per month:

| Activated OSS users | Cloud conversion | Paying accounts | Approximate MRR |
|---:|---:|---:|---:|
| 10,000 | 2% | 200 | $6,600 |
| 10,000 | 5% | 500 | $16,500 |
| 10,000 | 10% | 1,000 | $33,000 |

These are planning scenarios, not revenue forecasts.

## Metrics to Review

Pricing should be reviewed using:

- Trial-to-paid conversion
- OSS-to-Cloud conversion
- Processing minutes per active account
- Allocation utilization by tier
- Overage opt-in and consumption
- Gross margin by tier
- Storage consumption and retention
- Concurrent-job demand
- Upgrade and downgrade rates
- Voluntary and involuntary churn
- Expansion revenue
- Support cost by tier
- Failed-job and refunded-minute rate

The first formal pricing review should occur after 90 days of paid availability and at least 100 paying accounts.

## Launch Validation Checklist

- [ ] Benchmark end-to-end variable cost per source minute.
- [ ] Measure cost at median and 95th-percentile video workloads.
- [ ] Verify margin at full allocation for every plan.
- [ ] Define supported source formats, sizes, and durations.
- [ ] Implement usage estimation before job submission.
- [ ] Implement usage reservation and atomic settlement.
- [ ] Implement automatic refunds for Arena-controlled failures.
- [ ] Implement overage opt-in and spending caps.
- [ ] Implement usage notifications.
- [ ] Document storage and deletion behavior.
- [ ] Define tax, invoicing, refund, and cancellation policies.
- [ ] Add abuse prevention for the Cloud trial.
- [ ] Validate entitlement enforcement across API, web, and CLI clients.
- [ ] Test upgrades, downgrades, renewals, and failed payments.

## Final Recommendation

Launch Arena Cloud with the following public pricing:

```text
Arena OSS       Free forever
Cloud Trial     60 source minutes, one time
Creator         $19/month for 250 minutes
Pro             $49/month for 750 minutes
Studio          $149/month for 2,500 minutes
Enterprise      From $499/month
```

Maintain the headline prices for the first 90 days unless unit economics make them unsafe. Adjust included minutes, retention, or concurrency before changing the public price points.

Arena should remain explicit about the exchange: local ownership and self-managed compute are free; managed infrastructure, collaboration, automation, and scale are paid.
