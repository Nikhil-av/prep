# Google Docs / Real-Time Collaboration — Complete Deep Dive

> Interview-ready documentation — Covers Notion, Figma, Miro, any Collaborative Editing

---

# 1. FUNCTIONAL REQUIREMENTS

## Priority Levels
- **P0** = Must have (core functionality)
- **P1** = Should have (important features)
- **P2** = Nice to have (enhancements)

## Feature List

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 1 | **Real-time Editing** | P0 | Multiple users edit simultaneously |
| 2 | **Conflict Resolution** | P0 | Handle concurrent edits without data loss |
| 3 | **Cursor Presence** | P0 | See other users' cursors and selections |
| 4 | **Document Storage** | P0 | Save and retrieve documents |
| 5 | **Version History** | P1 | View and restore previous versions |
| 6 | **Comments** | P1 | Add comments, threads, resolve |
| 7 | **Sharing & Permissions** | P1 | Share with view/edit/comment access |
| 8 | **Offline Editing** | P2 | Edit without internet, sync later |
| 9 | **Rich Text Formatting** | P1 | Bold, italic, headings, lists |
| 10 | **Search** | P1 | Search within and across documents |
| 11 | **Templates** | P2 | Pre-made document templates |
| 12 | **Export** | P2 | Export to PDF, Word, etc. |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Character appear | < 50ms | Must feel instant while typing |
| Cursor update | < 100ms | Real-time presence |
| Document load | < 1 sec | Even for large docs |
| Save/sync | < 200ms | Continuous autosave |
| Conflict resolution | < 100ms | Seamless merging |

## Throughput

| Metric | Value |
|--------|-------|
| Total documents | 10 billion |
| DAU | 100 million |
| Concurrent editors per doc | Up to 100 |
| Operations per second (global) | 10 million |
| WebSocket connections | 50 million concurrent |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Document access | 99.99% | Multi-region replication |
| Real-time sync | 99.9% | Fallback to polling if WS fails |
| Version history | 99.9% | Eventual consistency OK |

---

# 3. THE CORE PROBLEM: CONCURRENT EDITING

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              THE COLLABORATION PROBLEM                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO:
  Document content: "Hello World"
  
  User A (position 6): Types "Beautiful "  →  "Hello Beautiful World"
  User B (position 11): Types "!"          →  "Hello World!"
  
  Both edits happen at the SAME TIME (within milliseconds)

PROBLEM:
  If we just apply edits in order received:
  
  Server receives A first, then B:
    "Hello World" → "Hello Beautiful World" → "Hello Beautiful World!"  ✓
  
  But what if B's position (11) is applied to NEW document?
    Position 11 in "Hello Beautiful World" = "d" (wrong place!)
    Result: "Hello Beauti!ful World"  ✗ WRONG!

THIS IS WHY WE NEED SPECIAL ALGORITHMS!
```

---

# 4. SOLUTIONS: OT vs CRDT

## 4.1 Operational Transformation (OT)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OPERATIONAL TRANSFORMATION (OT)                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONCEPT:
  Transform operations against each other so they can be applied in any order
  and still reach the same final state.

OPERATION FORMAT:
  {
    type: "insert" | "delete",
    position: number,
    character: string,
    timestamp: number,
    userId: string
  }

TRANSFORMATION RULES:

Case 1: Two INSERTS at different positions
  
  Op A: insert("X", pos=5)
  Op B: insert("Y", pos=8)
  
  If A applied first: B's position stays 8 (after A's position)
  If B applied first: A's position stays 5 (before B's insertion)
  
  No conflict!

Case 2: Two INSERTS at SAME position
  
  Op A: insert("X", pos=5)
  Op B: insert("Y", pos=5)
  
  Tie-breaker: User ID ordering (deterministic)
  If A.userId < B.userId: A goes first, B shifts right
  
  Result: "....XY...." (consistent everywhere)

Case 3: INSERT and DELETE overlap
  
  Original: "Hello"
  Op A: insert("X", pos=2)     →  "HeXllo"
  Op B: delete(pos=2, len=1)   →  "Helo"
  
  A before B: "HeXllo" → delete pos=3  → "HeXlo"
  B before A: "Helo"   → insert pos=2  → "HeXlo"
  
  Same result! ✓


GOOGLE DOCS USES OT:

Client                          Server                         Client
  A                               │                               B
  │                               │                               │
  │  Op1: insert("a", 0)         │                               │
  │ ─────────────────────────►   │                               │
  │                               │  Broadcast Op1                │
  │                               │ ─────────────────────────────►│
  │                               │                               │ Apply Op1
  │                               │                               │
  │                               │         Op2: insert("b", 0)   │
  │                               │ ◄─────────────────────────────│
  │                               │                               │
  │                               │  Transform Op2 against Op1    │
  │                               │  Op2': insert("b", 1)         │
  │                               │                               │
  │       Op2' (transformed)     │                               │
  │ ◄─────────────────────────── │                               │
  │ Apply Op2'                    │                               │
  │                               │                               │
  
  Final state on both: "ab" ✓


CHALLENGES WITH OT:
  - Server is the single source of truth
  - All operations must go through server
  - Complex transformation functions (N² for N operation types)
  - Harder to scale (centralized)
```

