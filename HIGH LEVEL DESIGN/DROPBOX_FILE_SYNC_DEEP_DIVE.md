# Dropbox / File Sync — Complete Deep Dive

> Interview-ready documentation — Covers Google Drive, OneDrive, iCloud, any Cloud Storage

---

# 1. FUNCTIONAL REQUIREMENTS

## Feature List

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 1 | **File Upload** | P0 | Upload files of any size |
| 2 | **File Download** | P0 | Download files to local device |
| 3 | **Auto-Sync** | P0 | Sync files automatically across devices |
| 4 | **Folder Structure** | P0 | Create, rename, delete folders |
| 5 | **File Versioning** | P1 | Keep version history, restore |
| 6 | **Sharing** | P1 | Share files/folders with others |
| 7 | **Conflict Resolution** | P0 | Handle concurrent edits |
| 8 | **Offline Access** | P1 | Mark files for offline use |
| 9 | **Selective Sync** | P2 | Choose which folders to sync |
| 10 | **Search** | P1 | Search files by name, content |
| 11 | **Deduplication** | P2 | Don't store duplicate files twice |
| 12 | **Resume Upload** | P1 | Resume interrupted uploads |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| File change detection | < 1 sec | Near real-time sync |
| Small file sync | < 5 sec | Quick for documents |
| Large file (1GB) | Network limited | Optimize bandwidth |
| Metadata operations | < 100ms | Folder list, rename |

## Throughput

| Metric | Value |
|--------|-------|
| Total users | 700 million |
| DAU | 100 million |
| Files stored | 1 trillion |
| Storage | 2 exabytes (2,000 PB) |
| Uploads/day | 1 billion files |
| API calls/sec | 1 million |

## Availability

| Component | Target |
|-----------|--------|
| Upload/Download | 99.99% |
| Sync service | 99.9% |
| Storage durability | 99.999999999% (11 9s) |

---

# 3. THE CORE PROBLEMS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY CHALLENGES IN FILE SYNC                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHALLENGE 1: LARGE FILE HANDLING
  - User uploads 10GB video
  - Can't upload in single request (timeout, memory)
  - Network interruption = start over?

CHALLENGE 2: EFFICIENT SYNC
  - User edits 1 line in 100MB file
  - Re-upload entire 100MB? Wasteful!
  - Need to detect and sync only CHANGES

CHALLENGE 3: CONFLICT RESOLUTION
  - User edits file on laptop (offline)
  - Same file edited on phone
  - Both come online - which version wins?

CHALLENGE 4: STORAGE EFFICIENCY
  - 1 million users upload same popular song
  - Store 1 million copies? Wasteful!
  - Deduplication saves 99% storage

CHALLENGE 5: SCALABILITY
  - 1 trillion files
  - 1 billion uploads/day
  - Can't have central bottleneck
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 DROPBOX / FILE SYNC ARCHITECTURE                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                       DESKTOP CLIENT
           ┌───────────────────────────────────────────────────────────────────────────┐
           │                                                                           │
           │   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌───────────┐   │
           │   │  Watcher    │   │  Chunker    │   │  Indexer    │   │  Sync     │   │
           │   │  Service    │   │  Service    │   │  Service    │   │  Engine   │   │
           │   ├─────────────┤   ├─────────────┤   ├─────────────┤   ├───────────┤   │
           │   │ Monitors    │   │ Splits file │   │ Local DB    │   │ Upload/   │   │
           │   │ file system │   │ into chunks │   │ of metadata │   │ Download  │   │
           │   │ for changes │   │             │   │             │   │ logic     │   │
           │   └─────────────┘   └─────────────┘   └─────────────┘   └───────────┘   │
           │                                                                           │
           │   LOCAL DATABASE (SQLite):                                                │
           │   - file_path, checksum, modified_time, sync_status                       │
           │   - chunk_id, chunk_hash, uploaded                                        │
           │                                                                           │
           └───────────────────────────────────────────────────────────────────────────┘
                              │                              │
                              │ Metadata API (HTTPS)         │ Block API (HTTPS)
                              ▼                              ▼
           ┌────────────────────────────────────────────────────────────────────────────┐
           │                            LOAD BALANCER                                   │
           └────────────────────────────────────────────────────────────────────────────┘
                              │                              │
           ┌──────────────────┴──────────────────┐           │
           ▼                                     ▼           ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    API LAYER                                                        │
