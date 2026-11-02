# Unit 3 — Selected workload assumptions

*November 1 shared-source snapshot. Current direction: [November 2 proposed decisions](../proposed-decisions.md).*

Author: Vladimyr Merci. Status: proposed; team approval pending.

## Selected scenario

Planning assumption: 10,000 active customer sessions, each submitting one new inquiry per minute on average. This implies approximately 166.67 inquiries per second. The assignment specifies concurrency; this arrival rate is our proposed workload assumption, not measured usage or demonstrated capacity.

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

For the worst-case planning scenario, every new inquiry requires one generation call: approximately 166.67 calls per second, 10,000 per minute or 600,000 per hour. Caching is not credited toward capacity. Additional model calls would increase demand.

Collins will identify the exact provider/model, account request and token quotas, concurrent-call limits, permitted use and prompt/response sizes. Cohere remains the first prototype candidate, with Groq as a comparison; production capacity requires separate evidence.

## Separate synchronized stress scenario

Proposed simulated load scenarios: approximately 166.67 inquiries/second steady state; 333.33 inquiries/second for two minutes; and a separate burst of 10,000 arrivals within one second. These scenarios use controlled substitutes before any permitted live-provider test.

Use bounded admission without an AI waiting queue. When capacity is unavailable, return a safe busy response and preserve the question. Keep support-request admission separate and bounded; agent work is not unlimited. Replica counts, in-flight limits and support capacity require measured sizing.

## Decisions still needed before sizing or validation

| Decision | Who helps resolve it | Why it matters |
| --- | --- | --- |
| Response-time, error-rate, timeout, and recovery targets | Vlad + David; Collins checks provider behavior | Defines acceptable service, rather than inferring it from illustrative averages |
| Prompt/answer sizes, inquiry mix, and number of external calls | Collins + Hanlin | Determines token demand, payloads, and dependency traffic |
| Customer-data lookup and escalation/feedback rates | Vlad + Hanlin + Collins | Determines database and agent-workflow demand |
| Queue bounds, admission limits, safe retries, and overload response | Vlad + Hanlin + Collins; David reviews | Prevents uncontrolled waiting and duplicate work |
| Production storage, replication, and deployment choices | Vlad; David reviews assumptions | Must follow measured capacity or justified estimates, not a guessed server count |
| Burst profile, test duration, environment, and provider allowances | David + Vlad + Collins | Makes the validation reproducible and distinguishes mocked from real dependencies |

Proposed production service level: at least 95% of all eligible inquiries receive a supported AI answer within 15 seconds. Eligibility means a valid, authorized, in-scope inquiry with supporting evidence assigned to the AI route before admission. Busy responses, timeouts, invalid answers and unnecessary fallback count as misses. Explicit human requests and genuinely unsupported questions are reported separately. Apply a 20-second end-to-end deadline and a provider timeout no longer than 12 seconds or the remaining budget, whichever is shorter. These are targets awaiting capacity evidence.