---

## 4.2 CRDT (Conflict-free Replicated Data Types)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CRDT (Conflict-free Replicated Data Types)                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONCEPT:
  Data structure that can be replicated across nodes, 
  updated independently, and mathematically guaranteed to converge.

KEY PROPERTY:
  Operations are COMMUTATIVE: A + B = B + A (order doesn't matter!)


TYPES OF CRDTs:

1. G-COUNTER (Grow-only Counter)
   
   Like counts: Can only increase
   Each node maintains its own count
   Total = sum of all node counts
   
   Node A: {A: 5, B: 0}  →  Total = 5
   Node B: {A: 0, B: 3}  →  Total = 3
   
   Merge: {A: 5, B: 3}   →  Total = 8

2. LWW-REGISTER (Last-Writer-Wins)
   
   For single values
   Each write has timestamp
   Latest timestamp wins
   
   Node A: {value: "X", timestamp: 100}
   Node B: {value: "Y", timestamp: 150}
   
   After merge: "Y" wins (timestamp 150 > 100)

3. SEQUENCE CRDT (for text editing)
   
   Characters have UNIQUE IDs that define order
   No positions - IDs determine sequence!


SEQUENCE CRDT EXAMPLE:

Initial: "CAT"
  
  Characters with IDs:
    {id: "a1", char: "C"}
    {id: "a2", char: "A"}
    {id: "a3", char: "T"}
  
  IDs are ordered: a1 < a2 < a3

User A inserts "H" at beginning:
  Generate ID before a1: "a0"
  {id: "a0", char: "H"}
  
  Sequence: a0, a1, a2, a3 = "HCAT"

User B inserts "S" at end:
  Generate ID after a3: "a4"
  {id: "a4", char: "S"}
  
  Sequence: a0, a1, a2, a3, a4 = "HCATS"

MAGIC: Both operations can happen independently!
  - No transformation needed
  - Just merge sets of characters
  - Sort by ID to get final text
  - ALWAYS converges to same result!


ID GENERATION (LSEQ / Logoot):

IDs are hierarchical paths:
  - Between 1 and 2: choose 1.5
  - Between 1 and 1.5: choose 1.25
  - Never run out of space!

Example:
  Original: [1] "A" [2] "B" [3] "C"
  
  Insert "X" between A and B:
    New ID: 1.5
    [1] "A" [1.5] "X" [2] "B" [3] "C"
  
  Insert "Y" between A and X:
    New ID: 1.25
    [1] "A" [1.25] "Y" [1.5] "X" [2] "B" [3] "C"


CRDT ADVANTAGES:
  ✓ Peer-to-peer possible (no central server required)
  ✓ Offline editing works naturally
  ✓ No transformation logic needed
  ✓ Mathematically guaranteed convergence

CRDT DISADVANTAGES:
  ✗ More storage (unique IDs per character)
  ✗ Tombstones for deletes (mark as deleted, don't remove)
  ✗ ID generation complexity


USED BY:
  - Figma
  - Apple Notes
  - Redis CRDTs
  - Automerge library
```

---

## 4.3 OT vs CRDT Comparison

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OT vs CRDT                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Aspect              │ OT                            │ CRDT                            │
├─────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ Server requirement  │ Required (central authority)  │ Optional (peer-to-peer OK)      │
│ Offline support     │ Harder (need to queue+sync)   │ Natural (just merge later)      │
│ Complexity          │ Transform functions           │ ID generation                   │
│ Storage             │ Efficient                     │ More (IDs + tombstones)         │
│ Latency             │ Depends on server RTT        │ Can be instant (local-first)    │
│ Proven at scale     │ Google Docs, Microsoft       │ Figma, newer systems            │
├─────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ Interview tip       │ Explain OT (simpler to explain)│ Mention CRDT as alternative    │
└─────────────────────┴───────────────────────────────┴─────────────────────────────────┘

FOR INTERVIEWS: I recommend explaining OT as primary approach (Google Docs uses it),
then mention CRDT as modern alternative (Figma).
```

---

# 5. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            GOOGLE DOCS / COLLABORATIVE EDITING ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
           ┌───────────────────────────────────────────────────────────────────────────┐
           │        Web (React)           iOS App            Android App              │
           │         │                       │                    │                   │
           │         └───────────────────────┼────────────────────┘                   │
           │                                 │                                        │
           │                    Local Editor (Quill/ProseMirror/Slate)               │
           │                    + Local Operation Queue                               │
           │                    + Offline Storage (IndexedDB)                         │
           └───────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ WebSocket (persistent connection)
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         WEBSOCKET GATEWAY                                   │
           │                                                                             │
           │   - Manages millions of persistent connections                             │
           │   - Routes operations to correct document session                          │
           │   - Handles heartbeat/ping-pong                                            │
           │   - Sticky sessions by document_id                                         │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         COLLABORATION SERVICE                               │
           │                                                                             │
           │   ┌─────────────────────────────────────────────────────────────────────┐ │
           │   │                    DOCUMENT SESSION                                  │ │
           │   │                                                                       │ │
           │   │   - One session per active document                                  │ │
           │   │   - Maintains current document state in memory                       │ │
           │   │   - Tracks connected clients + cursors                               │ │
           │   │   - Applies OT transformations                                        │ │
           │   │   - Broadcasts operations to all clients                             │ │
           │   │   - Periodically persists to database                                │ │
           │   │                                                                       │ │
           │   │   State:                                                              │ │
           │   │     - document_content: "Hello World..."                             │ │
           │   │     - revision: 1234                                                  │ │
           │   │     - pending_ops: [...]                                              │ │
           │   │     - clients: [{userId, cursorPos, color}, ...]                     │ │
           │   │                                                                       │ │
           │   └─────────────────────────────────────────────────────────────────────┘ │
           └─────────────────────────────────────────────────────────────────────────────┘
                                              │
           ┌──────────────────────────────────┼──────────────────────────────────────────┐
           │                                  │                                          │
           ▼                                  ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  DOCUMENT SERVICE   │  USER SERVICE       │  PERMISSION SERVICE │  VERSION SERVICE                 │
│                     │                     │                     │                                   │
│  - Create document  │  - Authentication   │  - ACL management   │  - Store revisions               │
│  - Load document    │  - User profiles    │  - Share links      │  - Restore versions              │
│  - Save document    │  - User settings    │  - Access checks    │  - Diff computation              │
│  - Delete document  │                     │                     │  - Compaction                    │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  COMMENT SERVICE    │  SEARCH SERVICE     │  NOTIFICATION SVC   │  EXPORT SERVICE                  │
│                     │                     │                     │                                   │
│  - Add comments     │  - Index documents  │  - Comment mentions │  - PDF generation                │
│  - Threads          │  - Full-text search │  - Share notifs     │  - Word export                   │
│  - Resolve          │  - Recent docs      │  - Edit alerts      │  - Markdown export               │
└─────────────────────┴─────────────────────┴─────────────────────┴───────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CACHE LAYER (REDIS)                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   DOCUMENT SESSION:                        PRESENCE:                                               │
│   doc:{id}:state = {content, revision}     doc:{id}:users = [                                     │
│   doc:{id}:ops_queue = [pending ops]         {userId, name, color, cursor_pos}                    │
│                                            ]                                                       │
│   ROUTING:                                                                                          │
│   doc:{id}:server = "collab-server-3"      USER STATE:                                            │
│   (which server handles this doc)          user:{id}:active_docs = ["doc1", "doc2"]               │
│                                                                                                     │
│   PERMISSIONS CACHE:                       RECENT DOCS:                                            │
│   doc:{id}:acl = {                         user:{id}:recent = [doc_ids...]                        │
│     owner: "user1",                                                                                 │
│     editors: ["user2"],                                                                             │
│     viewers: ["user3"]                                                                              │
│   }                                                                                                 │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                      │
│   │   POSTGRESQL        │   │     CASSANDRA       │   │  ELASTICSEARCH      │                      │
│   │   (Metadata)        │   │   (Operations Log)  │   │  (Search)           │                      │
│   ├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤                      │
│   │                     │   │                     │   │                     │                      │
│   │ • documents         │   │ • operations        │   │ • document content  │                      │
│   │ • users             │   │ • version_snapshots │   │ • title             │                      │
│   │ • permissions       │   │ • comments          │   │ • owner             │                      │
│   │ • folders           │   │                     │   │                     │                      │
│   │                     │   │ WHY:                │   │ Full-text search    │                      │
│   │ WHY:                │   │ • Append-only ops   │   │ across all docs     │                      │
│   │ • ACID for sharing  │   │ • Time-series       │   │                     │                      │
│   │ • Complex queries   │   │ • High write volume │   │                     │                      │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                      │
│                                                                                                     │
│   ┌─────────────────────┐                                                                           │
│   │   OBJECT STORAGE    │                                                                           │
│   │   (S3/GCS)          │                                                                           │
│   ├─────────────────────┤                                                                           │
│   │                     │                                                                           │
│   │ • Document snapshots│                                                                           │
│   │ • Embedded images   │                                                                           │
│   │ • Exported files    │                                                                           │
│   │                     │                                                                           │
│   └─────────────────────┘                                                                           │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 6. DATABASE SCHEMA

## Documents & Permissions

```sql
-- Documents metadata (PostgreSQL)
CREATE TABLE documents (
    document_id     UUID PRIMARY KEY,
    title           VARCHAR(500),
    owner_id        UUID NOT NULL REFERENCES users(user_id),
    folder_id       UUID REFERENCES folders(folder_id),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    is_deleted      BOOLEAN DEFAULT FALSE,
    current_revision BIGINT DEFAULT 0
);

-- Sharing & Permissions
CREATE TABLE document_permissions (
    permission_id   UUID PRIMARY KEY,
    document_id     UUID NOT NULL REFERENCES documents(document_id),
    user_id         UUID REFERENCES users(user_id),
    email           VARCHAR(255),  -- For pending invites
    access_level    VARCHAR(20) NOT NULL, -- owner, editor, commenter, viewer
    created_at      TIMESTAMP DEFAULT NOW(),
    created_by      UUID REFERENCES users(user_id),
    
    UNIQUE(document_id, user_id)
);

-- Share links (anyone with link)
CREATE TABLE share_links (
    link_id         UUID PRIMARY KEY,
    document_id     UUID NOT NULL REFERENCES documents(document_id),
    access_level    VARCHAR(20) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE,
    expires_at      TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

## Operations Log (Cassandra)

```sql
-- Append-only operations log
CREATE TABLE operations (
    document_id     UUID,
    revision        BIGINT,
    operation       TEXT,           -- JSON: {type, position, content, userId}
    user_id         UUID,
    created_at      TIMESTAMP,
    
    PRIMARY KEY ((document_id), revision)
) WITH CLUSTERING ORDER BY (revision ASC);

-- Periodic snapshots for fast loading
CREATE TABLE document_snapshots (
    document_id     UUID,
    revision        BIGINT,
    content         TEXT,           -- Full document content
    created_at      TIMESTAMP,
    
    PRIMARY KEY ((document_id), revision)
) WITH CLUSTERING ORDER BY (revision DESC);

-- Comments
CREATE TABLE comments (
    document_id     UUID,
    comment_id      UUID,
    thread_id       UUID,           -- For replies
    user_id         UUID,
    content         TEXT,
    anchor_start    INT,            -- Position in document
    anchor_end      INT,
    is_resolved     BOOLEAN,
    created_at      TIMESTAMP,
    
    PRIMARY KEY ((document_id), comment_id)
);
```

---

# 7. REQUEST FLOWS

## Flow 1: Open Document & Start Editing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OPEN DOCUMENT FLOW                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks on document link
           │
           ▼
1. AUTHENTICATE & AUTHORIZE
   
   - Validate JWT token
   - Check document_permissions table
   - Verify access level (view/edit/comment)
           │
           ▼
2. LOAD DOCUMENT STATE
   
   a) Find latest snapshot (revision 1000)
   
      SELECT content, revision FROM document_snapshots
      WHERE document_id = ? ORDER BY revision DESC LIMIT 1
   
   b) Apply operations since snapshot
   
      SELECT operation FROM operations
      WHERE document_id = ? AND revision > 1000
      ORDER BY revision ASC
   
   c) Result: Current document at revision 1050
           │
           ▼
3. ESTABLISH WEBSOCKET CONNECTION
   
   Client → WebSocket Gateway → Collaboration Service
   
   Join document session:
   {
     "type": "join",
     "documentId": "doc123",
     "userId": "user456",
     "revision": 1050
   }
           │
           ▼
4. SYNC STATE IF NEEDED
   
   If client's revision < server's revision:
     - Send missing operations to client
     - Client applies them locally
           │
           ▼
5. RECEIVE PRESENCE INFO
   
   Server broadcasts to client:
   {
     "type": "presence",
     "users": [
       { "id": "user789", "name": "Alice", "color": "#ff0000", "cursor": 150 }
     ]
   }
           │
           ▼
6. READY TO EDIT!
   
   Client renders document
   Shows other users' cursors
   Enables editing (if has permission)
```

---

## Flow 2: User Types a Character (Core OT Flow)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TYPING / EDITING FLOW (OT)                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User types "X" at position 10
           │
           ▼
1. LOCAL APPLICATION (Optimistic)
   
   - Apply immediately to local document
   - User sees their change INSTANTLY (< 1ms)
   - Add to pending operations queue
   
   pendingOps.push({
     type: "insert",
     position: 10,
     content: "X",
     revision: 1050,  // Based on last known server revision
     clientSeq: 1
   })
           │
           ▼
2. SEND TO SERVER (WebSocket)
   
   {
     "type": "operation",
     "documentId": "doc123",
     "op": { "insert": "X", "position": 10 },
     "revision": 1050,
     "clientSeq": 1
   }
           │
           ▼
3. SERVER RECEIVES OPERATION
   
   Document Session:
   
   a) Check revision
      - Client says revision 1050
      - Server is at revision 1055 (5 ops happened since client synced)
   
   b) Transform against concurrent operations
      
      For each op in [1051, 1052, 1053, 1054, 1055]:
        clientOp = transform(clientOp, serverOp)
      
      Example:
        Client: insert("X", 10)
        Op 1051: insert("Y", 5)  ← Someone inserted before position 10
        
        Transform: insert("X", 10) → insert("X", 11)  ← Shift position!
   
   c) Apply transformed operation
      - Update document state
      - Increment revision to 1056
      - Store in operations log (Cassandra)
           │
           ▼