├─────────────────────────────────────┬───────────────────────────────────────────────────────────────┤
│        METADATA SERVICE             │              BLOCK SERVICE                                   │
│                                     │                                                               │
│  - File/folder CRUD                 │  - Upload chunks                                              │
│  - Get file list                    │  - Download chunks                                            │
│  - Version history                  │  - Check chunk existence                                      │
│  - Sharing permissions              │  - Deduplication                                              │
│                                     │                                                               │
│  Endpoints:                         │  Endpoints:                                                   │
│  - GET  /files/{path}               │  - PUT  /blocks/{hash}                                       │
│  - POST /files/{path}               │  - GET  /blocks/{hash}                                       │
│  - PUT  /files/{path}/commit        │  - HEAD /blocks/{hash}  (exists?)                            │
│  - GET  /delta                      │                                                               │
│                                     │                                                               │
└─────────────────────────────────────┴───────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CACHE LAYER (REDIS)                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   BLOCK EXISTENCE:                     USER SESSIONS:                                              │
│   block:{hash}:exists = 1              session:{token} = {user_id, ...}                           │
│   (Check before upload)                                                                            │
│                                        SYNC CURSORS:                                               │
│   FILE METADATA:                       user:{id}:cursor = "cursor_12345"                          │
│   file:{id}:meta = {                                                                                │
│     name, size, modified,              RATE LIMITS:                                                │
│     chunks: [hash1, hash2]             rate:{user_id}:{window} = count                            │
│   }                                                                                                 │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   ┌─────────────────────────────────────┐   ┌─────────────────────────────────────┐                │
│   │        POSTGRESQL (METADATA)        │   │         CASSANDRA (BLOCKS)          │                │
│   ├─────────────────────────────────────┤   ├─────────────────────────────────────┤                │
│   │                                     │   │                                     │                │
│   │  users                              │   │  blocks                             │                │
│   │  files (id, path, user, chunks)    │   │    block_hash → metadata            │                │
│   │  file_versions                      │   │    (size, ref_count, storage_key)  │                │
│   │  sharing_permissions                │   │                                     │                │
│   │  folders                            │   │  block_references                   │                │
│   │                                     │   │    file_id → [block_hashes]         │                │
│   │  ACID for file operations           │   │                                     │                │
│   │                                     │   │  High write throughput              │                │
│   └─────────────────────────────────────┘   └─────────────────────────────────────┘                │
│                                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐              │
│   │                          OBJECT STORAGE (S3)                                    │              │
│   ├─────────────────────────────────────────────────────────────────────────────────┤              │
│   │                                                                                 │              │
│   │   Blocks stored by content hash:                                                │              │
│   │   s3://dropbox-blocks/{hash[0:2]}/{hash[2:4]}/{hash}                           │              │
│   │                                                                                 │              │
│   │   Example: abc123def456... → s3://blocks/ab/c1/abc123def456...                 │              │
│   │                                                                                 │              │
│   │   - 11 9s durability                                                            │              │
│   │   - Automatic replication                                                       │              │
│   │   - Lifecycle policies (cold storage)                                           │              │
│   │                                                                                 │              │
│   └─────────────────────────────────────────────────────────────────────────────────┘              │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NOTIFICATION SERVICE                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   LONG POLLING / WEBSOCKET:                                                                         │
│   - Client connects and waits                                                                       │
│   - Server pushes when files change                                                                 │
│   - Client then calls /delta for changes                                                            │
│                                                                                                     │
│   Why not push actual changes?                                                                      │
│   - Changes can be large                                                                            │
│   - Notification = "something changed"                                                              │
│   - Client fetches details via API                                                                  │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. KEY ALGORITHMS

## 5.1 Chunking Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FILE CHUNKING                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

WHY CHUNK FILES?

1. Large files split into manageable pieces (4MB each)
2. Only upload changed chunks (not entire file)
3. Resume interrupted uploads
4. Deduplication across files


FIXED-SIZE CHUNKING (Simple):

  File: [===========================================] 100MB
  
  Split every 4MB:
  [====][====][====][====][====][====]...[==]
   4MB   4MB   4MB   4MB   4MB   4MB     2MB

  Problem: Insert 1 byte at beginning
  - ALL chunks shift!
  - Must re-upload everything


