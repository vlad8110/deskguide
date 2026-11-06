# Unit 3 — Selected workload assumptions

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

For a stable workload, average in-flight inquiries can be estimated as average arrival rate multiplied by average end-to-end time. The following values are illustrations, not measured results or safe concurrency settings.

| Illustrative mean end-to-end time | Calculation | Estimated average in-flight inquiries, rounded up |
| --- | --- | --- |
| 5 seconds | (10,000 ÷ 60) × 5 | 834 |
| 10 seconds | (10,000 ÷ 60) × 10 | 1,667 |
| 15 seconds | (10,000 ÷ 60) × 15 | 2,500 |

These averages do not size a queue, predict peak concurrency, or establish a safe server count. A system that receives work faster than it can finish it will accumulate waiting work; a stable-average calculation does not prove it can sustain the arrival rate.

## AI-service demand assumption

For the worst-case planning scenario, every new inquiry requires one generation call: approximately 166.67 calls per second, 10,000 per minute or 600,000 per hour. Caching is not credited toward capacity. Additional model calls would increase demand.

Evaluate Cohere first and compare Groq on the same questions before selecting an exact model. Free evaluation access is for the fictional-data prototype only. Collins supplies account/model request and token quotas, concurrent-call limits, data/retention policy, latency evidence and a production capacity/cost proposal. Include any model calls used for evidence checking. A paid key alone does not establish capacity for 10,000 calls per minute; simulated application load does not prove provider capacity.

## Separate synchronized stress scenario

Proposed controlled load scenarios: approximately 166.67 inquiries/second for ten minutes; 333.33 inquiries/second for two minutes; and a separate overload case of 10,000 arrivals within one second. Agree resources and stop conditions before execution. Use controlled substitutes before any permitted live-provider test.

Use an aggregate AI admission limit across application instances, with no AI waiting queue. Return a controlled busy response when admission is unavailable. Prototype generation concurrency may be up to five only where account/model quotas permit; also enforce request and token budgets. Production concurrency remains pending quota and service-time evidence. Keep support-save/status admission separately bounded; replicas and agent work are not unlimited.

## Decisions still needed before sizing or validation

| Decision | Who helps resolve it | Why it matters |
| --- | --- | --- |
| Validate proposed service, failure and recovery targets | Vlad + David; Collins checks provider behavior | Defines acceptable service, rather than inferring it from illustrative averages |
| Prompt/answer sizes, inquiry mix, and number of external calls | Collins + Hanlin | Determines token demand, payloads, and dependency traffic |
| Customer-data lookup and escalation/feedback rates | Vlad + Hanlin + Collins | Determines database and agent-workflow demand |
| Aggregate admission limits, safe retries and overload responses | Vlad + Hanlin + Collins; David reviews | Prevents uncontrolled waiting and duplicate work |
| Production replica counts, resource limits and database sizing | Vlad; David reviews assumptions | Must follow measured capacity or justified estimates, not a guessed server count |
| Burst profile, test duration, environment, and provider allowances | David + Vlad + Collins | Makes the validation reproducible and distinguishes mocked from real dependencies |

Proposed AI service level: at least 95% of all eligible inquiries received return a supported AI answer within 15 seconds at the selected workload. Before testing, identify eligible questions, expected outcomes and source versions; another qualified member reviews the labels. Otherwise-eligible busy, timeout, invalid-answer and unnecessary-fallback outcomes count as misses. Do not relabel failures afterward. Report account-status checks, explicit human requests and unsupported questions separately.

Use a 20-second overall deadline, a provider wait of at most 12 seconds and a one-second fallback reserve. Shorten dependency waits to the remaining budget and stop waiting by approximately second 19. Return fallback as soon as failure is known. A 12-second provider call leaves only three seconds for other work to meet the 15-second target; timeout settings do not prove performance.

Proposed support-save target: at least 95% of valid, confirmed intended submissions are durably committed with the success response ready within two seconds of application receipt of the final submission. Count slow saves, definite failures, uncertain commits and capacity rejections as misses. Count each intended submission once; track every retry separately while retaining its original ID and timing. Late reconciliation cannot turn an untimely result into a timely success. Measure registration separately; exclude form editing and human response time. Report invalid, unauthorized, expired-ID and conflicting-payload attempts separately.