4. ACKNOWLEDGE TO SENDER
   
   {
     "type": "ack",
     "clientSeq": 1,
     "revision": 1056
   }
   
   Client removes from pending queue
           │
           ▼
5. BROADCAST TO OTHER CLIENTS
   
   To all other connected users:
   {
     "type": "operation",
     "op": { "insert": "X", "position": 11 },  // Transformed position!
     "revision": 1056,
     "userId": "user456"
   }
           │
           ▼
6. OTHER CLIENTS APPLY
   
   - Transform against their pending ops (if any)
   - Apply to local document
   - Update revision


HANDLING CLIENT'S PENDING OPS:

While waiting for ACK, if server sends new op:

Client state:
  - Confirmed revision: 1050
  - Pending ops: [A, B] (not yet ACKed)
  - Document includes A and B locally

Server sends op C at revision 1051:
  
  1. Transform C against pending ops
     C' = transform(transform(C, A), B)
  
  2. Apply C' to local document
  
  3. Transform pending ops against C
     A' = transform(A, C)
     B' = transform(B, C)
     
  4. Continue waiting for ACKs
```

---

## Flow 3: Cursor/Presence Updates

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CURSOR PRESENCE FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User moves cursor or selects text
           │
           ▼
1. DEBOUNCE LOCALLY (50ms)
   
   Don't send every keystroke/movement
   Bundle cursor updates
           │
           ▼
2. SEND CURSOR UPDATE
   
   {
     "type": "cursor",
     "documentId": "doc123",
     "userId": "user456",
     "position": 150,
     "selection": { "start": 150, "end": 160 }  // If selecting
   }
           │
           ▼
3. SERVER BROADCASTS (Low priority)
   
   To all other clients:
   {
     "type": "cursor_update",
     "userId": "user456",
     "name": "Bob",
     "color": "#00ff00",
     "position": 150,
     "selection": { "start": 150, "end": 160 }
   }
           │
           ▼
4. CLIENTS RENDER CURSORS
   
   - Show colored cursor at position
   - Show name label above cursor
   - Highlight selection range


OPTIMIZATION: Cursor updates are FIRE-AND-FORGET
  - No ACK needed
  - Can be dropped if network is slow
  - Lower priority than document operations
```