CONTENT-DEFINED CHUNKING (Better - Rabin Fingerprinting):

  Use rolling hash to find "natural" chunk boundaries
  
  Algorithm:
    for each byte position:
      hash = rolling_hash(window of N bytes)
      if hash % M == 0:  → This is a chunk boundary!
  
  Example:
    File content: "Hello World, this is a test document..."
    
    Rolling hash finds natural boundaries based on CONTENT
    Not fixed positions!

  Benefits:
    - Insert in middle → Only 1-2 chunks change
    - Similar files share chunks
    - Better deduplication


CHUNK STRUCTURE:

  ┌─────────────────────────────────┐
  │  Chunk                          │
  ├─────────────────────────────────┤
  │  hash: SHA256(content)          │  ← Content-addressable
  │  size: 4194304                  │
  │  data: <binary>                 │
  └─────────────────────────────────┘


FILE = LIST OF CHUNKS:

  File: presentation.pptx
  
  {
    file_id: "F123",
    path: "/work/presentation.pptx",
    size: 15728640,  // 15MB
    chunks: [
      { hash: "abc123...", offset: 0,       size: 4194304 },
      { hash: "def456...", offset: 4194304, size: 4194304 },
      { hash: "ghi789...", offset: 8388608, size: 4194304 },
      { hash: "jkl012...", offset: 12582912, size: 3145728 }
    ]
  }
```

---

## 5.2 Delta Sync Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DELTA SYNC                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO:
  User edits 100MB Word document
  Changes 1 paragraph (few KB)
  
  Naive: Re-upload 100MB
  Smart: Upload only changed chunks (~4MB)


DELTA SYNC FLOW:

1. USER SAVES FILE
   
   Watcher detects file change
     │
     ▼
2. CHUNK THE NEW FILE
   
   Old file chunks: [A, B, C, D, E]
   New file chunks: [A, B, C', D, E]  ← Only C changed!
     │
     ▼
3. COMPARE CHUNK HASHES
   
   Old: [hash_A, hash_B, hash_C, hash_D, hash_E]
   New: [hash_A, hash_B, hash_C', hash_D, hash_E]
   
   Different: [hash_C']
     │
     ▼
4. CHECK IF CHUNK EXISTS (HEAD request)
   
   HEAD /blocks/hash_C'
   
   404 → Need to upload
   200 → Already exists (dedup!)
     │
     ▼
5. UPLOAD ONLY NEW CHUNKS
   
   PUT /blocks/hash_C'
   Body: <chunk data>
     │
     ▼
6. COMMIT NEW FILE VERSION
   
   PUT /files/presentation.pptx/commit
   {
     chunks: [hash_A, hash_B, hash_C', hash_D, hash_E],
     modified: "2024-02-07T10:30:00Z"
   }


BANDWIDTH SAVINGS:

Before delta sync:
  Every edit = re-upload entire file

After delta sync:
  Average file: 4 chunks change (16MB)
  Average edit: 1 chunk changes (4MB)
  
  Savings: 75% bandwidth reduction!
```

---

## 5.3 Deduplication

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DEDUPLICATION                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONCEPT:
  Store each unique chunk ONCE
  Multiple files can reference same chunk


EXAMPLE:

User A uploads: song.mp3 (5MB)
  Chunks: [X, Y, Z]
  
User B uploads: same_song.mp3 (identical)
  Chunks: [X, Y, Z]  ← Same hashes!
  
Before upload:
  HEAD /blocks/X → 200 (exists)
  HEAD /blocks/Y → 200 (exists)
  HEAD /blocks/Z → 200 (exists)
  
Result: NOTHING uploaded! Just create file metadata.


REFERENCE COUNTING:

Block table in Cassandra:
  {
    hash: "abc123",
    size: 4194304,
    storage_key: "s3://blocks/ab/c1/abc123",
    ref_count: 15000  ← 15000 files reference this block!
  }

When file deleted:
  - Decrement ref_count
  - If ref_count = 0 → Delete from S3


DEDUP LEVELS:

1. FILE-LEVEL DEDUP
   - Hash entire file
   - Exact duplicates only
   - Simple but limited
   
2. CHUNK-LEVEL DEDUP (Dropbox uses this)
   - Hash each chunk
   - Similar files share chunks
   - Much better savings
   
3. BYTE-LEVEL DEDUP
   - Very granular
   - Complex, CPU intensive
   - Rarely used


