# Axiom public documentation

This repository is the sole editable source for public design and tutorials.
Implementation belongs to axiom-data, axiom-engine, axiom-research and axiom-ui.
Keep applicable code versions in versions.json and distinguish saved evidence,
fresh execution, synthetic checks and unfinished bulk acceptance.
The two notebook sources own their prose, code and saved outputs; HTML is generated.
Prose/link/comment changes do not trigger supplier collection, rebuilds or a full test suite.
Changed executable teaching needs only the affected cells and their prerequisites.
No credentials, production data or local supplier logs belong in this repository.

Write designs, tutorials and delivery notes in complete, natural sentences that explain who does what, why and what results. Keep technical details that help the reader understand or decide, explain them with concrete examples, and place material risks and limits beside the claims they affect. Before submitting prose, read it for a connected argument and replace repeated contrastive sentences, vague slash-separated phrases and compressed lists of abstract nouns.

Stable foundation maintenance follows [overall design §11.2.1](docs/design/01_axiom_overview.md#foundation-validity).
Validate platform and extension boundaries thoroughly before stabilizing them. Keep Data/Core/Runtime business semantics stable; research changes should use existing configuration and extensions. Documentation, performance and usability improvements may continue; commits need not stay fixed, and defects must be repaired.
Before a necessary business-semantic change, explain why existing interfaces/extensions are insufficient, assess the whole affected scope, and record compatibility, affected saved artifacts and minimal revalidation/migration steps for coordinator review before a coordinated implementation.
The change owner supplies that impact record; the execution owner checks affected candidate inputs before use. Preserve unaffected artifacts and original identities. This navigation does not add an admission step to already approved work in progress.