---

## Flow 4: Version History & Restore

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              VERSION HISTORY FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

STORING VERSIONS:

1. AUTOMATIC SNAPSHOTS
   
   Background job (every 100 operations or 5 minutes):
   
   - Take current document state
   - Store in document_snapshots table
   - Compress content (gzip)
   
2. OPERATION LOG (always)
   
   Every single operation stored in Cassandra
   Can replay from any snapshot


VIEWING VERSION HISTORY:

User clicks "Version History"
           │
           ▼
1. LOAD SNAPSHOT LIST
   
   SELECT revision, created_at, user_id
   FROM document_snapshots
   WHERE document_id = ?
   ORDER BY revision DESC
   LIMIT 50
   
   Group by: Today, Yesterday, Last 7 days, etc.
           │
           ▼
2. USER SELECTS VERSION
   
   Load that specific snapshot
   Show as read-only preview
   Highlight changes (diff) from current
           │
           ▼
3. RESTORE VERSION
   
   User clicks "Restore this version"
   
   a) Create operation: "replace_all"
      {
        type: "replace",
        content: <restored_content>,
        revision: current_revision + 1
      }
   
   b) Apply like normal operation
   
   c) All clients get the replacement


STORAGE OPTIMIZATION:

Problem: 10 billion documents × many versions = HUGE storage