STORAGE SAVINGS:

Without dedup: 2 EB (exabytes)
With dedup:    ~400 PB

Savings: 80% storage reduction!
```

---

## 5.4 Conflict Resolution

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONFLICT RESOLUTION                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCENARIO:
  User on laptop (offline): Edits doc.txt → Version A
  User on phone (offline): Edits doc.txt → Version B
  Both come online → CONFLICT!


DROPBOX STRATEGY: "Conflicted Copy"

1. First sync wins
   - Laptop comes online first
   - Uploads Version A → Becomes server version
   
2. Second device sees conflict
   - Phone tries to upload Version B
   - Server says: "Wait, you're behind!"
   
3. Create conflicted copy
   - Keep server version (A) as doc.txt
   - Save phone version as:
     "doc (User's conflicted copy 2024-02-07).txt"
   
4. User manually resolves
   - User sees both files
   - Decides which to keep
   - Deletes the other


ALTERNATIVE: Last-Write-Wins (Google Drive)

  - Whichever sync happens last overwrites
  - Version history keeps old versions
  - Less confusing UX
  - Risk: Silent data loss


CONFLICT DETECTION:

Client tracks:
  - local_version: Last known server version
  - server_version: Current server version

On sync:
  if local_version < server_version:
    → Someone else changed file!
    → Check if our changes overlap
    → If yes: Conflict!
    → If no: Three-way merge possible


OPTIMISTIC LOCKING:

Commit request includes expected version:
  PUT /files/doc.txt/commit
  {
    expected_version: 5,
    new_chunks: [...]
  }

Server:
  if current_version != 5:
    → 409 Conflict response
    → Client must handle
```

---

# 6. REQUEST FLOWS

## Flow 1: File Upload

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FILE UPLOAD FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User drags file to Dropbox folder
           │
           ▼
1. WATCHER DETECTS CHANGE (OS File System Events)
   
   macOS: FSEvents
   Windows: ReadDirectoryChangesW
   Linux: inotify
           │
           ▼
2. CHUNKER SPLITS FILE
   
   Using content-defined chunking (Rabin fingerprint)
   
   Result: [chunk1, chunk2, chunk3, ...]
   Each chunk: { hash: SHA256, data: bytes, size: int }
           │
           ▼
3. CHECK WHICH CHUNKS EXIST
   
   For each chunk:
     HEAD /blocks/{hash}
     
   Batch API for efficiency:
     POST /blocks/check
     { hashes: [hash1, hash2, hash3, ...] }
     
   Response:
     { exists: [hash1, hash3], missing: [hash2] }
           │
           ▼
4. UPLOAD MISSING CHUNKS
   
   For each missing chunk:
     PUT /blocks/{hash}
     Body: <chunk data>
     
   Parallel uploads (4-8 concurrent)
   With retry logic for failures
           │
           ▼
5. COMMIT FILE METADATA
   
   PUT /files/{path}/commit
   {
     path: "/Documents/report.pdf",
     size: 15728640,
     modified: "2024-02-07T10:30:00Z",
     chunks: [hash1, hash2, hash3, ...],
     checksum: "sha256:overall_file_hash"
   }
           │
           ▼
6. SERVER VALIDATES & STORES
   
   a) Verify all chunks exist
   b) Verify combined size matches
   c) Create file metadata record
   d) Store version history
   e) Increment block ref_counts
           │
           ▼
7. NOTIFY OTHER DEVICES
   
   Push notification to user's other devices:
   "New file: /Documents/report.pdf"
   
   Those devices call /delta to sync
```

---

## Flow 2: File Download

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FILE DOWNLOAD FLOW                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User's other device needs to sync new file
           │
           ▼
1. RECEIVE NOTIFICATION
   
   Long-polling or WebSocket:
   "Changes available at cursor X"
           │
           ▼
2. FETCH DELTA
   
   GET /delta?cursor=cursor_X
   
   Response:
   {
     entries: [
       { path: "/Documents/report.pdf", action: "add", file_id: "F123" }
     ],
     cursor: "cursor_Y",
     has_more: false
   }
           │
           ▼
3. GET FILE METADATA
   
   GET /files/F123/metadata
   
   Response:
   {
     file_id: "F123",
     path: "/Documents/report.pdf",
     size: 15728640,
     chunks: [hash1, hash2, hash3, ...]
   }
           │
           ▼
4. CHECK LOCAL CACHE
   
   For each chunk:
     Is chunk already downloaded locally?
     (Check local SQLite cache)
   
   Only download missing chunks
           │
           ▼
5. DOWNLOAD CHUNKS
   
   GET /blocks/{hash}
   
   Parallel downloads
   Write to temp file
           │
           ▼
6. ASSEMBLE FILE
   
   Concatenate chunks in order
   Verify checksum matches
   Move to final location
           │
           ▼
7. UPDATE LOCAL INDEX
   
   SQLite:
   INSERT INTO files (path, checksum, chunks, sync_status)
```

