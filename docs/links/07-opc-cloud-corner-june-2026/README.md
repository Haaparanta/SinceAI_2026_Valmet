# Cloud Corner – June 2026: from protocol connectivity to secure, semantic & automatic asset onboarding

| | |
|---|---|
| URL | https://opcconnect.opcfoundation.org/2026/06/cloud-corner-june-2026/ |
| Title | "Cloud Corner – June 2026", subtitle "From Protocol Connectivity to Secure, Semantic & Automatic Asset Onboarding" |
| Publisher / date | OPC Foundation, OPC Connect newsletter (Cloud Initiative column) · June 2026 (no exact day shown) |
| Pack's design implication | AI-ready semantic onboarding and structured information models |
| Read | 2026-11-06, full text |

## Page structure

1. Intro: the problem and the requirement list
2. Multiple Implementations Available
3. Building the Foundation for Industrial AI

## Section by section

### 1. The problem and the requirements

Industrial data is still locked in **proprietary protocols, inconsistent tag naming and onboarding that doesn't scale**. Connectivity itself is solved; the open problem is **semantic onboarding**: bringing assets into cloud platforms, digital twins, AI applications and data spaces *with their meaning attached*. The OPC Foundation Cloud Initiative has therefore defined common requirements for edge connectivity software:

| # | Requirement | Plain meaning |
|---|---|---|
| 1 | OPC UA Client/Server or OPC UA PubSub over MQTT northbound | one standard upstream interface |
| 2 | OPC UA Sign & Encrypt, even for assets with no security of their own | the edge adds security |
| 3 | Deployable as Linux containers | |
| 4 | Runs on AMD64 and ARM64 | from servers to small gateways |
| 5 | Read **and write** access to tags | enables closed-loop control |
| 6 | Asset commands exposed as OPC UA Methods | |
| 7 | **Structured information models, not flat tag lists** | the core semantic point |
| 8 | Zero data loss during northbound outages | buffering |
| 9 | Parse W3C Web of Things (WoT) Thing Descriptions | machine-readable device descriptions |
| 10 | Support the OPC UA WoT-Connectivity interface | configuration without a UI; automatic onboarding |
| 11 | Separate OPC UA namespace per asset | building a Unified Namespace (UNS) |
| 12 | Map to OPC UA Companion Specifications | industry-standard types |
| 13 | Integrate with the UA Cloud Library | download companion specs and dependencies |
| 14 | Support Complex Types and ExtensionObjects | structured values |

### 2. Multiple implementations available

Two products implement large parts of this architecture: **Prosys Forge** (commercial) and **UA Edge Translator** (open source).

### 3. Building the foundation for industrial AI

Semantic, structured models are framed as the prerequisite for industrial AI: an AI agent can only reason about a plant if the data says *what* each value is and *which* asset it belongs to. The same newsletter issue links an article on OPC UA information models used with AI agents (not read).

## Glossary

| Term | Meaning |
|---|---|
| Northbound | from the edge up to cloud/IT systems |
| PubSub over MQTT | OPC UA publish/subscribe messages carried on an MQTT broker |
| WoT Thing Description | W3C JSON-LD format describing a device's properties, actions and events |
| Unified Namespace (UNS) | one shared, hierarchical address space for all plant data |
| UA Cloud Library | OPC Foundation's online registry of information models |
| ExtensionObject | OPC UA container for structured (custom) data types |

## Relevance to our build

- **It argues our core thesis.** A raw scan is like a flat tag list: lots of data, no meaning. Our extraction + mapping step is "semantic onboarding" for space. Use that phrase.
- **The connectivity mix in the pack is this problem in miniature.** `Asset_Master.connectivity_profile` mixes `OPC_UA` (11), `MQTT_EDGE` (7), `SIMULATED_API` (7), `FOUNDATION_FIELDBUS` (3) and `HART` (2). A thin `DataSource` adapter per profile, all producing the same asset model, answers Builder Q-07 ("swap synthetic feeds for OPC UA/MQTT/API without redesign").
- **Write access is out of scope for us.** The requirements include writes and Methods for closed-loop control, but the builder pack's `DOC-FIELD-SAFETY` and the `/api/work-orders/draft` route are explicit: draft only, no control actions. Say so in the tech note.
- **Unified namespace ⇄ scene paths.** The pack's USD-style `scene_path` (`/SyntheticPlant/AREA-03/P-005`) is effectively a UNS path for space. Keeping the same hierarchy for data topics and scene nodes is a tidy design point.