Solution: Tiered retention
  - Last 24 hours: All snapshots (every 5 min)
  - Last 30 days: Hourly snapshots
  - Older: Daily snapshots
  
  + Always keep operation log (compact periodically)
```

---

## Flow 5: Offline Editing & Sync

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OFFLINE EDITING FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User goes offline while editing
           │
           ▼
1. DETECT OFFLINE
   
   - WebSocket disconnects
   - Navigator.onLine = false
   - Switch to offline mode
           │
           ▼
2. CONTINUE EDITING LOCALLY
   
   - Store operations in IndexedDB
   - Queue: [op1, op2, op3, ...]
   - Update local document state
   - Show "Offline - changes will sync" indicator
           │
           ▼
3. USER COMES BACK ONLINE
   
   - WebSocket reconnects
   - Send: "I was at revision 1050, here are my offline ops"
           │
           ▼
4. SERVER RECONCILIATION
   
   a) Server is now at revision 1070 (others edited while you were offline)
   
   b) Get all operations since 1050
   
   c) Transform your offline ops against server's ops
      
      Your ops: [A, B, C]
      Server ops: [X, Y, Z, ...]
      
      A' = transform(A, X, Y, Z, ...)
      B' = transform(B, X, Y, Z, ..., A')
      C' = transform(C, X, Y, Z, ..., A', B')
   
   d) Apply transformed ops to server
   
   e) Send merged state back to client
           │
           ▼
5. CLIENT UPDATES
   
   - Receive transformed operations
   - Update local state
   - Clear offline queue
   - Resume real-time sync


CONFLICT SCENARIOS:

Scenario 1: You edited paragraph, someone else deleted it
  - Your edits are lost (paragraph no longer exists)
  - Could show warning: "Your changes to deleted section were discarded"

Scenario 2: Both edited same paragraph
  - OT merges both changes
  - Result might be jumbled
  - User can undo/fix manually

BEST PRACTICE: Show merge preview for large offline changes
```