---

## Flow 3: Delta Sync (Edit Existing File)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DELTA SYNC FLOW                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User edits existing file (100MB document, changes 1 paragraph)
           │
           ▼
1. DETECT FILE CHANGE
   
   Watcher triggers: "/Documents/thesis.docx modified"
           │
           ▼
2. LOAD PREVIOUS CHUNK LIST
   
   From local SQLite:
   Previous chunks: [A, B, C, D, E, F, G, H, I, J]
           │
           ▼
3. RE-CHUNK MODIFIED FILE
   
   Using same algorithm (content-defined)
   New chunks: [A, B, C, D', E, F, G, H, I, J]
   
   Note: Only chunk D became D' (changed content)
           │
           ▼
4. COMPUTE DIFF
   
   Old: [A, B, C, D, E, F, G, H, I, J]
   New: [A, B, C, D', E, F, G, H, I, J]
   
   Added: [D']
   Removed: [D]
           │
           ▼
5. UPLOAD ONLY NEW CHUNK
   
   HEAD /blocks/D' → 404 (doesn't exist)
   PUT /blocks/D' → Upload 4MB
   
   9 chunks skipped! (already on server)
           │
           ▼
6. COMMIT NEW VERSION
   
   PUT /files/thesis.docx/commit
   {
     version: 15,
     chunks: [A, B, C, D', E, F, G, H, I, J],
     modified: "2024-02-07T12:00:00Z"
   }
           │
           ▼
7. SERVER UPDATES
   
   - Create new file version (v15)
   - Decrement ref_count for block D
   - Increment ref_count for block D'
   - Notify other devices


BANDWIDTH USED:

Without delta: 100MB
With delta: 4MB

Savings: 96%!
```

---

## Flow 4: Sharing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SHARING FLOW                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User shares folder with colleague
           │
           ▼
1. CREATE SHARING PERMISSION
   
   POST /sharing
   {
     path: "/Projects/Website",
     email: "colleague@example.com",
     access_level: "editor"  // viewer, editor
   }
           │
           ▼
2. LOOKUP USER
   
   Find user by email
   If not registered → Send invite email
           │
           ▼
3. STORE PERMISSION
   
   INSERT INTO sharing_permissions (
     folder_id, user_id, access_level, created_at
   )
           │
           ▼
4. NOTIFY RECIPIENT
   
   Email: "User shared 'Website' folder with you"
   Push notification if they have app
           │
           ▼
5. RECIPIENT SYNCS SHARED FOLDER
   
   Shared folder appears in their Dropbox
   Full sync triggered
   
   Blocks are NOT duplicated!
   Same blocks serve both users


SHARE LINKS:

Create public/private link:
  POST /sharing/links
  {
    path: "/Documents/report.pdf",
    access: "view_only",
    expires: "2024-03-01"
  }
  
  Response:
  { link: "https://dropbox.com/s/abc123/report.pdf" }


ACCESS CONTROL:

On every file operation:
1. Check user's permissions
2. Check parent folder permissions (inherited)
3. Check share link validity
4. Allow or deny
```

---

# 7. SCALING CONSIDERATIONS

## 7.1 Metadata Scaling

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              METADATA DB SCALING                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHALLENGE:
  - 1 trillion files
  - Complex queries (folder hierarchy, sharing)
  - Need consistency (no duplicate files)


POSTGRESQL SHARDING:

Shard by user_id:
  user_123 → shard_5
  user_456 → shard_12
  
  Hash(user_id) % num_shards = shard_id

Benefits:
  - User's files on same shard
  - Folder queries are local
  - Scale horizontally


CROSS-SHARD QUERIES:

Shared folders across users:
  - Store on both shards
  - Denormalize for reads
  - Event-driven sync for writes
```

---

## 7.2 Block Storage Scaling

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLOCK STORAGE SCALING                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

S3/GCS ORGANIZATION:

s3://dropbox-blocks/
  ├── ab/
  │   ├── c1/
  │   │   ├── abc123def456...
  │   │   └── abc1789xyz...
  │   └── c2/
  │       └── abc234...
  └── cd/
      └── ...

Prefix structure:
  - First 2 chars: bucket partition
  - Next 2 chars: subfolder
  - Prevents hot spots


STORAGE TIERS:

Hot (S3 Standard): Recent files
Warm (S3-IA): 30-90 days old
Cold (Glacier): > 90 days old

Automated lifecycle policies
```

---

# 8. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DROPBOX TECH STACK                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ Desktop Client         │ Python / Rust / C++           │ Cross-platform, performance      │
│ Local Database         │ SQLite                        │ Embedded, reliable              │
│ File Watcher           │ OS-native (fsevents, inotify) │ Efficient change detection      │
│                        │                               │                                  │
│ API Servers            │ Go / Python                   │ High throughput                 │
│ Metadata DB            │ PostgreSQL (sharded)          │ ACID, complex queries           │
│ Block References       │ Cassandra                     │ High write, scale               │
│ Cache                  │ Redis                         │ Block existence, sessions       │
│                        │                               │                                  │
│ Block Storage          │ S3 / Custom (Magic Pocket)    │ Durability, scale               │
│ CDN                    │ CloudFront                    │ Global download acceleration    │
│                        │                               │                                  │
│ Notifications          │ Long polling / WebSocket      │ Real-time sync triggers         │
│ Message Queue          │ Kafka                         │ Event-driven architecture       │
│                        │                               │                                  │
│ Search                 │ Elasticsearch                 │ File name, content search       │
│ Thumbnail/Preview      │ Custom workers                │ Image/doc previews              │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘

Note: Dropbox built their own storage system "Magic Pocket" 
to move off S3 (cost savings at scale)
```

---

# 9. INTERVIEW TALKING POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. WHY CHUNKING?
   - Large file handling
   - Delta sync (only upload changes)
   - Deduplication
   - Resume interrupted transfers

2. WHY CONTENT-DEFINED CHUNKING?
   - Fixed chunks shift on any edit
   - Content-defined finds natural boundaries
   - Edits affect fewer chunks
   - Better dedup hit rate

3. HOW DEDUP WORKS?
   - SHA256 hash of chunk content
   - Check existence before upload
   - Store once, reference many times
   - 80%+ storage savings

4. CONFLICT RESOLUTION?
   - Create "conflicted copy" files
   - User manually resolves
   - Alternative: Last-write-wins (Google)
   - Version history as safety net

5. WHY SEPARATE METADATA & BLOCK SERVICES?
   - Different scaling needs
   - Metadata: Complex queries, ACID
   - Blocks: Simple key-value, high throughput

6. HOW TO SYNC EFFICIENTLY?
   - Delta API returns changes since cursor
   - Push notifications trigger pull
   - Only fetch changed chunks
   - Parallel uploads/downloads

7. DURABILITY?
   - 11 9s (99.999999999%)
   - Multi-AZ replication
   - Erasure coding
   - Regular integrity checks
```

---

# 10. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    DROPBOX / FILE SYNC CHEAT SHEET                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHUNKING:
  • Content-defined (Rabin fingerprint)
  • ~4MB average chunk size
  • SHA256 hash for content addressing

DELTA SYNC:
  • Compare old vs new chunk lists
  • Upload only new/changed chunks
  • Typical savings: 70-95%

DEDUPLICATION:
  • Block-level (not file-level)
  • Check before upload (HEAD)
  • Reference counting for cleanup
  • ~80% storage savings

CONFLICT RESOLUTION:
  • Optimistic locking with version
  • Create "conflicted copy" on conflict
  • User manually resolves

ARCHITECTURE:
  • Metadata Service (PostgreSQL) - File structure
  • Block Service (S3 + Redis) - Actual data
  • Notification Service - Trigger sync

CLIENT COMPONENTS:
  • Watcher (file system events)
  • Chunker (split files)
  • Indexer (local state)
  • Sync Engine (upload/download)

SYNC TRIGGERS:
  • Local: File system watcher
  • Remote: Long polling / WebSocket notification
  • Cursor-based delta API
```

---
