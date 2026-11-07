# OPC UA for Asset Administration Shell (OPC 30270)

| | |
|---|---|
| URL | https://reference.opcfoundation.org/specs/OPC-30270/4 (clause 4) |
| Title | "General information on the Asset Administration Shell and OPC UA – OPC UA for Asset Administration Shell (AAS)" |
| Publisher / date | OPC Foundation · OPC 30270 **v1.00**, published **2021-06-04** |
| Namespace | `http://opcfoundation.org/UA/I4AAS/` (model version 5.0.0) |
| Pack's design implication | Semantic and interoperable industrial asset representation |
| Read | 2026-11-06. Clause 4 read in full; clauses 5, 6.7 and 6.8 also read; the rest by title only |

## Contents

- [Clause 4: concepts](#clause-4-concepts)
- [Clause 5: how AAS maps onto OPC UA](#clause-5-how-aas-maps-onto-opc-ua)
- [Clauses 6.7–6.8: submodels and their elements](#clauses-6768-submodels-and-their-elements)
- [Full clause list](#full-clause-list)
- [Glossary](#glossary)
- [Relevance to our build](#relevance-to-our-build)

## Clause 4: concepts

### 4.1 The Asset Administration Shell

- **4.1.1 Motivation.** The AAS is the standard **digital representation of an asset** and the cornerstone of interoperability between Industrie 4.0 components. An *I4.0 component* = asset + its AAS. An AAS can describe a single component, a machine or a whole plant. The manufacturer creates one per asset type and per asset instance; designers, users, applications and the asset itself keep updating it through its life until disposal.
- **4.1.2 Metamodel.** Defined formally in UML. An AAS describes **exactly one asset** and contains **submodels** (each covering one aspect, e.g. nameplate, condition, documentation). Optional parts: **dictionaries** of *concept descriptions* (what a property means) and **views** (a stakeholder-specific selection of elements, e.g. for a machine operator).

### 4.2 OPC UA

- **4.2.1 What it is.** An open, royalty-free interoperability framework with a modern security model, several fault-tolerant protocols and an object-oriented information model. It scales from tiny devices to ERP. Servers present data consistently to ERP, MES, maintenance systems, HMIs, phones and browsers.
- **4.2.2 Basics.** Runs over TCP/IP, HTTP and WebSockets with fast binary encoding. Defines standard Services plus a base information model that vendors extend. The transport handles lost messages, failover and heartbeats.
- **4.2.3.1 Information modelling.** Data lives in an **AddressSpace** of **Nodes** joined by **References**:
  - *Object* nodes structure things; *Variable* nodes hold values with a DataType; *Method* nodes are callable functions.
  - Every node has a **NodeId** (unique ID) and a **BrowseName** (non-localised name).
  - Objects and Variables point to a **TypeDefinition** (ObjectType / VariableType) that acts as a template. Clients find children by BrowseName, so they don't depend on server-specific NodeIds.
  - ObjectTypes can be **subtyped** (extended); DataTypes can only be **restricted**.
  - References are hierarchical (structure) or non-hierarchical (associations), each with a ReferenceType.
  - **Profiles** group features into testable, certifiable units.
- **4.2.3.2 Namespaces.** Each source of information gets a globally unique NamespaceUri, so models from many vendors can share one AddressSpace without name clashes.
- **4.2.3.3 Companion specifications.** Industry-specific models (ObjectTypes, VariableTypes, DataTypes, ReferenceTypes, entry-point objects). OPC 30270 is itself one.

## Clause 5: how AAS maps onto OPC UA

The core rulebook:

| AAS concept | OPC UA representation |
|---|---|
| Each metamodel class | ObjectType named `AAS<Class>Type` (e.g. `AASAssetType`, `AASSubmodelType`), derived from `BaseObjectType` |
| Types with no OPC UA primitive | DataType named `AAS<Name>DataType`; `LangStringSet` → `LocalizedText` |
| Simple attributes | `HasProperty` with a capitalised BrowseName (e.g. `Version`) |
| Cardinality 0..1 / 1 / 0..n / 1..n | modelling rules Optional / Mandatory / OptionalPlaceholder / MandatoryPlaceholder |
| Aggregation / composition | `HasComponent`; BrowseName = idShort when there can be many |
| Abstract classes (Referable, Identifiable) | interfaces `IAASReferableType`, `IAASIdentifiableType` attached via `HasInterface` (OPC UA has no multiple inheritance) |
| Blob | standard `FileType` object named `File` |
| File | property `FileReference`, optional `File` object |
| Ordered collection | `AASOrderedSubmodelElementCollectionType` with `HasOrderedComponent` |
| Operation | `AASOperationType` wrapping a Method named `Operation` |
| Event | `AASEventType` linked to OPC UA events via `GenerateEvent` |
| Reference between elements | new non-hierarchical reference type `AASReference`; keys stored as an array; may point outside the AAS |
| Qualifier | named `qualifier:<type>=<value>` |
| semanticId | `HasDictionaryEntry` to a concept description (IRDI, IRI or custom) in a top-level `Dictionaries` folder |
| DisplayName | prefixed `Asset:`, `AAS:`, `Submodel:`, `View:` |

## Clauses 6.7–6.8: submodels and their elements

**6.7 `AASSubmodelType`**: implements `IAASIdentifiableType`; has a mandatory `ModelingKind` (default `Instance`), optional `DataSpecification`, `Qualifier` and any number of `SubmodelElements`. A submodel describes one aspect of the asset in a well-defined domain and can be standardised as a template.

**6.8 Submodel element types** (all derive from abstract `AASSubmodelElementType`, which has a mandatory `Category` and `ModelingKind`):

| Element | Holds |
|---|---|
| `AASPropertyType` | one typed value (`Value`, `ValueType`, optional `ValueId`) |
| `AASMultiLanguagePropertyType` | a value in several languages |
| `AASRangeType` | `Min` / `Max` (open-ended if one is missing) |
| `AASSubmodelElementCollectionType` | a set/list of elements; `AllowDuplicates` flag |
| `AASOrderedSubmodelElementCollectionType` | an ordered list |
| `AASFileType` | file path + MIME type |
| `AASBlobType` | binary content |
| `AASReferenceElementType` | a pointer to another element |
| `AASRelationshipElementType` | a `First`–`Second` relation (annotated variant adds attributes) |
| `AASEntityType` | a sub-entity, optionally pointing to its own asset |
| `AASOperationType` | a callable method with semantic argument descriptions |
| `AASCapabilityType` | a capability defined only by its semantic ID |
| `AASEventType` | events the element can raise |

## Full clause list

1 Scope · 2 Normative references · 3 Terms, definitions, conventions · **4 General information on AAS and OPC UA** · **5 AAS metamodel in the OPC UA information model** · 6 ObjectTypes (6.1–6.6 root, reference, referable/identifiable, identifier, asset; **6.7 submodel; 6.8 submodel elements**; 6.9 concept descriptions; 6.10 data specification templates incl. IEC 61360; 6.11 qualifiers; 6.12 views) · 7 DataTypes (identifier, modelling kind, asset kind, keys, category, value type, path, MIME, entity type, IEC 61360 types, level type) · 8 Profiles and ConformanceUnits · 9 Namespaces · Annex A Namespace and mappings · Annex B Pick-and-place station example

Spec errata noticed while reading: "AASCostumConceptDescriptionType" in Table 8 vs "AASCustomConceptDescriptionType" in 6.9.3; a self-reference to "Table 45" in the annotated relationship element.

## Glossary

| Term | Meaning |
|---|---|
| AAS | Asset Administration Shell: the standard digital twin wrapper for one asset |
| Submodel | one aspect of the asset (nameplate, condition, documentation …) |
| idShort / semanticId | short local name / pointer to a dictionary definition of what the element means |
| Concept description | dictionary entry defining a property (often an IEC 61360 / ECLASS IRDI) |
| View | stakeholder-specific subset of elements |
| NodeId / BrowseName | OPC UA unique ID / stable name used for navigation |
| Companion specification | an industry-specific OPC UA information model |

## Relevance to our build

- **Shape our asset JSON like a mini AAS.** One record per scene asset, keyed by `asset_id`, with submodels:

  ```json
  {
    "asset_id": "ASSET-017", "idShort": "P-005",
    "submodels": {
      "Identification": { "asset_class": "PROCESS_PUMP", "area": "Utility Island", "criticality": "A", "qr_id": "QR-SYN-0017" },
      "SceneMapping":   { "scene_path": "/BoilerRoom/cluster_042", "bbox": [...], "mapping_confidence": 0.7 },
      "Condition":      { "health_score": 44, "issue_code": "FOULING", "telemetry_ref": "..." },
      "History":        { "work_orders": ["WO-00012", "..."], "events": ["EVT-00037", "..."] },
      "Documentation":  { "docs": ["DOC-PROCESS_PUMP-CORE", "DOC-ASSET-017"] }
    }
  }
  ```

- **One AAS, one asset** = the builder pack's `DOC-3D-MAPPING` rule: each 3D frame links to at most one asset ID, with explicit confidence.
- **Views** fit a two-audience UI: a technician view (state, next check) and a reliability-engineer view (trends, history, confidence).
- **Production path (Builder Q-07):** 11 of the 30 assets are `OPC_UA` in `Asset_Master`. A slide showing "our JSON ⇄ AAS submodels ⇄ OPC UA I4AAS nodes" answers "how does this scale to a real plant?" in one picture.