---

## Flow 6: Comments & Suggestions

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              COMMENTS FLOW                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User selects text and adds comment
           │
           ▼
1. CREATE COMMENT
   
   POST /documents/{id}/comments
   {
     "content": "This needs clarification",
     "anchor": { "start": 100, "end": 150 }
   }
           │
           ▼
2. STORE IN DATABASE
   
   INSERT INTO comments (
     document_id, comment_id, user_id,
     content, anchor_start, anchor_end
   )
           │
           ▼
3. BROADCAST TO COLLABORATORS
   
   WebSocket:
   {
     "type": "comment_added",
     "comment": { ... }
   }
           │
           ▼
4. RENDER HIGHLIGHT
   
   - Highlight anchored text
   - Show comment in sidebar
   - Update comment count


COMMENT ANCHORING CHALLENGE:

Problem: Document changes, but comments reference old positions

Original: "Hello World" (comment on "World" at 6-11)
Edit: "Hello Beautiful World" ("World" is now at 16-21)

Solution 1: Relative anchoring
  - Store: "after 'Hello ', anchor to 'World'"
  - Search for text pattern, not position

Solution 2: Update anchors on edit
  - When insert/delete happens
  - Shift all comment anchors accordingly

Solution 3: Marker-based
  - Insert invisible markers in document
  - Comments reference markers, not positions
  - Markers move with content
