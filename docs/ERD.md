# Entity Relationship Diagram

The current repositories use JSON and directories rather than a database. This logical model describes the merged product and the migration target. It combines graph content, source provenance, flashcards, question packages, assessment attempts, and transparent grading evidence.

```mermaid
erDiagram
    SUBJECT ||--o{ SOURCE_DOCUMENT : has
    SUBJECT ||--o{ SUBJECT_NODE : classifies
    NODE ||--o{ SUBJECT_NODE : belongs_to
    SOURCE_DOCUMENT ||--o{ NODE_SOURCE : contributes
    NODE ||--o{ NODE_SOURCE : sourced_from
    NODE ||--o{ GRAPH_EDGE : source
    NODE ||--o{ GRAPH_EDGE : target
    NODE ||--o{ FLASHCARD : generates
    NODE ||--o{ QUESTION_NODE : assesses
    QUESTION ||--o{ QUESTION_NODE : covers
    SUBJECT ||--o{ QUESTION_PACKAGE : organizes
    SOURCE_DOCUMENT ||--o{ QUESTION_PACKAGE : informs
    QUESTION_PACKAGE ||--o{ PACKAGE_VERSION : versions
    PACKAGE_VERSION ||--o{ QUESTION : contains
    QUESTION ||--o{ QUESTION_OPTION : offers
    QUESTION ||--o{ ESSAY_RUBRIC : uses
    ESSAY_RUBRIC ||--o{ RUBRIC_CRITERION : defines
    USER ||--o{ ASSESSMENT_ATTEMPT : takes
    PACKAGE_VERSION ||--o{ ASSESSMENT_ATTEMPT : used_by
    ASSESSMENT_ATTEMPT ||--o{ RESPONSE : records
    QUESTION ||--o{ RESPONSE : answered_in
    RESPONSE ||--o{ RESPONSE_CRITERION : earns
    RUBRIC_CRITERION ||--o{ RESPONSE_CRITERION : matched
    GRAPH_BUILD ||--o{ NODE_SNAPSHOT : captures
    NODE ||--o{ NODE_SNAPSHOT : versioned_as

    SUBJECT {
        uuid id PK
        string subject_id UK
        string display_name
        string course
        string level
        json tags
    }
    SOURCE_DOCUMENT {
        uuid id PK
        uuid subject_id FK
        string filename
        string media_type
        string content_hash
        string storage_uri
        datetime imported_at
    }
    NODE {
        uuid id PK
        string canonical_key UK
        string name
        string type
        string domain
        text definition
        text description
        json properties
    }
    GRAPH_EDGE {
        uuid id PK
        uuid source_node_id FK
        uuid target_node_id FK
        string relation_type
        uuid graph_build_id FK
    }
    FLASHCARD {
        uuid id PK
        uuid node_id FK
        string front
        text back
        string status
        datetime generated_at
    }
    QUESTION_PACKAGE {
        uuid id PK
        uuid subject_id FK
        uuid source_document_id FK
        string package_key UK
        string title
        string level
        string status
    }
    PACKAGE_VERSION {
        uuid id PK
        uuid package_id FK
        integer version
        string content_hash
        string status
        datetime published_at
    }
    QUESTION {
        uuid id PK
        uuid package_version_id FK
        string question_key UK
        string kind
        text prompt
        string difficulty
        text learning_objective
        json slide_refs
    }
    QUESTION_OPTION {
        uuid id PK
        uuid question_id FK
        string option_key
        text option_text
        boolean is_correct
    }
    ESSAY_RUBRIC {
        uuid id PK
        uuid question_id FK
        integer total_points
        text grading_notes
    }
    RUBRIC_CRITERION {
        uuid id PK
        uuid rubric_id FK
        string keyword
        integer weight
        text description
    }
    QUESTION_NODE {
        uuid question_id FK
        uuid node_id FK
        string link_type
    }
    USER {
        uuid id PK
        string external_key UK
        string display_name
    }
    ASSESSMENT_ATTEMPT {
        uuid id PK
        uuid user_id FK
        uuid package_version_id FK
        datetime started_at
        datetime submitted_at
        decimal final_score
        string status
    }
    RESPONSE {
        uuid id PK
        uuid attempt_id FK
        uuid question_id FK
        string selected_option
        text essay_text
        decimal score
        decimal max_score
        boolean correct
        json matched_keywords
        json node_links
    }
    RESPONSE_CRITERION {
        uuid response_id FK
        uuid criterion_id FK
        boolean matched
        text evidence
    }
    GRAPH_BUILD {
        uuid id PK
        datetime built_at
        string pipeline_version
        string status
    }
    NODE_SNAPSHOT {
        uuid id PK
        uuid graph_build_id FK
        uuid node_id FK
        json payload
    }
    SUBJECT_NODE {
        uuid subject_id FK
        uuid node_id FK
    }
    NODE_SOURCE {
        uuid node_id FK
        uuid source_document_id FK
    }
```

