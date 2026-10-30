# Unit 3 — Selected workload assumptions

Author: Vladimyr Merci. Working snapshot of the [shared Google Doc](https://docs.google.com/document/d/1wdhA6LgOib5h5mo8p6onD87kleM75OCan0gPUZMNuC4/edit). Make team edits there; refresh this repository copy before publishing a new revision. Team approval is pending.

## Selected scenario

I will use the busiest of our three proposed workloads: 10,000 concurrent customer sessions, with every customer submitting one new inquiry per minute on average. This is the working design assumption selected for my draft. It is not a measured usage pattern or a demonstrated capacity result.

A concurrent session means a customer is using the service during the same period as the other customers. It does not by itself specify a persistent network connection or mean all 10,000 customers submit at the same instant. This baseline assumes inquiries are distributed over the minute; synchronized demand is considered separately below.

## Baseline demand

| Quantity | Calculation | Design demand |
| --- | --- | --- |
| Concurrent customer sessions | Selected scope | 10,000 |
| New inquiries per customer | Selected busiest scenario | 1 per minute |
| New inquiries per minute | 10,000 × 1 | 10,000 |
| Average new inquiries per second | 10,000 ÷ 60 | 166.67, approximately 167 |
| New inquiries in one hour at this sustained rate | 10,000 × 60 | 600,000 |

Calculations below use the unrounded rate, 10,000 ÷ 60. The 167 figure is a rounded description, not an extra capacity allowance. This rate counts new customer inquiries only; retries, citation clicks, authentication, feedback, agent actions, database calls, and health checks add separate work.

## Simultaneous work depends on response time

For a stable workload, average in-flight inquiries can be estimated as average arrival rate multiplied by average end-to-end time. The following times illustrate the effect; none is an agreed response-time target or measured result.

| Illustrative mean end-to-end time | Calculation | Estimated average in-flight inquiries, rounded up |
| --- | --- | --- |
| 5 seconds | (10,000 ÷ 60) × 5 | 834 |
| 10 seconds | (10,000 ÷ 60) × 10 | 1,667 |
| 15 seconds | (10,000 ÷ 60) × 15 | 2,500 |

These averages do not size a queue, predict peak concurrency, or establish a safe server count. A system that receives work faster than it can finish it will accumulate waiting work; a stable-average calculation does not prove it can sustain the arrival rate.

## AI-service demand assumption

For initial capacity planning, assume every new inquiry requires one model-generation call and do not count on caching to reduce that demand. This produces approximately 167 generation calls per second, or 10,000 per minute, before retries or additional model calls. This is a planning case, not a promise that an existing provider permits that volume.

Collins will need to verify the chosen provider’s request, token, and in-flight limits and permitted use. Prompt/response sizes, extra calls, timeouts, and retries must be included before estimating cost or capacity. No provider, account, purchase, or service is activated by this document.

## Separate synchronized stress scenario

Also consider all 10,000 customers submitting an inquiry at once. This is a burst of 10,000 arrivals, not 10,000 requests per second sustained indefinitely. The eventual validation plan must define how closely spaced the arrivals are and how long the exercise runs.

The architecture must specify how it limits admitted work and waiting time, communicates overload, preserves the customer’s question, and permits a safe support request without duplicate saves. It must also account for capacity in the human-support workflow; escalation cannot be treated as an unlimited escape path. Do not claim every burst request receives an immediate AI answer.

## Decisions still needed before sizing or validation

| Decision | Who helps resolve it | Why it matters |
| --- | --- | --- |
| Response-time, error-rate, timeout, and recovery targets | Vlad + David; Collins checks provider behavior | Defines acceptable service, rather than inferring it from illustrative averages |
| Prompt/answer sizes, inquiry mix, and number of external calls | Collins + Hanlin | Determines token demand, payloads, and dependency traffic |
| Customer-data lookup and escalation/feedback rates | Vlad + Hanlin + Collins | Determines database and agent-workflow demand |
| Queue bounds, admission limits, safe retries, and overload response | Vlad + Hanlin + Collins; David reviews | Prevents uncontrolled waiting and duplicate work |
| Production storage, replication, and deployment choices | Vlad; David reviews assumptions | Must follow measured capacity or justified estimates, not a guessed server count |
| Burst profile, test duration, environment, and provider allowances | David + Vlad + Collins | Makes the validation reproducible and distinguishes mocked from real dependencies |

B05/B12 require agreeing on latency targets and configured timeouts after provider evaluation. The earlier sequential demo checks remain useful for the prototype, but do not establish capacity for this workload. No performance test has been run for this draft.