```

---

# 8. SCALING CONSIDERATIONS

## 8.1 WebSocket Scaling

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              WEBSOCKET SCALING                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHALLENGE:
  - 50 million concurrent connections
  - Each server can handle ~100K connections
  - Need 500+ WebSocket servers

SOLUTION: Sticky Sessions + Pub/Sub

1. ROUTING BY DOCUMENT
   
   hash(document_id) → server_id
   All users of same document → same server
   
   Redis: doc:{id}:server = "ws-server-42"

2. CROSS-SERVER MESSAGING
   
   If users on different servers (unlikely for same doc):
   
   User A (Server 1) → Redis Pub/Sub → User B (Server 2)
   
   Channel: doc:{document_id}

3. CONNECTION MANAGER
   
   class ConnectionManager:
     connections: Map<documentId, Set<WebSocket>>
     
     def broadcast(documentId, message):
       for ws in connections[documentId]:
         ws.send(message)


FAILOVER:

If WebSocket server crashes:
  1. Clients detect disconnect
  2. Reconnect to load balancer
  3. Routed to new server
  4. Re-join document session
  5. Sync from last known revision
```

---

## 8.2 Document Session Management

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SESSION MANAGEMENT                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

ACTIVE SESSION (in memory):

When document is being edited:
  - Full content loaded in RAM
  - Fast operation processing
  - Periodic save to database

INACTIVE SESSION:

When no one editing for 5 minutes:
  - Save final state to database
  - Clear from memory
  - Next open = load from database


GARBAGE COLLECTION:

Background process:
  - Scan for idle sessions (no activity 10 min)
  - Persist and evict
  - Free up memory


HOT DOCUMENTS:

Popular documents (100+ concurrent users):
  - Keep in memory always
  - Multiple servers (shard by user range)
  - Merge operations from all shards


COLD DOCUMENTS:

Old documents rarely opened:
  - Only in database (no memory)
  - Load on demand
  - Use snapshots for fast load
```

---

# 9. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GOOGLE DOCS TECH STACK                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ Client Editor          │ Quill / ProseMirror / Slate   │ Rich text editing                │
│ Client State           │ IndexedDB                     │ Offline storage                  │
│                        │                               │                                  │
│ Real-time Connection   │ WebSocket                     │ Bidirectional, low latency       │
│ WS Gateway             │ Socket.io / ws                │ Scalable connections             │
│                        │                               │                                  │
│ Collaboration Logic    │ OT library / Yjs (CRDT)       │ Conflict resolution              │
│ Session Management     │ Custom in-memory              │ Active document state            │
│                        │                               │                                  │
│ Metadata DB            │ PostgreSQL                    │ Documents, users, permissions    │
│ Operations DB          │ Cassandra                     │ Append-only, high write          │
│ Search                 │ Elasticsearch                 │ Full-text search                 │
│ Cache                  │ Redis                         │ Sessions, routing, presence      │
│                        │                               │                                  │
│ Object Storage         │ S3 / GCS                      │ Snapshots, images                │
│ CDN                    │ CloudFront                    │ Static assets                    │
│                        │                               │                                  │
│ Pub/Sub                │ Redis Pub/Sub / Kafka         │ Cross-server messaging           │
│ Background Jobs        │ Celery / SQS                  │ Snapshots, export                │
│                        │                               │                                  │
│ Monitoring             │ Prometheus / Grafana          │ Latency, connection count        │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

# 10. INTERVIEW TALKING POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. WHY OT OVER SIMPLE LOCKING?
   - Locking: Only one person edits at a time → Bad UX
   - OT: Everyone edits simultaneously → Good UX
   - OT transforms conflicting operations mathematically

2. WHY WEBSOCKET OVER HTTP POLLING?
   - Polling: 50ms latency impossible, wastes bandwidth
   - WebSocket: 5-10ms possible, bidirectional, efficient
   - Fallback to long-polling if WS blocked

3. HOW TO HANDLE LARGE DOCUMENTS?
   - Paginate content (load visible portion)
   - Lazy load images
   - Compress snapshots
   - Operation log compaction

4. HOW TO ENSURE CONSISTENCY?
   - Server is source of truth
   - Revision numbers for ordering
   - Transform all operations
   - ACK before removing from pending

5. OFFLINE SUPPORT?
   - IndexedDB for local storage
   - Queue operations while offline
   - Transform against server ops on reconnect
   - Merge and sync

6. WHY CASSANDRA FOR OPERATIONS?
   - Append-only (perfect for op log)
   - Time-ordered by revision
   - High write throughput
   - Horizontal scaling

7. CRDT ALTERNATIVE?
   - Mention as modern approach
   - Better offline support
   - No central server needed
   - Used by Figma
   - Trade-off: More storage
```

---

# 11. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    GOOGLE DOCS / COLLABORATION CHEAT SHEET                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONFLICT RESOLUTION:
  • OT: Transform operations on server, converge
  • CRDT: Unique IDs, merge anywhere, auto-converge
  • Either works; OT more common (Google), CRDT newer (Figma)

REAL-TIME SYNC:
  • WebSocket for persistent connection
  • Operations sent as they happen
  • ACK before removing from pending queue
  • Cursor updates = fire-and-forget (low priority)

DOCUMENT LOADING:
  • Snapshots (every N ops) + replay recent ops
  • Full op log for version history
  • Tiered retention for storage

OFFLINE:
  • IndexedDB for local ops queue
  • Transform against server on reconnect
  • May lose some changes if conflict

SCALING:
  • Sticky sessions by document_id
  • Redis Pub/Sub for cross-server
  • Active sessions in memory, cold in DB
  • ~100K connections per WS server

PRESENCE:
  • Cursor position + selection
  • User name + color
  • Broadcast to all collaborators
  • Debounce for efficiency
```

---
