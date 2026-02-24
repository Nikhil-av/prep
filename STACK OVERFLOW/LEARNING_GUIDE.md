# 📢 STACK OVERFLOW — Q&A Platform — Complete LLD Guide
## From Zero to Interview-Ready

---

## 📖 Table of Contents
1. [Problem Statement](#-problem-statement)
2. [Clarifying Questions](#-clarifying-questions)
3. [Requirements](#-requirements)
4. [The Key Insight: Voteable ABC](#-the-key-insight)
5. [Complete Class Design with Code](#-complete-class-design)
6. [Vote Toggling Logic — The Tricky Part](#-vote-toggling)
7. [Reputation System](#-reputation-system)
8. [Design Patterns](#-design-patterns)
9. [Full Working Implementation](#-full-implementation)
10. [Follow-Up Questions (15+)](#-follow-up-questions)
11. [Quick Recall Script](#-quick-recall)

---

## 🎯 Problem Statement

> Design a **Stack Overflow-like Q&A platform** where users post questions, answer them, vote (upvote/downvote), comment, tag questions, earn reputation, and accept answers.

**Why this is asked:**
- Tests **Abstract Base Class** design — Voteable shared by Question AND Answer
- Tests **vote toggling** — the most common bug in this problem
- Tests **reputation system** — event-driven score calculation
- Tests understanding of **composition** (Question has Tags, Answers, Comments)

---

## 🗣️ Clarifying Questions

<details>
<summary>👀 Click to reveal</summary>

| # | Question | Answer |
|---|----------|--------|
| 1 | "Who can vote?" | Any registered user (except on own posts) |
| 2 | "Voting behavior: upvote twice = undo?" | Yes — toggle behavior |
| 3 | "Accept answer — who can?" | Only question author |
| 4 | "Multiple accepted answers?" | No — only ONE per question |
| 5 | "Reputation system?" | +10 upvote, -2 downvote, +15 accepted answer |
| 6 | "Tags?" | Many-to-many: question has multiple tags |
| 7 | "Comments on answers?" | Yes — simple text, no voting |
| 8 | "Search?" | By keyword, by tag |
| 9 | "Edit history?" | Mention as extension |
| 10 | "Can you self-vote?" | No — validate and reject |

</details>

---

## ✅ Requirements

| # | FR | Priority |
|---|-----|---------|
| 1 | Users register with username/email | Must |
| 2 | Post questions with title, body, tags | Must |
| 3 | Post answers to questions | Must |
| 4 | **Upvote/Downvote on questions AND answers** | Must |
| 5 | **Vote toggling** (same vote = undo, opposite = switch) | Must |
| 6 | Accept one answer per question | Must |
| 7 | Reputation tracking | Must |
| 8 | Comment on questions and answers | Should |
| 9 | Search by keyword/tag | Should |

---

## 🔥 The Key Insight: Voteable ABC

### 🤔 THINK: Questions can be voted on. Answers can be voted on. They share IDENTICAL voting logic. How to avoid code duplication?

<details>
<summary>👀 Click to reveal — Abstract Base Class!</summary>

```python
from abc import ABC, abstractmethod
from datetime import datetime

class Voteable(ABC):
    """
    Shared voting behavior for BOTH Questions AND Answers.
    
    WHY ABC? Vote toggling is complex (3 cases). If you write it
    in both Question and Answer, you WILL have bugs in one of them.
    One place for voting logic = one place for bugs = easier to fix.
    """
    
    def __init__(self):
        self.votes: dict[int, int] = {}  # user_id → +1 or -1
        self.score = 0
    
    def vote(self, user_id: int, vote_type: int) -> str:
        """
        Handle ALL voting scenarios:
        1. New vote → add it
        2. Same vote again → UNDO it
        3. Opposite vote → SWITCH it
        """
        if user_id == self.get_author_id():
            return "❌ Cannot vote on your own post!"
        
        current_vote = self.votes.get(user_id)
        
        if current_vote is None:
            # Case 1: NEW VOTE
            self.votes[user_id] = vote_type
            self.score += vote_type
            return f"{'👍' if vote_type > 0 else '👎'} Vote recorded (score: {self.score})"
        
        elif current_vote == vote_type:
            # Case 2: SAME VOTE → UNDO
            del self.votes[user_id]
            self.score -= vote_type
            return f"↩️ Vote undone (score: {self.score})"
        
        else:
            # Case 3: OPPOSITE VOTE → SWITCH
            self.score -= current_vote  # Remove old
            self.votes[user_id] = vote_type
            self.score += vote_type     # Add new (net change = 2)
            return f"🔄 Vote switched (score: {self.score})"
    
    @abstractmethod
    def get_author_id(self) -> int:
        pass
```

**This is Template Method pattern:** The voting FLOW is fixed in the ABC. Only `get_author_id()` varies by subclass.

</details>

---

## 🔄 Vote Toggling Logic — Step by Step

### 🤔 THINK: User A upvotes, then upvotes again, then downvotes. Trace the score.

<details>
<summary>👀 Click to reveal — This is THE interview trap</summary>

```
Initial state: score=0, votes={}

Action: User A UPVOTES (+1)
  → Case 1 (new vote)
  → votes = {A: +1}, score = 1

Action: User A UPVOTES (+1) again  
  → Case 2 (same vote = UNDO)
  → votes = {}, score = 0

Action: User A DOWNVOTES (-1)
  → Case 1 (new vote — was removed)
  → votes = {A: -1}, score = -1

Action: User A UPVOTES (+1)
  → Case 3 (opposite = SWITCH)
  → Remove old: score = -1 - (-1) = 0
  → Add new: score = 0 + 1 = 1
  → votes = {A: +1}, score = 1

Action: User B UPVOTES (+1)
  → Case 1 (new vote)
  → votes = {A: +1, B: +1}, score = 2
```

**Most common bug:** Not handling Case 2 (undo) or Case 3 (switch). Most candidates only handle Case 1 (new vote), which fails when users toggle their votes.

**Why dict[user_id, vote_type]?**
- Prevents double-voting (one vote per user)
- Enables undo (check current_vote)
- Enables switch (know the OLD direction)

</details>

---

## 🏆 Reputation System

### 🤔 THINK: How does Stack Overflow's reputation work?

<details>
<summary>👀 Click to reveal — Event-driven scoring</summary>

```python
REPUTATION_RULES = {
    "question_upvoted":       +10,   # Author of question gets +10
    "question_downvoted":     -2,    # Author of question gets -2
    "answer_upvoted":         +10,   # Author of answer gets +10
    "answer_downvoted":       -2,    # Author of answer gets -2
    "answer_accepted":        +15,   # Answerer gets +15
    "accepted_someone":       +2,    # Questioner gets +2 for accepting
    "downvoted_someone":      -1,    # YOU lose -1 for downvoting others
}
```

**Key subtleties:**
1. **Downvoting costs the voter -1** → discourages random downvoting
2. **Accepted answer = +15** (biggest single gain)
3. **Reputation never goes below 1**
4. **Minimum reputation to perform actions:**
   - 15 rep → upvote
   - 50 rep → comment
   - 125 rep → downvote
   - 1500 rep → create tags

```python
class User:
    def __init__(self, user_id: int, username: str, email: str):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.reputation = 1  # Starts at 1, never below 1
        self.questions: list['Question'] = []
        self.answers: list['Answer'] = []
    
    def update_reputation(self, amount: int):
        self.reputation = max(1, self.reputation + amount)
    
    def __str__(self):
        return f"👤 {self.username} (rep: {self.reputation})"
```

</details>

---

## 🏗️ Complete Class Design

### Tag, Comment

```python
class Tag:
    def __init__(self, name: str, description: str = ""):
        self.name = name.lower()
        self.description = description
    
    def __str__(self):
        return f"[{self.name}]"
    
    def __hash__(self): return hash(self.name)
    def __eq__(self, other): return isinstance(other, Tag) and self.name == other.name

class Comment:
    _counter = 0
    def __init__(self, text: str, author: User):
        Comment._counter += 1
        self.comment_id = Comment._counter
        self.text = text
        self.author = author
        self.created_at = datetime.now()
```

### Question (extends Voteable)

```python
class Question(Voteable):
    _counter = 0
    
    def __init__(self, title: str, body: str, author: User, tags: list[Tag]):
        super().__init__()
        Question._counter += 1
        self.question_id = Question._counter
        self.title = title
        self.body = body
        self.author = author
        self.tags = tags
        self.answers: list['Answer'] = []
        self.comments: list[Comment] = []
        self.accepted_answer: 'Answer' = None
        self.created_at = datetime.now()
        self.is_closed = False
    
    def get_author_id(self) -> int:
        return self.author.user_id
    
    def accept_answer(self, answer: 'Answer', accepted_by: User) -> bool:
        if accepted_by.user_id != self.author.user_id:
            print("   ❌ Only question author can accept!")
            return False
        if self.accepted_answer:
            # Un-accept previous
            self.accepted_answer.is_accepted = False
        self.accepted_answer = answer
        answer.is_accepted = True
        return True
    
    def get_sorted_answers(self, sort_by: str = "votes") -> list['Answer']:
        """Accepted answer ALWAYS first, then sorted."""
        answers = list(self.answers)
        if sort_by == "votes":
            answers.sort(key=lambda a: (-a.is_accepted, -a.score))
        elif sort_by == "newest":
            answers.sort(key=lambda a: (-a.is_accepted, -a.created_at.timestamp()))
        return answers
    
    def __str__(self):
        tags_str = " ".join(str(t) for t in self.tags)
        accepted = " ✅" if self.accepted_answer else ""
        return (f"❓ [{self.score}] {self.title} ({len(self.answers)} answers){accepted}\n"
                f"   Tags: {tags_str} | by {self.author.username}")
```

### Answer (extends Voteable)

```python
class Answer(Voteable):
    _counter = 0
    
    def __init__(self, body: str, author: User, question: Question):
        super().__init__()
        Answer._counter += 1
        self.answer_id = Answer._counter
        self.body = body
        self.author = author
        self.question = question
        self.comments: list[Comment] = []
        self.is_accepted = False
        self.created_at = datetime.now()
    
    def get_author_id(self) -> int:
        return self.author.user_id
    
    def __str__(self):
        accepted = " ✅ ACCEPTED" if self.is_accepted else ""
        return f"   💬 [{self.score}] by {self.author.username}{accepted}: {self.body[:80]}..."
```

---

## 🔧 Full Working Implementation

```python
import threading

class StackOverflowSystem:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        self._initialized = True
        self.users: dict[int, User] = {}
        self.questions: dict[int, Question] = {}
        self.tags: dict[str, Tag] = {}
        self._lock = threading.Lock()
    
    def register_user(self, user_id, username, email):
        user = User(user_id, username, email)
        self.users[user_id] = user
        return user
    
    def post_question(self, user_id, title, body, tag_names):
        user = self.users[user_id]
        tags = [self._get_or_create_tag(name) for name in tag_names]
        question = Question(title, body, user, tags)
        self.questions[question.question_id] = question
        user.questions.append(question)
        print(f"   ✅ Question posted: {question}")
        return question
    
    def post_answer(self, user_id, question_id, body):
        user = self.users[user_id]
        question = self.questions[question_id]
        answer = Answer(body, user, question)
        question.answers.append(answer)
        user.answers.append(answer)
        print(f"   ✅ Answer posted by {user.username}")
        return answer
    
    def vote_question(self, voter_id, question_id, vote_type):
        voter = self.users[voter_id]
        question = self.questions[question_id]
        result = question.vote(voter_id, vote_type)
        print(f"   {result}")
        
        # Update reputations
        if "recorded" in result or "switched" in result:
            question.author.update_reputation(
                REPUTATION_RULES["question_upvoted"] if vote_type > 0
                else REPUTATION_RULES["question_downvoted"])
            if vote_type < 0:
                voter.update_reputation(REPUTATION_RULES["downvoted_someone"])
    
    def vote_answer(self, voter_id, question_id, answer_id, vote_type):
        question = self.questions[question_id]
        answer = next(a for a in question.answers if a.answer_id == answer_id)
        result = answer.vote(voter_id, vote_type)
        print(f"   {result}")
        
        if "recorded" in result or "switched" in result:
            answer.author.update_reputation(
                REPUTATION_RULES["answer_upvoted"] if vote_type > 0
                else REPUTATION_RULES["answer_downvoted"])
    
    def accept_answer(self, user_id, question_id, answer_id):
        question = self.questions[question_id]
        user = self.users[user_id]
        answer = next(a for a in question.answers if a.answer_id == answer_id)
        
        if question.accept_answer(answer, user):
            answer.author.update_reputation(REPUTATION_RULES["answer_accepted"])
            user.update_reputation(REPUTATION_RULES["accepted_someone"])
            print(f"   ✅ Answer by {answer.author.username} accepted!")
    
    def search_by_keyword(self, keyword):
        kw = keyword.lower()
        return [q for q in self.questions.values()
                if kw in q.title.lower() or kw in q.body.lower()]
    
    def search_by_tag(self, tag_name):
        return [q for q in self.questions.values()
                if any(t.name == tag_name.lower() for t in q.tags)]
    
    def _get_or_create_tag(self, name):
        name = name.lower()
        if name not in self.tags:
            self.tags[name] = Tag(name)
        return self.tags[name]


# ══════════ DEMO ══════════

if __name__ == "__main__":
    print("=" * 60)
    print("     STACK OVERFLOW SYSTEM - COMPLETE DEMO")
    print("=" * 60)
    
    so = StackOverflowSystem()
    
    alice = so.register_user(1, "alice_dev", "alice@mail.com")
    bob = so.register_user(2, "bob_coder", "bob@mail.com")
    carol = so.register_user(3, "carol_js", "carol@mail.com")
    
    print("\n--- Post Question ---")
    q = so.post_question(1, "How to reverse a linked list?",
                         "I need to reverse a singly linked list in Python...",
                         ["python", "linked-list", "algorithms"])
    
    print("\n--- Post Answers ---")
    a1 = so.post_answer(2, q.question_id, "Use iterative approach with 3 pointers: prev, curr, next...")
    a2 = so.post_answer(3, q.question_id, "Recursive approach: def reverse(head): ...")
    
    print("\n--- Vote Toggling Demo ---")
    so.vote_answer(1, q.question_id, a1.answer_id, +1)   # Alice upvotes Bob's answer
    so.vote_answer(1, q.question_id, a1.answer_id, +1)   # Alice upvotes again → UNDO
    so.vote_answer(1, q.question_id, a1.answer_id, -1)   # Alice downvotes → new vote
    so.vote_answer(1, q.question_id, a1.answer_id, +1)   # Alice upvotes → SWITCH
    so.vote_answer(3, q.question_id, a1.answer_id, +1)   # Carol upvotes
    
    print(f"\n   Final score of Bob's answer: {a1.score}")
    
    print("\n--- Self-Vote Prevention ---")
    so.vote_question(1, q.question_id, +1)  # Alice tries to upvote own question
    
    print("\n--- Accept Answer ---")
    so.accept_answer(1, q.question_id, a1.answer_id)
    
    print("\n--- Sorted Answers ---")
    for a in q.get_sorted_answers():
        print(f"   {a}")
    
    print("\n--- Reputation ---")
    for u in [alice, bob, carol]:
        print(f"   {u}")
    
    print("\n--- Search by Tag ---")
    results = so.search_by_tag("python")
    print(f"   Found {len(results)} questions tagged [python]")
    
    print("\n" + "=" * 60)
```

---

## 🎤 Interviewer Follow-Up Questions (15+)

### Q1: "How to add bounties?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Bounty:
    def __init__(self, question, amount, offered_by, expires_in_days=7):
        self.question = question
        self.amount = amount  # Deducted immediately from offerer
        self.offered_by = offered_by
        self.expires_at = datetime.now() + timedelta(days=expires_in_days)
    
    def award(self, answer):
        answer.author.update_reputation(self.amount)
```
Bounty amount deducted from offerer's rep immediately (non-refundable).

</details>

### Q2: "How to implement edit history?"

<details>
<summary>👀 Click to reveal</summary>

```python
class EditHistory:
    def __init__(self):
        self.versions: list[tuple[str, datetime, User]] = []
    
    def add_version(self, content, editor):
        self.versions.append((content, datetime.now(), editor))

# Add to Question/Answer:
# self.edit_history = EditHistory()
```

</details>

### Q3-15 (Quick)

| Q | Question | Key Answer |
|---|----------|-----------|
| 3 | "Duplicate question detection?" | Compare title similarity + suggest existing |
| 4 | "Close/reopen questions?" | Status enum: OPEN, CLOSED, DUPLICATE + vote to close |
| 5 | "Minimum rep for actions?" | 15=upvote, 50=comment, 125=downvote, 1500=create tag |
| 6 | "Badge system?" | Badge entity + rules (e.g., first answer, 100 votes) |
| 7 | "Why ABC for Voteable?" | DRY — vote toggling in ONE place, used by both Question and Answer |
| 8 | "Why -1 rep for downvoting?" | Discourages random/malicious downvoting |
| 9 | "Accepted answer sort order?" | Always first, regardless of score |
| 10 | "Rate limiting?" | Max 1 question per 10 min, prevent spam |
| 11 | "Markdown rendering?" | Separate concern — UI layer, not LLD |
| 12 | "Comment vs Answer?" | Comments: short, no voting. Answers: full, voteable |
| 13 | "Concurrency?" | Lock on vote() — two users voting simultaneously |
| 14 | "Compare with Coursera?" | Both have Users+Content, but SO has voting/reputation |
| 15 | "How to test vote toggling?" | Unit test all 3 cases: new, undo, switch — with score assertions |

---

## 🧠 Quick Recall Script

> **First 30 seconds:**
> "**Voteable ABC** shared by Question and Answer. `votes: dict[user_id, ±1]`, `score: int`. Vote toggling handles 3 cases: new, undo (same button again), switch (opposite). Prevents self-voting via `get_author_id()` check."

> **If they ask about reputation:**
> "+10 upvote, -2 downvote, +15 accepted answer, -1 for casting downvote. Never below 1. Min rep thresholds for actions."

> **If they ask about patterns:**
> "**ABC/Template Method** for Voteable. **Singleton** for system. **Strategy** for search (keyword vs tag). Tags are many-to-many with questions via list."

---

## ✅ Pre-Implementation Checklist

- [ ] Voteable ABC (votes dict, score, vote() with 3 cases, get_author_id())
- [ ] Self-vote prevention
- [ ] Question extends Voteable (title, body, author, tags, answers, accepted_answer)
- [ ] Answer extends Voteable (body, author, question, is_accepted)
- [ ] Comment (text, author — no voting)
- [ ] Tag (name, __hash__, __eq__)
- [ ] User (reputation, update_reputation, questions, answers)
- [ ] Reputation rules dict
- [ ] accept_answer() — only by question author, only one accepted
- [ ] get_sorted_answers() — accepted first, then by score
- [ ] Search by keyword and by tag
- [ ] Demo: post, vote toggle (3 cases), self-vote block, accept, search

---

*Version 3.0 — Truly Comprehensive Edition*