## Current JSON Mapping

| Logical entity | Current representation |
| --- | --- |
| Subject | `json_nodes/<subject_id>/` and graph metadata subject entries |
| Source document | Current graph `metadata.source_files[]`; question-bank PDF `source` field |
| Node | `data/graphs/merged_graph.json.nodes[entity]` |
| Graph edge | `data/graphs/merged_graph.json.edges[]` with `source`, `target`, `type` |
| Flashcard | Entry in `data/flashcards/flashcards.json` |
| Question package/version | `database/<subject>/<package_id>/package.json`; version currently implicit |
| MCQ question/option | `mcqs[]` entries with `question`, `options`, and `correct_option` |
| Essay question/rubric | `essay[]` entries with `prompt`, `expected_keywords`, and `rubric.criteria[]` |
| User | Currently implicit; submission filenames identify no stable user account |
| Assessment attempt | JSON in `results/user_submissions/` with answers and aggregate scores |
| Response | `responses[]` entries inside a submission, one per question |
| Criterion evidence | `matched_criteria[]` with `matched`, `weight`, and `evidence`; essay `matched_keywords[]` |
| Question-concept link | Question `node_links[]`, resolved through `core/learning_links.py` |
| Result review | `GET /results/{attempt_id}`, `GET /results`, Streamlit review/export page, and React result review |
| Graph build/snapshot | Graph `metadata.built_at`; historical builds are not retained |

## Integrity and Migration Rules

- Use stable IDs for subjects, packages, versions, questions, and nodes; display names are not primary keys.
- A package directory name and payload `package_id` must resolve to one canonical `package_key` during migration.
- A published `PACKAGE_VERSION` is immutable. Attempts always reference the exact version used.
- MCQ options are unique per question; exactly one option is correct unless a future question type explicitly allows otherwise.
- Essay rubric weights must be non-negative and have an explicit total-point interpretation.
- A response belongs to one attempt and one question; duplicate responses for the same attempt/question are prohibited.
- `RESPONSE_CRITERION` stores matched criteria and evidence so essay scores are auditable.
- Each submitted attempt stores one response for every delivered question, including unanswered questions, so result review is complete.
- Result summaries are derived from persisted response records; they must not replace the full attempt record needed for audit and review.
- Graph edges require valid source and target nodes and are unique by `(source, target, relation_type, graph_build)`.
- `QUESTION_NODE` is many-to-many: a question may link to multiple concepts and a concept may support multiple questions.
- A response inherits the question's concept links for remediation; incorrect/low-scoring responses expose those concepts, their typed graph neighbors, and related flashcards.
- Missing concept links must not block standalone assessment delivery, but published questions should report missing or invalid links as quality issues.
- Source uploads and generated drafts must retain content hashes and review status before publication.

## Recommended Migration Order

1. Normalize package and question IDs and add explicit package versions.
2. Introduce a shared subject/source registry for graph and question-bank content.
3. Convert question and submission JSON into package, question, option, attempt, and response records.
4. Add `QUESTION_NODE` links and remediation UI.
5. Move large source files and immutable artifacts to object storage while keeping metadata/query data relational.
