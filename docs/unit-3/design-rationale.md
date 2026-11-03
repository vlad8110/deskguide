# Design rationale — draft for team review

Coordinator: Vladimyr Merci. Revision 6, November 3, 2026.

Status: Proposed design; owner confirmations and final team approval pending.

[Revised proposed decisions](proposed-decisions.md) · [Design Decisions and Review Log](design-decisions-and-review-log.md)

## Rationale body

We propose modules for DeskGuide’s interaction, coordination, retrieval, generation, validation, human support, customer data, feedback, and persistence. Cohesion comes from keeping knowledge versioning within retrieval and request ownership within support. Typed component contracts reduce coupling through inputs, outputs, permissions, limits, and outcomes. Following [Parnas](https://www.cs.lafayette.edu/~gexia/cs301/resources/parnas.html) (1972), adapters hide changeable provider and storage decisions, helping junior developers understand and modify one area without depending on another module’s internal representation.

We choose one modular Flask application to limit deployment and coordination work for our four-person team. Separate services could improve fault isolation and allow independent scaling and releases, but add communication, deployment, and monitoring complexity ([Microsoft, 2025](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices)). We accept scaling and releasing the application together to keep the eight-week project manageable. [Microsoft](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures) (2023) describes internal separation within a single deployment and replication behind load balancing. Our production proposal uses HTTPS ingress, a production application server, replicated instances, and shared PostgreSQL; SQLite remains the local prototype choice.

Identity and authorization remain application responsibilities. One company and controlled account provisioning keep scope manageable. Proposed session expiry and shared revocation reduce unauthorized access and keep permissions consistent across instances. Customers access their own records; agents access unassigned or owned work. Explicit account-status selection reads only the customer’s identifier and account status through the read-only customer-data contract, returning fixed text without model generation or exposing database fields to the provider.

We limit prototype answers to reviewed, exactly matched excerpts. Source membership alone cannot establish answer support: executable evidence checks must pass before displaying answers with source links. Missing, failed, or unavailable checks produce a controlled limitation and support option. We retain Cohere-first evaluation against Groq, bounded admission without an AI queue, and no automatic retry. Shared breaker coordination permits one recovery trial across replicas; production counting, reset, and recovery details follow Collins’s proposal, pending team agreement. A 20-second deadline, 12-second provider cap, and one-second fallback reserve bound dependency waiting.

Customers confirm support content before saving, keeping escalation under their control. Registered submission IDs prevent duplicate requests and misleading confirmations when customers retry. Acknowledgement follows durable saving, protecting customers from false success messages. Agent ownership makes handoffs accountable. The proposed target requires 95% of valid, confirmed submissions to commit with acknowledgement ready within two seconds after the application receives confirmation. Slow saves, failures, uncertain commits, and capacity rejections count as misses.

Feedback informs reviewed, evaluated, versioned improvements instead of automatic retraining. Non-author release authorization, explicit permissions, and rollback references limit uncontrolled changes. We retain the lead architect as primary release authorizer, with Hanlin as the accepted backup. Defined retention, restricted audit content, and deletion checks after restoration limit unnecessary persistence.

Our workload assumption is 10,000 active sessions averaging one inquiry per minute, approximately 167 inquiries per second. The proposed AI objective requires supported answers within 15 seconds for 95% of eligible inquiries received; busy, failed, and unnecessary-fallback outcomes count as misses. Fixed, independently reviewed question labels prevent selective reporting. Provider quotas, resource sizing, and executed results remain pending; simulated load and free API access cannot establish production capacity.

## References

Microsoft. (2023, March 7). *Common web application architectures*. Microsoft Learn. [https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures](https://learn.microsoft.com/en-us/dotnet/architecture/modern-web-apps-azure/common-web-application-architectures)

Microsoft. (2025, July 11). *Microservices architecture style*. Microsoft Learn. [https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/microservices)

Parnas, D. L. (1972). On the criteria to be used in decomposing systems into modules. *Communications of the ACM, 15*(12), 1053–1058. [https://doi.org/10.1145/361598.361623](https://doi.org/10.1145/361598.361623)
